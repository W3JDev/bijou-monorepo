"""
Bijou AI - WA Learning Service
================================

Service layer for CRUD operations on the `wa_learning_jobs` table.
Used to track WhatsApp chat-history import analysis jobs.

All methods are async and enforce tenant_id isolation.

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WALearningService:
    """
    Service wrapper for Supabase CRUD on the `wa_learning_jobs` table.

    Each job represents a single WhatsApp chat-history import that is
    processed asynchronously. All queries are scoped to `tenant_id`.
    """

    def __init__(self, supabase_client: Any) -> None:
        """
        Initialise the service with a Supabase client.

        Args:
            supabase_client: An initialised `supabase.Client` instance.
        """
        self.supabase = supabase_client
        logger.info("✅ WALearningService initialized")

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────

    async def create_job(
        self,
        tenant_id: str,
        import_type: str,
        file_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new learning job with status='processing'.

        Args:
            tenant_id: UUID of the owning tenant.
            import_type: Type of import (e.g. 'whatsapp_export', 'csv').
            file_url: Optional URL to the uploaded source file.

        Returns:
            The newly created job record dict.

        Raises:
            RuntimeError: If the insert fails.
        """
        try:
            payload: Dict[str, Any] = {
                "tenant_id": tenant_id,
                "import_type": import_type,
                "status": "processing",
            }
            if file_url is not None:
                payload["file_url"] = file_url

            result = self.supabase.table("wa_learning_jobs").insert(payload).execute()

            if not result.data:
                raise RuntimeError("Insert returned no data")

            job = result.data[0]
            logger.info(
                f"✅ Created learning job {job['id']} (type={import_type}) "
                f"for tenant {tenant_id}"
            )
            return job
        except Exception as exc:
            logger.error(
                f"❌ WALearningService.create_job failed: {exc}", exc_info=True
            )
            raise RuntimeError(f"Failed to create learning job: {exc}") from exc

    # ─────────────────────────────────────────────────────────────────────────
    # READ
    # ─────────────────────────────────────────────────────────────────────────

    async def get_job(
        self,
        tenant_id: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single learning job by its UUID.

        Args:
            tenant_id: UUID of the owning tenant (isolation guard).
            job_id: UUID of the job.

        Returns:
            Job record dict, or None if not found.
        """
        try:
            result = (
                self.supabase.table("wa_learning_jobs")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("id", job_id)
                .execute()
            )
            if result.data:
                return result.data[0]
            return None
        except Exception as exc:
            logger.error(
                f"❌ WALearningService.get_job failed (id={job_id}): {exc}",
                exc_info=True,
            )
            return None

    async def list_jobs(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        List learning jobs for a tenant, newest first.

        Args:
            tenant_id: UUID of the owning tenant.
            status: Optional status filter (e.g. 'completed', 'processing').
            limit: Maximum number of records to return (default 20).

        Returns:
            List of job record dicts.
        """
        try:
            query = (
                self.supabase.table("wa_learning_jobs")
                .select("*")
                .eq("tenant_id", tenant_id)
                .order("created_at", desc=True)
                .limit(limit)
            )
            if status:
                query = query.eq("status", status)

            result = query.execute()
            logger.info(
                f"📋 Listed {len(result.data)} learning jobs for tenant {tenant_id}"
            )
            return result.data
        except Exception as exc:
            logger.error(
                f"❌ WALearningService.list_jobs failed: {exc}", exc_info=True
            )
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────────────────

    async def update_job_status(
        self,
        tenant_id: str,
        job_id: str,
        status: str,
        raw_message_count: Optional[int] = None,
        qa_pairs_extracted: Optional[int] = None,
        faq_count: Optional[int] = None,
        tone_detected: Optional[str] = None,
        suggested_system_prompt: Optional[str] = None,
        suggested_templates: Optional[List[Dict[str, Any]]] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a learning job's status and optional result fields.

        Args:
            tenant_id: UUID of the owning tenant (isolation guard).
            job_id: UUID of the job to update.
            status: New status value (e.g. 'completed', 'failed').
            raw_message_count: Total messages parsed from the export.
            qa_pairs_extracted: Number of Q&A pairs identified.
            faq_count: Number of FAQ items generated.
            tone_detected: Human-readable tone label.
            suggested_system_prompt: AI-generated system prompt suggestion.
            suggested_templates: List of template dicts to suggest.
            error_message: Error detail if status is 'failed'.
            completed_at: ISO-8601 timestamp when the job finished.

        Returns:
            Updated job record dict, or None on failure.
        """
        try:
            updates: Dict[str, Any] = {"status": status}

            if raw_message_count is not None:
                updates["raw_message_count"] = raw_message_count
            if qa_pairs_extracted is not None:
                updates["qa_pairs_extracted"] = qa_pairs_extracted
            if faq_count is not None:
                updates["faq_count"] = faq_count
            if tone_detected is not None:
                updates["tone_detected"] = tone_detected
            if suggested_system_prompt is not None:
                updates["suggested_system_prompt"] = suggested_system_prompt
            if suggested_templates is not None:
                updates["suggested_templates"] = suggested_templates
            if error_message is not None:
                updates["error_message"] = error_message
            if completed_at is not None:
                updates["completed_at"] = completed_at

            result = (
                self.supabase.table("wa_learning_jobs")
                .update(updates)
                .eq("tenant_id", tenant_id)
                .eq("id", job_id)
                .execute()
            )

            if result.data:
                logger.info(
                    f"✅ Updated learning job {job_id} → status={status} "
                    f"for tenant {tenant_id}"
                )
                return result.data[0]

            logger.warning(
                f"⚠️ Learning job {job_id} not found or not updated "
                f"for tenant {tenant_id}"
            )
            return None
        except Exception as exc:
            logger.error(
                f"❌ WALearningService.update_job_status failed: {exc}",
                exc_info=True,
            )
            return None
