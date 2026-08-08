"""Unit tests for MemoryStore — the isolation filter is the point."""
from unittest.mock import MagicMock

from src.core.agent_memory import MemoryStore


def _read_chain(return_data):
    """Supabase-style chainable mock for reads; records applied .eq() filters."""
    m = MagicMock()
    m._eqs = {}

    def eq(col, val):
        m._eqs[col] = val
        return m

    for meth in ("table", "select", "limit", "order"):
        getattr(m, meth).return_value = m
    m.eq.side_effect = eq
    m.execute.return_value = MagicMock(data=return_data)
    return m


def test_get_applies_tenant_and_chat_filters():
    db = _read_chain([{"key_facts": {"name": "Ali"}, "summary": "regular"}])
    out = MemoryStore(db).get("tenant-A", "60123@s.whatsapp.net")
    assert db._eqs["tenant_id"] == "tenant-A"  # isolation filter present
    assert db._eqs["chat_jid"] == "60123@s.whatsapp.net"
    assert out == {"facts": {"name": "Ali"}, "summary": "regular"}


def test_get_returns_empty_when_no_row():
    db = _read_chain([])
    assert MemoryStore(db).get("tenant-A", "x") == {"facts": {}, "summary": ""}


def test_update_upserts_with_tenant_id_in_payload():
    db = MagicMock()
    for meth in ("table", "upsert"):
        getattr(db, meth).return_value = db
    db.execute.return_value = MagicMock(data=[{}])
    MemoryStore(db).update("tenant-A", "60123@s.whatsapp.net", {"name": "Ali"}, "regular customer")
    payload = db.upsert.call_args.args[0]
    assert payload["tenant_id"] == "tenant-A"
    assert payload["chat_jid"] == "60123@s.whatsapp.net"
    assert payload["key_facts"] == {"name": "Ali"}
    assert payload["summary"] == "regular customer"
    assert db.upsert.call_args.kwargs.get("on_conflict") == "tenant_id,chat_jid"
