"""
Outbound guard — ONE gate for every AUTOMATED WhatsApp send to a customer.

Production WhatsApp is GOWA, an unofficial linked-device bridge, not the Cloud
API. There are no template approvals protecting us: unsolicited or bursty sends
get the tenant's number banned. So every automated path (lead follow-ups,
campaigns, silence re-engagement, scheduled messages, reminders, booking
confirmations) calls check_outbound() before it sends.

Kinds:
  PROACTIVE      we start the conversation (follow-up, campaign, re-engagement).
                 Allowed only if the customer messaged within 24h OR an active
                 opt_in/transactional row exists in outreach_consent_log. Subject
                 to a per-tenant daily cap and minimum spacing.
  TRANSACTIONAL  something the customer asked for (booking confirmation, a
                 reminder for a booking they made). No window/consent/cap needed.

Both kinds are refused for blacklisted, opted-out, do-not-contact and said-stop
contacts. AI-paused contacts (owner took over the chat) get no PROACTIVE sends,
but still get transactional ones — the customer asked for those. Owner/agent notifications are NOT customer sends and do not
come through here.

Gated by ENABLE_OUTBOUND_SAFETY (default OFF for the first rollout — turn it on
per environment once held counts look sane). Returns (allowed, reason); every
refusal is logged with its reason. Reasons in RETRYABLE (cap/spacing) mean
"not now" — callers leave the message pending instead of cancelling it. Reasons
in HELD (no permission evidence yet) are recoverable — callers park the item so
it can be re-queued once consent exists, rather than cancelling it.

Degrades gracefully: contacts is read with select("*") so a column that has not
been migrated yet (e.g. ai_paused) is simply absent. A PROACTIVE send whose
permission cannot be verified is refused (no evidence of permission = no send);
a failed suppression lookup is skipped, matching bijou.py's fail-open checks.
"""

import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PROACTIVE = "proactive"
TRANSACTIONAL = "transactional"
RETRYABLE = {"daily_cap", "spacing"}
HELD = {"no_24h_window_or_consent", "no_db_to_verify_permission"}

_STOP_RE = re.compile(
    r"^\s*(stop|unsubscribe|berhenti)\b|\b(remove me|don'?t (contact|message) me|"
    r"please don'?t message|jangan (hantar|mesej|contact))\b",
    re.IGNORECASE,
)

# tenant_id -> [utc_date, sends_today, last_send_monotonic]
# ponytail: in-process counter — resets on restart and is per-instance. Move it
# to a table if the backend ever runs more than one instance.
_tenant_sends: Dict[str, List] = {}


def outbound_safety_enabled() -> bool:
    return os.getenv("ENABLE_OUTBOUND_SAFETY", "false").lower() == "true"


def _rows(result) -> list:
    data = getattr(result, "data", None)
    return data if isinstance(data, list) else []


def _block(tenant_id, recipient, kind, reason) -> Tuple[bool, str]:
    logger.info(f"🚫 Outbound blocked tenant={tenant_id} to={recipient} kind={kind} reason={reason}")
    return False, reason


def check_outbound(db, tenant_id: Optional[str], recipient: Optional[str], kind: str = PROACTIVE) -> Tuple[bool, str]:
    """Decide whether an automated send may go out now. Reserves a cap slot on allow."""
    if not outbound_safety_enabled():
        return True, "safety_disabled"
    if not tenant_id or not recipient:
        return _block(tenant_id, recipient, kind, "missing_tenant_or_recipient")
    if not hasattr(db, "table"):
        # No Supabase (SQLite dev mode): nothing to verify permission against.
        if kind == PROACTIVE:
            return _block(tenant_id, recipient, kind, "no_db_to_verify_permission")
        return True, "transactional_no_db"

    jid = recipient if "@" in recipient else f"{recipient}@s.whatsapp.net"
    phone = recipient.split("@")[0]

    # ── Suppression (both kinds) ─────────────────────────────────────────────
    try:
        if _rows(db.table("blocked_numbers").select("id").eq("tenant_id", tenant_id)
                 .eq("phone_number", phone).eq("is_active", True).limit(1).execute()):
            return _block(tenant_id, recipient, kind, "blacklisted")
    except Exception as e:
        logger.warning(f"⚠️ outbound guard blacklist check skipped: {e}")

    contact: Dict = {}
    try:
        found = _rows(db.table("contacts").select("*").eq("tenant_id", tenant_id)
                      .eq("jid", jid).limit(1).execute())
        contact = found[0] if found else {}
    except Exception as e:
        logger.warning(f"⚠️ outbound guard contact lookup skipped: {e}")
    if kind == PROACTIVE and contact.get("ai_paused"):
        return _block(tenant_id, recipient, kind, "ai_paused")
    if contact.get("opted_out_at"):
        return _block(tenant_id, recipient, kind, "opted_out")
    if contact.get("do_not_contact"):
        return _block(tenant_id, recipient, kind, "do_not_contact")

    last_inbound: Dict = {}
    try:
        found = _rows(db.table("messages").select("content, created_at").eq("tenant_id", tenant_id)
                      .eq("chat_jid", jid).eq("role", "user")
                      .order("created_at", desc=True).limit(1).execute())
        last_inbound = found[0] if found else {}
    except Exception as e:
        logger.warning(f"⚠️ outbound guard last-inbound lookup skipped: {e}")
    if _STOP_RE.search(last_inbound.get("content") or ""):
        return _block(tenant_id, recipient, kind, "said_stop")

    consent_type = None
    if contact.get("id"):
        try:
            found = _rows(db.table("outreach_consent_log").select("consent_type")
                          .eq("tenant_id", tenant_id).eq("contact_id", contact["id"])
                          .is_("revoked_at", "null").order("granted_at", desc=True)
                          .limit(1).execute())
            consent_type = found[0].get("consent_type") if found else None
        except Exception as e:
            logger.warning(f"⚠️ outbound guard consent lookup skipped: {e}")
    if consent_type == "opt_out":
        return _block(tenant_id, recipient, kind, "opted_out")

    if kind == TRANSACTIONAL:
        return True, "transactional"

    # ── Permission (proactive only) ──────────────────────────────────────────
    in_window = False
    ts = last_inbound.get("created_at")
    if ts:
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            in_window = datetime.now(timezone.utc) - dt <= timedelta(hours=24)
        except ValueError:
            pass
    if not in_window and consent_type not in ("opt_in", "transactional"):
        return _block(tenant_id, recipient, kind, "no_24h_window_or_consent")

    # ── Pacing (proactive only) ──────────────────────────────────────────────
    today = datetime.now(timezone.utc).date()
    state = _tenant_sends.get(tenant_id)
    if not state or state[0] != today:
        state = _tenant_sends[tenant_id] = [today, 0, None]
    if state[1] >= int(os.getenv("OUTBOUND_DAILY_CAP", "50")):
        return _block(tenant_id, recipient, kind, "daily_cap")
    now = time.monotonic()
    if state[2] is not None and now - state[2] < float(os.getenv("OUTBOUND_MIN_SPACING_SEC", "90")):
        return _block(tenant_id, recipient, kind, "spacing")
    # Reserve on allow: a send that then fails still counts. Conservative on purpose.
    state[1] += 1
    state[2] = now
    return True, "24h_window" if in_window else "consent"
