"""
Bijou AI - Supabase Storage Setup
===================================

Utility functions for provisioning and using the `bijou-media` Supabase
Storage bucket.

Responsibilities:
- Idempotent bucket creation (check-before-create).
- Signed URL generation for private file access.

This module is imported during FastAPI startup via `bijou.py`.

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

BUCKET_NAME = "bijou-media"


async def ensure_bijou_media_bucket(supabase_client: Any) -> Dict[str, str]:
    """
    Idempotently create the `bijou-media` Supabase Storage bucket.

    Checks whether the bucket already exists before attempting to create it.
    Never deletes or modifies existing buckets.

    Args:
        supabase_client: An initialised `supabase.Client` instance.

    Returns:
        Dict with keys:
            - ``bucket``: bucket name (always ``"bijou-media"``)
            - ``status``: ``"created"`` or ``"already_exists"``
    """
    try:
        # List existing buckets to check for existence
        existing_buckets = supabase_client.storage.list_buckets()
        bucket_names = [b.name for b in existing_buckets]

        if BUCKET_NAME in bucket_names:
            logger.info(f"✅ Storage bucket '{BUCKET_NAME}' already exists — skipping creation")
            return {"bucket": BUCKET_NAME, "status": "already_exists"}

        # Create the bucket (private — no public URL access)
        supabase_client.storage.create_bucket(BUCKET_NAME, options={"public": False})
        logger.info(f"✅ Storage bucket '{BUCKET_NAME}' created successfully")
        return {"bucket": BUCKET_NAME, "status": "created"}

    except Exception as exc:
        logger.error(
            f"❌ ensure_bijou_media_bucket failed: {exc}", exc_info=True
        )
        # Non-fatal — return a warning status rather than crashing startup
        return {"bucket": BUCKET_NAME, "status": f"error: {exc}"}


def generate_signed_url(
    supabase_client: Any,
    tenant_id: str,
    stored_filename: str,
    expires_in: int = 3600,
) -> Optional[str]:
    """
    Generate a time-limited signed URL for a private file in Supabase Storage.

    Files are stored at the path ``{tenant_id}/{stored_filename}`` inside the
    ``bijou-media`` bucket.

    Args:
        supabase_client: An initialised `supabase.Client` instance.
        tenant_id: UUID of the owning tenant (used as the storage path prefix).
        stored_filename: The filename as stored in Supabase Storage.
        expires_in: URL validity in seconds (default 3600 = 1 hour).

    Returns:
        Signed URL string, or None if generation failed.
    """
    try:
        storage_path = f"{tenant_id}/{stored_filename}"
        response = supabase_client.storage.from_(BUCKET_NAME).create_signed_url(
            storage_path, expires_in
        )
        signed_url: Optional[str] = response.get("signedURL") or response.get("signedUrl")
        if signed_url:
            logger.debug(
                f"🔗 Signed URL generated for {storage_path} "
                f"(expires_in={expires_in}s)"
            )
        else:
            logger.warning(f"⚠️ No signed URL returned for {storage_path}")
        return signed_url
    except Exception as exc:
        logger.error(
            f"❌ generate_signed_url failed (tenant={tenant_id}, "
            f"file={stored_filename}): {exc}",
            exc_info=True,
        )
        return None
