"""Feature #3 (stop-texting a contact): _is_ai_paused must return True only when
contacts.ai_paused is set for (tenant_id, jid), and must FAIL OPEN (return False)
on any error or missing row so a lookup glitch never silences the agent."""
import asyncio

from src.core.bijou import BijouAI


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a):
        return self

    def eq(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        class _R:
            pass

        r = _R()
        r.data = self._rows
        return r


class _DB:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        return _Query(self._rows)


class _BadDB:
    def table(self, *a):
        raise RuntimeError("db down")


def _bijou():
    return BijouAI.__new__(BijouAI)  # skip __init__


def test_paused_true_when_flag_set():
    assert asyncio.run(_bijou()._is_ai_paused(_DB([{"ai_paused": True}]), "t1", "60123@s.whatsapp.net")) is True


def test_paused_false_when_flag_false():
    assert asyncio.run(_bijou()._is_ai_paused(_DB([{"ai_paused": False}]), "t1", "60123@s.whatsapp.net")) is False


def test_paused_false_when_no_contact_row():
    assert asyncio.run(_bijou()._is_ai_paused(_DB([]), "t1", "x@s.whatsapp.net")) is False


def test_paused_fail_open_on_db_error():
    # A DB failure must NOT silence the agent — fail open.
    assert asyncio.run(_bijou()._is_ai_paused(_BadDB(), "t1", "x@s.whatsapp.net")) is False
