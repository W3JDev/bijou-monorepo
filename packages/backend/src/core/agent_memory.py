"""Per-tenant durable customer memory for the Bijou autonomous agent.

EVERY query is tenant_id-scoped. The Supabase service-role key bypasses RLS,
so this application-level filter is the ONLY isolation guard — it must never
be omitted. See docs/superpowers/specs/2026-07-20-bijou-autonomous-agent-v1-design.md
"""
from datetime import datetime, timezone


class MemoryStore:
    """Reads/writes the tenant-scoped `customer_memory` table.

    Injected with a Supabase (service-role) client so it can be unit-tested
    with a mock and reused in the app via get_supabase().
    """

    def __init__(self, db):
        self.db = db

    def get(self, tenant_id: str, chat_jid: str) -> dict:
        """Return {"facts": dict, "summary": str} for one customer, or empties."""
        resp = (
            self.db.table("customer_memory")
            .select("key_facts, summary")
            .eq("tenant_id", tenant_id)
            .eq("chat_jid", chat_jid)
            .limit(1)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            return {"facts": row.get("key_facts") or {}, "summary": row.get("summary") or ""}
        return {"facts": {}, "summary": ""}

    def update(self, tenant_id: str, chat_jid: str, facts: dict, summary: str) -> None:
        """Upsert one customer's memory, always carrying tenant_id in the payload."""
        self.db.table("customer_memory").upsert(
            {
                "tenant_id": tenant_id,
                "chat_jid": chat_jid,
                "key_facts": facts,
                "summary": summary,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="tenant_id,chat_jid",
        ).execute()
