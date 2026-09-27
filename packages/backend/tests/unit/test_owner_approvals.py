"""Owner approval queue state machine + per-tenant owner resolution.

A tiny in-memory stand-in for the Supabase query builder (only the calls
owner_approvals.py makes), so tenant filtering and compare-and-set are
exercised for real rather than asserted on mocks.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.core import owner_approvals as oa


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload = db, table, [], "select", None

    def select(self, *_):
        return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def update(self, vals):
        self.op, self.payload = "update", vals
        return self

    def upsert(self, row, on_conflict=None):
        self.op, self.payload = "upsert", row
        return self

    def eq(self, c, v):
        self.filters.append(lambda r: r.get(c) == v)
        return self

    def gt(self, c, v):
        self.filters.append(lambda r: r.get(c) > v)
        return self

    def lte(self, c, v):
        self.filters.append(lambda r: r.get(c) <= v)
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_):
        return self

    def execute(self):
        if self.table in self.db.missing:
            raise RuntimeError(f'relation "{self.table}" does not exist')
        rows = self.db.tables.setdefault(self.table, [])
        if self.op in ("insert", "upsert"):
            rows.append(dict(self.payload))
            return SimpleNamespace(data=[dict(self.payload)])
        hit = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op == "update":
            for r in hit:
                r.update(self.payload)
        return SimpleNamespace(data=[dict(r) for r in hit])


class FakeDB:
    def __init__(self, missing=()):
        self.tables, self.missing = {}, set(missing)

    def table(self, name):
        return _Q(self, name)


T1, T2 = "tenant-1", "tenant-2"
CUST = "60111111111@s.whatsapp.net"


@pytest.fixture(autouse=True)
def _fresh_owner_cache():
    oa._owner_cache.clear()
    yield
    oa._owner_cache.clear()


@pytest.fixture
def sent():
    return []


@pytest.fixture
def notify(sent):
    return lambda tenant, jid, text: sent.append((tenant, jid, text))


def _db_with_owner(phones=("60123456789",)):
    db = FakeDB()
    db.tables["tenants"] = [{"id": T1, "owner_phones": list(phones)}, {"id": T2, "owner_phones": ["60999999999"]}]
    return db


def _reasons(db):
    return [r["metadata"]["approval_decision"] for r in db.tables.get("message_reasons", [])]


# ── owner resolution ────────────────────────────────────────────────────────


def test_owner_phones_per_tenant(monkeypatch):
    monkeypatch.setenv("OWNER_WHATSAPP_JID", "60100000000@s.whatsapp.net")
    db = _db_with_owner(("+60 12-345 6789",))
    assert oa.resolve_owner_phones(db, T1) == ["60123456789"]
    assert oa.resolve_owner_phones(db, T2) == ["60999999999"]


def test_owner_falls_back_to_global_env(monkeypatch):
    monkeypatch.setenv("OWNER_WHATSAPP_JID", "+60100000000@s.whatsapp.net")
    db = _db_with_owner(())
    assert oa.resolve_owner_phones(db, T1) == ["60100000000"]


def test_owner_column_missing_degrades_to_env(monkeypatch):
    monkeypatch.setenv("OWNER_WHATSAPP_JID", "60100000000@s.whatsapp.net")
    assert oa.resolve_owner_phones(FakeDB(missing={"tenants"}), T1) == ["60100000000"]


# ── parsing ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("text,expected", [
    ("1", ("approved", None)), ("Approve", None), ("2", ("rejected", None)),
    ("reject #ab12", ("rejected", "ab12")), ("1 ab12", ("approved", "ab12")),
    ("hello there", None), ("1 2 3", None), ("", None),
    # bare words must not hijack a casual owner DM; ids must look like ids
    ("yes", None), ("no", None), ("tolak", None), ("tolak ab12", ("rejected", "ab12")),
    ("1 more", None), ("no way", None),
])
def test_parse_decision(text, expected):
    assert oa.parse_decision(text) == expected


# ── state machine ───────────────────────────────────────────────────────────


def test_request_notifies_owner_and_queues(notify, sent):
    db = _db_with_owner()
    res = oa.request_approval(db, T1, CUST, "book_appointment", {"time": "15:00"}, notify)
    assert res["status"] == "pending_owner_approval"
    [row] = db.tables["pending_actions"]
    assert row["status"] == "pending" and row["tenant_id"] == T1
    assert sent[0][1] == "60123456789@s.whatsapp.net"
    assert "Reply 1 to approve, 2 to reject" in sent[0][2]


def test_request_never_routes_to_global_owner(monkeypatch, notify, sent):
    """No tenant owner_phones -> no approval (plain 'blocked'), even though the
    global OWNER_WHATSAPP_JID is set: one tenant's customer data must never be
    WhatsApped to the platform owner."""
    monkeypatch.setenv("OWNER_WHATSAPP_JID", "60100000000@s.whatsapp.net")
    db = _db_with_owner(())
    assert oa.request_approval(db, T1, CUST, "book_appointment", {}, notify) is None
    assert sent == [] and "pending_actions" not in db.tables
    assert oa.resolve_owner_phones(db, T1) == ["60100000000"]  # detection still falls back


def test_request_dedupes_and_caps_per_chat(notify, sent):
    db = _db_with_owner()
    a = oa.request_approval(db, T1, CUST, "book_appointment", {"time": "15:00"}, notify)
    b = oa.request_approval(db, T1, CUST, "book_appointment", {"time": "15:00"}, notify)
    assert a == b and len(db.tables["pending_actions"]) == 1 and len(sent) == 1
    for i in range(oa.MAX_PENDING_PER_CHAT - 1):
        assert oa.request_approval(db, T1, CUST, "send_email", {"n": i}, notify)
    assert oa.request_approval(db, T1, CUST, "send_email", {"n": 99}, notify) is None  # capped
    assert len(db.tables["pending_actions"]) == oa.MAX_PENDING_PER_CHAT
    assert oa.request_approval(db, T1, "60222222222@s.whatsapp.net", "send_email", {}, notify)  # other chat ok


def test_request_without_table_returns_none(notify, sent):
    db = _db_with_owner()
    db.missing.add("pending_actions")
    assert oa.request_approval(db, T1, CUST, "book_appointment", {}, notify) is None
    assert sent == []


def test_approve_executes_once_and_tells_customer(notify, sent):
    db = _db_with_owner()
    oa.request_approval(db, T1, CUST, "book_appointment", {"time": "15:00"}, notify)
    calls = []

    async def execute(row):
        calls.append(row["tool"])
        return {"success": True}

    reply = asyncio.run(oa.handle_owner_reply(db, T1, "60123456789@s.whatsapp.net", "1", execute, notify))
    assert "Approved" in reply and calls == ["book_appointment"]
    assert db.tables["pending_actions"][0]["status"] == "approved"
    assert (T1, CUST, oa.CUSTOMER_APPROVED) in sent
    assert _reasons(db) == ["approved"]
    # A second "1" finds nothing pending -> falls through, never re-executes.
    assert asyncio.run(oa.handle_owner_reply(db, T1, "60123456789", "1", execute, notify)) is None
    assert calls == ["book_appointment"]


def test_reject_does_not_execute(notify, sent):
    db = _db_with_owner()
    oa.request_approval(db, T1, CUST, "refund_payment", {}, notify)

    async def execute(row):
        raise AssertionError("must not run")

    reply = asyncio.run(oa.handle_owner_reply(db, T1, "60123456789", "2", execute, notify))
    assert "Rejected" in reply
    assert db.tables["pending_actions"][0]["status"] == "rejected"
    assert (T1, CUST, oa.CUSTOMER_REJECTED) in sent
    assert _reasons(db) == ["rejected"]


def test_several_pending_needs_short_id(notify):
    db = _db_with_owner()
    oa.request_approval(db, T1, CUST, "book_appointment", {}, notify)
    oa.request_approval(db, T1, CUST, "send_email", {}, notify)
    second = db.tables["pending_actions"][1]

    async def execute(row):
        return {"success": True}

    listing = asyncio.run(oa.handle_owner_reply(db, T1, "60123456789", "1", execute, notify))
    assert "2 requests waiting" in listing
    assert all(r["status"] == "pending" for r in db.tables["pending_actions"])
    asyncio.run(oa.handle_owner_reply(db, T1, "60123456789", f"1 {oa.short_id(second)}", execute, notify))
    assert [r["status"] for r in db.tables["pending_actions"]] == ["pending", "approved"]


def test_tenant_isolation(notify):
    db = _db_with_owner()
    oa.request_approval(db, T1, CUST, "book_appointment", {}, notify)

    async def execute(row):
        raise AssertionError("other tenant must not execute")

    assert asyncio.run(oa.handle_owner_reply(db, T2, "60999999999", "1", execute, notify)) is None
    assert db.tables["pending_actions"][0]["status"] == "pending"


def test_expiry_auto_rejects(notify, sent):
    db = _db_with_owner()
    oa.request_approval(db, T1, CUST, "book_appointment", {}, notify)
    db.tables["pending_actions"][0]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()
    assert oa.expire_due(db, notify) == 1
    assert db.tables["pending_actions"][0]["status"] == "expired"
    assert db.tables["pending_actions"][0]["decided_by"] == "system"
    assert (T1, CUST, oa.CUSTOMER_EXPIRED) in sent
    assert _reasons(db) == ["expired"]
    assert oa.expire_due(db, notify) == 0  # idempotent


def test_failed_execution_is_logged_and_customer_told(notify, sent):
    db = _db_with_owner()
    oa.request_approval(db, T1, CUST, "book_appointment", {}, notify)

    async def execute(row):
        return {"success": False, "error": "slot taken"}

    reply = asyncio.run(oa.handle_owner_reply(db, T1, "60123456789", "1", execute, notify))
    assert "failed" in reply
    assert (T1, CUST, oa.CUSTOMER_FAILED) in sent
    assert "slot taken" in db.tables["message_reasons"][0]["metadata"]["reason"]


def test_gateway_agent_on_confirm_replaces_blocked_result():
    """The gateway loop hands 'confirm' tools to on_confirm (the approval queue)."""
    from src.core.gateway_agent import run_gateway_agent

    tc = SimpleNamespace(id="t1", function=SimpleNamespace(name="book_appointment", arguments='{"time": "15:00"}'))
    replies = iter([
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tc]))]),
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Passed to owner", tool_calls=None))]),
    ])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: next(replies))))
    seen = []

    async def exe(n, a):
        raise AssertionError("must not execute")

    out = asyncio.run(run_gateway_agent(
        system="s", user_message="u", history=[], declarations=[], client=client, model_chain=["m"],
        execute_tool=exe, guard=lambda n: "confirm",
        on_confirm=lambda n, a: seen.append((n, a)) or {"status": "pending_owner_approval"},
    ))
    assert seen == [("book_appointment", {"time": "15:00"})]
    assert out["steps"][0]["result"]["status"] == "pending_owner_approval"


def test_openai_tools_path_honours_guard(monkeypatch):
    """The MiniMax/OpenAI-compatible loop (the PRIMARY provider path) had no
    ActionGuard at all; the guard hook must stop the tool from running."""
    import openai

    from src.saas.function_caller import FunctionCaller

    tc = SimpleNamespace(id="t1", function=SimpleNamespace(name="book_appointment", arguments="{}"))
    replies = iter([
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tc]))]),
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))]),
    ])
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: next(replies))))
    monkeypatch.setattr(openai, "OpenAI", lambda **_: fake)
    fc = FunctionCaller()

    async def boom(*_a, **_k):
        raise AssertionError("guarded tool must not run")

    fc._call_function = boom
    msgs = [{"role": "user", "content": "book me"}]
    out = asyncio.run(fc.call_with_openai_tools(
        msgs, model="m", api_key="k", guard=lambda n, a: {"status": "pending_owner_approval"},
    ))
    assert out == "ok"
    assert '"pending_owner_approval"' in msgs[-1]["content"]


def test_bijou_guard_tool_queues_only_when_flag_on(monkeypatch):
    """Bijou._guard_tool: ActionGuard 'confirm' -> approval queue when
    ENABLE_OWNER_APPROVALS is on for the tenant, plain 'blocked' otherwise."""
    from src.core.bijou import BijouAI

    db = _db_with_owner()
    sent = []
    bot = BijouAI.__new__(BijouAI)
    bot.db_conn = db
    bot.send_message = lambda jid, text, tenant_id=None: sent.append((tenant_id, jid))

    monkeypatch.delenv("ENABLE_OWNER_APPROVALS", raising=False)
    assert bot._guard_tool(T1, CUST, "book_appointment", {})["status"] == "blocked"
    assert "pending_actions" not in db.tables and sent == []

    monkeypatch.setenv("ENABLE_OWNER_APPROVALS", "true")
    monkeypatch.setenv("AGENT_TENANT_ALLOWLIST", T1)
    assert bot._guard_tool(T1, CUST, "book_appointment", {})["status"] == "pending_owner_approval"
    assert sent == [(T1, "60123456789@s.whatsapp.net")]
    assert bot._guard_tool(T2, CUST, "book_appointment", {})["status"] == "blocked"  # not allowlisted
    assert bot._guard_tool(T1, CUST, "search_knowledge", {}) is None  # safe tool runs


# ── dashboard API ───────────────────────────────────────────────────────────


def test_owner_phones_api_uses_session_tenant(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.core import owner_phones_api
    from src.core.dashboard_api_simple import verify_session

    db = _db_with_owner()
    monkeypatch.setattr(owner_phones_api, "_supabase", lambda: db)
    app = FastAPI()
    app.include_router(owner_phones_api.router)
    app.dependency_overrides[verify_session] = lambda: T1
    c = TestClient(app)

    r = c.put("/api/dashboard/owner-phones", json={"owner_phones": ["+60 12-777 8888", "60127778888"]})
    assert r.status_code == 200 and r.json() == {"owner_phones": ["60127778888"]}
    assert db.tables["tenants"][1]["owner_phones"] == ["60999999999"]  # other tenant untouched
    assert c.get("/api/dashboard/owner-phones").json() == {"owner_phones": ["60127778888"]}
    assert c.put("/api/dashboard/owner-phones", json={"owner_phones": ["abc"]}).status_code == 400

    db.missing.add("tenants")  # migration not applied yet
    assert c.get("/api/dashboard/owner-phones").status_code == 503


# ── real process_message filter ordering ────────────────────────────────────


OWNER_JID = "60123456789@s.whatsapp.net"


def _bot(db, monkeypatch):
    """BijouAI with just enough state for process_message to reach the owner
    branches: tenant routing -> T1, no filters/blacklist, no LLM."""
    from src.core.bijou import BijouAI

    class _Router:
        async def identify_tenant(self, **_):
            return T1

        async def get_client_config(self, _t):
            return {}

    bot = BijouAI.__new__(BijouAI)
    bot.db_conn, bot.config, bot.tenant_router, bot.message_filter = db, {}, _Router(), None
    bot.processed_message_ids, bot.rate_limiter = set(), {}
    bot.rate_limit_max, bot.rate_limit_window = 10, 60
    bot.recent_sent, bot.recent_sent_ttl, bot.recent_sent_max_per_chat = {}, 120, 10
    bot.owner_jid, bot.owner_linked_devices = OWNER_JID, {}
    bot.groups_manager = bot.ticket_manager = None
    bot.outbox = []
    bot.send_message = lambda jid, text, tenant_id=None, **_: bot.outbox.append((jid, text)) or True
    monkeypatch.setenv("ENABLE_OWNER_APPROVALS", "true")
    monkeypatch.delenv("AGENT_TENANT_ALLOWLIST", raising=False)
    return bot


def test_owner_digit_reply_survives_typing_and_self_echo_filters(monkeypatch):
    """A bare '1' is <2 chars (typing filter) AND a substring of the summary we
    just sent the owner (self-echo filter). It must still reach the approval
    handler, through the real process_message ordering."""
    db = _db_with_owner()
    bot = _bot(db, monkeypatch)
    ran = []

    async def _call_function(name, args, ctx):
        ran.append(name)
        return {"success": True}

    bot.function_caller = SimpleNamespace(_call_function=_call_function)
    oa.request_approval(db, T1, CUST, "book_appointment", {}, lambda *_: None)
    bot._record_sent_message(OWNER_JID, oa._summary(db.tables["pending_actions"][0]))

    asyncio.run(bot.process_message({"id": "m1", "chat_jid": OWNER_JID, "sender": OWNER_JID, "content": "1"}))
    assert ran == ["book_appointment"]
    assert db.tables["pending_actions"][0]["status"] == "approved"
    assert any(jid == OWNER_JID and "Approved" in t for jid, t in bot.outbox)
    assert (CUST, oa.CUSTOMER_APPROVED) in bot.outbox


def test_customer_digit_is_not_an_approval(monkeypatch):
    db = _db_with_owner()
    bot = _bot(db, monkeypatch)
    oa.request_approval(db, T1, CUST, "book_appointment", {}, lambda *_: None)
    asyncio.run(bot.process_message({"id": "m2", "chat_jid": CUST, "sender": CUST, "content": "1"}))
    assert db.tables["pending_actions"][0]["status"] == "pending"


def test_bijou_command_gets_message_text_not_dict(monkeypatch):
    """handle_command(message=...) expects the text; bijou.py passed the whole
    webhook dict, so every @bijou owner command crashed in is_command()."""
    bot = _bot(_db_with_owner(), monkeypatch)
    seen = []

    async def handle_command(message, chat_jid, sender, tenant_id=""):
        seen.append(message)
        return "ok"

    bot.command_handler = SimpleNamespace(handle_command=handle_command)
    asyncio.run(bot.process_message({"id": "m3", "chat_jid": OWNER_JID, "sender": OWNER_JID, "content": "@bijou bookings"}))
    assert seen == ["@bijou bookings"]
