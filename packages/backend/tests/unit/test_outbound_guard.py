"""Ban-safe outbound guard (GOWA): proactive sends need a 24h window or consent,
are paced per tenant, and never reach stopped/blocked/paused contacts."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.core import outbound_guard as g

T = "tenant-1"
JID = "60123456789@s.whatsapp.net"


class _Q:
    def __init__(self, rows):
        self._rows = list(rows)

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def is_(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) is None]
        return self

    def order(self, col, desc=False):
        self._rows.sort(key=lambda r: r.get(col) or "", reverse=desc)
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    def lte(self, *a):
        return self

    def update(self, values):
        self.updates.append(values)
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class FakeDB:
    def __init__(self, **tables):
        self.tables = tables
        self.updates = []

    def table(self, name):
        q = _Q(self.tables.get(name, []))
        q.updates = self.updates
        return q


def _ago(**kw):
    return (datetime.now(timezone.utc) - timedelta(**kw)).isoformat()


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setenv("ENABLE_OUTBOUND_SAFETY", "true")
    monkeypatch.setenv("OUTBOUND_DAILY_CAP", "50")
    monkeypatch.setenv("OUTBOUND_MIN_SPACING_SEC", "0")
    g._tenant_sends.clear()


def _inbound(content="hi", **ago):
    return {"tenant_id": T, "chat_jid": JID, "role": "user", "content": content, "created_at": _ago(**ago)}


def test_proactive_blocked_without_window_or_consent():
    db = FakeDB(messages=[_inbound(hours=30)])
    assert g.check_outbound(db, T, JID, g.PROACTIVE) == (False, "no_24h_window_or_consent")


def test_proactive_allowed_inside_24h_window():
    db = FakeDB(messages=[_inbound(hours=2)])
    assert g.check_outbound(db, T, JID, g.PROACTIVE) == (True, "24h_window")


def test_proactive_allowed_with_active_opt_in():
    db = FakeDB(
        contacts=[{"id": "c1", "tenant_id": T, "jid": JID}],
        outreach_consent_log=[{"tenant_id": T, "contact_id": "c1", "consent_type": "opt_in",
                               "revoked_at": None, "granted_at": _ago(days=3)}],
    )
    assert g.check_outbound(db, T, JID, g.PROACTIVE) == (True, "consent")


def test_transactional_needs_no_window():
    assert g.check_outbound(FakeDB(), T, JID, g.TRANSACTIONAL) == (True, "transactional")


@pytest.mark.parametrize("db,reason", [
    (FakeDB(blocked_numbers=[{"tenant_id": T, "phone_number": "60123456789", "is_active": True}]), "blacklisted"),
    (FakeDB(contacts=[{"id": "c1", "tenant_id": T, "jid": JID, "opted_out_at": _ago(days=1)}]), "opted_out"),
    (FakeDB(contacts=[{"id": "c1", "tenant_id": T, "jid": JID, "do_not_contact": True}]), "do_not_contact"),
    (FakeDB(messages=[_inbound("STOP", minutes=5)]), "said_stop"),
    (FakeDB(contacts=[{"id": "c1", "tenant_id": T, "jid": JID}],
            outreach_consent_log=[{"tenant_id": T, "contact_id": "c1", "consent_type": "opt_out",
                                   "revoked_at": None, "granted_at": _ago(days=1)}]), "opted_out"),
])
def test_suppressed_contacts_blocked_for_both_kinds(db, reason):
    assert g.check_outbound(db, T, JID, g.PROACTIVE) == (False, reason)
    assert g.check_outbound(db, T, JID, g.TRANSACTIONAL) == (False, reason)


def test_daily_cap_and_spacing_are_retryable(monkeypatch):
    db = FakeDB(messages=[_inbound(hours=1)])
    monkeypatch.setenv("OUTBOUND_DAILY_CAP", "1")
    assert g.check_outbound(db, T, JID)[0] is True
    assert g.check_outbound(db, T, JID) == (False, "daily_cap")
    assert "daily_cap" in g.RETRYABLE

    g._tenant_sends.clear()
    monkeypatch.setenv("OUTBOUND_DAILY_CAP", "50")
    monkeypatch.setenv("OUTBOUND_MIN_SPACING_SEC", "3600")
    assert g.check_outbound(db, T, JID)[0] is True
    assert g.check_outbound(db, T, JID) == (False, "spacing")
    # Pacing is per tenant.
    other = FakeDB(messages=[dict(_inbound(hours=1), tenant_id="tenant-2")])
    assert g.check_outbound(other, "tenant-2", JID)[0] is True


def test_ai_paused_blocks_proactive_only():
    """Owner took over the chat: no nudges, but the booking confirmation still goes."""
    db = FakeDB(contacts=[{"id": "c1", "tenant_id": T, "jid": JID, "ai_paused": True}],
                messages=[_inbound(hours=1)])
    assert g.check_outbound(db, T, JID, g.PROACTIVE) == (False, "ai_paused")
    assert g.check_outbound(db, T, JID, g.TRANSACTIONAL) == (True, "transactional")


def test_flag_off_by_default_allows_everything(monkeypatch):
    monkeypatch.delenv("ENABLE_OUTBOUND_SAFETY", raising=False)
    assert g.check_outbound(FakeDB(), T, JID, g.PROACTIVE) == (True, "safety_disabled")


def test_no_supabase_blocks_proactive_only():
    assert g.check_outbound(object(), T, JID, g.PROACTIVE)[0] is False
    assert g.check_outbound(object(), T, JID, g.TRANSACTIONAL)[0] is True


def test_lookup_errors_do_not_crash_and_proactive_fails_closed():
    class Broken:
        def table(self, name):
            raise RuntimeError("relation does not exist")
    assert g.check_outbound(Broken(), T, JID, g.PROACTIVE) == (False, "no_24h_window_or_consent")
    assert g.check_outbound(Broken(), T, JID, g.TRANSACTIONAL) == (True, "transactional")


def test_gateway_forwards_thinking_only_when_set(monkeypatch):
    """ai://fast disables MiniMax-M3 thinking via a per-entry YAML field."""
    from src.core import llm_gateway_v2 as gw
    sent = []

    class _Resp:
        status_code = 200
        text = ""
        def json(self):
            return {"choices": [{"message": {"content": "ok"}}], "usage": {}}

    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json=None, headers=None):
            sent.append(json)
            return _Resp()

    monkeypatch.setattr(gw.httpx, "Client", _Client)
    gw._call_openai_compatible("https://x/v1", "k", "MiniMax-M3", [], {"thinking": {"type": "disabled"}})
    gw._call_openai_compatible("https://x/v1", "k", "MiniMax-M3", [], {})
    assert sent[0]["thinking"] == {"type": "disabled"}
    assert "thinking" not in sent[1]
    fast = gw.llm._config["aliases"]["ai://fast"]["primary"]
    assert fast.get("thinking") == {"type": "disabled"}
    assert "thinking" not in gw.llm._config["aliases"]["ai://reasoning"]["primary"]


async def test_lead_followup_to_cold_contact_is_cancelled_not_sent():
    """Wiring: proactive_messaging must route follow-ups through the guard."""
    from src.core.proactive_messaging import ProactiveMessagingSystem
    sent = []
    channel = SimpleNamespace(send_text=lambda to, text: sent.append(to) or True)
    db = FakeDB(follow_ups=[{"id": "f1", "tenant_id": T, "chat_jid": JID, "status": "pending"}])
    assert await ProactiveMessagingSystem(db, channel)._process_lead_followups() == 0
    assert sent == []
    assert db.updates == [{"status": "cancelled", "notes": "outbound_guard: no_24h_window_or_consent"}]


async def test_lead_followup_pacing_skips_only_that_tenant(monkeypatch):
    """A cap hit for tenant A must not starve tenant B's follow-ups in the same tick."""
    from src.core.proactive_messaging import ProactiveMessagingSystem
    monkeypatch.setenv("OUTBOUND_DAILY_CAP", "1")
    a2, b1 = "60111111111@s.whatsapp.net", "60122222222@s.whatsapp.net"
    sent = []
    channel = SimpleNamespace(send_text=lambda to, text: sent.append(to) or True)
    db = FakeDB(
        follow_ups=[{"id": "f1", "tenant_id": T, "chat_jid": JID, "status": "pending"},
                    {"id": "f2", "tenant_id": T, "chat_jid": a2, "status": "pending"},
                    {"id": "f3", "tenant_id": "tenant-2", "chat_jid": b1, "status": "pending"}],
        messages=[_inbound(hours=1), dict(_inbound(hours=1), chat_jid=a2),
                  dict(_inbound(hours=1), tenant_id="tenant-2", chat_jid=b1)],
    )
    assert await ProactiveMessagingSystem(db, channel)._process_lead_followups() == 2
    assert sent == [JID, b1]
    assert not any(u.get("status") == "cancelled" for u in db.updates)  # f2 stays pending


def _scheduler(db, sent):
    from src.core.outreach_scheduler import OutreachScheduler
    s = OutreachScheduler(db, None)

    async def _true(*a, **k): return True
    async def _false(*a, **k): return False
    async def _none(*a, **k): return None
    async def _send(recipient, content):
        sent.append(recipient)
        return True
    s._check_daily_limit = _true
    s._is_business_hours = lambda *a: True
    s._is_contact_blocked = _false
    s._wait_for_delay = _none
    s._update_contact_outreach = _none
    s._increment_daily_count = _none
    s._send_via_bridge = _send
    return s


_QMSG = {"id": "q1", "tenant_id": T, "recipient_jid": JID, "message_content": "hi",
         "campaigns": {"stop_on_reply": False}}


async def test_outreach_scheduler_holds_no_consent_recoverably():
    sent, db = [], FakeDB()
    await _scheduler(db, sent)._send_message_safely(dict(_QMSG))
    assert sent == []
    assert db.updates == [{"status": "blocked", "error_code": "held_no_consent",
                           "error_message": "no_24h_window_or_consent"}]


async def test_outreach_scheduler_blocks_suppressed_contact():
    sent = []
    db = FakeDB(contacts=[{"id": "c1", "tenant_id": T, "jid": JID, "do_not_contact": True}])
    await _scheduler(db, sent)._send_message_safely(dict(_QMSG))
    assert sent == []
    assert db.updates == [{"status": "blocked", "error_message": "do_not_contact"}]


async def test_outreach_scheduler_leaves_retryable_pending(monkeypatch):
    monkeypatch.setenv("OUTBOUND_DAILY_CAP", "0")
    sent, db = [], FakeDB(messages=[_inbound(hours=1)])
    await _scheduler(db, sent)._send_message_safely(dict(_QMSG))
    assert sent == [] and db.updates == []


async def test_outreach_scheduler_sends_when_allowed():
    sent, db = [], FakeDB(messages=[_inbound(hours=1)])
    await _scheduler(db, sent)._send_message_safely(dict(_QMSG))
    assert sent == [JID]
    assert [u["status"] for u in db.updates] == ["sending", "sent"]


def _reminders(db, sent):
    from src.core.advanced_reminder_system import AdvancedReminderSystem
    r = AdvancedReminderSystem.__new__(AdvancedReminderSystem)
    r.bijou = SimpleNamespace(db_conn=db, db_type="supabase")

    async def _send(recipient, **k):
        sent.append(recipient)
        return True
    r._send_template_message = _send
    return r


def _reminder(reminder_type):
    import json
    return {"id": "r1", "tenant_id": T, "recipient": JID,
            "content": json.dumps({"reminder_type": reminder_type})}


async def test_reminder_transactional_sent_even_to_cold_paused_contact():
    sent = []
    db = FakeDB(contacts=[{"id": "c1", "tenant_id": T, "jid": JID, "ai_paused": True}])
    assert await _reminders(db, sent)._process_single_reminder(_reminder("consultation_reminder")) is True
    assert sent == [JID]


async def test_reminder_blocked_contact_cancelled():
    sent, db = [], FakeDB(messages=[_inbound("stop", minutes=5)])
    assert await _reminders(db, sent)._process_single_reminder(_reminder("consultation_reminder")) is False
    assert sent == [] and db.updates == [{"status": "cancelled"}]


async def test_reminder_proactive_retryable_stays_pending(monkeypatch):
    monkeypatch.setenv("OUTBOUND_DAILY_CAP", "0")
    sent, db = [], FakeDB(messages=[_inbound(hours=1)])
    assert await _reminders(db, sent)._process_single_reminder(_reminder("post_appointment")) is False
    assert sent == [] and db.updates == []


@pytest.mark.parametrize("flag,expected", [(None, None), ("true", {"thinking": {"type": "disabled"}})])
async def test_bijou_minimax_extra_body_follows_fast_reply_flag(monkeypatch, flag, expected):
    """Direct MiniMax path: thinking stays ON (extra_body=None) unless ENABLE_FAST_REPLY."""
    from src.core.bijou import BijouAI
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setenv("MINIMAX_MODELS", "MiniMax-M3")
    monkeypatch.delenv("AGENT_TENANT_ALLOWLIST", raising=False)
    for f in ("ENABLE_AGENT_LOOP", "ENABLE_AGENT_MEMORY", "ENABLE_FAST_REPLY"):
        monkeypatch.delenv(f, raising=False)
    if flag:
        monkeypatch.setenv("ENABLE_FAST_REPLY", flag)
    calls = []

    class _FC:
        enabled = True
        async def call_with_openai_tools(self, **kw):
            calls.append(kw)
            return "hello"

    b = BijouAI.__new__(BijouAI)
    b.knowledge_uploader = SimpleNamespace(get_combined_knowledge=lambda t: "")
    b.function_caller, b.db_conn, b.db_type = _FC(), None, "sqlite"
    assert await b._generate_response("hi", None, client_config={"tenant_id": T}) == "hello"
    assert len(calls) == 1 and "extra_body" in calls[0]
    assert calls[0]["extra_body"] == expected


async def test_generate_response_without_knowledge_uploader(monkeypatch):
    """tenant_id was only bound inside `if self.knowledge_uploader:`, so a failed
    uploader init made every reply raise UnboundLocalError (2026-09-26)."""
    from src.core.bijou import BijouAI
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setenv("MINIMAX_MODELS", "MiniMax-M3")
    for f in ("ENABLE_AGENT_LOOP", "ENABLE_AGENT_MEMORY", "ENABLE_FAST_REPLY"):
        monkeypatch.delenv(f, raising=False)

    class _FC:
        enabled = True
        async def call_with_openai_tools(self, **kw):
            return "hello"

    b = BijouAI.__new__(BijouAI)
    b.knowledge_uploader = None
    b.function_caller, b.db_conn, b.db_type = _FC(), None, "sqlite"
    assert await b._generate_response("hi", None, client_config={"tenant_id": T}) == "hello"
