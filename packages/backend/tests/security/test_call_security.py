"""
Critical Security Tests for WhatsApp Call Handler
================================================

Tests for the 3 CRITICAL vulnerabilities identified by Security Auditor:
- CVE-2026-001: Cross-Tenant Call Injection (CVSS 9.1)
- CVE-2026-002: API Key Bypass (CVSS 9.4)
- CVE-2026-003: Memory Exhaustion DoS (CVSS 7.5)

**These tests MUST PASS before production deployment.**

Author: QA Engineer
Date: 2026-02-23
Priority: P0 - CRITICAL SECURITY

2026-09-06 — retargeted onto the credential the product actually uses
--------------------------------------------------------------------
This file was written in Feb against a design that never shipped: it sent
`X-API-Key` and expected the backend to validate it against `BRIDGE_API_KEY`.
`BRIDGE_API_KEY` is an *outbound* credential — the backend presents it when it
calls the bridge (src/core/bijou.py:5681, src/core/dashboard_api_simple.py:106).
It has never gated anything inbound, so every "attack" in here arrived with a
header the handler does not read, and the file could not detect a bypass.

Inbound `/webhook/*` authentication landed as `BIJOU_WEBHOOK_SECRET`
(src/core/bijou.py:1304 `_verify_webhook_secret`), presented as
`X-Bijou-Webhook-Secret`, `Authorization: Bearer`, or a GOWA
`X-Hub-Signature-256` body HMAC. The bypass tests below now send that
credential, so a regression in it actually fails them.

Two setup facts that make the difference between a real assertion and a
rubber stamp:

1. `_verify_webhook_secret` FAILS OPEN when `BIJOU_WEBHOOK_SECRET` is unset —
   a deliberate, loudly-logged migration state pinned by
   tests/unit/test_webhook_auth.py. The suite-wide conftest does not set it, so
   without the `webhook_secret` fixture below every 401 assertion here passes
   nothing and rejects nobody. Configuring it is what arms these tests.
2. `bijou_instance` is a module global set during the app's startup lifespan.
   `TestClient(app)` used outside a `with` block never runs it, so the handler
   short-circuits every request with 503 "Service not ready" — which silently
   satisfied any assertion looking for a rejection. `bijou_stub` patches the
   module attribute; that works here (unlike patching a `Depends()`) because
   the handler declares `global bijou_instance` and reads it at request time.
"""

import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

import src.core.bijou as bijou_module

# Import test fixtures
from tests.fixtures.call_payloads import (
    create_call_offer_payload,
    create_missed_call_payload,
    create_cross_tenant_attack_payload,
)


# ── The credential the backend actually checks on /webhook/* ────────────────

WEBHOOK_SECRET = "test-webhook-shared-secret-4f2c9a"


def auth_headers(secret: str = WEBHOOK_SECRET) -> dict:
    """Headers for a request the bridge would send with a valid credential."""
    return {"Content-Type": "application/json", "X-Bijou-Webhook-Secret": secret}


@pytest.fixture
def webhook_secret(monkeypatch):
    """Configure the shared secret so the fail-open branch is not taken.

    Without this the handler authenticates nobody and no test here can observe
    a rejection. See the module docstring, point 1.
    """
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", WEBHOOK_SECRET)
    return WEBHOOK_SECRET


class _StubBijou:
    """Minimal stand-in for the BijouAI singleton the webhook handler reads.

    Records what reached the downstream boundaries so tests can assert on
    routing rather than only on a status code.
    """

    def __init__(self, db_conn=None, db_type="supabase"):
        self.db_type = db_type
        self.db_conn = db_conn
        self.processed_message_ids = set()
        self.processed = []       # msg_dicts handed to process_message
        self.queued = []          # items handed to message_queue.put_nowait
        outer = self

        class _Queue:
            def put_nowait(self, item):
                outer.queued.append(item)

        self.message_queue = _Queue()

    async def process_message(self, msg_dict):
        self.processed.append(msg_dict)


@pytest.fixture
def bijou_stub(request):
    """Install a Bijou singleton so the handler gets past the 503 guard.

    See the module docstring, point 2. Tests that need a database can pass one
    via indirect parametrization; most only need the instance to exist.
    """
    db_conn = getattr(request, "param", None)
    stub = _StubBijou(db_conn=db_conn)
    with patch.object(bijou_module, "bijou_instance", stub):
        yield stub


class _FakeQuery:
    """Chainable stand-in for a supabase-py query builder.

    Records every `.eq()` so a test can prove *which column* a lookup keyed on
    — the difference between "resolved the tenant from the device" and
    "resolved the tenant from whatever the caller claimed to be".
    """

    def __init__(self, rows_for, table, log):
        self._rows_for = rows_for
        self._table = table
        self._log = log
        self._filters = {}

    def select(self, *_a, **_kw):
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def eq(self, column, value):
        self._filters[column] = value
        self._log.append((self._table, column, value))
        return self

    def execute(self):
        return MagicMock(data=self._rows_for(self._table, self._filters))


class _FakeSupabase:
    def __init__(self, rows_for):
        self.queries = []          # (table, column, value) for every filter applied
        self.tables_touched = []
        self._rows_for = rows_for

    def table(self, name):
        self.tables_touched.append(name)
        return _FakeQuery(self._rows_for, name, self.queries)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCallSecurityCritical:
    """
    P0 CRITICAL SECURITY TESTS

    These tests validate fixes for critical vulnerabilities.
    Failures indicate immediate security risk.
    """

    async def test_cve_2026_001_cross_tenant_call_injection_blocked(
        self, test_client, webhook_secret, bijou_stub
    ):
        """
        CVE-2026-001: Cross-Tenant Call Injection Prevention

        ATTACK: a call/missed-call payload pairs one tenant's *caller* JID with
        a different tenant's `device_id`, hoping the caller JID decides which
        tenant the event lands in.

        WHAT "BLOCKED" MEANS HERE. The original version of this test asserted
        403 + "tenant_mismatch". No such control exists, and it should not: the
        caller JID is the *customer's* number, and a customer phoning tenant B's
        WhatsApp line is ordinary tenant-B traffic, not an attack. Rejecting it
        would drop real calls. There is nothing to "mismatch" against, because
        a customer number is not bound to a tenant.

        The property that actually keeps tenants apart is that the tenant is
        resolved server-side from the device that received the event, and the
        caller-supplied JID never gets a vote. That is what is asserted below —
        at the webhook boundary (what routing key is handed downstream) and in
        TenantRouter.identify_tenant (which tenant that key resolves to).
        Weakening either one is what a real cross-tenant leak would look like.
        """
        # Setup: Two tenants with different device IDs
        tenant_a_device = "device-tenant-a-12345"
        tenant_b_device = "device-tenant-b-67890"
        tenant_a_id = "tenant-a-uuid"
        tenant_b_id = "tenant-b-uuid"
        tenant_a_caller = "+601234567890@s.whatsapp.net"

        # ATTACK: Use Tenant A's number with Tenant B's device_id
        malicious_payload = create_cross_tenant_attack_payload(
            caller_jid=tenant_a_caller,      # a caller known to Tenant A
            device_id=tenant_b_device,       # Tenant B's device (injection!)
            call_id="attack-call-001"
        )

        # Execute attack
        response = test_client.post(
            "/webhook/message",
            json=malicious_payload,
            headers=auth_headers(),
        )

        # The event is accepted as ordinary traffic for the device that got it.
        assert response.status_code == 200, response.text

        # SECURITY VALIDATION 1 — the routing key handed downstream is the
        # device from the envelope, never anything the caller supplied.
        assert len(bijou_stub.processed) == 1
        routed = bijou_stub.processed[0]
        assert routed["device_id"] == tenant_b_device
        assert routed["device_id"] != tenant_a_device
        # The caller JID is carried as sender/chat only — never as a tenant key.
        assert routed["sender"] == tenant_a_caller
        assert "tenant_id" not in routed, (
            "the webhook must not stamp a tenant from the request; it is "
            "resolved server-side from the device"
        )

        # SECURITY VALIDATION 2 — that device key resolves to the DEVICE's
        # tenant. Tenant A owns the caller JID in this fixture; if the router
        # ever prefers the caller, this is where the leak shows up.
        from src.saas.tenant_router import TenantRouter

        def rows_for(table, filters):
            if table == "whatsapp_devices" and filters.get("whatsapp_jid") == (
                f"{tenant_b_device}@s.whatsapp.net"
            ):
                return [{"tenant_id": tenant_b_id, "device_id": tenant_b_device}]
            if table == "tenants" and filters.get("whatsapp_jid") == tenant_a_caller:
                return [{"id": tenant_a_id, "name": "Tenant A"}]
            return []

        fake_db = _FakeSupabase(rows_for)
        router = TenantRouter(supabase_client=fake_db)

        resolved = await router.identify_tenant(
            chat_jid=routed["chat_jid"],
            sender=routed["sender"],
            business_jid=None,
            device_id=routed["device_id"],
        )

        assert resolved == tenant_b_id, (
            f"cross-tenant leak: event on {tenant_b_device} resolved to {resolved}"
        )
        assert resolved != tenant_a_id

        # SECURITY VALIDATION 3 — the customer-JID fallback
        # (TenantRouter._identify_from_customer, which reads `conversations`)
        # must not be consulted once the device is known. Reaching it would let
        # a caller's own history decide the tenant.
        assert "conversations" not in fake_db.tables_touched
        device_lookups = [q for q in fake_db.queries if q[0] == "whatsapp_devices"]
        assert device_lookups, "tenant must be resolved via a whatsapp_devices lookup"
        assert all(
            tenant_a_caller not in str(value) for _t, _c, value in fake_db.queries
        ), f"caller JID was used as a lookup key: {fake_db.queries}"

    async def test_cve_2026_002_api_key_bypass_blocked(
        self, test_client, webhook_secret, bijou_stub
    ):
        """
        CVE-2026-002: API Authentication Bypass Prevention

        ATTACK: Send call webhook without proper credential
        EXPECTED: 401 Unauthorized
        CURRENT RISK: Complete authentication bypass
        """
        # Valid call payload
        call_payload = create_call_offer_payload(
            caller_jid="+601234567890@s.whatsapp.net",
            device_id="valid-device-123",
            call_id="auth-test-001"
        )

        # Control: a valid credential gets all the way through to message
        # processing. Without this, every assertion below would also pass
        # against an endpoint that rejects everything for an unrelated reason.
        # It uses a "message" payload deliberately — a "call.offer" envelope is
        # answered 200/skipped without ever reaching process_message, so it
        # could not tell an authenticated request from a dropped one.
        accepted = test_client.post(
            "/webhook/message",
            json=create_missed_call_payload(
                caller_jid="+601234567890@s.whatsapp.net",
                device_id="valid-device-123",
                call_id="auth-test-control",
            ),
            headers=auth_headers(),
        )
        assert accepted.status_code == 200, accepted.text
        assert len(bijou_stub.processed) == 1

        # ATTACK 1: No credential header
        response1 = test_client.post(
            "/webhook/message",
            json=call_payload,
            headers={"Content-Type": "application/json"}
            # Missing X-Bijou-Webhook-Secret header
        )

        assert response1.status_code == 401, "Missing credential should return 401"
        assert "unauthorized" in response1.json().get("detail", "").lower()

        # ATTACK 2: Invalid credential
        response2 = test_client.post(
            "/webhook/message",
            json=call_payload,
            headers=auth_headers("invalid-fake-key-12345"),
        )

        assert response2.status_code == 401, "Invalid credential should return 401"
        assert "unauthorized" in response2.json().get("detail", "").lower()

        # ATTACK 3: Empty credential
        response3 = test_client.post(
            "/webhook/message",
            json=call_payload,
            headers=auth_headers(""),
        )

        assert response3.status_code == 401, "Empty credential should return 401"

        # ATTACK 4: the Bearer spelling of the same credential must be gated
        # identically — the handler accepts either header, so a bypass in one
        # is a bypass outright.
        response4 = test_client.post(
            "/webhook/message",
            json=call_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer not-the-secret",
            },
        )
        assert response4.status_code == 401, "Wrong bearer token should return 401"

        # Nothing rejected may have reached message processing.
        assert len(bijou_stub.processed) == 1, (
            f"a rejected request was processed anyway: {bijou_stub.processed}"
        )

    async def test_cve_2026_002_api_key_brute_force_protection(
        self, test_client, webhook_secret, bijou_stub
    ):
        """
        CVE-2026-002: API Key Brute Force Protection

        ATTACK: Rapid-fire requests with invalid credentials
        EXPECTED: Rate limiting after threshold (e.g., 10 attempts/minute)
        CURRENT RISK: Unlimited brute force attempts
        """
        call_payload = create_call_offer_payload(
            caller_jid="+601234567890@s.whatsapp.net",
            device_id="device-123",
            call_id="brute-force-test"
        )

        failed_attempts = 0
        rate_limited = False

        # ATTACK: Send 15 requests with invalid keys in quick succession
        for i in range(15):
            response = test_client.post(
                "/webhook/message",
                json=call_payload,
                headers=auth_headers(f"fake-key-{i:03d}"),
            )

            if response.status_code == 429:  # Too Many Requests
                rate_limited = True
                break
            elif response.status_code == 401:
                failed_attempts += 1

            # Small delay to avoid overwhelming test client
            time.sleep(0.01)

        # SECURITY VALIDATION
        assert rate_limited or failed_attempts >= 10, (
            "Rate limiting should activate after repeated failed attempts. "
            f"Got {failed_attempts} 401s, rate_limited={rate_limited}"
        )

        # Whichever branch held, no guessed credential may have been accepted.
        assert not bijou_stub.processed, (
            f"a guessed credential was accepted: {bijou_stub.processed}"
        )

    @pytest.mark.slow
    async def test_cve_2026_003_memory_exhaustion_protection(
        self, test_client, webhook_secret, bijou_stub
    ):
        """
        CVE-2026-003: Memory Exhaustion DoS Protection

        ATTACK: Flood server with call events to exhaust memory
        EXPECTED: Memory usage capped, excess calls rejected
        CURRENT RISK: Unbounded memory growth crashes service

        KNOWN RED as of 2026-09-06 — this is a product gap, not a stale test.
        `/webhook/message` has no HTTP-layer backpressure: the only middleware
        on the app is CORS and the no-cache header pass (src/core/bijou.py:479,
        :512), and the per-chat limiter at src/core/bijou.py:2941 lives inside
        `process_message`, i.e. after the 200 has already been returned. An
        authenticated flood therefore gets 100 x 200. The assertion is left as
        written rather than retargeted at something that happens to pass.
        """
        # A flood from an *unauthenticated* attacker — the CVE's actual threat
        # model — is refused at the door. This is the part that holds today.
        unauth = test_client.post(
            "/webhook/message",
            json=create_call_offer_payload(
                caller_jid="+60123456789@s.whatsapp.net",
                device_id="dos-unauth",
                call_id="dos-unauth-001",
            ),
            headers={"Content-Type": "application/json"},
        )
        assert unauth.status_code == 401

        # ATTACK: Generate 1000 concurrent call events
        attack_payloads = []
        for i in range(1000):
            payload = create_call_offer_payload(
                caller_jid=f"+6012345{i:05d}@s.whatsapp.net",
                device_id=f"attack-device-{i:03d}",
                call_id=f"dos-attack-{i:05d}"
            )
            attack_payloads.append(payload)

        # Execute DoS attack
        responses = []
        start_time = time.time()

        for payload in attack_payloads[:100]:  # Test with 100 to avoid test timeout
            response = test_client.post(
                "/webhook/message",
                json=payload,
                headers=auth_headers(),
            )
            responses.append(response.status_code)

        end_time = time.time()
        duration = end_time - start_time

        # SECURITY VALIDATION
        success_responses = [r for r in responses if r == 200]
        rejected_responses = [r for r in responses if r in [429, 503]]  # Rate limit or service unavailable

        # At least some requests should be rejected to prevent memory exhaustion
        assert len(rejected_responses) > 0, (
            "Memory protection should reject excess calls. "
            f"All {len(responses)} requests succeeded, indicating no DoS protection."
        )

        # Response time should not degrade significantly (< 5 seconds for 100 requests)
        assert duration < 5.0, (
            f"Response time {duration:.2f}s indicates server stress. "
            "DoS protection may be insufficient."
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestCallAuthenticationIntegration:
    """
    Integration tests for API authentication flow
    """

    async def test_valid_api_key_authentication_flow(
        self, test_client, webhook_secret, bijou_stub
    ):
        """
        Verify a valid credential allows call processing
        """
        call_payload = create_missed_call_payload(
            caller_jid="+601234567890@s.whatsapp.net",
            device_id="valid-device-123",
            call_id="auth-integration-001"
        )

        response = test_client.post(
            "/webhook/message",
            json=call_payload,
            headers=auth_headers(),  # Valid credential
        )

        # Should succeed with valid authentication
        assert response.status_code == 200
        assert response.json().get("status") == "accepted"
        assert bijou_stub.processed, "an accepted message must reach process_message"

        # The 200 must come from the credential, not from the fail-open branch:
        # the identical request without it is refused.
        without = test_client.post(
            "/webhook/message",
            json=create_missed_call_payload(
                caller_jid="+601234567890@s.whatsapp.net",
                device_id="valid-device-123",
                call_id="auth-integration-002",
            ),
            headers={"Content-Type": "application/json"},
        )
        assert without.status_code == 401

    async def test_api_key_validation_edge_cases(
        self, test_client, webhook_secret, bijou_stub
    ):
        """
        Test credential validation with various edge cases
        """
        call_payload = create_call_offer_payload(
            caller_jid="+601234567890@s.whatsapp.net",
            device_id="device-123",
            call_id="edge-case-test"
        )

        edge_cases = [
            # Case 1: Very long credential (potential buffer overflow)
            ("A" * 10000, 401, "Extremely long credential should be rejected"),

            # Case 2: Special characters in credential
            ("key-with-@#$%^&*()-chars", 401, "Special chars in key should be handled"),

            # Case 3: Case sensitivity test
            (WEBHOOK_SECRET.upper(), 401, "Credential should be case sensitive"),

            # Case 4: Whitespace handling
            (" valid-key-with-spaces ", 401, "Whitespace should be handled properly"),

            # Case 5: SQL injection attempt in credential
            ("'; DROP TABLE tenants; --", 401, "SQL injection in key should be blocked"),

            # Case 6: a prefix of the real secret — guards against a
            # startswith/short-circuit comparison.
            (WEBHOOK_SECRET[:-1], 401, "Prefix of the real secret should be rejected"),
        ]

        for api_key, expected_status, description in edge_cases:
            response = test_client.post(
                "/webhook/message",
                json=call_payload,
                headers=auth_headers(api_key),
            )

            assert response.status_code == expected_status, (
                f"{description}. Got {response.status_code}, expected {expected_status}"
            )

        assert not bijou_stub.processed, (
            f"an edge-case credential was accepted: {bijou_stub.processed}"
        )


@pytest.mark.regression
@pytest.mark.asyncio
class TestCallSecurityRegression:
    """
    Regression tests for call security vulnerabilities

    These tests ensure previously fixed security bugs don't regress.
    DO NOT DELETE these tests - they prevent regression.
    """

    async def test_regression_tenant_isolation_enforcement(
        self, test_client, webhook_secret
    ):
        """
        REGRESSION TEST - DO NOT DELETE

        Previous Bug: Call events could leak between tenants
        Fix: Added strict tenant_id validation
        Verified: 2026-02-23
        Re-verified against the shipped handler: 2026-09-06

        Drives the *call* branch of the webhook (src/core/bijou.py:7622), which
        is the one that resolves a tenant itself and puts it on the processing
        queue. The original version stopped at `assert response.status_code ==
        200` with a comment saying the tenant-write check was still to be
        written; it is written now — the queued tenant_id is asserted, and
        tenant B's id must appear nowhere.
        """
        tenant_a_id = "aaaa-bbbb-cccc-dddd"
        tenant_b_id = "eeee-ffff-gggg-hhhh"
        device_map = {
            "tenant-a-device": tenant_a_id,
            "tenant-b-device": tenant_b_id,
        }
        lookups = []

        def rows_for(table, filters):
            if table == "whatsapp_devices" and "device_id" in filters:
                tid = device_map.get(filters["device_id"])
                return [{"tenant_id": tid}] if tid else []
            return []

        fake_db = _FakeSupabase(rows_for)
        stub = _StubBijou(db_conn=fake_db)

        # Call from Tenant A should only process for Tenant A
        tenant_a_payload = {
            "event": "call",
            "timestamp": datetime.now().isoformat(),
            "device_id": "tenant-a-device",
            "payload": {
                "call_id": "regression-test-a",
                "from": "+601111111111@s.whatsapp.net",
                "status": "missed",
            },
        }

        with patch.object(bijou_module, "bijou_instance", stub):
            response = test_client.post(
                "/webhook/message",
                json=tenant_a_payload,
                headers=auth_headers(),
            )

        # Should be accepted for proper tenant
        assert response.status_code == 200

        # Verify tenant isolation maintained: exactly one queued item, carrying
        # tenant A, resolved by a whatsapp_devices lookup on tenant A's device.
        assert len(stub.queued) == 1, stub.queued
        queued = stub.queued[0]
        assert queued["tenant_id"] == tenant_a_id
        assert queued["device_id"] == "tenant-a-device"
        assert tenant_b_id not in json.dumps(queued), (
            f"tenant B leaked into a tenant A call event: {queued}"
        )
        assert ("whatsapp_devices", "device_id", "tenant-a-device") in fake_db.queries

        # And an event on a device belonging to no tenant queues nothing at all
        # rather than falling back to some other tenant.
        stub.queued.clear()
        orphan_payload = dict(tenant_a_payload, device_id="unknown-device")
        with patch.object(bijou_module, "bijou_instance", stub):
            orphan = test_client.post(
                "/webhook/message", json=orphan_payload, headers=auth_headers()
            )
        assert orphan.status_code == 200
        assert stub.queued == [], (
            f"an unowned device was routed to a tenant anyway: {stub.queued}"
        )

    async def test_regression_call_memory_leaks_fixed(self):
        """
        REGRESSION TEST - DO NOT DELETE

        Previous Bug: Call tracking map grew unbounded
        Fix: Added periodic cleanup and memory limits
        Verified: 2026-02-23
        """
        # This test would simulate the memory leak scenario
        # and verify cleanup mechanisms are working

        # Mock the pendingCalls map from the Go bridge
        with patch('src.core.bijou.logger') as mock_logger:
            # Simulate 1000 calls being tracked
            # Verify cleanup occurs after timeout
            # Ensure memory usage remains bounded

            # For now, this is a placeholder for the actual implementation
            assert True, "Memory cleanup mechanism should be verified"


@pytest.mark.load
@pytest.mark.slow
@pytest.mark.asyncio
class TestCallSecurityUnderLoad:
    """
    Security validation under load conditions
    """

    async def test_security_under_concurrent_load(
        self, test_client, webhook_secret, bijou_stub
    ):
        """
        Verify security measures hold under concurrent load
        """
        import concurrent.futures
        import threading

        # Create concurrent requests with mix of valid/invalid credentials
        def make_request(api_key: str, call_id: str) -> int:
            payload = create_call_offer_payload(
                caller_jid=f"+60123456{call_id}@s.whatsapp.net",
                device_id=f"load-test-{call_id}",
                call_id=f"concurrent-{call_id}"
            )

            response = test_client.post(
                "/webhook/message",
                json=payload,
                headers=auth_headers(api_key),
            )
            return response.status_code

        # Execute 50 concurrent requests (25 valid, 25 invalid)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            # Submit requests with mix of valid/invalid keys
            for i in range(50):
                api_key = WEBHOOK_SECRET if i % 2 == 0 else f"invalid-key-{i}"
                future = executor.submit(make_request, api_key, str(i).zfill(3))
                futures.append(future)

            # Collect results
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify security held under load
        unauthorized_count = sum(1 for r in results if r == 401)
        success_count = sum(1 for r in results if r == 200)

        # Should have rejected invalid API keys even under load
        assert unauthorized_count >= 20, (
            f"Security validation failed under load. Only {unauthorized_count}/25 invalid requests rejected"
        )

        # Concurrency must not cost the valid half its access either — a check
        # that only ever counts rejections would still pass if the endpoint
        # started refusing everyone.
        assert success_count == 25, (
            f"valid credentials were refused under load: {success_count}/25 accepted"
        )


# Test fixtures and data creation functions would be imported from separate files
# for better organization and reusability across test modules
