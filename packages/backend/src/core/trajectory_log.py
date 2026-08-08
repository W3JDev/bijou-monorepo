"""Agent trajectory logging (Phase 3) — records each step for eval/rollback.

Tenant-scoped: every row carries tenant_id. Best-effort (never raises into the
reply path); logging failures are swallowed so they can't break a customer reply.
"""
import logging

logger = logging.getLogger(__name__)


class TrajectoryLog:
    def __init__(self, db):
        self.db = db

    def record(self, tenant_id: str, chat_jid: str, steps: list) -> int:
        """Insert one row per step. Returns the number of rows written."""
        if not steps:
            return 0
        rows = []
        for i, s in enumerate(steps):
            rows.append({
                "tenant_id": tenant_id,
                "chat_jid": chat_jid,
                "step_no": i,
                "thought": s.get("thought"),
                "tool": s.get("tool"),
                "args": s.get("args"),
                "result": s.get("result"),
            })
        try:
            self.db.table("agent_trajectory").insert(rows).execute()
            return len(rows)
        except Exception as e:  # never break the reply path on a logging failure
            logger.warning(f"trajectory log failed (tenant={tenant_id}): {e}")
            return 0
