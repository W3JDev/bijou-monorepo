"""Regression: /api/auth/signup must be rate-limited per IP.

The bug
-------
Nothing throttled /api/auth/signup at our own edge — only Supabase's own
project-wide signup limit (signup.html's own comment cites "~4 per IP per
hour"). Combined with the email-enumeration fix in _check_signup_rate_limit's
sibling change (identities==[] no longer distinguishable via status code),
an attacker could otherwise probe candidate emails at whatever rate our
server would accept, only throttled once Supabase's own limit tripped —
which surfaced as a raw, uncontrolled error rather than our own honest 429.

The fix is a per-IP token bucket, same algorithm as the webhook rate limiter
in src/core/bijou.py (kept as an independent copy — see the comment in
auth_api.py for why it isn't a shared import).
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


@pytest.fixture(autouse=True)
def _reset_bucket():
    auth_api._reset_signup_rate_limit()
    yield
    auth_api._reset_signup_rate_limit()


def _fake_request(ip="1.2.3.4"):
    req = MagicMock()
    req.headers = {"x-forwarded-for": ip}
    req.client = MagicMock(host=ip)
    return req


def test_ip_is_read_from_x_forwarded_for_first():
    assert auth_api._signup_client_ip(_fake_request("9.9.9.9")) == "9.9.9.9"


def test_falls_back_to_request_client_host_without_forwarded_header():
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host="5.5.5.5")
    assert auth_api._signup_client_ip(req) == "5.5.5.5"


def test_allows_up_to_capacity_then_blocks(monkeypatch):
    monkeypatch.setenv("SIGNUP_RATE_CAPACITY", "3")
    monkeypatch.setenv("SIGNUP_RATE_REFILL_PER_SEC", "0")  # no refill mid-test
    req = _fake_request("1.1.1.1")

    for _ in range(3):
        auth_api._check_signup_rate_limit(req)  # must not raise

    with pytest.raises(HTTPException) as exc_info:
        auth_api._check_signup_rate_limit(req)
    assert exc_info.value.status_code == 429


def test_different_ips_have_independent_buckets(monkeypatch):
    monkeypatch.setenv("SIGNUP_RATE_CAPACITY", "1")
    monkeypatch.setenv("SIGNUP_RATE_REFILL_PER_SEC", "0")

    auth_api._check_signup_rate_limit(_fake_request("2.2.2.2"))  # consumes 2.2.2.2's only token
    with pytest.raises(HTTPException):
        auth_api._check_signup_rate_limit(_fake_request("2.2.2.2"))

    # A different IP is unaffected.
    auth_api._check_signup_rate_limit(_fake_request("3.3.3.3"))


def test_capacity_zero_disables_the_limiter(monkeypatch):
    monkeypatch.setenv("SIGNUP_RATE_CAPACITY", "0")
    req = _fake_request("4.4.4.4")

    for _ in range(50):
        auth_api._check_signup_rate_limit(req)  # never raises
