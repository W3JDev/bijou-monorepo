"""
Tests for the A2A shared-context API (issue #23).

Covers:
- POST /api/shared-context/append happy path
- POST /api/shared-context/append rejects invalid channel
- POST /api/shared-context/append rejects invalid role
- GET /api/shared-context with phone filter, returns rows sorted desc
- GET /api/shared-context with no entries returns empty list
- tenant_id isolation: a request with no session returns 4xx

Supabase is stubbed with unittest.mock; the session is supplied through
FastAPI's dependency_overrides (see _authenticate below).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_tenant_id() -> str:
    return "607690ec-4ff7-4ef4-b98e-bfb00442fe95"


@pytest.fixture
def app():
    from src.core.shared_context_api import router

    a = FastAPI()
    a.include_router(router)
    return a


def _authenticate(app: FastAPI, tenant_id: str) -> None:
    """Make verify_session resolve to `tenant_id` for this app.

    Depends() captures the dependency function object when the route is
    declared, so patching src.core.shared_context_api.verify_session after
    import does nothing — the override registry is the only seam. The real
    verify_session fails closed under the default DASHBOARD_MODE=strict,
    which is why every authenticated test needs this.
    """
    from src.core.dashboard_api_simple import verify_session

    app.dependency_overrides[verify_session] = lambda: tenant_id


@pytest.fixture
def fake_supabase():
    """A MagicMock that mimics the chainable Supabase client surface used by
    shared_context_api (table().insert().execute(), .select().eq().eq().gte()
    .order().limit().execute())."""
    sb = MagicMock()
    insert_chain = sb.table.return_value.insert.return_value
    insert_chain.execute.return_value = MagicMock(data=[{
        "id": "00000000-0000-0000-0000-000000000001",
        "tenant_id": "607690ec-4ff7-4ef4-b98e-bfb00442fe95",
        "customer_phone": "+60123456789",
        "channel": "whatsapp",
        "thread_id": "+60123456789@s.whatsapp.net",
        "role": "user",
        "content": "hi",
        "metadata": {},
        "created_at": "2026-08-23T06:00:00+00:00",
    }])
    select_chain = sb.table.return_value.select.return_value
    select_chain.eq.return_value = select_chain
    select_chain.gte.return_value = select_chain
    select_chain.order.return_value = select_chain
    select_chain.limit.return_value = select_chain
    # Returned in the order a real Postgres would hand back for
    # ORDER BY created_at DESC — newest (the 06:05 voice turn) first.
    select_chain.execute.return_value = MagicMock(data=[
        {
            "id": "00000000-0000-0000-0000-000000000011",
            "tenant_id": "607690ec-4ff7-4ef4-b98e-bfb00442fe95",
            "customer_phone": "+60123456789",
            "channel": "voice",
            "thread_id": "call_abc123",
            "role": "user",
            "content": "Hi, I want to book a viewing",
            "metadata": {"call_sid": "abc123"},
            "created_at": "2026-08-23T06:05:00+00:00",
        },
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "tenant_id": "607690ec-4ff7-4ef4-b98e-bfb00442fe95",
            "customer_phone": "+60123456789",
            "channel": "whatsapp",
            "thread_id": "+60123456789@s.whatsapp.net",
            "role": "assistant",
            "content": "hello, how can I help?",
            "metadata": {},
            "created_at": "2026-08-23T06:00:01+00:00",
        },
    ])
    return sb


# ---------------------------------------------------------------------------
# POST /api/shared-context/append
# ---------------------------------------------------------------------------


def test_append_happy_path(app, fake_tenant_id, fake_supabase):
    """POST append with valid body returns the inserted row."""
    _authenticate(app, fake_tenant_id)
    with patch("src.core.shared_context_api._supabase", return_value=fake_supabase):
        client = TestClient(app)

        r = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "whatsapp",
                "thread_id": "+60123456789@s.whatsapp.net",
                "role": "user",
                "content": "hi",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["channel"] == "whatsapp"
        assert body["role"] == "user"
        assert body["tenant_id"] == fake_tenant_id

        # tenant_id is taken from the session, never from the request body.
        written = fake_supabase.table.return_value.insert.call_args[0][0]
        assert written["tenant_id"] == fake_tenant_id


def test_append_rejects_invalid_channel(app, fake_tenant_id, fake_supabase):
    """POST append with channel='carrier-pigeon' returns 400."""
    _authenticate(app, fake_tenant_id)
    with patch("src.core.shared_context_api._supabase", return_value=fake_supabase):
        client = TestClient(app)

        r = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "carrier-pigeon",
                "thread_id": "t1",
                "role": "user",
                "content": "hi",
            },
        )
        assert r.status_code == 400
        assert "channel" in r.json()["detail"].lower()


def test_append_rejects_invalid_role(app, fake_tenant_id, fake_supabase):
    """POST append with role='admin' returns 400."""
    _authenticate(app, fake_tenant_id)
    with patch("src.core.shared_context_api._supabase", return_value=fake_supabase):
        client = TestClient(app)

        r = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "whatsapp",
                "thread_id": "t1",
                "role": "admin",
                "content": "hi",
            },
        )
        assert r.status_code == 400
        assert "role" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/shared-context
# ---------------------------------------------------------------------------


def test_get_returns_rows_sorted_desc(app, fake_tenant_id, fake_supabase):
    """GET asks Postgres for newest-first and passes that order through."""
    _authenticate(app, fake_tenant_id)
    with patch("src.core.shared_context_api._supabase", return_value=fake_supabase):
        client = TestClient(app)

        r = client.get("/api/shared-context", params={"phone": "+60123456789"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["count"] == 2
        # Ordering is the DB's job, so assert the API actually requested it...
        select_chain = fake_supabase.table.return_value.select.return_value
        select_chain.order.assert_called_once_with("created_at", desc=True)
        # ...and that the rows reach the client in the order the DB gave them.
        assert body["entries"][0]["channel"] == "voice"
        assert body["entries"][1]["channel"] == "whatsapp"


def test_get_empty_list_when_no_rows(app, fake_tenant_id):
    """GET returns count=0 and entries=[] when Supabase returns nothing."""
    empty_sb = MagicMock()
    chain = empty_sb.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(data=[])

    _authenticate(app, fake_tenant_id)
    with patch("src.core.shared_context_api._supabase", return_value=empty_sb):
        client = TestClient(app)

        r = client.get("/api/shared-context", params={"phone": "+60000000000"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["count"] == 0
        assert body["entries"] == []


# ---------------------------------------------------------------------------
# tenant_id isolation
# ---------------------------------------------------------------------------


def test_unauthenticated_request_returns_401_or_403(app):
    """A request with no session should fail before touching Supabase.

    No dependency override here: the real verify_session runs and, under the
    default DASHBOARD_MODE=strict, refuses a request that carries no session.
    We don't pin the exact status (400/401/403 all mean "denied"), only that
    it is not a success and that no write reached the DB.
    """
    sb_sentinel = MagicMock()
    with patch("src.core.shared_context_api._supabase", return_value=sb_sentinel):
        client = TestClient(app, raise_server_exceptions=False)

        r = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "whatsapp",
                "thread_id": "t1",
                "role": "user",
                "content": "hi",
            },
        )
        assert r.status_code != 200
        assert 400 <= r.status_code < 500
        # And critically: the Supabase client should not have been called
        # for a write (no tenant_id = no write).
        sb_sentinel.table.return_value.insert.assert_not_called()


# ---------------------------------------------------------------------------
# Sanity: the SQL migration file parses
# ---------------------------------------------------------------------------


def test_migration_sql_is_syntactically_clean():
    """The migration file is plain SQL; this test just asserts it exists and
    contains the expected table name. A real Postgres parse would require a
    running DB; the user can run `psql -f ...` manually after applying."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    migration_path = os.path.join(
        repo_root, "packages", "backend", "migrations-py", "add_shared_context.sql"
    )
    assert os.path.isfile(migration_path), f"missing migration: {migration_path}"
    with open(migration_path) as f:
        sql = f.read()
    assert "create table" in sql.lower()
    assert "shared_context" in sql
    assert "tenant_id" in sql
    assert "customer_phone" in sql
    assert "channel" in sql
    assert "role" in sql
    assert "content" in sql
    assert "row level security" in sql.lower()


# ---------------------------------------------------------------------------
# A2A seam round-trip (issue #31 — design the A2A seam protocol)
# ---------------------------------------------------------------------------
#
# The fundamental guarantee of the A2A layer: a single customer having a
# conversation across two channels (e.g., WhatsApp + voice) must see both
# channels' messages in a unified timeline, scoped to one tenant. The test
# below is the API-level proof — it stubs Supabase to record the inserts
# and returns them as if a real query had run, then asserts the API
# correctly threads the customer_phone + tenant_id through both writes
# and the read.


def _build_recording_supabase():
    """A Supabase mock that records every insert and returns them on GET.

    The mock is stateful: each `insert(row).execute()` stores the row with an
    auto-generated id and a monotonically increasing created_at, and every
    `select()...execute()` replays the stored rows honouring the chained
    eq()/gte()/order()/limit() calls the router made.

    created_at is anchored to *now* rather than a fixed date because the
    router's GET filters with `.gte("created_at", now - since_hours)`; a
    hard-coded 2026-08-23 timestamp would fall outside every window and the
    round-trip would silently read back nothing.

    This is intentionally more realistic than the `fake_supabase` fixture
    above: the seam test exercises actual round-trip behaviour, while
    the per-endpoint tests just assert that the API calls the chain
    correctly.
    """
    sb = MagicMock()
    state: Dict[str, Any] = {"rows": []}
    base = datetime.now(timezone.utc) - timedelta(minutes=10)

    def _do_insert(row):
        seq = len(state["rows"])
        full = {
            "id": f"00000000-0000-0000-0000-{seq:012d}",
            "created_at": (base + timedelta(seconds=seq)).isoformat(),
            **row,
        }
        state["rows"].append(full)
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[full])
        return chain

    sb.table.return_value.insert.side_effect = _do_insert

    def _do_select(*args, **kwargs):
        # The chain captures eq() filters; capture them as we go.
        filters: Dict[str, Any] = {}
        chain = MagicMock()

        def _eq(k, v):
            filters[k] = v
            return chain

        def _gte(k, v):
            filters[f"_gte_{k}"] = v
            return chain

        def _order(k, **kw):
            filters["_order"] = (k, kw.get("desc", False))
            return chain

        def _limit(n):
            filters["_limit"] = n
            return chain

        def _execute():
            rows = [r for r in state["rows"]
                    if all(r.get(k) == v for k, v in filters.items()
                           if not k.startswith("_"))]
            gte = filters.get("_gte_created_at")
            if gte:
                rows = [r for r in rows if r.get("created_at", "") >= gte]
            order_key, order_desc = filters.get("_order", ("created_at", True))
            rows = sorted(rows, key=lambda r: r.get(order_key, ""), reverse=order_desc)
            lim = filters.get("_limit", len(rows))
            rows = rows[:lim]
            return MagicMock(data=rows)

        chain.eq.side_effect = _eq
        chain.gte.side_effect = _gte
        chain.order.side_effect = _order
        chain.limit.side_effect = _limit
        chain.execute.side_effect = _execute
        return chain

    sb.table.return_value.select.side_effect = _do_select
    return sb, state


def test_a2a_round_trip_whatsapp_then_voice(app, fake_tenant_id):
    """A customer messages on WhatsApp, then 5 min later calls the voice
    concierge. The A2A layer must let the next query return both
    messages interleaved (newest first), scoped to the same tenant.

    This is the core invariant of issue #31. The test stubs Supabase
    but exercises the real FastAPI router end-to-end.
    """
    sb, state = _build_recording_supabase()

    _authenticate(app, fake_tenant_id)
    with patch("src.core.shared_context_api._supabase", return_value=sb):
        client = TestClient(app)

        # 1. WhatsApp message — the customer asks about a viewing
        r1 = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "whatsapp",
                "thread_id": "+60123456789@s.whatsapp.net",
                "role": "user",
                "content": "Hi, I want to book a viewing for unit 12B",
                "metadata": {"source": "whatsapp"},
            },
        )
        assert r1.status_code == 200, r1.text

        # 2. WhatsApp reply from the AI
        r2 = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "whatsapp",
                "thread_id": "+60123456789@s.whatsapp.net",
                "role": "assistant",
                "content": "Sure, unit 12B is available. What time works?",
                "metadata": {"message_id": "msg_001"},
            },
        )
        assert r2.status_code == 200, r2.text

        # 3. 5 min later: customer calls the voice concierge. The
        #    voice webhook writes to the same (tenant, phone) pair.
        r3 = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "voice",
                "thread_id": "call_abc123",
                "role": "user",
                "content": "Hi, I'm following up on the WhatsApp chat — is unit 12B still available?",
                "metadata": {"call_sid": "abc123", "transferred_from": "whatsapp"},
            },
        )
        assert r3.status_code == 200, r3.text

        # 4. The voice AI reply
        r4 = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "voice",
                "thread_id": "call_abc123",
                "role": "assistant",
                "content": "Yes, I see we discussed unit 12B on WhatsApp. Booking for tomorrow at 3pm?",
                "metadata": {"call_sid": "abc123"},
            },
        )
        assert r4.status_code == 200, r4.text

        # 5. Now the BIJOU DASHBOARD asks: "show me the unified thread
        #    for this customer". GET should return all 4 messages,
        #    newest first, regardless of channel.
        r5 = client.get(
            "/api/shared-context",
            params={"phone": "+60123456789", "since_hours": 24, "limit": 50},
        )
        assert r5.status_code == 200, r5.text
        body = r5.json()
        assert body["count"] == 4, f"expected 4 entries, got {body['count']}"

        # The voice assistant reply (last written) should be first
        # (newest first ordering)
        assert body["entries"][0]["channel"] == "voice"
        assert body["entries"][0]["role"] == "assistant"
        assert "WhatsApp" in body["entries"][0]["content"]

        # The voice user message (r3) is second
        assert body["entries"][1]["channel"] == "voice"
        assert body["entries"][1]["role"] == "user"

        # The two WhatsApp messages are 3rd and 4th
        assert body["entries"][2]["channel"] == "whatsapp"
        assert body["entries"][3]["channel"] == "whatsapp"

        # Every row is tenant-scoped (the API always sets tenant_id
        # from verify_session, never from request body)
        for entry in body["entries"]:
            assert entry["tenant_id"] == fake_tenant_id, (
                f"tenant_id leak: {entry['tenant_id']} != {fake_tenant_id}"
            )

        # Every row preserves the customer_phone
        for entry in body["entries"]:
            assert entry["customer_phone"] == "+60123456789"


def test_a2a_cross_tenant_isolation(app):
    """Two tenants both have customers with the same phone. The A2A
    read for tenant A must NEVER return rows for tenant B. This is
    the security primitive that keeps the cross-channel inbox from
    being a data-leak vector.
    """
    sb, state = _build_recording_supabase()
    tenant_a = "607690ec-4ff7-4ef4-b98e-bfb00442fe95"
    tenant_b = "00000000-0000-0000-0000-000000000999"

    client = TestClient(app)

    with patch("src.core.shared_context_api._supabase", return_value=sb):
        # Tenant A writes a row for the phone
        _authenticate(app, tenant_a)
        r = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "whatsapp",
                "thread_id": "t1",
                "role": "user",
                "content": "I'm tenant A's customer",
            },
        )
        assert r.status_code == 200, r.text

        # Tenant B writes a row for the SAME phone (totally different
        # business, same customer, same phone)
        _authenticate(app, tenant_b)
        r = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "whatsapp",
                "thread_id": "t2",
                "role": "user",
                "content": "I'm tenant B's customer",
            },
        )
        assert r.status_code == 200, r.text

        # Both rows really are in the shared store — otherwise the
        # isolation assertions below would pass vacuously.
        assert len(state["rows"]) == 2
        assert {row["tenant_id"] for row in state["rows"]} == {tenant_a, tenant_b}

        # Tenant A's read: should only see the tenant_a row
        _authenticate(app, tenant_a)
        r = client.get(
            "/api/shared-context",
            params={"phone": "+60123456789"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["count"] == 1, f"tenant A should see 1 row, got {body['count']}"
        assert body["entries"][0]["tenant_id"] == tenant_a
        assert "tenant A" in body["entries"][0]["content"]

        # Tenant B's read: should only see the tenant_b row
        _authenticate(app, tenant_b)
        r = client.get(
            "/api/shared-context",
            params={"phone": "+60123456789"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["count"] == 1, f"tenant B should see 1 row, got {body['count']}"
        assert body["entries"][0]["tenant_id"] == tenant_b
        assert "tenant B" in body["entries"][0]["content"]


def test_a2a_channel_value_set(app):
    """The A2A protocol contract documents the allowed channel values.
    Test that the API rejects an unknown channel with 400 BEFORE
    touching Supabase (so a bad client cannot waste a DB round-trip
    or smuggle in a non-canonical channel value).
    """
    sb = MagicMock()
    _authenticate(app, "t1")
    with patch("src.core.shared_context_api._supabase", return_value=sb):
        client = TestClient(app)

        r = client.post(
            "/api/shared-context/append",
            json={
                "customer_phone": "+60123456789",
                "channel": "fax",  # not in the allowed set
                "thread_id": "t1",
                "role": "user",
                "content": "hello",
            },
        )
        assert r.status_code == 400
        assert "channel" in r.json()["detail"].lower()
        # Supabase was never touched
        sb.table.return_value.insert.assert_not_called()
