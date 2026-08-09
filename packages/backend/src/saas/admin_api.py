"""
Bijou AI - Admin Panel API
===========================

Admin endpoints for managing tenants and WhatsApp connections.

Routes:
- GET /api/admin/tenants → List all tenants
- POST /api/admin/qr/{tenant_id} → Generate WhatsApp QR code

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel
from supabase import create_client

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ════════════════════════════════════════════════════════════════
# AUTH GATE
# ════════════════════════════════════════════════════════════════
# The admin API is for internal operator use only and exposes full
# tenant PII (phone numbers, emails, business names). It MUST NOT be
# reachable from the public internet without a shared secret.
#
# Set ADMIN_API_KEY in the environment and pass the same value as the
# `X-Admin-Key` request header. The operator stores the key in
# `localStorage.admin_api_key` on the /admin page (one-time, per browser).
#
# If ADMIN_API_KEY is unset, the admin endpoints return 503 — never 200.
# This is a behavior change: the legacy open endpoints are now locked.
# To re-enable, set ADMIN_API_KEY and reload the operator's browser
# with the key in localStorage.admin_api_key.


def _check_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        # Fail closed: refusing service is safer than leaking tenant PII.
        raise HTTPException(
            status_code=503,
            detail="Admin API not configured. Set ADMIN_API_KEY env var.",
        )
    # Constant-time-ish compare. Not perfect, but no early-return timing leak.
    if not x_admin_key or not _secrets_equal(x_admin_key.strip(), expected):
        raise HTTPException(status_code=401, detail="Missing or invalid X-Admin-Key")


def _secrets_equal(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a.encode(), b.encode())


# ════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════


class TenantInfo(BaseModel):
    """Tenant information for admin panel"""

    id: str
    business_name: Optional[str] = None  # ✅ BUG 3 FIX: Allow NULL for existing records
    email: Optional[str] = None           # ✅ BUG 3 FIX: Allow NULL for existing records
    phone: Optional[str] = None
    status: str
    whatsapp_jid: Optional[str] = None
    whatsapp_connected_at: Optional[str] = None
    onboarding_completed: bool
    created_at: str


class TenantsResponse(BaseModel):
    """Response with list of tenants"""

    tenants: List[TenantInfo]
    total: int


# ════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════


def get_supabase():
    """Get Supabase admin client"""
    supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip('"')

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

    return create_client(supabase_url, supabase_key)


def get_bridge_url() -> str:
    """Get WhatsApp bridge URL from environment"""
    bridge_url = os.getenv("BRIDGE_URL", "http://localhost:8080").rstrip("/")
    return bridge_url


def get_bridge_headers() -> dict:
    """Get headers for bridge API requests with authentication"""
    import base64
    
    headers = {"Content-Type": "application/json"}
    
    # Bridge API Key is required - format: username:password
    api_key = os.getenv("BRIDGE_API_KEY", "")
    
    if not api_key:
        logger.warning("⚠️ No BRIDGE_API_KEY configured - bridge requests will fail!")
        return headers
    
    # Check if API key is in username:password format (Basic Auth)
    if ':' in api_key:
        logger.info(f"🔐 Using Basic Auth with username: {api_key.split(':')[0]}")
        auth_str = base64.b64encode(api_key.encode()).decode()
        headers["Authorization"] = f"Basic {auth_str}"
    else:
        # Fallback to X-API-Key header
        logger.warning("⚠️ BRIDGE_API_KEY should be in username:password format")
        headers["X-API-Key"] = api_key
    
    return headers


# ════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ════════════════════════════════════════════════════════════════


@router.get("/tenants", response_model=TenantsResponse)
async def list_tenants(_: None = Depends(_check_admin_key)):
    """
    Get list of all tenants with their WhatsApp connection status

    Returns:
        TenantsResponse with tenant details
    """
    try:
        supabase = get_supabase()

        # Fetch all tenants
        result = (
            supabase.table("tenants")
            .select(
                "id, business_name, email, phone, status, whatsapp_jid, "
                "whatsapp_connected_at, onboarding_completed, created_at"
            )
            .order("created_at", desc=True)
            .execute()
        )

        logger.info(f"📊 Fetched {len(result.data)} tenants from database")

        # Create tenant info objects with error handling
        tenants = []
        for tenant_data in result.data:
            try:
                # Convert None status to 'pending'
                if not tenant_data.get("status"):
                    tenant_data["status"] = "pending"
                
                tenant_info = TenantInfo(**tenant_data)
                tenants.append(tenant_info)
            except Exception as tenant_error:
                logger.warning(f"⚠️ Skipping tenant {tenant_data.get('id')}: {tenant_error}")
                continue

        logger.info(f"✅ Returning {len(tenants)} valid tenant records")
        return TenantsResponse(tenants=tenants, total=len(tenants))

    except Exception as e:
        logger.error(f"❌ Failed to fetch tenants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch tenants: {str(e)}")


@router.post("/qr/{tenant_id}")
async def generate_qr_code(tenant_id: str, _: None = Depends(_check_admin_key)):
    """
    Generate WhatsApp QR code for a tenant

    Creates a device on the bridge and returns QR code image

    Args:
        tenant_id: UUID of the tenant

    Returns:
        PNG image of QR code
    """
    try:
        supabase = get_supabase()

        # Verify tenant exists
        tenant_result = (
            supabase.table("tenants")
            .select("id, business_name, whatsapp_connected_at")
            .eq("id", tenant_id)
            .execute()
        )

        if not tenant_result.data:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant = tenant_result.data[0]

        # Check if already connected
        if tenant.get("whatsapp_connected_at"):
            raise HTTPException(
                status_code=400,
                detail="WhatsApp already connected for this tenant"
            )

        # Get bridge URL and headers
        bridge_url = get_bridge_url()
        bridge_headers = get_bridge_headers()
        device_id = f"bijou-{tenant_id}"
        
        # Add device ID to headers (GOWA v8+ requirement)
        bridge_headers["X-Device-Id"] = device_id

        logger.info(f"🔄 Generating QR for tenant {tenant['business_name']} (device: {device_id})")
        logger.info(f"📍 Bridge URL: {bridge_url}")
        logger.info(f"📋 Headers: {', '.join([k for k in bridge_headers.keys()])}")

        # Create device and get QR from bridge
        import asyncio
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to get QR directly first
            qr_response = await client.get(
                f"{bridge_url}/qr",
                params={"device_id": device_id},
                headers=bridge_headers
            )

            logger.info(f"📥 QR GET response: {qr_response.status_code}")

            # If QR not found (404), create device first
            if qr_response.status_code == 404:
                logger.info(f"📱 Creating device {device_id} on bridge...")

                # Create device (device_id is in X-Device-Id header)
                create_response = await client.post(
                    f"{bridge_url}/api/devices",
                    json={},  # Empty body - device_id comes from header
                    headers=bridge_headers
                )

                logger.info(f"📥 Device creation response: {create_response.status_code}")

                if create_response.status_code not in [200, 201]:
                    error_detail = create_response.text
                    logger.error(f"❌ Device creation failed ({create_response.status_code}): {error_detail}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create device: {error_detail}"
                    )

                logger.info(f"✅ Device created, fetching QR...")

                # Wait a moment for QR to be ready
                await asyncio.sleep(2)

                # Get QR again
                qr_response = await client.get(
                    f"{bridge_url}/qr",
                    params={"device_id": device_id},
                    headers=bridge_headers
                )

            if qr_response.status_code == 200:
                # Store device record in database
                try:
                    device_data = {
                        "tenant_id": tenant_id,
                        "device_id": device_id,
                        "device_name": tenant["business_name"],
                        "status": "pending",
                        "created_at": datetime.utcnow().isoformat(),
                    }
                    supabase.table("whatsapp_devices").upsert(device_data).execute()
                    logger.info(f"✅ Device record stored for {device_id}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Could not store device record: {db_error}")

                # Return QR code image
                logger.info(f"✅ Returning QR code for {device_id}")
                return Response(
                    content=qr_response.content,
                    media_type="image/png",
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    },
                )
            else:
                error_detail = qr_response.text
                logger.error(f"❌ QR fetch failed ({qr_response.status_code}): {error_detail}")
                logger.error(f"❌ Bridge URL was: {bridge_url}/qr?device_id={device_id}")
                raise HTTPException(
                    status_code=qr_response.status_code,
                    detail=f"Failed to generate QR code: {error_detail}"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ QR generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"QR generation failed: {str(e)}"
        )


# ════════════════════════════════════════════════════════════════
# TEMPLATE SEEDING ENDPOINT
# ════════════════════════════════════════════════════════════════


class SeedTemplatesRequest(BaseModel):
    """Request body for seeding official templates."""
    tenant_id: str


@router.post("/seed-templates")
async def seed_official_templates(body: SeedTemplatesRequest, _: None = Depends(_check_admin_key)) -> Dict[str, Any]:
    """
    Idempotently seed Bijou-official message templates for a tenant.

    Calls `seed_bijou_official_templates` from `template_seeder.py`.
    Safe to call multiple times — already-existing templates are skipped.

    Args:
        body: JSON body with ``tenant_id`` field.

    Returns:
        Dict with ``seeded``, ``skipped``, and ``warnings`` counts/list.
    """
    try:
        from src.saas.template_seeder import seed_bijou_official_templates

        supabase = get_supabase()
        result = await seed_bijou_official_templates(supabase, body.tenant_id)
        logger.info(
            f"✅ Seed templates complete for tenant {body.tenant_id}: {result}"
        )
        return {"status": "ok", **result}
    except Exception as exc:
        logger.error(f"❌ Seed templates endpoint failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Template seeding failed: {str(exc)}",
        )


# ════════════════════════════════════════════════════════════════
# DOCUMENT TEMPLATES ENDPOINTS
# ════════════════════════════════════════════════════════════════

import glob
import pathlib

_TEMPLATES_DIR = pathlib.Path(__file__).parent.parent.parent / "bijou_templates" / "official"


@router.get("/templates/documents")
async def list_document_templates(_: None = Depends(_check_admin_key)) -> Dict[str, Any]:
    """
    List all official document templates available in `bijou_templates/official/`.

    Returns:
        Dict with ``templates`` list, each entry containing ``slug`` and ``filename``.
    """
    try:
        if not _TEMPLATES_DIR.exists():
            return {"templates": []}

        md_files = list(_TEMPLATES_DIR.glob("*.md"))
        templates = [
            {"slug": f.stem, "filename": f.name}
            for f in sorted(md_files)
        ]
        return {"templates": templates, "total": len(templates)}
    except Exception as exc:
        logger.error(f"❌ list_document_templates failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/templates/documents/{slug}")
async def get_document_template(slug: str, _: None = Depends(_check_admin_key)) -> Dict[str, Any]:
    """
    Return the raw Markdown content of an official document template.

    Args:
        slug: Template slug (filename without `.md` extension).

    Returns:
        Dict with ``slug``, ``filename``, and ``content`` fields.
    """
    try:
        target = _TEMPLATES_DIR / f"{slug}.md"
        if not target.exists() or not target.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Template '{slug}' not found"
            )
        content = target.read_text(encoding="utf-8")
        return {"slug": slug, "filename": target.name, "content": content}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ get_document_template failed (slug={slug}): {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

