"""
Bijou AI - WhatsApp Learning API
==================================

FastAPI router for managing WhatsApp chat-history import & AI analysis jobs.

Routes:
    POST  /api/learn/upload-history      — Upload a WA export file, kick off analysis
    GET   /api/learn/status/{job_id}     — Poll job status
    POST  /api/learn/apply/{job_id}      — Apply suggested templates/prompt from a completed job
    GET   /api/learn/insights            — List recent learning jobs (last 20)

All routes require the ``X-Tenant-ID`` request header.

Author: W3J Bijou AI
Version: 1.0.0
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.core.dashboard_api_simple import verify_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learn", tags=["learning"])

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME = "bijou-media"


def _get_supabase() -> Any:
    """Return an initialised Supabase service-role client."""
    from supabase import create_client  # type: ignore

    url = os.getenv("SUPABASE_URL", "").strip('"')
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip('"')
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


def _require_tenant(x_tenant_id: Optional[str]) -> str:
    """Raise HTTP 401 if the tenant header is missing."""
    if not x_tenant_id:
        raise HTTPException(
            status_code=401,
            detail="Missing required header: X-Tenant-ID",
        )
    return x_tenant_id


def _parse_wa_export(raw_text: str) -> List[Dict[str, str]]:
    """
    Parse a plain-text WhatsApp export into a list of message dicts.

    WhatsApp export lines look like:
        ``[DD/MM/YYYY, HH:MM:SS] Name: message body``
    or (without brackets):
        ``DD/MM/YYYY, HH:MM - Name: message body``

    Args:
        raw_text: Full plaintext content of the exported chat file.

    Returns:
        List of dicts with keys: ``timestamp``, ``sender``, ``message``.
    """
    messages: List[Dict[str, str]] = []

    # Match both iOS (brackets) and Android (no brackets) WA export formats
    pattern = re.compile(
        r"[\[‎]?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}),?\s+"  # date
        r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)"          # time
        r"[\]‎]?\s*[-–]\s*"                                   # separator
        r"([^:]+):\s*"                                        # sender name
        r"(.+)"                                               # message body
    )

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            date_str, time_str, sender, body = match.groups()
            messages.append(
                {
                    "timestamp": f"{date_str} {time_str}",
                    "sender": sender.strip(),
                    "message": body.strip(),
                }
            )

    return messages


async def process_wa_history(
    job_id: str,
    tenant_id: str,
    file_content: str,
    supabase: Any,
) -> None:
    """
    Background task: analyse a WhatsApp export and update the learning job.

    Steps:
        1. Parse raw WA export text into structured messages.
        2. Send to Gemini for Q&A extraction, tone analysis, FAQ generation.
        3. Persist results via WALearningService.update_job_status().

    Args:
        job_id: UUID of the learning job to update.
        tenant_id: UUID of the owning tenant.
        file_content: Raw text content of the WA export file.
        supabase: Initialised Supabase client.
    """
    from src.saas.wa_learning_service import WALearningService

    service = WALearningService(supabase)

    try:
        logger.info(
            f"🔬 Starting WA history analysis for job {job_id} (tenant={tenant_id})"
        )

        # Step 1 — Parse messages
        messages = _parse_wa_export(file_content)
        raw_count = len(messages)
        logger.info(f"📊 Parsed {raw_count} messages from WA export")

        if raw_count == 0:
            await service.update_job_status(
                tenant_id=tenant_id,
                job_id=job_id,
                status="failed",
                error_message="No messages found in the uploaded file. "
                "Ensure you exported a WhatsApp chat as a plain .txt file.",
                completed_at=datetime.now().isoformat(),
            )
            return

        # Step 2 — Gemini analysis
        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip('"')
        qa_pairs: List[Dict[str, str]] = []
        tone_detected = "professional"
        suggested_prompt = ""
        suggested_templates: List[Dict[str, Any]] = []

        if gemini_api_key:
            try:
                import google.generativeai as genai  # type: ignore

                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")

                # Build a condensed conversation sample (max 200 messages to stay in context)
                sample = messages[:200]
                conversation_text = "\n".join(
                    f"[{m['sender']}]: {m['message']}" for m in sample
                )

                analysis_prompt = f"""You are an AI business analyst. Analyse this WhatsApp business chat history.

CONVERSATION SAMPLE ({len(sample)} of {raw_count} messages):
---
{conversation_text}
---

Return a JSON object with EXACTLY these keys:
{{
  "qa_pairs": [
    {{"question": "...", "answer": "..."}},
    ...
  ],
  "faq_count": <integer>,
  "tone_detected": "<one of: formal, semi-formal, casual, friendly, professional>",
  "suggested_system_prompt": "<a 2-3 sentence system prompt for an AI to match this business's communication style>",
  "suggested_templates": [
    {{"name": "...", "trigger_keywords": ["..."], "body": "..."}},
    ...
  ]
}}

Rules:
- Extract up to 15 Q&A pairs from real customer questions and business answers
- Suggest up to 5 message templates based on recurring questions
- Keep template bodies concise (under 200 chars)
- Respond ONLY with valid JSON, no markdown
"""

                response = model.generate_content(analysis_prompt)
                raw_json = response.text.strip()

                # Strip markdown code fences if present
                if raw_json.startswith("```"):
                    raw_json = re.sub(r"^```[a-z]*\n?", "", raw_json)
                    raw_json = re.sub(r"\n?```$", "", raw_json)

                import json

                parsed = json.loads(raw_json)
                qa_pairs = parsed.get("qa_pairs", [])
                tone_detected = parsed.get("tone_detected", "professional")
                suggested_prompt = parsed.get("suggested_system_prompt", "")
                suggested_templates = parsed.get("suggested_templates", [])

                logger.info(
                    f"✅ Gemini analysis complete: {len(qa_pairs)} Q&A pairs, "
                    f"tone={tone_detected}"
                )

            except Exception as gemini_exc:
                logger.warning(
                    f"⚠️ Gemini analysis failed (non-fatal): {gemini_exc}"
                )
                # Continue with partial results rather than failing the whole job
        else:
            logger.warning(
                "⚠️ GEMINI_API_KEY not set — skipping AI analysis, "
                "saving parse results only"
            )

        # Step 3 — Persist results
        await service.update_job_status(
            tenant_id=tenant_id,
            job_id=job_id,
            status="completed",
            raw_message_count=raw_count,
            qa_pairs_extracted=len(qa_pairs),
            faq_count=len(suggested_templates),
            tone_detected=tone_detected,
            suggested_system_prompt=suggested_prompt,
            suggested_templates=suggested_templates,
            completed_at=datetime.now().isoformat(),
        )

        logger.info(
            f"✅ Learning job {job_id} completed for tenant {tenant_id}"
        )

    except Exception as exc:
        logger.error(
            f"❌ process_wa_history failed for job {job_id}: {exc}", exc_info=True
        )
        try:
            await service.update_job_status(
                tenant_id=tenant_id,
                job_id=job_id,
                status="failed",
                error_message=str(exc),
                completed_at=datetime.now().isoformat(),
            )
        except Exception as update_exc:
            logger.error(
                f"❌ Could not update job {job_id} to failed: {update_exc}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/upload-history")
async def upload_wa_history(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Accept a WhatsApp chat export (.txt) and kick off AI analysis as a background job.

    The uploaded file is stored in Supabase Storage (``bijou-media`` bucket) under
    ``{tenant_id}/wa_exports/`` and a new ``wa_learning_jobs`` record is created
    with ``status='processing'``.

    Args:
        file: Multipart text file upload (WhatsApp .txt export).
        background_tasks: FastAPI BackgroundTasks for async processing.
        x_tenant_id: Tenant UUID from ``X-Tenant-ID`` header (required).

    Returns:
        Dict containing the new ``job_id`` and ``status``.

    Raises:
        HTTPException 400: If the uploaded file is not a .txt file.
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
        HTTPException 500: If job creation or storage upload fails.
    """

    # Validate file type
    filename = file.filename or "upload.txt"
    if not filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Only plain .txt WhatsApp export files are accepted.",
        )

    try:
        from src.saas.wa_learning_service import WALearningService
        from src.saas.storage_setup import generate_signed_url

        supabase = _get_supabase()
        service = WALearningService(supabase)

        # Read content
        raw_bytes = await file.read()
        try:
            file_content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            file_content = raw_bytes.decode("utf-8", errors="replace")

        # Store file in Supabase Storage
        import uuid as _uuid

        file_key = f"{tenant_id}/wa_exports/{_uuid.uuid4()}_{filename}"
        file_url: Optional[str] = None
        try:
            supabase.storage.from_(BUCKET_NAME).upload(
                file_key,
                raw_bytes,
                file_options={"content-type": "text/plain"},
            )
            file_url = generate_signed_url(
                supabase, tenant_id, f"wa_exports/{filename}"
            )
            logger.info(f"📤 WA export stored at {file_key}")
        except Exception as storage_exc:
            # Non-fatal — we still have the content in memory
            logger.warning(f"⚠️ Storage upload failed (non-fatal): {storage_exc}")

        # Create learning job record
        job = await service.create_job(
            tenant_id=tenant_id,
            import_type="whatsapp_export",
            file_url=file_url,
        )
        job_id = job["id"]

        # Queue background analysis
        background_tasks.add_task(
            process_wa_history,
            job_id=job_id,
            tenant_id=tenant_id,
            file_content=file_content,
            supabase=supabase,
        )

        logger.info(
            f"🚀 WA history upload queued — job_id={job_id}, tenant={tenant_id}"
        )

        return {
            "job_id": job_id,
            "status": "processing",
            "message": (
                "Your WhatsApp export is being analysed. "
                "Poll GET /api/learn/status/{job_id} to track progress."
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ upload_wa_history failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start learning job: {str(exc)}",
        )


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Poll the status of a learning job.

    Args:
        job_id: UUID of the learning job.
        x_tenant_id: Tenant UUID from ``X-Tenant-ID`` header (required).

    Returns:
        Full job record dict including status, extracted counts, and suggestions.

    Raises:
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
        HTTPException 404: If the job is not found for this tenant.
    """

    try:
        from src.saas.wa_learning_service import WALearningService

        supabase = _get_supabase()
        service = WALearningService(supabase)

        job = await service.get_job(tenant_id=tenant_id, job_id=job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Learning job {job_id} not found",
            )

        return job

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ get_job_status failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch job status: {str(exc)}",
        )


@router.post("/apply/{job_id}")
async def apply_learning_job(
    job_id: str,
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Apply suggestions from a completed learning job to the tenant's config.

    This will:
    - Insert ``suggested_templates`` into the ``message_templates`` table.
    - Update the tenant's ``system_prompt`` in the ``tenants`` table if a
      ``suggested_system_prompt`` is present.

    Args:
        job_id: UUID of the completed learning job.
        x_tenant_id: Tenant UUID from ``X-Tenant-ID`` header (required).

    Returns:
        Dict summarising what was applied.

    Raises:
        HTTPException 400: If the job is not in ``completed`` status.
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
        HTTPException 404: If the job is not found for this tenant.
        HTTPException 500: If applying suggestions fails.
    """

    try:
        from src.saas.wa_learning_service import WALearningService

        supabase = _get_supabase()
        service = WALearningService(supabase)

        # Fetch job
        job = await service.get_job(tenant_id=tenant_id, job_id=job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Learning job {job_id} not found",
            )

        if job.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Job is not completed yet (status={job.get('status')}). "
                    "Wait until status='completed' before applying."
                ),
            )

        applied_templates = 0
        prompt_updated = False

        # Apply suggested templates
        suggested_templates: List[Dict[str, Any]] = job.get("suggested_templates") or []
        for tmpl in suggested_templates:
            try:
                supabase.table("message_templates").insert(
                    {
                        "tenant_id": tenant_id,
                        "template_name": tmpl.get("name", "Auto-generated template"),
                        "trigger_keywords": tmpl.get("trigger_keywords", []),
                        "template_content": tmpl.get("body", ""),
                        "trigger_mode": "keyword_auto" if tmpl.get("trigger_keywords") else "manual_only",
                        "is_active": True,
                        "source": "wa_learning",
                    }
                ).execute()
                applied_templates += 1
            except Exception as tmpl_exc:
                logger.warning(
                    f"⚠️ Could not insert template '{tmpl.get('name')}': {tmpl_exc}"
                )

        # Apply suggested system prompt
        suggested_prompt: str = job.get("suggested_system_prompt") or ""
        if suggested_prompt:
            try:
                supabase.table("tenants").update(
                    {"system_prompt": suggested_prompt}
                ).eq("id", tenant_id).execute()
                prompt_updated = True
                logger.info(
                    f"✅ System prompt updated for tenant {tenant_id} "
                    f"from learning job {job_id}"
                )
            except Exception as prompt_exc:
                logger.warning(
                    f"⚠️ Could not update system prompt: {prompt_exc}"
                )

        logger.info(
            f"✅ Applied learning job {job_id}: "
            f"{applied_templates} templates, prompt_updated={prompt_updated}"
        )

        return {
            "job_id": job_id,
            "applied_templates": applied_templates,
            "prompt_updated": prompt_updated,
            "message": (
                f"Applied {applied_templates} message template(s). "
                + ("System prompt updated." if prompt_updated else "System prompt unchanged.")
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ apply_learning_job failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply learning job: {str(exc)}",
        )


@router.get("/insights")
async def list_learning_insights(
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Return the 20 most recent learning jobs for the tenant.

    Args:
        x_tenant_id: Tenant UUID from ``X-Tenant-ID`` header (required).

    Returns:
        Dict with ``jobs`` list and ``total`` count.

    Raises:
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
    """

    try:
        from src.saas.wa_learning_service import WALearningService

        supabase = _get_supabase()
        service = WALearningService(supabase)

        jobs = await service.list_jobs(tenant_id=tenant_id, limit=20)
        return {"jobs": jobs, "total": len(jobs)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ list_learning_insights failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list learning insights: {str(exc)}",
        )
