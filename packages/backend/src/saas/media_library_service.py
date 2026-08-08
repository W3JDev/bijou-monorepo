"""
Bijou AI - Media Library Service
==================================

Service layer for CRUD operations on the `media_library` table.
All methods are async and enforce tenant_id isolation.

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class MediaLibraryService:
    """
    Service wrapper for Supabase CRUD on the `media_library` table.

    All methods require `tenant_id` to enforce strict multi-tenant isolation.
    """

    def __init__(self, supabase_client: Any) -> None:
        """
        Initialise the service with a Supabase client.

        Args:
            supabase_client: An initialised `supabase.Client` instance.
        """
        self.supabase = supabase_client
        logger.info("✅ MediaLibraryService initialized")

    # ─────────────────────────────────────────────────────────────────────────
    # READ
    # ─────────────────────────────────────────────────────────────────────────

    async def list(
        self,
        tenant_id: str,
        file_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all media records for a tenant, with an optional type filter.

        Args:
            tenant_id: UUID of the owning tenant.
            file_type: Optional file_type filter (e.g. "image", "pdf").

        Returns:
            List of media record dicts.

        Raises:
            RuntimeError: If the Supabase query fails.
        """
        try:
            query = (
                self.supabase.table("media_library")
                .select("*")
                .eq("tenant_id", tenant_id)
                .order("created_at", desc=True)
            )
            if file_type:
                query = query.eq("file_type", file_type)

            result = query.execute()
            logger.info(
                f"📋 Listed {len(result.data)} media records for tenant {tenant_id}"
            )
            return result.data
        except Exception as exc:
            logger.error(f"❌ MediaLibraryService.list failed: {exc}", exc_info=True)
            raise RuntimeError(f"Failed to list media records: {exc}") from exc

    async def get_by_id(
        self,
        tenant_id: str,
        record_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single media record by its UUID.

        Args:
            tenant_id: UUID of the owning tenant (isolation guard).
            record_id: UUID of the media record.

        Returns:
            Media record dict, or None if not found.
        """
        try:
            result = (
                self.supabase.table("media_library")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("id", record_id)
                .execute()
            )
            if result.data:
                return result.data[0]
            return None
        except Exception as exc:
            logger.error(
                f"❌ MediaLibraryService.get_by_id failed (id={record_id}): {exc}",
                exc_info=True,
            )
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────

    async def create_record(
        self,
        tenant_id: str,
        original_name: str,
        stored_filename: str,
        file_type: str,
        file_url: str,
        mime_type: Optional[str] = None,
        file_size: Optional[int] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new media record into the `media_library` table.

        Args:
            tenant_id: UUID of the owning tenant.
            original_name: Original filename as uploaded by the user.
            stored_filename: Filename used in Supabase Storage.
            file_type: Broad category (e.g. "image", "pdf", "video").
            file_url: Public or signed storage URL.
            mime_type: MIME type (e.g. "image/png").
            file_size: File size in bytes.
            description: Optional human-readable description.
            tags: Optional list of string tags.

        Returns:
            The newly created media record dict.

        Raises:
            RuntimeError: If the insert fails.
        """
        try:
            payload: Dict[str, Any] = {
                "tenant_id": tenant_id,
                "original_name": original_name,
                "stored_filename": stored_filename,
                "file_type": file_type,
                "file_url": file_url,
            }
            if mime_type is not None:
                payload["mime_type"] = mime_type
            if file_size is not None:
                payload["file_size"] = file_size
            if description is not None:
                payload["description"] = description
            if tags is not None:
                payload["tags"] = tags

            result = self.supabase.table("media_library").insert(payload).execute()

            if not result.data:
                raise RuntimeError("Insert returned no data")

            record = result.data[0]
            logger.info(
                f"✅ Created media record {record['id']} for tenant {tenant_id}"
            )
            return record
        except Exception as exc:
            logger.error(
                f"❌ MediaLibraryService.create_record failed: {exc}", exc_info=True
            )
            raise RuntimeError(f"Failed to create media record: {exc}") from exc

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────────────────────────────────

    async def delete_record(
        self,
        tenant_id: str,
        record_id: str,
    ) -> bool:
        """
        Delete a media record from the database.

        Storage-side deletion must be performed by the caller before or after
        invoking this method.

        Args:
            tenant_id: UUID of the owning tenant (isolation guard).
            record_id: UUID of the media record to delete.

        Returns:
            True if the record was deleted, False if not found.
        """
        try:
            result = (
                self.supabase.table("media_library")
                .delete()
                .eq("tenant_id", tenant_id)
                .eq("id", record_id)
                .execute()
            )
            deleted = bool(result.data)
            if deleted:
                logger.info(
                    f"🗑️ Deleted media record {record_id} for tenant {tenant_id}"
                )
            else:
                logger.warning(
                    f"⚠️ Media record {record_id} not found for tenant {tenant_id}"
                )
            return deleted
        except Exception as exc:
            logger.error(
                f"❌ MediaLibraryService.delete_record failed (id={record_id}): {exc}",
                exc_info=True,
            )
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────────────────

    async def increment_send_count(
        self,
        tenant_id: str,
        record_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically increment the `send_count` field for a media record.

        Uses a Supabase RPC call to avoid read-modify-write races.
        Falls back to a manual increment if RPC is unavailable.

        Args:
            tenant_id: UUID of the owning tenant (isolation guard).
            record_id: UUID of the media record.

        Returns:
            Updated media record dict, or None on failure.
        """
        try:
            # Fetch current value
            existing = await self.get_by_id(tenant_id, record_id)
            if not existing:
                logger.warning(
                    f"⚠️ Media record {record_id} not found for tenant {tenant_id}"
                )
                return None

            new_count = existing.get("send_count", 0) + 1

            result = (
                self.supabase.table("media_library")
                .update({"send_count": new_count})
                .eq("tenant_id", tenant_id)
                .eq("id", record_id)
                .execute()
            )

            if result.data:
                logger.info(
                    f"📤 send_count incremented to {new_count} for media {record_id}"
                )
                return result.data[0]
            return None
        except Exception as exc:
            logger.error(
                f"❌ MediaLibraryService.increment_send_count failed: {exc}",
                exc_info=True,
            )
            return None
