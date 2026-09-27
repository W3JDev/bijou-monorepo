"""Owner morning brief (ENABLE_MORNING_BRIEF): DB aggregation, the 09:00
tenant-local due-check, and per-tenant-per-date idempotency across restarts /
workers (the morning_briefs primary key is the guard)."""
import asyncio
from datetime import date, datetime, timezone

import pytest

from src.core import morning_brief as mb
from src.core.proactive_messaging import ProactiveMessagingSystem

UTC = timezone.utc
T1 = "11111111-1111-1111-1111-111111111111"


class _Res:
    def __init__(self, data):
        self.data = data
        self.count = len(data)


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op = db, table, [], ("select",)

    def select(self, *a, **k):
        return self

    def eq(self, c, v):
        self.filters.append(lambda r: r.get(c) == v)
        return self

    def gte(self, c, v):
        self.filters.append(lambda r: r.get(c) is not None and r[c] >= v)
        return self

    def lt(self, c, v):
        self.filters.append(lambda r: r.get(c) is not None and r[c] < v)
        return self

    def in_(self, c, vs):
        self.filters.append(lambda r: r.get(c) in vs)
        return self

    def insert(self, row):
        self.op = ("insert", row)
        return self

    def update(self, row):
        self.op = ("update", row)
        return self

    def execute(self):
        if self.table in self.db.missing:
            raise Exception("PGRST205 Could not find the table")
        rows = self.db.rows.setdefault(self.table, [])
        if self.op[0] == "insert":
            row = self.op[1]
            if self.table == "morning_briefs" and any(
                r["tenant_id"] == row["tenant_id"] and r["brief_date"] == row["brief_date"] for r in rows
            ):
                raise Exception("23505 duplicate key value violates unique constraint")
            rows.append(dict(row))
            return _Res([row])
        hit = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op[0] == "update":
            for r in hit:
                r.update(self.op[1])
        return _Res(hit)


class FakeDB:
    def __init__(self, rows=None, missing=()):
        self.rows, self.missing = rows or {}, set(missing)

    def table(self, name):
        return _Q(self, name)


def _iso(h, d=26):
    return datetime(2026, 9, d, h, 0, tzinfo=UTC).isoformat()


def _tenant(**kw):
    t = {"id": T1, "name": "Kedai Ali", "owner_phone": "+60 12-345 6789",
         "whatsapp_jid": "60999:3@s.whatsapp.net", "settings": {},
         "business_hours": {"timezone": "Asia/Kuala_Lumpur"}, "is_active": True,
         "whatsapp_connected": True}
    t.update(kw)
    return t


@pytest.fixture(autouse=True)
def _fresh_process(monkeypatch):
    mb._handled.clear()

    async def _no_llm(*a, **k):
        raise RuntimeError("no provider in unit tests")

    import src.core.llm_gateway_v2 as gw
    monkeypatch.setattr(gw.llm, "complete", _no_llm)


# --- due-check / timezone ---------------------------------------------------

def test_due_at_nine_local_with_timezones():
    kl = mb.tenant_tz(_tenant())
    assert mb.due_local_date(datetime(2026, 9, 26, 1, 0, tzinfo=UTC), kl) == date(2026, 9, 26)   # 09:00 KL
    assert mb.due_local_date(datetime(2026, 9, 26, 0, 59, tzinfo=UTC), kl) is None               # 08:59 KL
    assert mb.due_local_date(datetime(2026, 9, 26, 4, 0, tzinfo=UTC), kl) is None                # 12:00 KL
    # Local date, not UTC date: 09:00 in Auckland (+12) is still the 25th in UTC.
    nz = mb.tenant_tz(_tenant(business_hours={"timezone": "Pacific/Auckland"}))
    assert mb.due_local_date(datetime(2026, 9, 25, 21, 0, tzinfo=UTC), nz) == date(2026, 9, 26)


def test_timezone_defaults_to_utc():
    for t in (_tenant(business_hours=None), _tenant(business_hours={"timezone": "Not/AZone"})):
        tz = mb.tenant_tz(t)
        assert str(tz) == "UTC"
        assert mb.due_local_date(datetime(2026, 9, 26, 9, 30, tzinfo=UTC), tz) == date(2026, 9, 26)
    assert str(mb.tenant_tz(_tenant(business_hours={}, settings={"timezone": "Europe/London"}))) == "Europe/London"


def test_owner_destination_is_tenant_self_chat_not_owner_phone():
    # owner_phone replies would be handled as a customer chat; self-chat replies are is_from_me.
    assert mb.owner_jid(_tenant()) == "60999@s.whatsapp.net"   # device suffix stripped
    assert mb.owner_jid(_tenant(whatsapp_jid=None)) is None


# --- aggregation ------------------------------------------------------------

def _seeded_db():
    return FakeDB({
        "tenants": [_tenant(business_hours={"timezone": "UTC"})],
        "contacts": [
            {"tenant_id": T1, "tag": "hot_lead", "first_message_at": _iso(5), "last_message_at": _iso(6)},
            {"tenant_id": T1, "tag": "inquiry", "first_message_at": _iso(3), "last_message_at": _iso(3)},
            {"tenant_id": T1, "tag": "lead", "first_message_at": _iso(2), "last_message_at": _iso(2)},
            {"tenant_id": T1, "tag": "hot_lead", "first_message_at": _iso(5, d=20), "last_message_at": _iso(7)},
            {"tenant_id": T1, "tag": "lead", "first_message_at": _iso(5, d=20), "last_message_at": _iso(5, d=20)},
            {"tenant_id": "other", "tag": "hot_lead", "first_message_at": _iso(5), "last_message_at": _iso(5)},
        ],
        "call_bookings": [{"tenant_id": T1, "created_at": _iso(4)}, {"tenant_id": T1, "created_at": _iso(4, d=24)}],
        "messages": [
            {"tenant_id": T1, "role": "assistant", "created_at": _iso(3)},
            {"tenant_id": T1, "role": "assistant", "created_at": _iso(4)},
            {"tenant_id": T1, "role": "user", "created_at": _iso(4)},
            {"tenant_id": "other", "role": "assistant", "created_at": _iso(4)},
        ],
        "escalations": [
            {"tenant_id": T1, "status": "pending", "reason_type": "knowledge_gap", "created_at": _iso(2)},
            {"tenant_id": T1, "status": "resolved", "reason_type": "human_request", "created_at": _iso(3)},
        ],
        "whatsapp_devices": [{"tenant_id": T1, "device_id": "bijou-dev-1"}],
    })


def test_aggregate_counts_last_24h_for_this_tenant_only():
    stats = mb.aggregate(_seeded_db(), T1, datetime(2026, 9, 25, 9, tzinfo=UTC), datetime(2026, 9, 26, 9, tzinfo=UTC))
    assert stats == {
        "new_conversations": 3, "leads": 2, "hot_leads": 2, "bookings": 1,
        "ai_messages": 2, "escalations": 2, "unanswered": 1, "knowledge_gaps": 1,
    }
    assert mb.suggest_action(stats).startswith("Reply to the 1 customer")
    text = mb.fallback_text("Kedai Ali", stats, mb.suggest_action(stats))
    assert "New conversations: 3" in text and "Messages handled by AI: 2" in text


def test_aggregate_missing_table_is_none_not_crash():
    stats = mb.aggregate(FakeDB(missing={"call_bookings", "escalations"}), T1,
                         datetime(2026, 9, 25, tzinfo=UTC), datetime(2026, 9, 26, tzinfo=UTC))
    assert stats["bookings"] is None and stats["escalations"] is None
    assert "Bookings: -" in mb.fallback_text("X", stats, "a")


def test_llm_text_that_drops_a_number_falls_back(monkeypatch):
    import src.core.llm_gateway_v2 as gw

    class R:
        text = "Morning boss! Busy day yesterday, check your leads."

    async def _llm(*a, **k):
        return R()

    monkeypatch.setattr(gw.llm, "complete", _llm)
    stats = {"new_conversations": 7, "leads": 0}
    out = asyncio.run(mb.phrase("Biz", stats, "Do it.", T1))
    assert out == mb.fallback_text("Biz", stats, "Do it.")


def test_llm_text_kept_when_all_numbers_survive(monkeypatch):
    import src.core.llm_gateway_v2 as gw
    calls = []

    class R:
        text = "Morning boss! 7 new chats yesterday. Do it."

    async def _llm(alias, messages, **k):
        calls.append(alias)
        return R()

    monkeypatch.setattr(gw.llm, "complete", _llm)
    assert asyncio.run(mb.phrase("Biz", {"new_conversations": 7, "leads": 0}, "Do it.", T1)) == R.text
    assert calls == ["ai://fast"]


# --- idempotency / gating ---------------------------------------------------

NINE = datetime(2026, 9, 26, 9, 5, tzinfo=UTC)  # seeded tenant is on UTC


def _run(db, sent, enabled=lambda t: True, now=NINE):
    async def send(jid, text, tid):
        sent.append((jid, text, tid))
        return True
    return asyncio.run(mb.run_due_briefs(db, send, enabled, now=now))


def test_sends_once_per_tenant_per_date_across_restarts_and_workers():
    db, sent = _seeded_db(), []
    assert _run(db, sent) == 1
    assert sent[0][0] == "60999@s.whatsapp.net" and "Suggested action" in sent[0][1]
    mb._handled.clear()                                       # restart / other worker
    assert _run(db, sent, now=NINE.replace(minute=40)) == 0
    assert len(sent) == 1
    row = db.rows["morning_briefs"][0]
    assert row["status"] == "sent" and row["stats"]["new_conversations"] == 3
    mb._handled.clear()                                       # next local day sends again
    assert _run(db, sent, now=datetime(2026, 9, 27, 9, 5, tzinfo=UTC)) == 1


def test_missing_ledger_table_sends_nothing():
    db = _seeded_db()
    db.missing.add("morning_briefs")
    sent = []
    assert _run(db, sent) == 0 and sent == []


def test_opt_out_flag_gate_and_outside_window_send_nothing():
    sent = []
    assert _run(FakeDB({"tenants": [_tenant(settings={"morning_brief": False})]}), sent) == 0
    assert _run(_seeded_db(), sent, enabled=lambda t: False) == 0
    assert _run(_seeded_db(), sent, now=datetime(2026, 9, 26, 12, tzinfo=UTC)) == 0  # past window
    assert sent == []


def test_scheduler_hook_is_off_without_env_flag(monkeypatch):
    monkeypatch.delenv("ENABLE_MORNING_BRIEF", raising=False)
    s = ProactiveMessagingSystem(_seeded_db(), channel_adapter=None,
                                 wa_sender=lambda *a, **k: True, feature_enabled=lambda f, t: True)
    assert asyncio.run(s._process_morning_briefs()) == 0


def test_tenant_without_own_connected_device_is_skipped():
    # No whatsapp_devices row -> send_message would use another business's device.
    db, sent = _seeded_db(), []
    db.rows["whatsapp_devices"] = []
    assert _run(db, sent) == 0
    # Row exists but WhatsApp not connected.
    mb._handled.clear()
    db = _seeded_db()
    db.rows["tenants"][0]["whatsapp_connected"] = False
    assert _run(db, sent) == 0
    assert sent == [] and "morning_briefs" not in db.rows   # no claim consumed


def test_cancelled_or_churned_tenant_is_skipped():
    for kw in ({"status": "cancelled"}, {"subscription_status": "churned"}):
        mb._handled.clear()
        db, sent = _seeded_db(), []
        db.rows["tenants"][0].update(kw)
        assert _run(db, sent) == 0 and sent == []


def test_one_malformed_tenant_does_not_stop_the_others():
    db, sent = _seeded_db(), []
    good = db.rows["tenants"][0]
    db.rows["tenants"] = [
        {"id": "bad1", "settings": "not-a-dict", "business_hours": {"timezone": "UTC"},
         "whatsapp_jid": "60111@s.whatsapp.net", "whatsapp_connected": True},
        {"id": "bad2", "business_hours": {"timezone": "UTC"}, "whatsapp_jid": 12345},  # jid not a str
        "garbage-row",
        good,
    ]
    assert _run(db, sent) == 1
    assert [s[2] for s in sent] == [T1]


def test_scheduler_hook_ticks_at_most_every_five_minutes(monkeypatch):
    monkeypatch.setenv("ENABLE_MORNING_BRIEF", "true")
    calls = []

    async def fake_run(*a, **k):
        calls.append(1)
        return 0

    monkeypatch.setattr(mb, "run_due_briefs", fake_run)
    s = ProactiveMessagingSystem(_seeded_db(), channel_adapter=None,
                                 wa_sender=lambda *a, **k: True, feature_enabled=lambda f, t: True)
    asyncio.run(s._process_morning_briefs())
    asyncio.run(s._process_morning_briefs())
    assert calls == [1]
