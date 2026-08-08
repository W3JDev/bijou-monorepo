"""
Bijou AI - Live Learning Extractor
=====================================

Extracts Q&A patterns, tone, and FAQ candidates from resolved escalation
conversations in real-time and saves the results as a ``wa_learning_jobs``
record with ``import_type='live_conversation'``.

Called as a fire-and-forget async task from ``handover_system.resolve_escalation()``.

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def extract_and_save_live_learning(
    tenant_id: str,
    conversation_messages: List[Dict[str, Any]],
    supabase_client: Any,
) -> None:
    """
    Analyse a resolved conversation for learning signals and persist results.

    This function is intended to be called as a fire-and-forget background task
    (via ``asyncio.create_task``) from ``resolve_escalation()``. Failures are
    logged but never raised — they must not affect the caller.

    The function:
        1. Creates a ``wa_learning_jobs`` record (``import_type='live_conversation'``).
        2. Sends the conversation to Gemini for Q&A + tone extraction.
        3. Updates the job record with results (status='completed') or
           status='failed' on error.

    Args:
        tenant_id: UUID of the owning tenant.
        conversation_messages: List of message dicts, each expected to have
            at minimum ``sender`` and ``message`` keys (additional keys are fine).
        supabase_client: An initialised Supabase client (service role).
    """
    from src.saas.wa_learning_service import WALearningService

    service = WALearningService(supabase_client)
    job_id: Optional[str] = None

    try:
        if not conversation_messages:
            logger.info(
                "ℹ️ Live learning skipped — no conversation messages provided "
                f"(tenant={tenant_id})"
            )
            return

        logger.info(
            f"🧠 Live learning extraction started for tenant {tenant_id} "
            f"({len(conversation_messages)} messages)"
        )

        # Step 1 — Create job record
        job = await service.create_job(
            tenant_id=tenant_id,
            import_type="live_conversation",
            file_url=None,
        )
        job_id = job["id"]

        # Step 2 — Build conversation text for Gemini
        conversation_text = "\n".join(
            f"[{m.get('sender', 'Unknown')}]: {m.get('message', '')}"
            for m in conversation_messages
        )

        raw_count = len(conversation_messages)
        qa_pairs: List[Dict[str, str]] = []
        tone_detected = "professional"
        suggested_prompt = ""
        suggested_templates: List[Dict[str, Any]] = []

        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip('"')
        if gemini_api_key:
            try:
                import google.generativeai as genai  # type: ignore

                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")

                analysis_prompt = f"""You are an AI business analyst. Analyse this resolved customer support conversation.

CONVERSATION ({raw_count} messages):
---
{conversation_text}
---

Return a JSON object with EXACTLY these keys:
{{
  "qa_pairs": [
    {{"question": "...", "answer": "..."}},
    ...
  ],
  "tone_detected": "<one of: formal, semi-formal, casual, friendly, professional>",
  "suggested_system_prompt": "<optional: 1-2 sentence system prompt improvement based on this conversation style>",
  "suggested_templates": [
    {{"name": "...", "trigger_keywords": ["..."], "body": "..."}},
    ...
  ]
}}

Rules:
- Extract up to 5 Q&A pairs from real customer questions and business answers
- Suggest at most 2 message templates if clear recurring patterns exist
- Keep template bodies under 200 chars
- If nothing useful can be extracted, return empty lists
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
                    f"✅ Live learning Gemini analysis complete: "
                    f"{len(qa_pairs)} Q&A pairs, tone={tone_detected} "
                    f"(job={job_id})"
                )

            except Exception as gemini_exc:
                logger.warning(
                    f"⚠️ Gemini analysis failed in live learning (non-fatal): "
                    f"{gemini_exc}"
                )
                # Continue with partial results
        else:
            logger.warning(
                "⚠️ GEMINI_API_KEY not set — live learning saved without AI analysis"
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
            f"✅ Live learning job {job_id} completed for tenant {tenant_id}"
        )

    except Exception as exc:
        logger.error(
            f"❌ extract_and_save_live_learning failed "
            f"(tenant={tenant_id}, job={job_id}): {exc}",
            exc_info=True,
        )
        # Try to mark job as failed if we got far enough to create it
        if job_id:
            try:
                from src.saas.wa_learning_service import WALearningService

                svc = WALearningService(supabase_client)
                await svc.update_job_status(
                    tenant_id=tenant_id,
                    job_id=job_id,
                    status="failed",
                    error_message=str(exc),
                    completed_at=datetime.now().isoformat(),
                )
            except Exception as update_exc:
                logger.error(
                    f"❌ Could not mark live learning job {job_id} as failed: "
                    f"{update_exc}"
                )
