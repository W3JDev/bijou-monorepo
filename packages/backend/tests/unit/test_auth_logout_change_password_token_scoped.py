"""
Regression tests for /api/auth/logout and /api/auth/change-password.

The bug (found during the 2026-09-18 onboarding/signup/signin audit):
`logout()` extracted the caller's Bearer token but never used it — it called
`get_auth_client().auth.sign_out()` with no arguments, which acts on whatever
session happens to be cached on that process-wide shared client (see its
docstring in auth_api.py), not on the caller's own token. Two failure modes:
  1. No ambient session cached -> sign_out() silently no-ops; the caller's
     token stays valid until natural expiry regardless of clicking "log out".
  2. A different concurrent request populated the ambient session -> logout
     revokes THAT session instead of the caller's.

`change_password()` had the analogous problem: it called `set_session(token,
"")` on the same shared client before `update_user(...)`, mutating shared
ambient state for the duration of the call.

The fix makes both endpoints token-scoped instead of ambient-session-scoped:
- logout: `get_auth_client().auth.admin.sign_out(token, "global")` revokes
  exactly the token passed in, via a one-off request, without touching
  session storage.
- change_password: resolve the user id via the already-stateless
  `db.auth.get_user(token)` (same pattern `/api/auth/me` uses), then
  `db.auth.admin.update_user_by_id(user_id, {...})` — no set_session call.

These tests pin: the exact token reaches the exact admin call, and the
ambient-session methods (bare `sign_out()`, `set_session()`) are never
invoked.
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

from fastapi import HTTPException  # noqa: E402

from src.saas import auth_api  # noqa: E402
from src.saas.auth_api import ChangePasswordRequest, change_password, logout  # noqa: E402


TOKEN = "caller-own-access-token"


@pytest.mark.asyncio
async def test_logout_revokes_exactly_the_callers_token(monkeypatch):
    fake_auth_client = MagicMock()
    monkeypatch.setattr(auth_api, "get_auth_client", lambda: fake_auth_client)

    result = await logout(authorization=f"Bearer {TOKEN}")

    assert result == {"message": "Logged out successfully"}
    fake_auth_client.auth.admin.sign_out.assert_called_once_with(TOKEN, "global")
    # The old, buggy call must be gone.
    fake_auth_client.auth.sign_out.assert_not_called()


@pytest.mark.asyncio
async def test_logout_without_bearer_token_is_401(monkeypatch):
    fake_auth_client = MagicMock()
    monkeypatch.setattr(auth_api, "get_auth_client", lambda: fake_auth_client)

    with pytest.raises(HTTPException) as exc_info:
        await logout(authorization=None)

    assert exc_info.value.status_code == 401
    fake_auth_client.auth.admin.sign_out.assert_not_called()


@pytest.mark.asyncio
async def test_logout_swallows_already_invalid_token(monkeypatch):
    """An expired/already-revoked token is still a successful logout for the
    caller — matches the leniency the old `with suppress(AuthApiError)` gave."""
    fake_auth_client = MagicMock()
    fake_auth_client.auth.admin.sign_out.side_effect = auth_api.AuthApiError(
        "invalid token", 401, "bad_jwt"
    )
    monkeypatch.setattr(auth_api, "get_auth_client", lambda: fake_auth_client)

    result = await logout(authorization=f"Bearer {TOKEN}")

    assert result == {"message": "Logged out successfully"}


@pytest.mark.asyncio
async def test_change_password_updates_by_resolved_user_id_not_ambient_session(monkeypatch):
    fake_user = MagicMock()
    fake_user.id = "11111111-1111-1111-1111-111111111111"

    fake_db = MagicMock()
    fake_db.auth.get_user.return_value = MagicMock(user=fake_user)
    fake_db.auth.admin.update_user_by_id.return_value = MagicMock(user=fake_user)

    monkeypatch.setattr(auth_api, "get_supabase", lambda: fake_db)

    result = await change_password(
        ChangePasswordRequest(new_password="new-password-123"),
        authorization=f"Bearer {TOKEN}",
    )

    assert result["success"] is True
    fake_db.auth.get_user.assert_called_once_with(TOKEN)
    fake_db.auth.admin.update_user_by_id.assert_called_once_with(
        str(fake_user.id), {"password": "new-password-123"}
    )
    # The old, ambient-session-mutating call must be gone.
    fake_db.auth.set_session.assert_not_called()


@pytest.mark.asyncio
async def test_change_password_rejects_invalid_token_before_updating(monkeypatch):
    fake_db = MagicMock()
    fake_db.auth.get_user.return_value = MagicMock(user=None)
    monkeypatch.setattr(auth_api, "get_supabase", lambda: fake_db)

    with pytest.raises(HTTPException) as exc_info:
        await change_password(
            ChangePasswordRequest(new_password="new-password-123"),
            authorization=f"Bearer {TOKEN}",
        )

    assert exc_info.value.status_code == 401
    fake_db.auth.admin.update_user_by_id.assert_not_called()
