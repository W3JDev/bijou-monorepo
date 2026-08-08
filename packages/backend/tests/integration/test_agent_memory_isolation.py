"""Phase-1 gate: prove tenant A cannot read tenant B's memory. Real Supabase.

Skips cleanly without creds or before the customer_memory table exists.
Run: ./.venv/Scripts/python.exe -m pytest tests/integration/test_agent_memory_isolation.py \
     -p no:cacheprovider -o addopts="" -s -q   (with backend .env creds exported)
"""
import os
import uuid

import pytest

from src.core.agent_memory import MemoryStore

pytestmark = pytest.mark.integration


def _db():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        pytest.skip("no Supabase creds in env")
    from supabase import create_client

    return create_client(url, key)


def test_tenant_cannot_read_other_tenants_memory():
    db = _db()
    store = MemoryStore(db)
    A = "dae52bc5-8ad7-40fb-81bb-84325b23c6ff"  # MY BIJOU AI
    B = "607690ec-4ff7-4ef4-b98e-bfb00442fe95"  # W3J LLC
    jid = f"test-{uuid.uuid4().hex[:8]}@s.whatsapp.net"
    try:
        try:
            store.update(A, jid, {"secret": "A-only"}, "A summary")
        except Exception as e:  # table not applied yet
            pytest.skip(f"customer_memory table not ready: {e}")
        assert store.get(A, jid)["facts"] == {"secret": "A-only"}
        assert store.get(B, jid) == {"facts": {}, "summary": ""}  # B sees nothing
    finally:
        try:
            db.table("customer_memory").delete().eq("tenant_id", A).eq("chat_jid", jid).execute()
        except Exception:
            pass
