"""Unit tests for TrajectoryLog — tenant-scoped rows, empty-safe, never raises."""
from unittest.mock import MagicMock

from src.core.trajectory_log import TrajectoryLog


def _insert_db():
    db = MagicMock()
    for meth in ("table", "insert"):
        getattr(db, meth).return_value = db
    db.execute.return_value = MagicMock(data=[{}])
    return db


def test_records_one_row_per_step_with_tenant_id():
    db = _insert_db()
    steps = [
        {"thought": "plan", "tool": "search", "args": {"q": "hours"}, "result": {"ok": True}},
        {"thought": "act", "tool": "book_appointment", "args": {"day": "Mon"}, "result": {"ok": True}},
    ]
    n = TrajectoryLog(db).record("tenant-A", "60123@s.whatsapp.net", steps)
    assert n == 2
    rows = db.insert.call_args.args[0]
    assert [r["step_no"] for r in rows] == [0, 1]
    assert all(r["tenant_id"] == "tenant-A" for r in rows)  # every row tenant-scoped
    assert all(r["chat_jid"] == "60123@s.whatsapp.net" for r in rows)
    assert rows[1]["tool"] == "book_appointment"


def test_empty_steps_writes_nothing():
    db = _insert_db()
    assert TrajectoryLog(db).record("tenant-A", "x", []) == 0
    db.insert.assert_not_called()


def test_logging_failure_does_not_raise():
    db = MagicMock()
    db.table.return_value = db
    db.insert.return_value = db
    db.execute.side_effect = Exception("db down")
    # must swallow the error and return 0, never break the reply path
    assert TrajectoryLog(db).record("tenant-A", "x", [{"tool": "t"}]) == 0
