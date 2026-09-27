"""Dashboard API: read/set the per-tenant owner phones (tenants.owner_phones).

These phones are treated as the business owner for owner detection and receive
the WhatsApp approval requests (see src/core/owner_approvals.py). Empty list =
fall back to the global OWNER_WHATSAPP_JID. Only read by the runtime when
ENABLE_OWNER_APPROVALS=true; this API just stores the setting.

tenant_id comes from verify_session only, never client input. Returns 503 until
migrations-py/add_owner_approvals.sql has been applied.
"""
from __future__ import annotations

import logging
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.core.dashboard_api_simple import verify_session
from src.core.owner_approvals import _owner_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard/owner-phones", tags=["owner-phones"])

_MAX_PHONES = 5


def _supabase():
    """Service-role client — same pattern as src/core/shared_context_api.py."""
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
    )
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


class OwnerPhones(BaseModel):
    owner_phones: List[str] = Field(default_factory=list, max_length=_MAX_PHONES)


def _normalize(phone: str) -> str:
    """'+60 12-345 6789' -> '60123456789'; rejects anything that isn't 8-15 digits."""
    digits = "".join(c for c in phone if c.isdigit())
    if not (8 <= len(digits) <= 15) or any(c not in "+0123456789 -()" for c in phone):
        raise HTTPException(status_code=400, detail=f"Invalid phone number: {phone!r}")
    return digits


@router.get("", response_model=OwnerPhones)
async def get_owner_phones(tenant_id: str = Depends(verify_session)):
    try:
        r = _supabase().table("tenants").select("owner_phones").eq("id", tenant_id).limit(1).execute()
    except Exception as e:
        logger.error("owner_phones read failed tenant=%s: %s", tenant_id, e)
        raise HTTPException(status_code=503, detail="Owner phones not available yet")
    return OwnerPhones(owner_phones=((r.data or [{}])[0].get("owner_phones") or []))


@router.put("", response_model=OwnerPhones)
async def set_owner_phones(req: OwnerPhones, tenant_id: str = Depends(verify_session)):
    phones = list(dict.fromkeys(_normalize(p) for p in req.owner_phones))
    try:
        r = (
            _supabase()
            .table("tenants")
            .update({"owner_phones": phones})
            .eq("id", tenant_id)
            .execute()
        )
    except Exception as e:
        logger.error("owner_phones update failed tenant=%s: %s", tenant_id, e)
        raise HTTPException(status_code=503, detail="Owner phones not available yet")
    if not (r.data or []):
        raise HTTPException(status_code=404, detail="Tenant not found")
    _owner_cache.pop(tenant_id, None)  # other workers pick it up within the 60s TTL
    return OwnerPhones(owner_phones=phones)
