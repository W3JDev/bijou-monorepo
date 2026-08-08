"""Unit tests for ActionGuard — defaults + explicit policy + tenant isolation."""
from unittest.mock import MagicMock

from src.core.action_guard import ActionGuard


def _policy_chain(return_data):
    m = MagicMock()
    m._eqs = {}

    def eq(col, val):
        m._eqs[col] = val
        return m

    for meth in ("table", "select", "limit"):
        getattr(m, meth).return_value = m
    m.eq.side_effect = eq
    m.execute.return_value = MagicMock(data=return_data)
    return m


def test_consequential_tool_defaults_to_confirm():
    db = _policy_chain([])  # no explicit policy
    assert ActionGuard(db).check("tenant-A", "book_appointment") == "confirm"


def test_safe_tool_defaults_to_allow():
    db = _policy_chain([])
    assert ActionGuard(db).check("tenant-A", "search_knowledge") == "allow"


def test_explicit_policy_overrides_default():
    db = _policy_chain([{"mode": "allow"}])  # tenant opted book_appointment into auto
    assert ActionGuard(db).check("tenant-A", "book_appointment") == "allow"


def test_explicit_deny_is_respected():
    db = _policy_chain([{"mode": "deny"}])
    assert ActionGuard(db).check("tenant-A", "search_knowledge") == "deny"


def test_lookup_is_tenant_scoped():
    db = _policy_chain([])
    ActionGuard(db).check("tenant-A", "book_appointment")
    assert db._eqs["tenant_id"] == "tenant-A"  # isolation filter applied
    assert db._eqs["tool_name"] == "book_appointment"


def test_invalid_policy_mode_falls_back_to_default():
    db = _policy_chain([{"mode": "garbage"}])
    assert ActionGuard(db).check("tenant-A", "book_appointment") == "confirm"
