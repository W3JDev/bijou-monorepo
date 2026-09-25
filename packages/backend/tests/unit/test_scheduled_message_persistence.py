"""Regression test for B1: scheduled messages silently failed to persist because
_save_scheduled_message wrote columns that don't exist on the real
scheduled_messages table (recipient/message_type/content/metadata) and omitted
the NOT NULL schedule_name/cron_expression — so every insert failed, was
swallowed, and messages lived in memory only (lost on restart).

This asserts the save payload uses ONLY real columns (incl. the NOT NULLs) and
that a fresh instance can reload the row back into an equivalent ScheduledMessage.
"""
import asyncio
import datetime

from src.core.proactive_messaging import (
    ProactiveMessagingSystem,
    ScheduledMessage,
    MessageType,
    MessageStatus,
)

# Columns that actually exist on public.scheduled_messages (0000_baseline.sql:1771).
REAL_COLUMNS = {
    "id", "tenant_id", "schedule_name", "cron_expression", "timezone",
    "template_id", "recipients", "message_content", "is_active", "next_run_at",
    "last_run_at", "run_count", "created_at", "updated_at", "status",
    "scheduled_time", "sent_at",
}
PHANTOM_COLUMNS = {"recipient", "message_type", "content", "metadata"}


class _Query:
    def __init__(self, store, name):
        self.store = store
        self.name = name
        self._filters = {}

    def upsert(self, data):
        self.store.setdefault(self.name, {})[data["id"]] = data
        return self

    def select(self, *a):
        return self

    def eq(self, c, v):
        self._filters[c] = v
        return self

    def lte(self, c, v):
        return self

    def execute(self):
        rows = list(self.store.get(self.name, {}).values())
        st = self._filters.get("status")
        if st is not None:
            rows = [r for r in rows if r.get("status") == st]

        class _R:
            pass

        r = _R()
        r.data = rows
        return r


class _FakeSupabase:
    def __init__(self):
        self.store = {}

    def table(self, name):
        return _Query(self.store, name)


def _system(db):
    # Bypass __init__ (needs a send callback etc.) — we only exercise persistence.
    s = ProactiveMessagingSystem.__new__(ProactiveMessagingSystem)
    s.db = db
    s.scheduled_messages = {}
    return s


def _msg():
    ts = datetime.datetime(2026, 1, 1, 0, 0, 0)
    return ScheduledMessage(
        id="11111111-1111-1111-1111-111111111111",
        tenant_id="tenant-1",
        recipient="60123456789@s.whatsapp.net",
        message_type=MessageType.REMINDER,
        content="Follow up with Ali",
        scheduled_time=ts,
        status=MessageStatus.SCHEDULED,
        created_at=ts,
        sent_at=None,
        metadata=None,
    )


def test_scheduled_message_persists_with_real_columns_and_reloads():
    db = _FakeSupabase()
    s = _system(db)
    msg = _msg()

    asyncio.run(s._save_scheduled_message(msg))

    saved = list(db.store["scheduled_messages"].values())[0]
    # NOT NULL columns present, no phantom columns, all keys are real.
    assert {"schedule_name", "cron_expression", "recipients", "message_content"} <= set(saved)
    assert saved["cron_expression"] == "@once"
    assert saved["recipients"] == ["60123456789@s.whatsapp.net"]
    assert not (PHANTOM_COLUMNS & set(saved)), f"phantom columns leaked: {PHANTOM_COLUMNS & set(saved)}"
    assert set(saved) <= REAL_COLUMNS, f"unknown columns: {set(saved) - REAL_COLUMNS}"

    # A fresh instance reloads the row into an equivalent object.
    s2 = _system(db)
    asyncio.run(s2._load_scheduled_messages())
    assert msg.id in s2.scheduled_messages
    got = s2.scheduled_messages[msg.id]
    assert got.recipient == "60123456789@s.whatsapp.net"
    assert got.content == "Follow up with Ali"
    assert got.message_type == MessageType.REMINDER
    assert got.status == MessageStatus.SCHEDULED
