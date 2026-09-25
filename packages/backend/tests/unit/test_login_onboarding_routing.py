"""A new tenant must be routed to onboarding after login, not to the dashboard.

The bug
-------
`static/login.html:555` sent every successful email/password login to
`/dashboard`, unconditionally. Nothing in login.html or dashboard.html ever
looked at whether the tenant had finished onboarding, so a brand-new user who
had never scanned the WhatsApp QR landed on an empty dashboard with no prompt
and no way to discover the connect flow. Reported from the browser as
"after i sign up it brought me to login page ... nothing is happening".

The Google sign-in path already did this correctly
(`src/saas/google_oauth.py:210`): it reads `whatsapp_connected_at` and
redirects to `/onboard/{signup_token}` when WhatsApp is not connected, and to
`/dashboard` when it is. So the two sign-in methods disagreed — Google users
got onboarding, email/password users did not.

The fix puts the decision on the server, in the login response, so both paths
share one rule instead of duplicating it in JavaScript.
"""

import pytest

from src.saas.auth_api import _onboarding_redirect_for


class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeDB:
    """Just enough Supabase surface for _onboarding_redirect_for."""

    def __init__(self, row, *, on_update=None):
        self._row = row
        self._on_update = on_update
        self.updated = None

    def table(self, _name):
        return self

    def select(self, *_a, **_k):
        return self

    def update(self, payload):
        self.updated = payload
        if self._on_update:
            self._on_update(payload)
        return self

    def eq(self, *_a, **_k):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return _Resp(self._row)


def test_unconnected_tenant_is_sent_to_onboarding():
    """The actual regression: a fresh tenant must get the QR flow."""
    db = _FakeDB({"whatsapp_connected_at": None,
                  "onboarding_completed": False,
                  "signup_token": "tok-abc123"})

    url = _onboarding_redirect_for(db, "tenant-1")

    assert url is not None, "a tenant with no WhatsApp connection must be onboarded"
    assert url.endswith("/onboard/tok-abc123"), url


def test_connected_tenant_goes_to_dashboard():
    """Guard the other direction — do not trap returning users in onboarding."""
    db = _FakeDB({"whatsapp_connected_at": "2026-09-01T10:00:00Z",
                  "onboarding_completed": True,
                  "signup_token": "tok-abc123"})

    assert _onboarding_redirect_for(db, "tenant-1") is None


def test_completed_onboarding_without_timestamp_goes_to_dashboard():
    """onboarding_completed alone is enough; not every row has the timestamp."""
    db = _FakeDB({"whatsapp_connected_at": None,
                  "onboarding_completed": True,
                  "signup_token": "tok-abc123"})

    assert _onboarding_redirect_for(db, "tenant-1") is None


def test_missing_signup_token_is_minted_not_crashed():
    """Tenants created before signup_token existed must still be onboardable."""
    minted = {}
    db = _FakeDB({"whatsapp_connected_at": None,
                  "onboarding_completed": False,
                  "signup_token": None},
                 on_update=lambda p: minted.update(p))

    url = _onboarding_redirect_for(db, "tenant-1")

    assert url is not None, "a missing token must be minted, not fatal"
    assert minted.get("signup_token"), "the new token must be persisted"
    assert url.endswith(f"/onboard/{minted['signup_token']}")


def test_missing_tenant_row_does_not_break_login():
    """Routing is a nicety; it must never turn a good login into a failure."""
    db = _FakeDB(None)
    assert _onboarding_redirect_for(db, "tenant-1") is None


def test_database_error_does_not_break_login():
    """Same reasoning: degrade to /dashboard rather than 500 on a working login."""
    class _Boom(_FakeDB):
        def execute(self):
            raise RuntimeError("connection reset")

    assert _onboarding_redirect_for(_Boom({}), "tenant-1") is None
