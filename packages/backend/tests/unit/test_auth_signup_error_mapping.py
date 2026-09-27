"""
Unit tests for /api/auth/signup error mapping.

Before 2026-08-09 the signup endpoint's outer `except Exception` was
mapping a narrow set of Supabase error message strings to 4xx codes
and falling through to a generic 500 for everything else. The fly-edge
proxy in front of app.mybijou.xyz returns a 500 with an empty body
when the origin takes too long or throws an uncaught exception — which
is what users were seeing.

The fix in `src/saas/auth_api.py` adds:
- specific handling for `supabase_auth.errors.AuthApiError` using its
  `.status` attribute (422 → 409, 429 → 429, 403 → 403, 400 → 400, etc.)
- a `httpx.HTTPError` branch that returns 503 (service unreachable)
- a final 500 with a `ref: <ExceptionType>` hint so the dashboard
  shows something non-vague AND we can grep Fly logs by exception class

These tests pin all of those mappings.
"""

import os
import sys
import types
import pytest
from unittest.mock import Mock, patch, MagicMock


# ---------------------------------------------------------------------------
# 2026-09-06: auth_api now performs user-scoped auth calls (sign_up,
# sign_in_with_password, set_session, refresh_session) on a DEDICATED client
# from get_auth_client(), not on the shared service-role client from
# get_supabase().
#
# That split is the fix for a P0: supabase-py rewrites
# options.headers["Authorization"] on SIGNED_IN/TOKEN_REFRESHED, so running a
# login on the shared data client replaced the service-role credential with
# that user's JWT for the whole worker process. See
# tests/unit/test_auth_client_isolation.py.
#
# These tests assert on signup/login error mapping and response shape, not on
# which client object is used, so they keep patching get_supabase and this
# fixture points get_auth_client at the same mock. Resolution is deferred to
# call time so it picks up whatever `with patch(...)` is currently active.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _auth_client_uses_patched_supabase(monkeypatch):
    import src.saas.auth_api as _auth_api
    monkeypatch.setattr(
        _auth_api, "get_auth_client", lambda: _auth_api.get_supabase(), raising=False
    )


# These tests call signup() directly with no `http_request`, so every call in
# this file shares the same "unknown"-IP bucket (see _check_signup_rate_limit,
# 2026-09-18). Without resetting between tests, whichever test runs 6th here
# gets a spurious 429 instead of the error it's actually pinning — same
# reasoning as bijou.py's _reset_webhook_rate_limits for its own tests.
@pytest.fixture(autouse=True)
def _reset_signup_rate_limit_between_tests():
    import src.saas.auth_api as _auth_api
    _auth_api._reset_signup_rate_limit()
    yield
    _auth_api._reset_signup_rate_limit()


if "supabase" not in sys.modules:
    supabase_stub = types.ModuleType("supabase")
    setattr(supabase_stub, "create_client", lambda *args, **kwargs: None)
    setattr(supabase_stub, "Client", object)
    sys.modules["supabase"] = supabase_stub

# Fake supabase_auth.errors so the `from supabase_auth.errors import AuthApiError`
# import in auth_api.py resolves to a real class we can raise.
if "supabase_auth" not in sys.modules:
    sa = types.ModuleType("supabase_auth")
    sa_errors = types.ModuleType("supabase_auth.errors")

    class AuthApiError(Exception):
        """Fake stand-in for supabase_auth.errors.AuthApiError.

        The signature MIRRORS the real one exactly — (message, status, code),
        all required — and that is load-bearing. The fake is only installed
        when supabase_auth is not already in sys.modules, so running this file
        alone gets the fake while running the whole suite gets the REAL class
        (something else imports it first). A more forgiving fake therefore
        hides real breakage: two tests here passed alone and raised

            TypeError: AuthApiError.__init__() missing 1 required positional
            argument: 'code'

        in the suite, because supabase_auth 2.31.0 requires `code` and the
        old fake defaulted it to None.
        """
        def __init__(self, message, status, code):
            super().__init__(message)
            self.status = status
            self.code = code

    sa_errors.AuthApiError = AuthApiError
    sys.modules["supabase_auth"] = sa
    sys.modules["supabase_auth.errors"] = sa_errors

from fastapi import HTTPException  # noqa: E402

from src.saas import auth_api  # noqa: E402
from src.saas.auth_api import SignupRequest, signup  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _make_db():
    """Build a minimal fake supabase client. Only the methods the signup
    flow actually calls (or that the outer except handler expects) need
    to exist — everything else stays as a MagicMock so chained calls
    don't blow up."""
    db = MagicMock()
    db.auth.sign_up = MagicMock()
    # The cascade after sign_up uses these — leave them no-op so the
    # tests that DO want sign_up to succeed (and proceed into the
    # tenant/tenant_users cascade) get a clean run.
    db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
    return db


async def _raise(signup_exc):
    """Run the signup endpoint and surface whatever HTTPException it raises."""
    with patch("src.saas.auth_api.get_supabase", return_value=_make_db()):
        with patch("src.saas.auth_api.TenantManager") as tm_cls:
            tm = MagicMock()
            tm.create_tenant.return_value = None  # will fail before this matters
            tm_cls.return_value = tm
            try:
                await signup(SignupRequest(
                    email="test@example.com",
                    password="test1234",
                    business_name="Test Co",
                    phone="+60123456789",
                ))
            except HTTPException as http_exc:
                return http_exc
    return None


# ─────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signup_already_registered_returns_409():
    """AuthApiError(status=422, message="User already registered") → 409."""
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        db.auth.sign_up.side_effect = auth_api.AuthApiError(
            "User already registered", status=422, code="user_already_exists"
        )
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager"):
            with pytest.raises(HTTPException) as ei:
                await signup(SignupRequest(
                    email="dup@example.com",
                    password="test1234",
                    business_name="Dup Co",
                    phone="+60123456789",
                ))
    assert ei.value.status_code == 409
    assert "already exists" in ei.value.detail.lower()


@pytest.mark.asyncio
async def test_signup_rate_limited_returns_429():
    """AuthApiError(status=429, code=over_request_rate_limit) → 429."""
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        db.auth.sign_up.side_effect = auth_api.AuthApiError(
            "Request rate limit reached", status=429, code="over_request_rate_limit"
        )
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager"):
            with pytest.raises(HTTPException) as ei:
                await signup(SignupRequest(
                    email="rl@example.com",
                    password="test1234",
                    business_name="RL Co",
                    phone="+60123456789",
                ))
    assert ei.value.status_code == 429
    assert "too many" in ei.value.detail.lower() or "rate" in ei.value.detail.lower()


async def _signup_raising(sign_up_exc):
    db = _make_db()
    db.auth.sign_up.side_effect = sign_up_exc
    with patch("src.saas.auth_api.get_supabase", return_value=db), patch("src.saas.auth_api.TenantManager"):
        with pytest.raises(HTTPException) as ei:
            await signup(SignupRequest(
                email="x@example.com", password="test1234",
                business_name="X Co", phone="+60123456789",
            ))
    return ei.value


@pytest.mark.asyncio
async def test_signup_email_send_limit_is_503_not_blame_the_user():
    """over_email_send_rate_limit is Supabase's PROJECT-WIDE confirmation-email
    cap. Production returned it on a first-ever signup (2026-09-28) and the
    user was told "wait a minute" — untrue; it resets hourly and is not theirs."""
    exc = await _signup_raising(auth_api.AuthApiError(
        "email rate limit exceeded", status=429, code="over_email_send_rate_limit"
    ))
    assert exc.status_code == 503
    assert "verification email" in exc.detail
    assert "minute" not in exc.detail


@pytest.mark.asyncio
async def test_signup_weak_password_error_subclass_returns_400_not_500():
    """supabase-py raises AuthWeakPasswordError (a CustomAuthError, NOT an
    AuthApiError, status 422). It fell through to 500 on production."""
    class AuthWeakPasswordError(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.status, self.code = 422, "weak_password"

    exc = await _signup_raising(AuthWeakPasswordError("Password should be at least 6 characters."))
    assert exc.status_code == 400
    assert "already exists" not in exc.detail


@pytest.mark.asyncio
async def test_signup_signups_disabled_returns_403():
    """AuthApiError(status=403, message="Signups not allowed") → 403."""
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        db.auth.sign_up.side_effect = auth_api.AuthApiError(
            "Signups not allowed", status=403, code="signup_disabled"
        )
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager"):
            with pytest.raises(HTTPException) as ei:
                await signup(SignupRequest(
                    email="new@example.com",
                    password="test1234",
                    business_name="New Co",
                    phone="+60123456789",
                ))
    assert ei.value.status_code == 403
    assert "disabled" in ei.value.detail.lower() or "signups" in ei.value.detail.lower()


@pytest.mark.asyncio
async def test_signup_weak_password_returns_400():
    """AuthApiError(status=400, message="Password should be at least 6 characters") → 400."""
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        db.auth.sign_up.side_effect = auth_api.AuthApiError(
            "Password should be at least 6 characters", status=400, code="weak_password"
        )
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager"):
            with pytest.raises(HTTPException) as ei:
                await signup(SignupRequest(
                    email="weak@example.com",
                    password="123",
                    business_name="Weak Co",
                    phone="+60123456789",
                ))
    assert ei.value.status_code == 400
    assert "password" in ei.value.detail.lower()


@pytest.mark.asyncio
async def test_signup_legacy_string_match_rate_limit_returns_429():
    """Old (pre-2.x supabase-py) error string "rate limit" still maps to 429."""
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        # Plain Exception, not AuthApiError, to test the string-match fallback.
        db.auth.sign_up.side_effect = RuntimeError("Email rate limit exceeded")
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager"):
            with pytest.raises(HTTPException) as ei:
                await signup(SignupRequest(
                    email="rl2@example.com",
                    password="test1234",
                    business_name="RL2 Co",
                    phone="+60123456789",
                ))
    assert ei.value.status_code == 429


@pytest.mark.asyncio
async def test_signup_network_error_returns_503():
    """httpx network errors → 503, not 500."""
    import httpx as real_httpx
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        db.auth.sign_up.side_effect = real_httpx.ConnectError("Connection refused")
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager"):
            with pytest.raises(HTTPException) as ei:
                await signup(SignupRequest(
                    email="net@example.com",
                    password="test1234",
                    business_name="Net Co",
                    phone="+60123456789",
                ))
    assert ei.value.status_code == 503
    assert "unreachable" in ei.value.detail.lower() or "service" in ei.value.detail.lower()


@pytest.mark.asyncio
async def test_signup_unknown_error_returns_500_with_ref():
    """Unknown exception → 500 with a `ref: <ExceptionType>` hint for log correlation."""
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        db.auth.sign_up.side_effect = ValueError("Some unexpected supabase quirk")
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager"):
            with pytest.raises(HTTPException) as ei:
                await signup(SignupRequest(
                    email="odd@example.com",
                    password="test1234",
                    business_name="Odd Co",
                    phone="+60123456789",
                ))
    assert ei.value.status_code == 500
    assert "ref: ValueError" in ei.value.detail


# ─────────────────────────────────────────────────────────────────────
# Regression: email-confirmation-pending must NOT be reported as
# "account already exists" (the 2026-08-10 signup outage).
#
# This project runs with GoTrue mailer_autoconfirm=false, so a brand-new
# successful signup returns session=None. The old code read that as
# "email already exists", returned 409, and deleted the tenant — which
# rejected 100% of new registrations and stranded the auth user.
# ─────────────────────────────────────────────────────────────────────

def _signup_response(identities, session):
    """Fake supabase auth.sign_up return value."""
    user = MagicMock()
    user.id = "user-abc"
    user.identities = identities
    resp = MagicMock()
    resp.user = user
    resp.session = session
    return resp


@pytest.mark.asyncio
async def test_signup_pending_confirmation_succeeds_and_keeps_tenant():
    """New user + confirmation required (session=None, one identity)
    → 200 with email_confirmation_required=True, tenant preserved."""
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        db.auth.sign_up.return_value = _signup_response(
            identities=[{"provider": "email"}], session=None,
        )
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager") as tm_cls:
            tm = MagicMock()
            tm.create_tenant.return_value = "tenant-123"
            tm_cls.return_value = tm
            result = await signup(SignupRequest(
                email="brand.new@example.com",
                password="test1234",
                business_name="Brand New Co",
                phone="+60123456789",
            ))

    assert result.email_confirmation_required is True
    assert result.access_token is None
    assert result.tenant_id == "tenant-123"
    # The tenant must survive — deleting it is what stranded users before.
    assert not db.table.return_value.delete.called


@pytest.mark.asyncio
async def test_signup_existing_email_looks_identical_to_pending_confirmation():
    """Existing email → GoTrue returns identities == [].

    2026-09-18 FIX: this used to raise 409 "An account with this email
    already exists" — a plain email-enumeration oracle (POST candidate
    emails, 409 vs 200 tells you which are registered). It must now respond
    with the EXACT SAME SHAPE as a genuine new signup awaiting email
    confirmation (see test_signup_pending_confirmation_succeeds_and_keeps_tenant
    above): 200, access_token=None, email_confirmation_required=True, and a
    tenant_id that is *some* string (a throwaway UUID here, since there's no
    real tenant to point at) rather than null — a null-vs-populated
    tenant_id would itself be a distinguishing signal.
    """
    with patch("src.saas.auth_api.get_supabase") as gs:
        db = _make_db()
        db.auth.sign_up.return_value = _signup_response(
            identities=[], session=None,
        )
        gs.return_value = db
        with patch("src.saas.auth_api.TenantManager") as tm_cls:
            tm = MagicMock()
            tm_cls.return_value = tm
            result = await signup(SignupRequest(
                email="taken@example.com",
                password="test1234",
                business_name="Taken Co",
                phone="+60123456789",
            ))

    assert result.email_confirmation_required is True
    assert result.access_token is None
    assert result.refresh_token is None
    assert isinstance(result.tenant_id, str) and result.tenant_id
    assert result.email == "taken@example.com"
    # No tenant/tenant_users row is created for someone else's account.
    tm.create_tenant.assert_not_called()
    db.table.return_value.insert.assert_not_called()
    # The actual account owner gets a password-reset email instead.
    db.auth.reset_password_email.assert_called_once()
    assert db.auth.reset_password_email.call_args.kwargs["email"] == "taken@example.com"
