"""
Integration Tests for WhatsApp Missed-Call Handling
===================================================

What this file used to test, and why it was rewritten
-----------------------------------------------------
Every test here used to POST to ``/webhook/call`` and patch
``src.core.bijou.process_call_event`` / ``send_whatsapp_message`` /
``TenantManager`` / ``supabase_client``. None of those five names has ever
existed in this codebase:

    $ grep -rn "webhook/call" --include=*.py src/          -> no matches
    $ grep -n "@app.post" src/core/bijou.py                -> /api/webhook,
      /webhook/message, /webhook/connection, /webhook/telegram   (no /webhook/call)

So all 15 tests failed at setup with ``AttributeError: module 'src.core.bijou'
does not have the attribute ...`` and the one test that got as far as an HTTP
call got a 404. They were describing a design that was never built.

The call flow that *does* exist
-------------------------------
There is no separate call webhook. The bridge posts call events to the same
``/webhook/message`` endpoint, and ``src/core/bijou.py`` (the ``event_type in
("call", "call.missed", "call.received", "call.rejected")`` branch) synthesises
a ``"📞 MISSED_CALL"`` message onto ``bijou_instance.message_queue`` so the
normal AI pipeline produces the follow-up. ``is_missed_call()`` recognises that
sentinel again inside ``process_message`` and swaps in
``build_missed_call_context()``.

These tests exercise that real seam: authentication, the accepted event
vocabulary, the missed/answered discrimination, tenant resolution from
``whatsapp_devices``, and the exact shape of the synthesised payload.

KNOWN LIVE DEFECT — the follow-up never actually fires
------------------------------------------------------
``bijou_instance.message_queue`` is written at src/core/bijou.py:7638 and
appears nowhere else in the repo — ``BijouAI`` never creates it and nothing
consumes it. Confirmed against the running local stack:

    $ curl -X POST .../webhook/message -H "Authorization: Bearer $SECRET" \
        -d '{"event":"call","device_id":"bijou-b78d4123-...","payload":{...}}'
    200 {"status":"processed","event":"call"}
    ERROR:src.core.bijou:❌ [MISSED CALL] Failed to queue follow-up:
        'BijouAI' object has no attribute 'message_queue'

The AttributeError is swallowed by the branch's ``except Exception`` and the
bridge is still told 200/"processed", so the failure is invisible in
production. The tests below supply a real ``asyncio.Queue`` as the collaborator
double, which is what the handler is written against; they therefore verify the
handler's half of the contract and CANNOT catch that missing wiring. Fixing it
is a product change and is left to the owner — see the report for this pass.

Author: QA Engineer - Bijou AI Enterprise
Date: 2026-02-23 (rewritten against the real endpoint 2026-09-06)
"""

import asyncio
import time
import tracemalloc
from types import SimpleNamespace
from typing import Dict, Optional
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Test constants
TEST_BRIDGE_URL = "http://mock-bridge:8080"
TEST_CORE_URL = "http://localhost:8080"
TEST_CALLER_JID = "60198765432@s.whatsapp.net"
TEST_BUSINESS_JID = "60123456789@s.whatsapp.net"
TEST_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
WEBHOOK_SECRET = "call-flow-test-webhook-secret"

MISSED_CALL_SENTINEL = "📞 MISSED_CALL"


class _DeviceTable:
    """Stand-in for ``db.table("whatsapp_devices")``.

    Only the exact chain the handler uses is modelled —
    ``.select("tenant_id").eq("device_id", <id>).execute()`` — and every call is
    recorded so tests can assert the query, not just its result.
    """

    def __init__(self, tenant_by_device: Dict[str, str], calls: list):
        self._tenant_by_device = tenant_by_device
        self._calls = calls

    def select(self, *columns):
        self._calls.append(("select", columns))
        return self

    def eq(self, column, value):
        self._calls.append(("eq", (column, value)))
        self._matched = self._tenant_by_device.get(value)
        return self

    def execute(self):
        result = MagicMock()
        result.data = (
            [{"tenant_id": self._matched}] if getattr(self, "_matched", None) else []
        )
        return result


def make_fake_bijou(
    tenant_by_device: Optional[Dict[str, str]] = None,
    table_error: Optional[Exception] = None,
    queue: Optional[asyncio.Queue] = None,
):
    """Minimal stand-in for the ``bijou_instance`` global on the call path.

    The handler touches exactly two attributes: ``db_conn`` (to resolve the
    tenant that owns the device) and ``message_queue`` (to hand the synthesised
    message to the AI pipeline). See the module docstring for why supplying
    ``message_queue`` here is a double and not a claim that production has one.
    """
    instance = SimpleNamespace()
    instance.message_queue = queue if queue is not None else asyncio.Queue()
    instance.db_type = "supabase"
    instance.table_calls = []

    db = MagicMock()
    if table_error is not None:
        db.table = MagicMock(side_effect=table_error)
    else:
        def table(name):
            instance.table_calls.append(name)
            return _DeviceTable(tenant_by_device or {}, instance.table_calls)

        db.table = MagicMock(side_effect=table)
    instance.db_conn = db
    return instance


def drain(queue: asyncio.Queue) -> list:
    """Return everything currently queued, oldest first."""
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


def call_event(event: str = "call", device_id: str = TEST_BUSINESS_JID, **payload):
    """Build a bridge call webhook envelope."""
    body = {"event": event, "timestamp": "2026-02-23T10:00:00Z", "payload": payload}
    if device_id is not None:
        body["device_id"] = device_id
    return body


@pytest.fixture(autouse=True)
def unauthenticated_webhook(monkeypatch):
    """Most tests here are about call routing, not auth.

    ``load_dotenv()`` runs at import of src.core.bijou, so BIJOU_WEBHOOK_SECRET
    may be inherited from a developer's .env and would 401 every request.
    Clear it so the endpoint is in its fail-open migration mode; the one test
    that cares about auth sets it back explicitly.
    """
    monkeypatch.delenv("BIJOU_WEBHOOK_SECRET", raising=False)


@pytest.fixture
def bijou_module():
    import src.core.bijou as bijou

    return bijou


@pytest.fixture
def wire_bijou(bijou_module, monkeypatch):
    """Install a fake ``bijou_instance`` and hand it back to the test."""

    def _wire(**kwargs):
        instance = make_fake_bijou(**kwargs)
        monkeypatch.setattr(bijou_module, "bijou_instance", instance)
        return instance

    return _wire


class TestBridgeToCoreCommunication:
    """Test communication between bridge and core for call events."""

    @pytest.mark.integration
    def test_call_event_reaches_the_core_webhook(self, test_client: TestClient, wire_bijou):
        """Test bridge call events are accepted and acknowledged by core."""
        # Arrange
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

        # Act - Simulate bridge sending webhook
        response = test_client.post(
            "/webhook/message",
            headers={"Content-Type": "application/json"},
            json=call_event(
                "call",
                call_id="CALL_123456789",
                **{"from": TEST_CALLER_JID},
                status="missed",
            ),
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert response_data["event"] == "call"

        # Verify call processing was triggered
        queued = drain(instance.message_queue)
        assert len(queued) == 1
        assert queued[0]["tenant_id"] == TEST_TENANT_ID
        assert queued[0]["device_id"] == TEST_BUSINESS_JID
        assert queued[0]["payload"]["from"] == TEST_CALLER_JID

    @pytest.mark.integration
    def test_call_event_requires_the_webhook_secret_when_configured(
        self, test_client: TestClient, wire_bijou, monkeypatch
    ):
        """A configured secret gates the call path too, before any body handling."""
        # Arrange
        monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", WEBHOOK_SECRET)
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})
        payload = call_event("call", status="missed", **{"from": TEST_CALLER_JID})

        # Act / Assert - no credential is rejected and never reaches the DB
        rejected = test_client.post("/webhook/message", json=payload)
        assert rejected.status_code == 401
        assert instance.table_calls == []
        assert instance.message_queue.empty()

        # Act / Assert - the same body with the secret is processed normally
        accepted = test_client.post(
            "/webhook/message",
            json=payload,
            headers={"Authorization": f"Bearer {WEBHOOK_SECRET}"},
        )
        assert accepted.status_code == 200
        assert len(drain(instance.message_queue)) == 1

    @pytest.mark.integration
    def test_missed_call_followup_creation(self, test_client: TestClient, wire_bijou, bijou_module):
        """Test that missed calls trigger follow-up message creation."""
        # Arrange
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

        # Act
        response = test_client.post(
            "/webhook/message",
            json=call_event(
                "call.missed",
                call_id="CALL_MISSED_001",
                **{"from": TEST_CALLER_JID},
                reason="timeout",
                duration=35,
            ),
        )

        # Assert
        assert response.status_code == 200

        # Verify a follow-up message was synthesised for the AI pipeline
        queued = drain(instance.message_queue)
        assert len(queued) == 1
        synthetic = queued[0]["payload"]
        assert synthetic["chat_id"] == TEST_CALLER_JID
        assert synthetic["from"] == TEST_CALLER_JID
        assert synthetic["message_id"].startswith(f"CALL_{TEST_CALLER_JID}_")
        assert synthetic["timestamp"]

        # Check that the message carries missed call context
        assert synthetic["message_type"] == "missed_call"
        assert synthetic["body"] == MISSED_CALL_SENTINEL
        assert bijou_module.is_missed_call(synthetic) is True

    @pytest.mark.integration
    def test_answered_call_no_followup(self, test_client: TestClient, wire_bijou):
        """Test that answered calls don't trigger follow-up messages."""
        # Arrange - Call that gets answered
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

        # Act - Process call lifecycle
        answered = test_client.post(
            "/webhook/message",
            json=call_event(
                "call",
                call_id="CALL_ANSWERED_001",
                **{"from": TEST_CALLER_JID},
                status="answered",
                duration=120,
            ),
        )

        # Assert
        assert answered.status_code == 200
        assert answered.json()["status"] == "processed"

        # Verify NO follow-up message was queued (call was answered)
        assert instance.message_queue.empty()


class TestCallEventVocabulary:
    """Test which bridge event names and call statuses reach the follow-up path.

    Replaces the old TestConfigurationCombinations. It toggled
    WHATSAPP_CALLS_ENABLED / MISSED_CALL_FOLLOWUP, two env vars that exist only
    inside test files — nothing in src/ or in any compose/env template reads
    them. The real switches on this path are the event name and the call status.
    """

    @pytest.mark.integration
    def test_handled_call_event_names_queue_a_followup(self, test_client: TestClient, wire_bijou):
        """All four event names the handler claims to accept must work."""
        for event in ("call", "call.missed", "call.received", "call.rejected"):
            instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

            response = test_client.post(
                "/webhook/message",
                json=call_event(event, status="missed", **{"from": TEST_CALLER_JID}),
            )

            assert response.status_code == 200, event
            assert response.json() == {"status": "processed", "event": event}
            assert len(drain(instance.message_queue)) == 1, event

    @pytest.mark.integration
    def test_event_name_alone_decides_when_no_status_is_sent(
        self, test_client: TestClient, wire_bijou
    ):
        """With no status field the event name itself is the status string.

        "call.rejected" contains "reject" so it is missed; "call.received" says
        nothing about the outcome, so the handler declines to guess. Pinned
        because the fallback chain (status -> outcome -> type -> event) makes
        this easy to break by reordering.
        """
        rejected = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})
        response = test_client.post(
            "/webhook/message", json=call_event("call.rejected", **{"from": TEST_CALLER_JID})
        )
        assert response.status_code == 200
        assert len(drain(rejected.message_queue)) == 1

        received = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})
        response = test_client.post(
            "/webhook/message", json=call_event("call.received", **{"from": TEST_CALLER_JID})
        )
        assert response.status_code == 200
        assert received.message_queue.empty()

    @pytest.mark.integration
    def test_unhandled_call_event_names_are_skipped(self, test_client: TestClient, wire_bijou):
        """call.offer / call.accept / call.terminate fall through to the
        non-message skip branch — they are acknowledged but never acted on.

        This is the vocabulary the original author of this file assumed the
        bridge speaks. Nothing in-repo emits it (packages/bridge/main.go handles
        no call events at all), so it is pinned as current behaviour rather than
        asserted as correct. See the report for this pass.
        """
        for event in ("call.offer", "call.accept", "call.terminate"):
            instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

            response = test_client.post(
                "/webhook/message",
                json=call_event(event, status="missed", **{"from": TEST_CALLER_JID}),
            )

            assert response.status_code == 200, event
            assert response.json() == {
                "status": "skipped",
                "reason": f"event_type_{event}",
            }
            assert instance.message_queue.empty(), event
            assert instance.table_calls == [], event

    @pytest.mark.integration
    def test_missed_detection_across_status_words(self, test_client: TestClient, wire_bijou):
        """The status vocabulary the bridge may use, both ways."""
        missed = ("missed", "unanswered", "rejected", "timeout", "no_answer")
        not_missed = ("answered", "accepted", "completed", "ongoing")

        for status in missed:
            instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})
            response = test_client.post(
                "/webhook/message",
                json=call_event("call", status=status, **{"from": TEST_CALLER_JID}),
            )
            assert response.status_code == 200, status
            assert len(drain(instance.message_queue)) == 1, status

        for status in not_missed:
            instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})
            response = test_client.post(
                "/webhook/message",
                json=call_event("call", status=status, **{"from": TEST_CALLER_JID}),
            )
            assert response.status_code == 200, status
            assert instance.message_queue.empty(), status


class TestMultiTenantCallHandling:
    """Test multi-tenant isolation for call handling."""

    @pytest.mark.integration
    def test_tenant_call_isolation(self, test_client: TestClient, wire_bijou, test_tenants):
        """Test that calls for different tenants are properly isolated."""
        # Arrange - Two different tenants, each with its own bridge device.
        # The fixtures carry no "id" (the DB assigns it), so slug is the stable
        # identity here — it is what tells the two tenants apart.
        tenant_a = test_tenants[0]["slug"]  # Property tenant
        tenant_b = test_tenants[1]["slug"]  # Gaming tenant
        device_a = "60111111111@s.whatsapp.net"
        device_b = "60222222222@s.whatsapp.net"

        instance = wire_bijou(tenant_by_device={device_a: tenant_a, device_b: tenant_b})

        # Act - Process calls for both tenants
        response_a = test_client.post(
            "/webhook/message",
            json=call_event(
                "call", device_id=device_a, status="missed", **{"from": "60333333333@s.whatsapp.net"}
            ),
        )
        response_b = test_client.post(
            "/webhook/message",
            json=call_event(
                "call", device_id=device_b, status="missed", **{"from": "60444444444@s.whatsapp.net"}
            ),
        )

        # Assert
        assert response_a.status_code == 200
        assert response_b.status_code == 200

        # Verify both tenants got their respective follow-ups
        queued = drain(instance.message_queue)
        assert len(queued) == 2

        # Verify tenant isolation - each follow-up carries its own tenant and caller
        assert queued[0]["tenant_id"] == tenant_a
        assert queued[0]["device_id"] == device_a
        assert queued[0]["payload"]["chat_id"] == "60333333333@s.whatsapp.net"
        assert queued[1]["tenant_id"] == tenant_b
        assert queued[1]["device_id"] == device_b
        assert queued[1]["payload"]["chat_id"] == "60444444444@s.whatsapp.net"
        assert tenant_a != tenant_b

    @pytest.mark.integration
    def test_unknown_tenant_call_handling(self, test_client: TestClient, wire_bijou):
        """Test handling of calls from unknown/unregistered devices."""
        # Arrange - Call arriving on a device no tenant owns
        instance = wire_bijou(tenant_by_device={})

        # Act
        response = test_client.post(
            "/webhook/message",
            json=call_event(
                "call",
                device_id="60999999999@s.whatsapp.net",
                status="missed",
                **{"from": TEST_CALLER_JID},
            ),
        )

        # Assert - Should handle gracefully, not crash, and attribute nothing
        assert response.status_code == 200
        assert instance.message_queue.empty()


class TestDatabaseIntegration:
    """Test database operations for call handling."""

    @pytest.mark.integration
    def test_call_event_tenant_lookup(self, test_client: TestClient, wire_bijou):
        """Test that call events resolve their tenant from whatsapp_devices."""
        # Arrange
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

        # Act
        response = test_client.post(
            "/webhook/message",
            json=call_event("call", status="missed", **{"from": TEST_CALLER_JID}),
        )

        # Assert
        assert response.status_code == 200

        # Verify the exact query, not just that some table was touched
        assert instance.table_calls == [
            "whatsapp_devices",
            ("select", ("tenant_id",)),
            ("eq", ("device_id", TEST_BUSINESS_JID)),
        ]

    @pytest.mark.integration
    def test_followup_message_handoff_to_ai_pipeline(
        self, test_client: TestClient, wire_bijou, bijou_module
    ):
        """Test that the synthesised follow-up is one the AI pipeline recognises.

        This is the seam that matters: the webhook writes the sentinel, and
        process_message reads it back through is_missed_call() to swap in the
        missed-call system context. A change to either side alone breaks the
        follow-up silently.
        """
        # Arrange
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

        # Act
        response = test_client.post(
            "/webhook/message",
            json=call_event("call", status="missed", **{"from": TEST_CALLER_JID}),
        )

        # Assert
        assert response.status_code == 200

        queued = drain(instance.message_queue)
        assert len(queued) == 1
        synthetic = queued[0]["payload"]

        # The pipeline's own detector must accept what the webhook produced
        assert bijou_module.is_missed_call(synthetic) is True
        # ...and the context it then injects must actually describe a missed call
        context = bijou_module.build_missed_call_context()
        assert "call" in context.lower()
        assert "escalate" in context.lower()


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios."""

    @pytest.mark.integration
    def test_bridge_communication_failure(self, test_client: TestClient, wire_bijou):
        """Test handling of malformed payloads from the bridge."""
        # Arrange - Call event missing both caller and device
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

        # Act - an incomplete call event is absorbed, not acted on
        response = test_client.post("/webhook/message", json={"event": "call"})

        # Assert
        assert response.status_code == 200
        assert response.json() == {"status": "processed", "event": "call"}
        assert instance.message_queue.empty()
        assert instance.table_calls == []

        # Act / Assert - a malformed *message* event is still a client error;
        # the call branch's leniency must not have widened to everything.
        malformed = test_client.post("/webhook/message", json={"event": "message"})
        assert malformed.status_code in [400, 422]

    @pytest.mark.integration
    def test_database_failure_graceful_handling(self, test_client: TestClient, wire_bijou):
        """Test graceful handling of database failures."""
        # Arrange - tenant lookup blows up
        instance = wire_bijou(table_error=Exception("Database connection failed"))

        # Act - Should not crash despite DB failure
        response = test_client.post(
            "/webhook/message",
            json=call_event(
                "call", call_id="CALL_DB_ERROR_001", status="missed", **{"from": TEST_CALLER_JID}
            ),
        )

        # Assert - Should handle gracefully
        assert response.status_code in [200, 500]
        assert instance.message_queue.empty()

    @pytest.mark.integration
    def test_followup_queue_failure_handling(self, test_client: TestClient, wire_bijou):
        """Test handling of failures handing the follow-up to the AI pipeline."""
        # Arrange - the queue rejects the synthesised message
        broken_queue = MagicMock()
        broken_queue.put_nowait.side_effect = Exception("Queue unavailable")
        instance = wire_bijou(
            tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID}, queue=broken_queue
        )

        # Act
        response = test_client.post(
            "/webhook/message",
            json=call_event(
                "call", call_id="CALL_SEND_ERROR_001", status="missed", **{"from": TEST_CALLER_JID}
            ),
        )

        # Assert - Should handle the failure gracefully rather than 5xx the bridge
        assert response.status_code in [200, 500]
        assert instance.message_queue.put_nowait.called


class TestPerformanceIntegration:
    """Test performance characteristics in integration scenarios."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_high_call_volume_handling(self, test_client: TestClient, wire_bijou):
        """Test system performance under high call volume."""
        # Arrange - Generate multiple calls
        num_calls = 20
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})

        call_payloads = [
            call_event(
                "call",
                call_id=f"CALL_VOLUME_{i:03d}",
                status="missed",
                **{"from": f"6012345{i:04d}@s.whatsapp.net"},
            )
            for i in range(num_calls)
        ]

        # Act
        start_time = time.time()
        responses = [test_client.post("/webhook/message", json=p) for p in call_payloads]
        total_time = time.time() - start_time

        # Assert
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

        # Performance should be reasonable (< 5 seconds for 20 calls)
        assert total_time < 5.0, f"Processing {num_calls} calls took {total_time:.2f}s (should be <5s)"

        # All follow-ups should be queued, one per call, with distinct callers
        queued = drain(instance.message_queue)
        assert len(queued) == num_calls
        assert len({q["payload"]["chat_id"] for q in queued}) == num_calls

    @pytest.mark.integration
    def test_call_tracking_memory_usage(
        self, test_client: TestClient, wire_bijou, no_webhook_rate_limit
    ):
        """Test that call tracking doesn't cause memory leaks.

        Uses tracemalloc rather than psutil RSS: psutil is not installed here,
        and RSS is noisy enough that a 50MB budget barely constrains anything.
        tracemalloc measures Python allocations directly, so the same 50MB
        budget is a tighter bound than the original.
        """
        import gc

        # Arrange - Get baseline memory usage
        num_calls = 50
        instance = wire_bijou(tenant_by_device={TEST_BUSINESS_JID: TEST_TENANT_ID})
        gc.collect()
        tracemalloc.start()
        baseline, _ = tracemalloc.get_traced_memory()

        # Act - Process many call events
        for i in range(num_calls):
            response = test_client.post(
                "/webhook/message",
                json=call_event(
                    "call",
                    call_id=f"CALL_MEMORY_{i:03d}",
                    status="missed",
                    **{"from": f"60123456{i:03d}@s.whatsapp.net"},
                ),
            )
            assert response.status_code == 200

            # Simulate call cleanup after some time
            if i % 10 == 0:
                gc.collect()

        # Final cleanup
        gc.collect()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory_increase_mb = (peak - baseline) / (1024 * 1024)

        # Assert - Memory increase should be reasonable (<50MB for 50 calls)
        assert memory_increase_mb < 50, (
            f"Memory increased by {memory_increase_mb:.2f}MB (should be <50MB)"
        )

        # ...and the handler must queue exactly one follow-up per call, no
        # duplicates hiding inside that budget.
        assert len(drain(instance.message_queue)) == num_calls
