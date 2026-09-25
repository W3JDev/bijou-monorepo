"""Shared-secret authentication for the bridge -> backend webhooks.

The hole
--------
`/webhook/message` (src/core/bijou.py:7411) and `/webhook/connection` (:7791)
had no authentication of any kind. Verified during the 2026-09-06 audit:

    $ sed -n '7411,7491p' src/core/bijou.py | grep -E "Authorization|API_KEY|verify|Depends"
      (no matches)

`/webhook/connection` then reads the tenant straight from the request body —
`tenant_id = data.get("tenant_id")` — and updates that tenant's `whatsapp_jid`
with the service-role client. So an unauthenticated caller could repoint any
tenant's WhatsApp binding. `/webhook/message` let anyone inject inbound
messages, drive a tenant's AI and burn its LLM budget.

The migration compromise, stated plainly
----------------------------------------
`_verify_webhook_secret` enforces the shared secret **when one is configured**
and logs a CRITICAL on every unauthenticated request when it is not. That is
fail-open by default, which is a real weakness and is deliberate: making it
mandatory in code would take inbound WhatsApp down for any already-running
deployment the instant it upgraded, before an operator could set the variable.

The safety net is that both new compose files mark `BIJOU_WEBHOOK_SECRET`
required, so a *new* deploy cannot come up without it. The window is only for
existing deployments, and the CRITICAL log is how you find them.

`test_unconfigured_logs_critical` exists so that this stays a deliberate,
noisy migration state and cannot quietly become the permanent default.
"""

import importlib
import logging

import pytest


@pytest.fixture
def verify():
    """Import late so monkeypatched env is read at call time, not import time."""
    mod = importlib.import_module("src.core.bijou")
    return mod._verify_webhook_secret


SECRET = "s3cr3t-webhook-value-for-test"


def _req(headers: dict):
    """Minimal stand-in for a starlette Request — only .headers is read."""
    class _R:
        def __init__(self, h):
            self.headers = h
    return _R(headers)


# ── Configured: the secret is enforced ─────────────────────────────────────

def test_correct_bearer_token_is_accepted(verify, monkeypatch):
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    assert verify(_req({"authorization": f"Bearer {SECRET}"})) is True


def test_correct_header_token_is_accepted(verify, monkeypatch):
    """The bridge sends X-Bijou-Webhook-Secret; both spellings must work."""
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    assert verify(_req({"x-bijou-webhook-secret": SECRET})) is True


def test_missing_credential_is_rejected(verify, monkeypatch):
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    assert verify(_req({})) is False


def test_wrong_credential_is_rejected(verify, monkeypatch):
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    assert verify(_req({"authorization": "Bearer not-the-secret"})) is False


def test_near_miss_is_rejected(verify, monkeypatch):
    """Guards against a prefix/startswith comparison."""
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    assert verify(_req({"authorization": f"Bearer {SECRET}extra"})) is False
    assert verify(_req({"authorization": f"Bearer {SECRET[:-1]}"})) is False


def test_comparison_is_constant_time(verify, monkeypatch):
    """A shared secret compared with == leaks length/prefix through timing.

    Asserting on wall-clock timing is flaky, so this asserts on the mechanism:
    the implementation must route through hmac.compare_digest.
    """
    import hmac
    import src.core.bijou as bijou

    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    calls = []
    real = hmac.compare_digest
    monkeypatch.setattr(
        bijou.hmac, "compare_digest",
        lambda a, b: calls.append(1) or real(a, b),
    )
    verify(_req({"authorization": f"Bearer {SECRET}"}))
    assert calls, "secret comparison must use hmac.compare_digest, not =="


# ── Unconfigured: fail open, but loudly ────────────────────────────────────

def test_unconfigured_allows_request(verify, monkeypatch):
    """Deliberate migration behaviour — see the module docstring."""
    monkeypatch.delenv("BIJOU_WEBHOOK_SECRET", raising=False)
    assert verify(_req({})) is True


def test_unconfigured_logs_critical(verify, monkeypatch, caplog):
    """The noise is the whole point. If this test is ever deleted, the endpoint
    silently becomes permanently unauthenticated again."""
    monkeypatch.delenv("BIJOU_WEBHOOK_SECRET", raising=False)
    with caplog.at_level(logging.CRITICAL, logger="src.core.bijou"):
        verify(_req({}))
    assert any(r.levelno >= logging.CRITICAL for r in caplog.records), (
        "an unauthenticated webhook must log CRITICAL when no secret is set"
    )
    assert any("BIJOU_WEBHOOK_SECRET" in r.getMessage() for r in caplog.records), (
        "the log must name the variable an operator has to set"
    )


def test_empty_string_secret_counts_as_unconfigured(verify, monkeypatch):
    """`BIJOU_WEBHOOK_SECRET=` in a compose file must not enable a check that
    then accepts an empty credential from anyone."""
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", "")
    assert verify(_req({"authorization": "Bearer "})) is True  # treated as unset


# ── GOWA HMAC signature (X-Hub-Signature-256) ──────────────────────────────
#
# The production bridge is GOWA (aldinokemal2104/go-whatsapp-web-multidevice),
# started with `--webhook <url> --webhook-secret <key>`. It does NOT send the
# secret in a header; it signs the request BODY:
#
#     X-Hub-Signature-256: sha256=<hex hmac-sha256(body, secret)>
#
# Confirmed against the running image (v3.4.0) and documented in this repo at
# docs/handoffs-and-audits/GOWA_BRIDGE_EXPERT_GUIDE.md:1128-1140.
#
# Without this branch every inbound WhatsApp message from the real bridge is
# rejected with 401 — the shared-secret forms below only cover the in-repo Go
# bridge, which is not what runs in production.

import hashlib


def _sig(body: bytes, secret: str) -> str:
    import hmac as _h
    return "sha256=" + _h.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_gowa_signature_is_accepted(verify, monkeypatch):
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    body = b'{"event":"message","payload":{"from":"60123@s.whatsapp.net"}}'
    assert verify(_req({"x-hub-signature-256": _sig(body, SECRET)}), body) is True


def test_gowa_signature_over_different_body_is_rejected(verify, monkeypatch):
    """A replayed signature must not authenticate a substituted payload."""
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    good = b'{"event":"message","payload":{"from":"victim"}}'
    tampered = b'{"event":"message","payload":{"from":"attacker"}}'
    assert verify(_req({"x-hub-signature-256": _sig(good, SECRET)}), tampered) is False


def test_gowa_signature_with_wrong_secret_is_rejected(verify, monkeypatch):
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    body = b'{"event":"message"}'
    assert verify(_req({"x-hub-signature-256": _sig(body, "not-the-secret")}), body) is False


def test_gowa_signature_without_body_is_rejected(verify, monkeypatch):
    """A signature header cannot be verified with no body to hash."""
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    body = b'{"event":"message"}'
    assert verify(_req({"x-hub-signature-256": _sig(body, SECRET)}), None) is False


def test_malformed_signature_header_is_rejected(verify, monkeypatch):
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", SECRET)
    body = b'{"event":"message"}'
    for bad in ("", "sha256=", "notsha256=abc", "deadbeef"):
        assert verify(_req({"x-hub-signature-256": bad}), body) is False, bad
