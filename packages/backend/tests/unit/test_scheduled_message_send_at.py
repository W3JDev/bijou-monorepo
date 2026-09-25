"""Feature #4 (scheduled messages): schedule_message accepts an absolute ISO-8601
`send_at` that OVERRIDES delay_minutes and is normalised to naive UTC (so it
compares cleanly against datetime.utcnow() in the scheduler loop). delay_minutes
still works when send_at is omitted."""
import asyncio
import datetime

from src.core.proactive_messaging import (
    ProactiveMessagingSystem,
    MessageType,
    MessageStatus,
)


class _NoopQuery:
    def upsert(self, *a):
        return self

    def execute(self):
        class _R:
            pass

        r = _R()
        r.data = []
        return r


class _NoopDB:
    def table(self, *a):
        return _NoopQuery()


def _system():
    s = ProactiveMessagingSystem.__new__(ProactiveMessagingSystem)
    s.db = _NoopDB()
    s.scheduled_messages = {}
    return s


def test_send_at_absolute_overrides_delay_and_is_naive_utc():
    s = _system()
    msg = asyncio.run(
        s.schedule_message(
            tenant_id="t1",
            recipient="60123456789@s.whatsapp.net",
            message_type=MessageType.REMINDER,
            content="Viewing tomorrow 3pm",
            delay_minutes=99999,  # must be ignored
            send_at="2027-03-04T15:00:00+08:00",  # 15:00 +08:00 == 07:00 UTC
        )
    )
    assert msg.scheduled_time == datetime.datetime(2027, 3, 4, 7, 0, 0)
    assert msg.scheduled_time.tzinfo is None
    assert msg.status == MessageStatus.SCHEDULED


def test_delay_minutes_still_works_without_send_at():
    s = _system()
    msg = asyncio.run(
        s.schedule_message(
            tenant_id="t1",
            recipient="x@s.whatsapp.net",
            message_type=MessageType.CUSTOM,
            content="hi",
            delay_minutes=10,
        )
    )
    delta = (msg.scheduled_time - datetime.datetime.utcnow()).total_seconds()
    assert 540 < delta < 660  # ~600s (10 min), generous bounds for timing
