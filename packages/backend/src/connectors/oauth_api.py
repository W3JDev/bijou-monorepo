"""FastAPI router for per-tenant Composio OAuth connect/status.

Mount in the main app, wiring the tenant-auth dependency to the app's session
verifier so tenant_id comes from the authenticated session (never the client):

    from src.connectors.oauth_api import router as connectors_router, require_tenant
    from src.core.dashboard_api_simple import verify_session
    app.dependency_overrides[require_tenant] = verify_session
    app.include_router(connectors_router)

NOTE: connector methods are unit-tested and the HTTP layer is TestClient-tested,
but the live Composio OAuth round-trip + Supabase persistence must be exercised on
staging (needs a valid COMPOSIO_API_KEY + applied migration).
"""
from __future__ import annotations
import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.connectors.composio_connector import ComposioConnector
from src.connectors.auth_configs import auth_config_id, supported_toolkits

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connectors", tags=["connectors"])


async def require_tenant() -> str:
    """Auth dependency returning the authenticated tenant_id.

    This is a placeholder that FAILS CLOSED. The app must override it with the
    core session verifier (see module docstring); otherwise every protected
    endpoint returns an error rather than trusting client input. Overriding via
    FastAPI's dependency_overrides keeps this package decoupled from the large
    dashboard module and keeps tenant_id server-authoritative (no IDOR).
    """
    raise RuntimeError(
        "require_tenant is not configured: app must override it with verify_session")


class InitiateRequest(BaseModel):
    toolkit: str  # canonical slug, e.g. 'googlesheets'; tenant comes from the session


def _supabase():
    """Return a Supabase client (service role). Matches src/core/bijou.py:get_supabase().
    Kept as a thin indirection so tests can patch it."""
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


@router.get("/toolkits")
async def list_supported_toolkits():
    """Toolkits that have an auth-config configured and can be connected."""
    return {"toolkits": supported_toolkits()}


@router.post("/initiate")
async def initiate(req: InitiateRequest, tenant_id: str = Depends(require_tenant)):
    """Begin OAuth for the authenticated tenant + a toolkit; returns the redirect_url."""
    ac_id = auth_config_id(req.toolkit)
    if not ac_id:
        raise HTTPException(status_code=400, detail=f"No auth config for toolkit '{req.toolkit}'")

    callback_url = os.getenv("COMPOSIO_OAUTH_CALLBACK_URL")
    connector = ComposioConnector()
    result = connector.initiate_connection(tenant_id, ac_id, callback_url=callback_url)
    if "error" in result:
        logger.error("Composio initiate failed for tenant=%s toolkit=%s: %s",
                     tenant_id, req.toolkit, result["error"])
        raise HTTPException(status_code=502, detail="Could not start connection with Composio")

    # Persist the pending connection (upsert on tenant+toolkit).
    try:
        _supabase().table("composio_connections").upsert({
            "tenant_id": tenant_id,
            "toolkit": req.toolkit,
            "connection_id": result["connection_id"],
            "auth_config_id": ac_id,
            "status": result.get("status", "INITIATED"),
        }, on_conflict="tenant_id,toolkit").execute()
    except Exception as e:  # persistence failure shouldn't lose the redirect
        logger.error("Failed to persist composio_connections row: %s", e)

    return {"redirect_url": result["redirect_url"], "connection_id": result["connection_id"]}


@router.get("/status/{connection_id}")
async def status(connection_id: str, tenant_id: str = Depends(require_tenant)):
    """Poll a connection's status — only if it belongs to the authenticated tenant."""
    sup = _supabase()

    # Ownership check: the connection must belong to this tenant (prevents
    # polling another tenant's connection id).
    try:
        row = (sup.table("composio_connections")
               .select("tenant_id").eq("connection_id", connection_id).limit(1).execute())
    except Exception as e:
        logger.error("Ownership lookup failed for %s: %s", connection_id, e)
        raise HTTPException(status_code=502, detail="Could not verify connection")
    if not row.data or row.data[0]["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="Connection not found")

    state = ComposioConnector().connection_status(connection_id)
    try:  # best-effort DB sync, scoped to this tenant
        (sup.table("composio_connections").update({"status": state})
         .eq("connection_id", connection_id).eq("tenant_id", tenant_id).execute())
    except Exception as e:
        logger.warning("Failed to sync connection status: %s", e)
    return {"connection_id": connection_id, "status": state}
