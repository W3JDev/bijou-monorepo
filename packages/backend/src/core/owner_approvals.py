"""Per-tenant owner identity + WhatsApp approval queue (ENABLE_OWNER_APPROVALS).

When ActionGuard says 'confirm' for a consequential tool, the action is stored
in public.pending_actions and the tenant's owner gets a short WhatsApp summary
("Reply 1 to approve, 2 to reject"). The owner's reply executes or cancels it,
the customer is told, and unanswered requests auto-reject at expires_at.
Every decision (auto/approved/rejected/expired) is logged to message_reasons.

Approval requests go ONLY to the tenant's own tenants.owner_phones - never to
the global OWNER_WHATSAPP_JID (that would send one tenant's customer data to
another person). No owner phones -> request_approval returns None and the caller
keeps its old 'blocked' result. The env fallback applies to plain owner
detection only (resolve_owner_phones), as it did before this feature.

Degrades gracefully before migrations-py/add_owner_approvals.sql is applied:
a missing owner_phones column / pending_actions table makes request_approval
return None. Nothing here raises into the reply path.

Tenant-scoped: every pending_actions read/write filters tenant_id (the
service-role key bypasses RLS, so this is the only isolation guard).
"""
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

APPROVE_WORDS = frozenset({"1", "approve", "approved", "yes", "lulus"})
REJECT_WORDS = frozenset({"2", "reject", "rejected", "no", "tolak"})
MAX_PENDING_PER_CHAT = 3
_OWNER_TTL_SECONDS = 60
_owner_cache = {}  # tenant_id -> (monotonic fetched_at, [digits])


def _digits(jid) -> str:
    """'+60 12-345@s.whatsapp.net' / '6012345:3@s.whatsapp.net' -> '6012345'."""
    return "".join(c for c in str(jid or "").split("@")[0].split(":")[0] if c.isdigit())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def short_id(row: dict) -> str:
    return str(row.get("id", "")).replace("-", "")[:4]


# ── Owner identity ──────────────────────────────────────────────────────────


def tenant_owner_phones(db, tenant_id) -> list:
    """This tenant's own tenants.owner_phones (digits). No global fallback - this is
    who may receive and answer approval requests. Cached per tenant for 60s because
    owner detection reads it on every inbound message (a sync Supabase call)."""
    if db is None or not tenant_id:
        return []
    hit = _owner_cache.get(tenant_id)
    if hit and time.monotonic() - hit[0] < _OWNER_TTL_SECONDS:
        return hit[1]
    phones = []
    try:
        r = db.table("tenants").select("owner_phones").eq("id", tenant_id).limit(1).execute()
        phones = (r.data[0].get("owner_phones") if r.data else None) or []
    except Exception as e:  # column not migrated yet
        logger.debug(f"owner_phones lookup skipped: {e}")
    phones = [d for d in (_digits(p) for p in phones) if d]
    _owner_cache[tenant_id] = (time.monotonic(), phones)
    return phones


def resolve_owner_phones(db, tenant_id) -> list:
    """Owner DETECTION only: the tenant's owner_phones, else the global
    OWNER_WHATSAPP_JID (the pre-existing behaviour). Never route approvals by this."""
    phones = tenant_owner_phones(db, tenant_id)
    if not phones:
        g = _digits(os.getenv("OWNER_WHATSAPP_JID", ""))
        phones = [g] if g else []
    return phones


# ── Reply parsing ───────────────────────────────────────────────────────────


def parse_decision(text):
    """'1' / 'approve ab12' / '2 #ab12' -> ('approved'|'rejected', short_id|None); else None.

    Only the bare digits '1'/'2' work without an id: a casual "yes" / "no" in an
    owner's DM must not hijack a pending action. The id must look like a real
    short id (4 hex chars), so "1 more" isn't a reply either."""
    tokens = (text or "").strip().lower().split()
    if not tokens or len(tokens) > 2:
        return None
    if tokens[0] in APPROVE_WORDS:
        decision = "approved"
    elif tokens[0] in REJECT_WORDS:
        decision = "rejected"
    else:
        return None
    sid = tokens[1].lstrip("#") if len(tokens) == 2 else None
    if sid is None and tokens[0] not in ("1", "2"):
        return None
    if sid is not None and not re.fullmatch(r"[0-9a-f]{4}", sid):
        return None
    return decision, sid


def pick_pending(pending: list, sid):
    """The row the owner means, or None if ambiguous / not found."""
    if sid:
        matches = [r for r in pending if short_id(r) == sid]
        return matches[0] if len(matches) == 1 else None
    return pending[0] if len(pending) == 1 else None


# ── Persistence ─────────────────────────────────────────────────────────────


class ApprovalQueue:
    def __init__(self, db):
        self.db = db

    def create(self, tenant_id, chat_jid, tool, args, ttl_minutes=None) -> dict:
        ttl = ttl_minutes or int(os.getenv("OWNER_APPROVAL_TTL_MINUTES", "60"))
        row = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "chat_jid": chat_jid,
            "tool": tool,
            "args": args or {},
            "status": "pending",
            "expires_at": (_now() + timedelta(minutes=ttl)).isoformat(),
        }
        r = self.db.table("pending_actions").insert(row).execute()
        return (r.data or [row])[0]

    def list_pending(self, tenant_id, chat_jid=None) -> list:
        q = (
            self.db.table("pending_actions")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("status", "pending")
            .gt("expires_at", _now().isoformat())
        )
        if chat_jid:
            q = q.eq("chat_jid", chat_jid)
        return q.order("created_at").execute().data or []

    def due(self, tenant_id=None) -> list:
        q = (
            self.db.table("pending_actions")
            .select("*")
            .eq("status", "pending")
            .lte("expires_at", _now().isoformat())
        )
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)
        return q.execute().data or []

    def decide(self, tenant_id, action_id, status, decided_by) -> bool:
        """Compare-and-set pending -> status. False if someone already decided it
        (so a double reply / sweeper race can never execute an action twice)."""
        r = (
            self.db.table("pending_actions")
            .update({"status": status, "decided_by": decided_by, "decided_at": _now().isoformat()})
            .eq("id", action_id)
            .eq("tenant_id", tenant_id)
            .eq("status", "pending")
            .execute()
        )
        return bool(r.data)


def log_decision(db, tenant_id, chat_jid, tool, args, decision, reason, action_id=None):
    """Best-effort audit row in message_reasons (EU AI Act Art. 13 trace).
    Plain insert: the baseline has no UNIQUE(tenant_id, message_id) for an upsert
    to target, and every decision row has a fresh message_id anyway."""
    try:
        db.table("message_reasons").insert(
            {
                "tenant_id": tenant_id,
                "message_id": f"approval-{action_id or uuid.uuid4()}-{decision}",
                "chat_jid": chat_jid or "",
                "channel": "whatsapp",
                "retrieved_docs": [],
                "tool_calls": [{"name": tool, "args": args or {}}],
                "model": None,
                "confidence": None,
                "alternatives": [],
                "metadata": {
                    "approval_decision": decision,
                    "reason": reason,
                    "pending_action_id": action_id,
                },
            },
        ).execute()
    except Exception as e:
        logger.debug(f"approval decision log skipped: {e}")


# ── State machine ───────────────────────────────────────────────────────────
# notify(tenant_id, jid, text) is the caller's WhatsApp sender (Bijou.send_message).

CUSTOMER_APPROVED = "Good news - the team has approved your request and it's done. ✅"
CUSTOMER_FAILED = "Your request was approved, but we hit a snag completing it. The team will follow up with you shortly."
CUSTOMER_REJECTED = "Sorry, the team couldn't approve that request. They'll follow up with you directly."
CUSTOMER_EXPIRED = "Sorry for the wait - the team couldn't confirm your request in time. They'll follow up with you directly."


def _summary(row) -> str:
    args = json.dumps(row.get("args") or {}, ensure_ascii=False, default=str)
    if len(args) > 200:
        args = args[:200] + "..."
    sid = short_id(row)
    return (
        f"🛎️ Approval needed #{sid}\n"
        f"Customer: +{_digits(row.get('chat_jid'))}\n"
        f"Wants: {row.get('tool')} {args}\n\n"
        f"Reply 1 to approve, 2 to reject (or '1 {sid}' / '2 {sid}' if several are waiting)."
    )


def request_approval(db, tenant_id, chat_jid, tool, args, notify):
    """Queue the action + WhatsApp the tenant's owner(s). Returns the tool result to
    hand the LLM, or None if approvals can't run (tenant has no owner_phones, table
    missing, or this chat already has MAX_PENDING_PER_CHAT waiting). The same
    action already pending for this chat is returned as-is: no new row, no re-notify."""
    phones = tenant_owner_phones(db, tenant_id)
    if not phones:
        return None
    q = ApprovalQueue(db)
    # ponytail: check-then-insert; two identical tool calls in the same instant can
    # both queue. Add a partial unique index WHERE status='pending' if that's seen.
    try:
        waiting = q.list_pending(tenant_id, chat_jid)
        for r in waiting:
            if r.get("tool") == tool and (r.get("args") or {}) == (args or {}):
                return _pending_result(tool, r)
        if len(waiting) >= MAX_PENDING_PER_CHAT:
            logger.info(f"approval cap: {len(waiting)} already pending for {chat_jid} (tenant={tenant_id})")
            return None
        row = q.create(tenant_id, chat_jid, tool, args)
    except Exception as e:
        logger.warning(f"pending_actions insert failed (migration applied?): {e}")
        return None
    text = _summary(row)
    for p in phones:
        notify(tenant_id, f"{p}@s.whatsapp.net", text)
    return _pending_result(tool, row)


def _pending_result(tool, row) -> dict:
    return {
        "status": "pending_owner_approval",
        "approval_id": short_id(row),
        "message": (
            f"'{tool}' has been sent to the business owner for approval. Tell the "
            "customer you've passed it on and will confirm once the owner approves. "
            "Do not say it is done."
        ),
    }


def _ok(result) -> bool:
    return not (
        isinstance(result, dict)
        and (result.get("success") is False or result.get("status") == "error")
    )


async def handle_owner_reply(db, tenant_id, owner_jid, text, execute, notify):
    """Apply an owner's WhatsApp reply. Returns the text to send back to the owner,
    or None if the message isn't an approval reply (caller processes it normally).

    execute: async (row) -> tool result.
    """
    parsed = parse_decision(text)
    if not parsed:
        return None
    decision, sid = parsed
    q = ApprovalQueue(db)
    try:
        expire_due(db, notify, tenant_id)
        pending = q.list_pending(tenant_id)
    except Exception as e:
        logger.debug(f"owner approval lookup skipped: {e}")
        return None
    if not pending:
        return None
    row = pick_pending(pending, sid)
    if row is None:
        lines = "\n".join(f"#{short_id(r)} {r.get('tool')} (+{_digits(r.get('chat_jid'))})" for r in pending)
        return f"{len(pending)} requests waiting - reply '1 <id>' or '2 <id>':\n{lines}"

    owner = _digits(owner_jid)
    try:
        decided = q.decide(tenant_id, row["id"], decision, owner)
    except Exception as e:
        logger.warning(f"pending_actions decide failed: {e}")
        return f"Couldn't record your reply for #{short_id(row)} - please try again."
    if not decided:
        return f"#{short_id(row)} was already handled."

    tool, args, chat = row.get("tool"), row.get("args") or {}, row.get("chat_jid")
    if decision == "rejected":
        log_decision(db, tenant_id, chat, tool, args, "rejected", f"owner +{owner} rejected", row["id"])
        notify(tenant_id, chat, CUSTOMER_REJECTED)
        return f"❌ Rejected #{short_id(row)} ({tool}). Customer informed."

    try:
        result = await execute(row)
        ok, err = _ok(result), (result.get("error") if isinstance(result, dict) else None)
    except Exception as e:
        ok, err = False, str(e)
    reason = f"owner +{owner} approved" + ("" if ok else f"; execution failed: {err}")
    log_decision(db, tenant_id, chat, tool, args, "approved", reason, row["id"])
    notify(tenant_id, chat, CUSTOMER_APPROVED if ok else CUSTOMER_FAILED)
    if ok:
        return f"✅ Approved #{short_id(row)} ({tool}) - done, customer informed."
    return f"⚠️ Approved #{short_id(row)} ({tool}) but it failed: {str(err)[:120]}. Customer told the team will follow up."


def expire_due(db, notify, tenant_id=None) -> int:
    """Auto-reject every pending action past expires_at. Returns how many flipped."""
    q = ApprovalQueue(db)
    n = 0
    for r in q.due(tenant_id):
        if q.decide(r["tenant_id"], r["id"], "expired", "system"):
            n += 1
            log_decision(db, r["tenant_id"], r.get("chat_jid"), r.get("tool"), r.get("args"),
                         "expired", "no owner reply before expiry", r["id"])
            notify(r["tenant_id"], r.get("chat_jid"), CUSTOMER_EXPIRED)
    return n
