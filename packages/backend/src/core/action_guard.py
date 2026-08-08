"""Per-tenant action policy for the autonomous agent (Phase 3).

Decides whether the agent may run a tool autonomously. Order of precedence:
  1. explicit per-tenant policy row (tenant_action_policy) — always wins,
  2. otherwise: consequential tools default to 'confirm' (human-in-the-loop),
     everything else defaults to 'allow'.

Tenant-scoped: the policy lookup ALWAYS filters tenant_id (the only isolation
guard, since the service-role key bypasses RLS).
"""

# Consequential tools that must NOT auto-run without an explicit tenant opt-in.
# (Booking, outbound messaging, money, and destructive writes.)
DEFAULT_CONFIRM = frozenset({
    "book_appointment",
    "reschedule_appointment",
    "cancel_appointment",
    "send_email",
    "send_message",
    "send_whatsapp",
    "create_payment",
    "create_payment_link",
    "refund_payment",
    "delete_contact",
    "delete_document",
    "update_settings",
    "escalate_to_human",
})

VALID_MODES = frozenset({"allow", "confirm", "deny"})


class ActionGuard:
    def __init__(self, db):
        self.db = db

    def check(self, tenant_id: str, tool_name: str, args: dict | None = None) -> str:
        """Return 'allow' | 'confirm' | 'deny' for this tenant + tool."""
        resp = (
            self.db.table("tenant_action_policy")
            .select("mode")
            .eq("tenant_id", tenant_id)
            .eq("tool_name", tool_name)
            .limit(1)
            .execute()
        )
        if resp.data:
            mode = resp.data[0].get("mode")
            if mode in VALID_MODES:
                return mode
        return "confirm" if tool_name in DEFAULT_CONFIRM else "allow"
