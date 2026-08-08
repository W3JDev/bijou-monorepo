"""
Bijou AI - Media Library API
==============================

FastAPI router for managing tenant media assets stored in Supabase Storage.

Routes:
    POST   /api/media/upload       — Upload a file to Supabase Storage
    GET    /api/media              — List all media for a tenant
    DELETE /api/media/{id}         — Delete a media record + storage file
    POST   /api/media/{id}/send    — Increment send_count, return signed URL

All routes require the ``X-Tenant-ID`` request header.

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from src.core.dashboard_api_simple import verify_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/media", tags=["media"])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_supabase() -> Any:
    """Return an initialised Supabase service-role client."""
    from supabase import create_client  # type: ignore

    url = os.getenv("SUPABASE_URL", "").strip('"')
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip('"')
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


def _classify_file_type(mime_type: str) -> str:
    """Derive a broad file_type category from a MIME type string."""
    if mime_type.startswith("image/"):
        return "image"
    if mime_type in ("application/pdf",):
        return "pdf"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type.startswith("audio/"):
        return "audio"
    return "document"


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME = "bijou-media"


@router.post("/upload")
async def upload_media(
    file: UploadFile,
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Upload a file to Supabase Storage and register it in `media_library`.

    The file is stored at ``{tenant_id}/{uuid}_{original_filename}`` inside
    the ``bijou-media`` private bucket.

    Args:
        file: Multipart file upload.
        x_tenant_id: Tenant UUID from ``X-Tenant-ID`` header (required).

    Returns:
        Newly created `media_library` record dict.

    Raises:
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
        HTTPException 500: If storage upload or DB insert fails.
    """

    try:
        from src.saas.media_library_service import MediaLibraryService
        from src.saas.storage_setup import generate_signed_url

        supabase = _get_supabase()
        service = MediaLibraryService(supabase)

        # Build storage path
        file_uuid = str(uuid.uuid4())
        original_name = file.filename or "upload"
        stored_filename = f"{file_uuid}_{original_name}"
        storage_path = f"{tenant_id}/{stored_filename}"

        # Read file bytes
        file_bytes = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        file_type = _classify_file_type(mime_type)

        logger.info(
            f"📤 Uploading {original_name} ({len(file_bytes)} bytes) "
            f"to storage path {storage_path}"
        )

        # Upload to Supabase Storage
        supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            file_bytes,
            file_options={"content-type": mime_type},
        )

        # Generate initial signed URL (valid 1 hour)
        file_url = generate_signed_url(supabase, tenant_id, stored_filename) or ""

        # Insert record in media_library
        record = await service.create_record(
            tenant_id=tenant_id,
            original_name=original_name,
            stored_filename=stored_filename,
            file_type=file_type,
            file_url=file_url,
            mime_type=mime_type,
            file_size=len(file_bytes),
        )

        return record

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ upload_media failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Media upload failed: {str(exc)}",
        )


@router.get("")
async def list_media(
    type: Optional[str] = Query(default=None, description="Filter by file_type"),
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    List all media records for a tenant, with optional type filter.

    Args:
        x_tenant_id: Tenant UUID from ``X-Tenant-ID`` header (required).
        type: Optional ``file_type`` filter (e.g. ``image``, ``pdf``).

    Returns:
        Dict with ``media`` list and ``total`` count.

    Raises:
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
    """

    try:
        from src.saas.media_library_service import MediaLibraryService

        supabase = _get_supabase()
        service = MediaLibraryService(supabase)
        records = await service.list(tenant_id, file_type=type)
        return {"media": records, "total": len(records)}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ list_media failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list media: {str(exc)}",
        )


@router.delete("/{record_id}")
async def delete_media(
    record_id: str,
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Delete a media record from Supabase Storage and the `media_library` table.

    Args:
        record_id: UUID of the media record to delete.
        x_tenant_id: Tenant UUID from ``X-Tenant-ID`` header (required).

    Returns:
        Dict with ``status`` field.

    Raises:
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
        HTTPException 404: If the record does not exist for this tenant.
        HTTPException 500: If deletion fails.
    """

    try:
        from src.saas.media_library_service import MediaLibraryService

        supabase = _get_supabase()
        service = MediaLibraryService(supabase)

        # Fetch record to get storage path
        record = await service.get_by_id(tenant_id, record_id)
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Media record {record_id} not found",
            )

        stored_filename = record.get("stored_filename", "")
        storage_path = f"{tenant_id}/{stored_filename}"

        # Delete from Supabase Storage
        try:
            supabase.storage.from_(BUCKET_NAME).remove([storage_path])
            logger.info(f"🗑️ Deleted storage file: {storage_path}")
        except Exception as storage_exc:
            logger.warning(
                f"⚠️ Storage deletion failed for {storage_path}: {storage_exc}"
            )

        # Delete DB record
        deleted = await service.delete_record(tenant_id, record_id)
        if not deleted:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete DB record",
            )

        return {"status": "deleted", "id": record_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ delete_media failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Media deletion failed: {str(exc)}",
        )


@router.post("/{record_id}/send")
async def send_media(
    record_id: str,
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Mark a media record as sent: increment ``send_count`` and return a signed URL.

    Args:
        record_id: UUID of the media record.
        x_tenant_id: Tenant UUID from ``X-Tenant-ID`` header (required).

    Returns:
        Dict with updated record data and ``signed_url``.

    Raises:
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
        HTTPException 404: If the record does not exist for this tenant.
    """

    try:
        from src.saas.media_library_service import MediaLibraryService
        from src.saas.storage_setup import generate_signed_url

        supabase = _get_supabase()
        service = MediaLibraryService(supabase)

        # Verify record exists
        record = await service.get_by_id(tenant_id, record_id)
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Media record {record_id} not found",
            )

        # Increment send count
        updated = await service.increment_send_count(tenant_id, record_id)

        # Generate a fresh signed URL
        stored_filename = record.get("stored_filename", "")
        signed_url = generate_signed_url(supabase, tenant_id, stored_filename)

        return {
            **(updated or record),
            "signed_url": signed_url,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ send_media failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Media send failed: {str(exc)}",
        )


@router.get("/{record_id}/url")
async def get_media_url(
    record_id: str,
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Return a fresh signed URL for a media record WITHOUT incrementing send_count.
    Used for in-dashboard previews.
    """

    try:
        from src.saas.media_library_service import MediaLibraryService
        from src.saas.storage_setup import generate_signed_url

        supabase = _get_supabase()
        service = MediaLibraryService(supabase)

        record = await service.get_by_id(tenant_id, record_id)
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Media record {record_id} not found",
            )

        stored_filename = record.get("stored_filename", "")
        signed_url = generate_signed_url(supabase, tenant_id, stored_filename)

        return {
            "id": record_id,
            "signed_url": signed_url,
            "file_type": record.get("file_type", "document"),
            "original_name": record.get("original_name", ""),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ get_media_url failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get media URL: {str(exc)}")


@router.patch("/{record_id}")
async def update_media_metadata(
    record_id: str,
    body: Dict[str, Any] = Body(...),
    tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Update ``description`` and/or ``tags`` (trigger keywords) for a media record.

    Body JSON fields (all optional):
        description: Human-readable note about the file and when to send it.
        tags: List of trigger keyword strings (e.g. ["floor plan", "layout"]).

    Returns:
        Updated media record dict.

    Raises:
        HTTPException 401: If ``X-Tenant-ID`` header is missing.
        HTTPException 404: If the record does not exist for this tenant.
    """

    try:
        supabase = _get_supabase()

        # Verify record belongs to this tenant
        existing = (
            supabase.table("media_library")
            .select("id")
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not existing.data:
            raise HTTPException(
                status_code=404,
                detail=f"Media record {record_id} not found",
            )

        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")

        patch: Dict[str, Any] = {}
        if "description" in body:
            patch["description"] = body["description"]
        if "tags" in body:
            raw = body["tags"]
            if isinstance(raw, str):
                patch["tags"] = [t.strip() for t in raw.split(",") if t.strip()]
            elif isinstance(raw, list):
                patch["tags"] = [str(t).strip() for t in raw if str(t).strip()]
            else:
                patch["tags"] = []

        if not patch:
            raise HTTPException(status_code=400, detail="No updatable fields provided")

        result = (
            supabase.table("media_library")
            .update(patch)
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )

        logger.info(f"✏️ Updated media metadata for {record_id}: {list(patch.keys())}")
        return result.data[0] if result.data else {"id": record_id, **patch}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ update_media_metadata failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Media update failed: {str(exc)}",
        )
