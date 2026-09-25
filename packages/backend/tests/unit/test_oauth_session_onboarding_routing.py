"""A brand-new tenant signing in via Google must be routed to onboarding too.

The bug
-------
`/api/auth/login` (email/password) computes `next_url` via
`_onboarding_redirect_for` so a tenant that hasn't connected WhatsApp yet gets
sent to `/onboard/{token}` instead of an empty dashboard
(test_login_onboarding_routing.py covers that path). `/api/auth/oauth_session`
— the endpoint `static/auth-callback.html` calls after Google's native
Supabase OAuth round-trip — never made this call at all, and
auth-callback.html unconditionally did `window.location.href = "/dashboard"`.
So a brand-new user who signed in with Google (the *correct*, Supabase-native
Google flow, not the legacy `/api/auth/google/login`) landed on an empty
dashboard with no QR prompt, same class of bug `/api/auth/login` was already
fixed for.

The fix makes `oauth_session` call `_onboarding_redirect_for` exactly like
`login` does, and return it as `next_url`; auth-callback.html then does
`window.location.href = data.next_url || "/dashboard"`, mirroring login.html.
"""

import sys
import types

import pytest
from unittest.mock import MagicMock

if "supabase" not in sys.modules:
    supabase_stub = types.ModuleType("supabase")
    setattr(supabase_stub, "create_client", lambda *args, **kwargs: None)
    setattr(supabase_stub, "Client", object)
    sys.modules["supabase"] = supabase_stub

if "supabase_auth" not in sys.modules:
    sa = types.ModuleType("supabase_auth")
    sa_errors = types.ModuleType("supabase_auth.errors")

    class AuthApiError(Exception):
        def __init__(self, message, status, code):
            super().__init__(message)
            self.status = status
            self.code = code

    sa_errors.AuthApiError = AuthApiError
    sys.modules["supabase_auth"] = sa
    sys.modules["supabase_auth.errors"] = sa_errors

from src.saas import auth_api  # noqa: E402
from src.saas.auth_api import oauth_session  # noqa: E402


TOKEN = "google-access-token"
TENANT_ID = "tenant-1"


def _fake_db(biz_data):
    db = MagicMock()
    db.auth.get_user.return_value = MagicMock(
        user=MagicMock(id="user-1", email="new@example.com"), session=None
    )
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=biz_data
    )
    return db


@pytest.mark.asyncio
async def test_oauth_session_routes_unconnected_tenant_to_onboarding(monkeypatch):
    db = _fake_db([{"business_name": "Test Co"}])
    monkeypatch.setattr(auth_api, "get_supabase", lambda: db)
    monkeypatch.setattr(auth_api, "_resolve_or_link_tenant", lambda *a, **k: TENANT_ID)
    monkeypatch.setattr(
        auth_api, "_onboarding_redirect_for",
        lambda _db, tenant_id: f"https://app.mybijou.xyz/onboard/tok-{tenant_id}",
    )

    result = await oauth_session(authorization=f"Bearer {TOKEN}")

    assert result["tenant_id"] == TENANT_ID
    assert result["next_url"] == f"https://app.mybijou.xyz/onboard/tok-{TENANT_ID}"


@pytest.mark.asyncio
async def test_oauth_session_returns_none_next_url_for_connected_tenant(monkeypatch):
    db = _fake_db([{"business_name": "Test Co"}])
    monkeypatch.setattr(auth_api, "get_supabase", lambda: db)
    monkeypatch.setattr(auth_api, "_resolve_or_link_tenant", lambda *a, **k: TENANT_ID)
    monkeypatch.setattr(auth_api, "_onboarding_redirect_for", lambda _db, _tid: None)

    result = await oauth_session(authorization=f"Bearer {TOKEN}")

    assert result["next_url"] is None


@pytest.mark.asyncio
async def test_oauth_session_provisions_tenant_for_new_google_user(monkeypatch):
    """D-AUTH-1: a first-time Google user (no tenant yet) must be provisioned a
    tenant + tenant_users owner row and get a 200 with an onboarding next_url,
    not the old 404 'Please sign up first.'"""
    db = _fake_db([{"business_name": "newco"}])
    monkeypatch.setattr(auth_api, "get_supabase", lambda: db)
    # No tenant resolves for this brand-new Google account.
    monkeypatch.setattr(auth_api, "_resolve_or_link_tenant", lambda *a, **k: None)
    # create_tenant() mints the workspace without touching a real DB.
    fake_tm = MagicMock()
    fake_tm.create_tenant.return_value = "new-tenant"
    monkeypatch.setattr(auth_api, "TenantManager", lambda _db: fake_tm)
    monkeypatch.setattr(
        auth_api, "_onboarding_redirect_for",
        lambda _db, tenant_id: f"https://app.mybijou.xyz/onboard/tok-{tenant_id}",
    )

    result = await oauth_session(authorization=f"Bearer {TOKEN}")

    assert result["tenant_id"] == "new-tenant"
    assert result["next_url"] == "https://app.mybijou.xyz/onboard/tok-new-tenant"
    fake_tm.create_tenant.assert_called_once()
    # tenant_users owner row written with the same column shape as signup().
    payload = db.table.return_value.insert.call_args.args[0]
    assert payload["tenant_id"] == "new-tenant"
    assert payload["user_id"] == "user-1"
    assert payload["role"] == "owner"


@pytest.mark.asyncio
async def test_oauth_session_existing_tenant_does_not_provision(monkeypatch):
    """A Google user who already has a tenant must be unchanged: no new tenant
    created (login path preserved)."""
    db = _fake_db([{"business_name": "Test Co"}])
    monkeypatch.setattr(auth_api, "get_supabase", lambda: db)
    monkeypatch.setattr(auth_api, "_resolve_or_link_tenant", lambda *a, **k: TENANT_ID)
    fake_tm = MagicMock()
    monkeypatch.setattr(auth_api, "TenantManager", lambda _db: fake_tm)
    monkeypatch.setattr(auth_api, "_onboarding_redirect_for", lambda _db, _tid: None)

    result = await oauth_session(authorization=f"Bearer {TOKEN}")

    assert result["tenant_id"] == TENANT_ID
    fake_tm.create_tenant.assert_not_called()
