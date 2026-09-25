"""
Functional Tests for WhatsApp Call Handler
==========================================

Tests core call handling functionality after security vulnerabilities are fixed:
- End-to-end call flow validation
- Multi-tenant call isolation
- Configuration matrix testing
- Missed call follow-up logic
- Bridge-Core integration

Priority: P1 - HIGH (functional validation after security fixes)

Author: QA Engineer
Date: 2026-02-23

2026-09-06 — why every test in here was rewritten
-------------------------------------------------
All 14 failed with 503 "Service not ready". `test_client` builds
`TestClient(app)` without the lifespan, so the module-global
`src.core.bijou.bijou_instance` that `/webhook/message` reads at request time
was still None and the handler bailed at bijou.py:7507 before reaching a single
line of call logic. The `bridge_backend` fixture supplies that global. This is
the same class of mistake as patching a `Depends()` callable instead of using
`app.dependency_overrides`: the route resolves its collaborator at request
time, so the test has to install it where the route looks.

Three further expectations were written against a bridge contract that was
never built, and are corrected here against the handler that actually shipped:

* `call.offer` / `call.accept` / `call.terminate` are not event names the
  backend knows. The call branch at bijou.py:7599 matches `call`,
  `call.missed`, `call.received` and `call.rejected`; anything else falls
  through to the generic non-message skip and answers 200
  `{"status": "skipped"}` — never "accepted". Tests that need the follow-up
  path to actually fire now send a supported name.
* `X-API-Key` authenticated nothing. `BRIDGE_API_KEY` is the *outbound*
  backend→bridge credential (bijou.py:1519) and is never consulted on an
  inbound webhook. `/webhook/message` is now authenticated by the
  `BIJOU_WEBHOOK_SECRET` shared secret (or a GOWA HMAC body signature) —
  see `_verify_webhook_secret`, bijou.py:1304.
* `WHATSAPP_CALLS_ENABLED` / `MISSED_CALL_FOLLOWUP` are read nowhere in the
  backend. Ring-vs-auto-reject is a bridge-side decision, so the config matrix
  pins that the backend's follow-up path is deliberately config-independent.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

import src.core.bijou as bijou_module
from src.core.bijou import is_missed_call

from tests.fixtures.call_payloads import (
    create_call_offer_payload,
    create_call_accept_payload,
    create_call_terminate_payload,
    create_missed_call_payload,
    create_multi_tenant_test_scenario,
)


# ── Bridge → backend authentication ──────────────────────────────────────────
# /webhook/message rejects with 401 unless the caller presents the shared secret
# (or an HMAC body signature). Fail-open only applies when BIJOU_WEBHOOK_SECRET
# is unset, and these tests set it, so every request here must be signed.

WEBHOOK_SECRET = "call-functional-tests-webhook-secret"

AUTH_HEADERS = {
    "Content-Type": "application/json",
    "X-Bijou-Webhook-Secret": WEBHOOK_SECRET,
}


@pytest.fixture(autouse=True)
def webhook_secret_configured(monkeypatch):
    """Close the fail-open window for the duration of every test in this file."""
    monkeypatch.setenv("BIJOU_WEBHOOK_SECRET", WEBHOOK_SECRET)


@pytest.fixture
def bridge_backend(mock_supabase, monkeypatch):
    """Install the `bijou_instance` global that /webhook/message reads per request.

    Returns the stand-in so tests can assert on what the webhook handed it:
    `process_message` for the message path, `message_queue.put_nowait` for the
    call path. `processed_message_ids` is a real set because the handler does
    `in` and `.add()` on it for idempotency.
    """
    backend = MagicMock()
    backend.db_type = "supabase"
    backend.db_conn = mock_supabase
    backend.processed_message_ids = set()
    backend.message_queue = MagicMock()
    backend.process_message = AsyncMock()
    monkeypatch.setattr(bijou_module, "bijou_instance", backend)
    return backend


def bind_device(mock_supabase, tenant_id: str) -> None:
    """Point the whatsapp_devices lookup at `tenant_id`.

    The call branch resolves the tenant with
    `db.table("whatsapp_devices").select("tenant_id").eq(...).execute()`.
    conftest's mock hands out one cached mock per table name, so setting
    execute() here leaves `tenants` / `onboarding_progress` returning empty.
    """
    mock_supabase.table("whatsapp_devices").execute.return_value = MagicMock(
        data=[{"tenant_id": tenant_id}]
    )


def make_call_event(event: str, caller_jid: str, device_id: str, call_id: str) -> Dict[str, Any]:
    """A call event under a name the backend actually dispatches on.

    The fixtures in call_payloads.py use `call.offer` / `call.accept` /
    `call.terminate`, which the handler does not recognise — see the module
    docstring. Tests that need the missed-call follow-up to fire use this.
    """
    return {
        "event": event,
        "timestamp": datetime.now().isoformat(),
        "device_id": device_id,
        "payload": {"call_id": call_id, "from": caller_jid},
    }


def queued_followups(backend) -> List[Dict[str, Any]]:
    """Every synthetic missed-call job the webhook pushed onto the AI queue."""
    return [call.args[0] for call in backend.message_queue.put_nowait.call_args_list]


@pytest.mark.integration
@pytest.mark.asyncio
class TestCallFlowEndToEnd:
    """
    End-to-end call flow testing across different scenarios
    """

    async def test_missed_call_flow_with_followup_enabled(
        self, test_client, mock_supabase, bridge_backend
    ):
        """
        Test complete missed call flow: Call Offer → Timeout → Missed Call Follow-up

        Configuration: CALLS_ENABLED=true, MISSED_CALL_FOLLOWUP=true
        Expected: Phone rings, times out, AI sends follow-up message
        """
        tenant_id = "test-tenant-001"
        device_id = "device-call-test-001"
        caller_jid = "+601234567890@s.whatsapp.net"
        bind_device(mock_supabase, tenant_id)

        # Step 1: the ring itself. `call.offer` is not a name the backend
        # dispatches on, so it is acknowledged and deliberately not processed.
        call_offer = create_call_offer_payload(
            caller_jid=caller_jid, device_id=device_id, call_id="e2e-test-001"
        )
        response1 = test_client.post("/webhook/message", json=call_offer, headers=AUTH_HEADERS)

        assert response1.status_code == 200
        assert response1.json() == {"status": "skipped", "reason": "event_type_call.offer"}
        assert queued_followups(bridge_backend) == [], "a ring alone must not trigger follow-up"

        # Step 2: the timeout, under the name the backend does dispatch on.
        missed = make_call_event("call.missed", caller_jid, device_id, "e2e-test-001")
        response2 = test_client.post("/webhook/message", json=missed, headers=AUTH_HEADERS)

        assert response2.status_code == 200
        assert response2.json() == {"status": "processed", "event": "call.missed"}

        queued = queued_followups(bridge_backend)
        assert len(queued) == 1, "a missed call must queue exactly one AI follow-up"
        assert queued[0]["tenant_id"] == tenant_id
        assert queued[0]["device_id"] == device_id
        assert queued[0]["payload"]["body"] == "📞 MISSED_CALL"
        assert queued[0]["payload"]["message_type"] == "missed_call"
        assert queued[0]["payload"]["chat_id"] == caller_jid

        # Step 3: the bridge also re-delivers the follow-up as a normal message.
        missed_call = create_missed_call_payload(
            caller_jid=caller_jid, device_id=device_id, call_id="e2e-test-001"
        )
        response3 = test_client.post("/webhook/message", json=missed_call, headers=AUTH_HEADERS)

        assert response3.status_code == 200
        assert response3.json().get("status") == "accepted"

        bridge_backend.process_message.assert_called_once()
        call_args = bridge_backend.process_message.call_args[0][0]
        assert call_args["content"] == "📞 MISSED_CALL"
        assert call_args["chat_jid"] == caller_jid
        assert is_missed_call(call_args), "the AI must see this message as a missed call"

    async def test_answered_call_no_followup(self, test_client, mock_supabase, bridge_backend):
        """
        Test answered call flow: Call Offer → Accept → Terminate → No Follow-up

        Expected: Call answered, terminated normally, no AI follow-up sent
        """
        bind_device(mock_supabase, "test-tenant-002")

        call_id = "answered-call-001"
        caller_jid = "+601987654321@s.whatsapp.net"
        device_id = "device-call-test-002"

        # Step 1: Call offer
        call_offer = create_call_offer_payload(caller_jid, device_id, call_id)
        response1 = test_client.post("/webhook/message", json=call_offer, headers=AUTH_HEADERS)
        assert response1.status_code == 200
        assert response1.json()["status"] == "skipped"

        # Step 2: Call accepted — under the name the backend dispatches on, an
        # answered call is `call.received`: recognised, and deliberately not
        # treated as missed.
        answered = make_call_event("call.received", caller_jid, device_id, call_id)
        response2 = test_client.post("/webhook/message", json=answered, headers=AUTH_HEADERS)
        assert response2.status_code == 200
        assert response2.json() == {"status": "processed", "event": "call.received"}

        # Step 3: Call terminated (answered, not missed)
        call_terminate = create_call_terminate_payload(
            caller_jid, device_id, call_id, is_missed=False, duration_seconds=120.5
        )
        response3 = test_client.post("/webhook/message", json=call_terminate, headers=AUTH_HEADERS)
        assert response3.status_code == 200
        assert response3.json()["status"] == "skipped"

        # Verify NO missed call follow-up was triggered, on either path
        assert queued_followups(bridge_backend) == []
        bridge_backend.process_message.assert_not_called()

    async def test_auto_reject_mode_immediate_followup(
        self, test_client, mock_supabase, bridge_backend
    ):
        """
        Test auto-reject mode: CALLS_ENABLED=false

        Expected: Call rejected immediately, follow-up triggered within seconds
        """
        tenant_id = "test-tenant-003"
        device_id = "device-call-test-003"
        caller_jid = "+602123456789@s.whatsapp.net"
        bind_device(mock_supabase, tenant_id)

        # The bridge auto-rejects and reports `call.rejected`. A rejected call
        # counts as missed, so the follow-up fires without waiting for a timeout.
        rejected = make_call_event("call.rejected", caller_jid, device_id, "auto-reject-001")
        response = test_client.post("/webhook/message", json=rejected, headers=AUTH_HEADERS)

        assert response.status_code == 200
        assert response.json() == {"status": "processed", "event": "call.rejected"}

        queued = queued_followups(bridge_backend)
        assert len(queued) == 1, "an auto-rejected call must still get a follow-up"
        assert queued[0]["tenant_id"] == tenant_id
        assert queued[0]["payload"]["message_type"] == "missed_call"

        # The bridge then re-delivers that follow-up as a normal message.
        missed_call = create_missed_call_payload(
            caller_jid=caller_jid, device_id=device_id, call_id="auto-reject-001"
        )
        response2 = test_client.post("/webhook/message", json=missed_call, headers=AUTH_HEADERS)

        assert response2.status_code == 200
        bridge_backend.process_message.assert_called_once()
        assert is_missed_call(bridge_backend.process_message.call_args[0][0])


@pytest.mark.integration
@pytest.mark.asyncio
class TestMultiTenantCallIsolation:
    """
    Test multi-tenant isolation for call handling
    """

    async def test_tenant_call_isolation(self, test_client, mock_supabase, bridge_backend):
        """
        Verify calls are properly isolated between tenants

        The webhook's tenant selector is `device_id`, never the caller's JID —
        a caller who talks to two tenants is ordinary, not an attack. So the
        real boundaries are (a) the shared secret, which is what stops a
        stranger injecting a message into someone else's tenant at all, and
        (b) routing that follows device_id only. Both are asserted here; the
        pre-2026-09-06 expectation of a 403/404 on a JID/device mismatch was
        never a contract the handler had.
        """
        scenario = create_multi_tenant_test_scenario()
        tenants = scenario["tenants"]

        # Tenant A: a legitimate missed-call message on tenant A's device.
        bind_device(mock_supabase, tenants["tenant_a"]["tenant_id"])
        tenant_a_call = scenario["legitimate_calls"]["tenant_a"][1]
        response_a = test_client.post("/webhook/message", json=tenant_a_call, headers=AUTH_HEADERS)
        assert response_a.status_code == 200
        assert response_a.json()["status"] == "accepted"
        assert (
            bridge_backend.process_message.call_args[0][0]["device_id"]
            == tenants["tenant_a"]["device_id"]
        )

        # Tenant B: a call event on tenant B's device queues against tenant B.
        bind_device(mock_supabase, tenants["tenant_b"]["tenant_id"])
        response_b = test_client.post(
            "/webhook/message",
            json=make_call_event(
                "call.missed",
                tenants["tenant_b"]["whatsapp_jid"],
                tenants["tenant_b"]["device_id"],
                "tenant-b-call-001",
            ),
            headers=AUTH_HEADERS,
        )
        assert response_b.status_code == 200
        queued = queued_followups(bridge_backend)
        assert len(queued) == 1
        assert queued[0]["tenant_id"] == tenants["tenant_b"]["tenant_id"]
        assert queued[0]["tenant_id"] != tenants["tenant_a"]["tenant_id"]

        # An unauthenticated stranger cannot inject into any tenant at all, and
        # is rejected before the payload is even parsed.
        for attack_payload in scenario["attack_payloads"]:
            unauth = test_client.post(
                "/webhook/message",
                json=attack_payload,
                headers={"Content-Type": "application/json"},
            )
            assert unauth.status_code == 401, (
                f"Unauthenticated injection must be blocked, got {unauth.status_code}"
            )
            assert unauth.json() == {"detail": "Unauthorized"}

        # And with the secret, a mismatched caller JID never redirects the
        # message away from the device's own tenant.
        for attack_payload in scenario["attack_payloads"]:
            bridge_backend.process_message.reset_mock()
            attack_response = test_client.post(
                "/webhook/message", json=attack_payload, headers=AUTH_HEADERS
            )
            assert attack_response.status_code == 200
            routed = bridge_backend.process_message.call_args[0][0]
            assert routed["device_id"] == attack_payload["device_id"], (
                "routing must follow device_id, not the caller JID in the body"
            )

    async def test_tenant_configuration_isolation(
        self, test_client, mock_supabase, bridge_backend
    ):
        """
        Verify each tenant's call configuration is applied independently
        """
        # Setup tenants with different call configurations
        tenant_configs = [
            {
                "tenant_id": "config-test-001",
                "device_id": "config-device-001",
                "whatsapp_jid": "+601111111111@s.whatsapp.net",
                "calls_enabled": True,   # Accepts calls
                "missed_call_followup": True
            },
            {
                "tenant_id": "config-test-002",
                "device_id": "config-device-002",
                "whatsapp_jid": "+602222222222@s.whatsapp.net",
                "calls_enabled": False,  # Auto-rejects calls
                "missed_call_followup": True
            },
            {
                "tenant_id": "config-test-003",
                "device_id": "config-device-003",
                "whatsapp_jid": "+603333333333@s.whatsapp.net",
                "calls_enabled": True,
                "missed_call_followup": False  # No follow-up
            }
        ]

        for i, config in enumerate(tenant_configs, 1):
            bridge_backend.message_queue.put_nowait.reset_mock()
            bind_device(mock_supabase, config["tenant_id"])

            # A tenant that auto-rejects reports `call.rejected`; one that rings
            # reports `call.missed` on timeout. Both are missed as far as the
            # backend is concerned.
            event = "call.rejected" if not config["calls_enabled"] else "call.missed"
            response = test_client.post(
                "/webhook/message",
                json=make_call_event(
                    event, config["whatsapp_jid"], config["device_id"], f"config-test-{i:03d}"
                ),
                headers=AUTH_HEADERS,
            )

            assert response.status_code == 200
            assert response.json() == {"status": "processed", "event": event}

            queued = queued_followups(bridge_backend)
            assert len(queued) == 1, f"{config['tenant_id']} must get its own follow-up"
            assert queued[0]["tenant_id"] == config["tenant_id"]
            assert queued[0]["device_id"] == config["device_id"]
            assert queued[0]["payload"]["chat_id"] == config["whatsapp_jid"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestCallBridgeIntegration:
    """
    Test integration between WhatsApp bridge and Bijou core
    """

    async def test_webhook_payload_compatibility(
        self, test_client, mock_supabase, bridge_backend
    ):
        """
        Verify bridge webhooks are correctly processed by core
        """
        caller_jid = "+601234567890@s.whatsapp.net"
        device_id = "integration-device-001"
        bind_device(mock_supabase, "integration-test-001")

        # The three `call.*` shapes the fixtures invented are acknowledged but
        # not dispatched — the handler's call branch does not know these names.
        unhandled = [
            ("call.offer", create_call_offer_payload(caller_jid, device_id, "call-001")),
            ("call.accept", create_call_accept_payload(caller_jid, device_id, "call-001")),
            (
                "call.terminate",
                create_call_terminate_payload(
                    caller_jid, device_id, "call-001", is_missed=False, duration_seconds=30.0
                ),
            ),
        ]
        for event_name, payload in unhandled:
            response = test_client.post("/webhook/message", json=payload, headers=AUTH_HEADERS)
            assert response.status_code == 200
            assert response.json() == {
                "status": "skipped",
                "reason": f"event_type_{event_name}",
            }

        # The names it does dispatch on reach the AI queue.
        for event_name in ("call", "call.missed", "call.rejected"):
            bridge_backend.message_queue.put_nowait.reset_mock()
            response = test_client.post(
                "/webhook/message",
                json=make_call_event(event_name, caller_jid, device_id, "call-002"),
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 200
            assert response.json() == {"status": "processed", "event": event_name}
            assert len(queued_followups(bridge_backend)) == 1

        # A missed call re-delivered as a normal message is accepted for the
        # background AI pass.
        response = test_client.post(
            "/webhook/message",
            json=create_missed_call_payload(caller_jid, device_id, "call-003"),
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200
        assert "accepted" in response.json().get("status", "").lower()

    async def test_webhook_error_handling(self, test_client, bridge_backend):
        """
        Test webhook error handling for malformed payloads

        Pins the validation the handler actually performs. Two shapes the
        Feb 2026 version expected to be rejected are not validated at all —
        an unparseable JID and an empty device_id both sail through. That is
        a real gap, reported rather than silently accepted here: the
        assertions below state that the unvalidated value reaches the AI
        verbatim, so a future validator will break this test loudly.
        """
        from tests.fixtures.call_payloads import create_malformed_call_payload

        # Structurally invalid: pydantic rejects before any tenant work.
        for payload_type, missing in (
            ("missing_fields", "device_id"),
            ("empty_payload", "payload"),
        ):
            response = test_client.post(
                "/webhook/message",
                json=create_malformed_call_payload(payload_type),
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 422, (
                f"{payload_type} must be rejected. Got {response.status_code}"
            )
            assert missing in response.json()["detail"]

        # An event the handler has no branch for is skipped, not errored.
        response = test_client.post(
            "/webhook/message",
            json=create_malformed_call_payload("wrong_event_type"),
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200, "Wrong event type should be skipped gracefully"
        assert response.json() == {"status": "skipped", "reason": "event_type_unknown_event"}

        # NOT VALIDATED (gap, see docstring): a JID that is not a JID.
        bridge_backend.process_message.reset_mock()
        invalid_jid = create_malformed_call_payload("invalid_jid")
        response = test_client.post("/webhook/message", json=invalid_jid, headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert (
            bridge_backend.process_message.call_args[0][0]["chat_jid"]
            == invalid_jid["payload"]["chat_id"]
        ), "no JID validation exists; the raw value must at least pass through unaltered"

        # NOT VALIDATED (gap, see docstring): an empty device_id, i.e. no tenant.
        bridge_backend.process_message.reset_mock()
        response = test_client.post(
            "/webhook/message",
            json=create_malformed_call_payload("invalid_device"),
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200
        assert bridge_backend.process_message.call_args[0][0]["device_id"] == ""

    async def test_webhook_authentication_integration(
        self, test_client, mock_supabase, bridge_backend
    ):
        """
        Test end-to-end authentication between bridge and core

        `X-API-Key` (the pre-2026-09-06 expectation) never authenticated
        anything — BRIDGE_API_KEY is the outbound backend→bridge credential.
        The inbound boundary is BIJOU_WEBHOOK_SECRET.
        """
        call_payload = create_missed_call_payload(
            "+601234567890@s.whatsapp.net", "auth-test-device", "auth-test-001"
        )
        bind_device(mock_supabase, "auth-test-tenant")

        # Accepted: the secret in either header spelling.
        for headers in (
            AUTH_HEADERS,
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {WEBHOOK_SECRET}",
            },
        ):
            bridge_backend.processed_message_ids.clear()
            bridge_backend.process_message.reset_mock()
            response = test_client.post("/webhook/message", json=call_payload, headers=headers)

            assert response.status_code == 200
            assert response.json().get("status") == "accepted"
            bridge_backend.process_message.assert_called_once()

        # Rejected: absent, wrong, and near-miss credentials, and the old
        # X-API-Key that used to be treated as proof of identity.
        for label, headers in (
            ("no credential", {}),
            ("wrong secret", {"X-Bijou-Webhook-Secret": "not-the-secret"}),
            ("truncated secret", {"X-Bijou-Webhook-Secret": WEBHOOK_SECRET[:-1]}),
            ("extended secret", {"X-Bijou-Webhook-Secret": WEBHOOK_SECRET + "x"}),
            ("stale X-API-Key", {"X-API-Key": WEBHOOK_SECRET}),
        ):
            bridge_backend.process_message.reset_mock()
            response = test_client.post(
                "/webhook/message",
                json=call_payload,
                headers={"Content-Type": "application/json", **headers},
            )

            assert response.status_code == 401, f"{label} must be rejected"
            assert response.json() == {"detail": "Unauthorized"}
            bridge_backend.process_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
class TestCallConfigurationMatrix:
    """
    Test all combinations of call configuration settings
    """

    @pytest.mark.parametrize("calls_enabled,followup_enabled,expected_behavior", [
        (True, True, "ring_and_followup_if_missed"),
        (True, False, "ring_no_followup"),
        (False, True, "auto_reject_with_followup"),
        (False, False, "auto_reject_forced_followup"),  # Implementation forces followup when disabled
    ])
    async def test_configuration_matrix(
        self, calls_enabled, followup_enabled, expected_behavior,
        test_client, mock_supabase, bridge_backend,
    ):
        """
        Test all combinations of CALLS_ENABLED and MISSED_CALL_FOLLOWUP settings

        The invariant being pinned is that the backend does not read either
        variable: whether the phone rings and whether the bridge decides to
        report a miss are bridge-side choices. Once a missed call reaches
        `/webhook/message`, the follow-up is queued under all four settings.
        The `auto_reject_forced_followup` row is exactly that — follow-up
        happens even with MISSED_CALL_FOLLOWUP=false.
        """
        tenant_id = f"tenant-{expected_behavior}"
        device_id = f"device-{expected_behavior}"
        caller_jid = "+601234567890@s.whatsapp.net"
        bind_device(mock_supabase, tenant_id)

        with patch.dict(os.environ, {
            "WHATSAPP_CALLS_ENABLED": str(calls_enabled).lower(),
            "MISSED_CALL_FOLLOWUP": str(followup_enabled).lower()
        }):
            # A bridge with calls disabled reports a rejection; one with calls
            # enabled reports a timeout. Same outcome downstream.
            event = "call.missed" if calls_enabled else "call.rejected"
            response = test_client.post(
                "/webhook/message",
                json=make_call_event(
                    event, caller_jid, device_id, f"config-test-{expected_behavior}"
                ),
                headers=AUTH_HEADERS,
            )

            assert response.status_code == 200
            assert response.json() == {"status": "processed", "event": event}

            queued = queued_followups(bridge_backend)
            assert len(queued) == 1, (
                f"{expected_behavior}: follow-up must not depend on env config"
            )
            assert queued[0]["tenant_id"] == tenant_id
            assert queued[0]["payload"]["body"] == "📞 MISSED_CALL"

            # And the message-shaped redelivery is accepted in every case too.
            followup_response = test_client.post(
                "/webhook/message",
                json=create_missed_call_payload(
                    caller_jid, device_id, f"config-test-{expected_behavior}"
                ),
                headers=AUTH_HEADERS,
            )

            assert followup_response.status_code == 200
            assert followup_response.json()["status"] == "accepted"


@pytest.mark.smoke
@pytest.mark.asyncio
class TestCallHandlerSmoke:
    """
    Smoke tests for critical call handler paths
    """

    async def test_missed_call_context_override(
        self, test_client, mock_supabase, bridge_backend
    ):
        """
        SMOKE TEST: Verify missed call context override is working

        This tests the core functionality that was recently integrated.

        The override is driven by `is_missed_call()` (bijou.py:1270), so this
        asserts against that predicate rather than against a single field:
        the webhook drops the bridge's `message_type` (see the report — it is
        not declared on GOWAMessagePayload), and detection currently survives
        only on the content sentinel.
        """
        bind_device(mock_supabase, "smoke-test-001")

        missed_call = create_missed_call_payload(
            "+601234567890@s.whatsapp.net", "smoke-test-device", "smoke-001"
        )

        response = test_client.post("/webhook/message", json=missed_call, headers=AUTH_HEADERS)

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

        # Verify AI processing was called with missed call context
        bridge_backend.process_message.assert_called_once()
        processed_message = bridge_backend.process_message.call_args[0][0]

        # Should contain missed call indicators
        assert processed_message["content"] == "📞 MISSED_CALL"
        assert is_missed_call(processed_message) is True
        assert processed_message["chat_jid"] == "+601234567890@s.whatsapp.net"

    async def test_basic_call_webhook_processing(
        self, test_client, mock_supabase, bridge_backend
    ):
        """
        SMOKE TEST: Basic call webhook is processed without errors
        """
        caller_jid = "+601234567890@s.whatsapp.net"
        device_id = "smoke-basic-device"
        bind_device(mock_supabase, "smoke-basic-001")

        # The bare `call` event is the minimum shape the backend dispatches on.
        response = test_client.post(
            "/webhook/message",
            json=make_call_event("call", caller_jid, device_id, "smoke-basic-001"),
            headers=AUTH_HEADERS,
        )

        # Should process successfully
        assert response.status_code == 200
        assert response.json() == {"status": "processed", "event": "call"}
        assert len(queued_followups(bridge_backend)) == 1

        # The offer shape the fixtures build is acknowledged without error too.
        basic_call = create_call_offer_payload(caller_jid, device_id, "smoke-basic-002")
        offer_response = test_client.post(
            "/webhook/message", json=basic_call, headers=AUTH_HEADERS
        )
        assert offer_response.status_code == 200
        assert offer_response.json()["status"] == "skipped"
