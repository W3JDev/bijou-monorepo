"""
Bijou AI - Contacts CRM API
============================

REST API for the contacts table (auto-saved from WhatsApp + manual entries).

Endpoints:
- GET  /api/contacts          - List contacts (filterable)
- POST /api/contacts          - Manually add a contact
- PATCH /api/contacts/{jid}   - Update tag / notes / name / status
- DELETE /api/contacts/{jid}  - Remove a contact

Auth: X-Tenant-ID header (same pattern as settings_api, media_api, etc.)

Author: W3J Bijou AI
Version: 1.0.0
"""

import csv
import io
import logging
import os
from typing import List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from supabase import create_client

from src.core.dashboard_api_simple import verify_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

VALID_TAGS = {"lead", "inquiry", "hot_lead", "customer", "vip", "blocked"}
VALID_STATUSES = {"active", "inactive", "blocked"}


# ────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────

def get_supabase():
    supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip('"')
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    return create_client(supabase_url, supabase_key)


def _jid(raw: str) -> str:
    """Decode URL-encoded JID from path param."""
    return unquote(raw)


# ────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ────────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    jid: str                              # WhatsApp JID (required)
    phone: Optional[str] = None
    name: Optional[str] = None
    tag: Optional[str] = "lead"
    source: Optional[str] = "manual"
    status: Optional[str] = "active"
    notes: Optional[str] = None
    property_interest: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    tag: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    property_interest: Optional[str] = None


# ────────────────────────────────────────────────────────────
# GET /api/contacts
# ────────────────────────────────────────────────────────────

@router.get("")
async def list_contacts(
    tenant_id: str = Depends(verify_session),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search name or phone"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all contacts for a tenant. Supports filtering and search."""
    try:
        supabase = get_supabase()
        q = (
            supabase.table("contacts")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("last_message_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if tag:
            q = q.eq("tag", tag)
        if status:
            q = q.eq("status", status)
        if search:
            # Supabase ilike with OR — search name or phone
            q = q.or_(f"name.ilike.%{search}%,phone.ilike.%{search}%")

        result = q.execute()
        return {"contacts": result.data, "total": len(result.data)}
    except Exception as e:
        logger.error(f"contacts list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────────────────
# POST /api/contacts
# ────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_contact(
    body: ContactCreate,
    tenant_id: str = Depends(verify_session),
):
    """Manually add a contact. Safe to call if JID already exists (upsert)."""
    if body.tag and body.tag not in VALID_TAGS:
        raise HTTPException(status_code=400, detail=f"Invalid tag. Use: {VALID_TAGS}")
    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {VALID_STATUSES}")
    try:
        supabase = get_supabase()
        data = {
            "tenant_id": tenant_id,
            "jid": body.jid,
            "phone": body.phone or body.jid.replace("@s.whatsapp.net", "").replace("@g.us", ""),
            "name": body.name,
            "tag": body.tag or "lead",
            "source": body.source or "manual",
            "status": body.status or "active",
            "notes": body.notes,
            "property_interest": body.property_interest,
        }
        result = (
            supabase.table("contacts")
            .upsert(data, on_conflict="tenant_id,jid")
            .execute()
        )
        return {"success": True, "contact": result.data[0] if result.data else data}
    except Exception as e:
        logger.error(f"contacts create error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────────────────
# GET /api/contacts/export.csv  — download all contacts as CSV
# NOTE: must be declared BEFORE /{jid:path} to avoid route shadowing
# ────────────────────────────────────────────────────────────

@router.get("/export.csv")
async def export_contacts_csv(
    tenant_id: str = Depends(verify_session),
):
    """Export all contacts for the tenant as a downloadable CSV file."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("contacts")
            .select("name,phone,jid,tag,notes,status,created_at,updated_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = result.data or []

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["name", "phone", "jid", "tag", "notes", "status", "created_at", "updated_at"],
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=bijou_contacts.csv"},
        )
    except Exception as e:
        logger.error(f"contacts export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────────────────
# POST /api/contacts/import  — bulk import contacts from CSV
# CSV must have header row: name,phone,tag,notes
# ────────────────────────────────────────────────────────────

@router.post("/import")
async def import_contacts_csv(
    file: UploadFile = File(...),
    tenant_id: str = Depends(verify_session),
):
    """Bulk-import contacts from a CSV file. Columns: name, phone, tag, notes (all optional except phone)."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    try:
        content = await file.read()
        text = content.decode("utf-8-sig")  # handles BOM from Excel exports
        reader = csv.DictReader(io.StringIO(text))

        supabase = get_supabase()
        imported = 0
        skipped = 0
        errors = []

        for i, row in enumerate(reader, start=2):  # row 2 = first data row
            phone = (row.get("phone") or row.get("Phone") or "").strip()
            if not phone:
                skipped += 1
                continue

            name = (row.get("name") or row.get("Name") or "").strip() or None
            tag = (row.get("tag") or row.get("Tag") or "lead").strip().lower()
            notes = (row.get("notes") or row.get("Notes") or "").strip() or None

            if tag not in VALID_TAGS:
                tag = "lead"

            jid_val = f"{phone}@s.whatsapp.net"
            try:
                supabase.table("contacts").upsert(
                    {
                        "tenant_id": tenant_id,
                        "jid": jid_val,
                        "phone": phone,
                        "name": name,
                        "tag": tag,
                        "notes": notes,
                        "source": "csv_import",
                        "status": "active",
                    },
                    on_conflict="tenant_id,jid",
                ).execute()
                imported += 1
            except Exception as row_err:
                errors.append({"row": i, "phone": phone, "error": str(row_err)})
                skipped += 1

        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:10],  # cap to first 10 errors
        }
    except Exception as e:
        logger.error(f"contacts import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────────────────
# PATCH /api/contacts/{jid}
# ────────────────────────────────────────────────────────────

@router.patch("/{jid:path}")
async def update_contact(
    jid: str,
    body: ContactUpdate,
    tenant_id: str = Depends(verify_session),
):
    """Update tag, notes, name, or status for a contact."""
    jid = _jid(jid)
    if body.tag and body.tag not in VALID_TAGS:
        raise HTTPException(status_code=400, detail=f"Invalid tag. Use: {VALID_TAGS}")
    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {VALID_STATUSES}")

    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        supabase = get_supabase()
        result = (
            supabase.table("contacts")
            .update(updates)
            .eq("tenant_id", tenant_id)
            .eq("jid", jid)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Contact not found")
        return {"success": True, "contact": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"contacts update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────────────────
# DELETE /api/contacts/{jid}
# ────────────────────────────────────────────────────────────

@router.delete("/{jid:path}")
async def delete_contact(
    jid: str,
    tenant_id: str = Depends(verify_session),
):
    """Remove a contact record."""
    jid = _jid(jid)
    try:
        supabase = get_supabase()
        result = (
            supabase.table("contacts")
            .delete()
            .eq("tenant_id", tenant_id)
            .eq("jid", jid)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Contact not found")
        return {"success": True, "deleted_jid": jid}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"contacts delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
