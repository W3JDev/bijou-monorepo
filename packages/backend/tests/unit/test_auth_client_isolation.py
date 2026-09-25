"""The shared service-role Supabase client must never inherit a user session.

The bug
-------
`get_supabase()` (src/core/dashboard_api_simple.py:156) returns a process-wide
singleton created with the **service-role** key. Every `.table(...)` call in
the backend goes through it, and RLS was hardened so that `service_role` is the
only role that can read or write (ops/_fix_rls_v6.js dropped every permissive
public-role policy).

`src/saas/auth_api.py` performed user-scoped auth operations on that same
singleton — `sign_in_with_password` (:554), `set_session` (:761),
`refresh_session` (:101). supabase-py's `Client._listen_to_auth_events`
rewrites `options.headers["Authorization"]` and drops the cached PostgREST
client on SIGNED_IN / TOKEN_REFRESHED / SIGNED_OUT, so a successful login
replaced the service-role credential with that user's JWT for the whole worker
process.

Measured on the repo's own venv before the fix:

    login   before: Bearer SERVICE-ROLE-KEY-AAA
    login   after : Bearer eyJhbGciOiAiSFMyNTYiL...   <-- the user's JWT
    BEFORE postgrest Authorization: Bearer SERVICE-ROLE-KEY-AAA
    AFTER  postgrest Authorization: Bearer eyJhbGciOiAiSFMyNTYiL...

Nothing restores it, so every later request handled by that worker — other
tenants' dashboards, the WhatsApp webhook, the schedulers — authorized as that
one user until the next login.

Note the `change-password` path behaves differently and is NOT the bug: its
`update_user` call fires USER_UPDATED, which supabase-py maps back to the
service key, so the success path self-heals. Only the error path leaks. Login
is the real trigger, and it leaks every single time.

These tests pin the invariant rather than any one call site: auth work happens
on a client of its own, and the data client's credential never moves.
"""

import base64
import json
import time

import pytest

from src.core.dashboard_api_simple import get_supabase
from src.saas.auth_api import get_auth_client


SERVICE_KEY = "SERVICE-ROLE-KEY-FOR-TEST"


def _fake_user_jwt() -> str:
    def seg(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")

    return ".".join([
        seg({"alg": "HS256", "typ": "JWT"}),
        seg({"sub": "11111111-1111-1111-1111-111111111111",
             "exp": int(time.time()) + 3600}),
        "signature",
    ])


@pytest.fixture
def supabase_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", SERVICE_KEY)
    # Reset both module singletons so each test gets a clean process state.
    import src.core.dashboard_api_simple as dash
    import src.saas.auth_api as auth
    monkeypatch.setattr(dash, "_dashboard_supabase_client", None, raising=False)
    monkeypatch.setattr(auth, "_auth_supabase_client", None, raising=False)
    yield


def _auth_header(client) -> str:
    return client.options.headers.get("Authorization", "")


def test_auth_client_is_not_the_shared_data_client(supabase_env):
    """The whole point: auth work must not run on the data client."""
    assert get_auth_client() is not get_supabase(), (
        "auth operations are running on the shared service-role data client; "
        "a successful login will overwrite its credential process-wide"
    )


def test_data_client_keeps_service_role_after_auth_client_signs_in(supabase_env):
    """The actual regression, expressed as the invariant that was broken."""
    from supabase_auth.types import Session, User, UserResponse

    data_client = get_supabase()
    auth_client = get_auth_client()

    before = _auth_header(data_client)
    assert SERVICE_KEY in before, "precondition: data client starts as service_role"

    user = User(
        id="11111111-1111-1111-1111-111111111111",
        app_metadata={}, user_metadata={}, aud="authenticated",
        created_at="2026-01-01T00:00:00Z", email="victim@example.com",
    )
    auth_client.auth.get_user = lambda *a, **k: UserResponse(user=user)
    session = Session(
        access_token=_fake_user_jwt(), refresh_token="r",
        expires_in=3600, token_type="bearer", user=user,
    )

    # Exactly what a successful sign_in_with_password fires.
    auth_client.auth._notify_all_subscribers("SIGNED_IN", session)

    after = _auth_header(data_client)
    assert after == before, (
        "a login on the auth client changed the SHARED data client's "
        f"Authorization header ({before[:24]}... -> {after[:24]}...). "
        "Every subsequent query in this worker would authorize as that user."
    )
    assert SERVICE_KEY in _auth_header(data_client)

    # `options.headers` is the authorization source here, not
    # `postgrest.session.headers`. get_supabase() constructs the client with a
    # custom httpx_client (to force HTTP/1.1), and in that configuration
    # postgrest.session.headers carries no Authorization at all — verified:
    #
    #   with custom httpx_client -> postgrest hdr: None
    #   with custom httpx_client -> options  hdr: 'Bearer SERVICE-KEY'
    #   default client           -> postgrest hdr: 'Bearer SERVICE-KEY'
    #
    # supabase-py sets `self._postgrest = None` on an auth event and rebuilds it
    # lazily from options.headers, so options.headers is what a later .table()
    # call ends up authorizing with. Asserting on postgrest.session.headers
    # would pass vacuously against an empty dict.
    assert data_client._postgrest is None or SERVICE_KEY in _auth_header(data_client), (
        "the cached PostgREST client would be rebuilt from a non-service-role header"
    )


def test_auth_client_is_reused_not_rebuilt_per_call(supabase_env):
    """Guard the performance rationale that motivated the singleton.

    get_supabase()'s docstring records that create_client per call opened a
    fresh httpx pool and produced ConnectionTerminated errors under load. The
    fix must not reintroduce that by building a client on every auth request.
    """
    assert get_auth_client() is get_auth_client()
