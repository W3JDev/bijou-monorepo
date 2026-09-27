#!/usr/bin/env python3
"""
Owner Morning Brief
===================

One WhatsApp message per tenant owner at 09:00 tenant-local time summarising
the last 24h. Driven from ProactiveMessagingSystem's scheduler loop (every 5 min) and
gated by ENABLE_MORNING_BRIEF (+ AGENT_TENANT_ALLOWLIST).

- Numbers come from the DB here; the LLM (ai://fast) only rephrases, and any
  reply that drops a number falls back to the deterministic plain text.
- Idempotent per (tenant, local date) across restarts and uvicorn workers via
  the primary key on public.morning_briefs (migrations-py/add_morning_briefs.sql).
  Claim-then-send = at-most-once: a failed send is NOT retried (ban-safe).
  If the table does not exist yet, the claim fails and nothing is sent.
- Opt-out: tenants.settings.morning_brief = false. Skipped: inactive /
  cancelled / churned tenants and tenants without their own connected device.
- Timezone: tenants.business_hours.timezone, then settings.timezone, else UTC.
"""

import asyncio
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Awaitable, Callable, Dict, Optional
from zoneinfo import ZoneInfo

from src.core.jid_utils import normalize_device_jid

logger = logging.getLogger(__name__)

BRIEF_HOUR = 9
# Send window 09:00-11:59 local, so a restart at 09:05 still sends; after
# noon the day is skipped rather than sending a "morning" brief at night.
BRIEF_WINDOW_HOURS = 3

# tenant_id -> last local date handled in this process (skips the DB claim on
# every tick). Bounded by tenant count. The DB claim is the real guard.
_handled: Dict[str, date] = {}


def tenant_tz(tenant: dict) -> ZoneInfo:
    for src in (tenant.get("business_hours"), tenant.get("settings")):
        name = (src or {}).get("timezone") if isinstance(src, dict) else None
        if name:
            try:
                return ZoneInfo(name)
            except Exception:
                logger.debug(f"Invalid timezone {name!r} for tenant {tenant.get('id')}")
    return ZoneInfo("UTC")


def due_local_date(now_utc: datetime, tz: ZoneInfo) -> Optional[date]:
    """Local date if `now_utc` falls inside the tenant's brief window, else None."""
    local = now_utc.astimezone(tz)
    if BRIEF_HOUR <= local.hour < BRIEF_HOUR + BRIEF_WINDOW_HOURS:
        return local.date()
    return None


def owner_jid(tenant: dict) -> Optional[str]:
    """The tenant's own WA JID (self-chat) — the same destination
    _send_owner_notification uses. Not owner_phone: inbound owner recognition
    only knows the global OWNER_JID, so replies from owner_phone would be
    handled as a customer chat, while self-chat replies are is_from_me and skipped."""
    jid = tenant.get("whatsapp_jid")
    return normalize_device_jid(jid) if jid else None


# tenants.status / subscription_status values that must never get a brief.
_INACTIVE = {"cancelled", "canceled", "churned", "suspended"}


def has_own_device(db, tenant: dict) -> bool:
    """True only if the tenant's WhatsApp is connected AND it has its own
    whatsapp_devices row. Without the row, send_message falls back to the
    default / first bridge device, i.e. another business's number."""
    if not (tenant.get("whatsapp_connected") or tenant.get("session_active")):
        return False
    try:
        rows = (db.table("whatsapp_devices").select("device_id")
                .eq("tenant_id", tenant["id"]).execute().data) or []
    except Exception as e:
        logger.debug(f"Morning brief device lookup failed for {tenant.get('id')}: {e}")
        return False
    return any(r.get("device_id") not in (None, "", "default") for r in rows)


def _count(q) -> Optional[int]:
    try:
        return q.execute().count or 0
    except Exception as e:
        logger.debug(f"Morning brief count skipped: {e}")
        return None


def aggregate(db, tenant_id: str, since: datetime, until: datetime) -> dict:
    """Last-24h numbers for one tenant. A failed query yields None (shown as '-')."""
    s, u = since.isoformat(), until.isoformat()

    def contacts():
        return (db.table("contacts").select("id", count="exact")
                .eq("tenant_id", tenant_id))

    stats = {
        "new_conversations": _count(contacts().gte("first_message_at", s).lt("first_message_at", u)),
        "leads": _count(contacts().gte("first_message_at", s).lt("first_message_at", u)
                        .in_("tag", ["inquiry", "hot_lead"])),
        "hot_leads": _count(contacts().eq("tag", "hot_lead")
                            .gte("last_message_at", s).lt("last_message_at", u)),
        "bookings": _count(db.table("call_bookings").select("id", count="exact")
                           .eq("tenant_id", tenant_id).gte("created_at", s).lt("created_at", u)),
        "ai_messages": _count(db.table("messages").select("id", count="exact")
                              .eq("tenant_id", tenant_id).eq("role", "assistant")
                              .gte("created_at", s).lt("created_at", u)),
        "escalations": None,
        "unanswered": None,
        "knowledge_gaps": None,
    }
    try:
        rows = (db.table("escalations").select("status,reason_type")
                .eq("tenant_id", tenant_id).gte("created_at", s).lt("created_at", u)
                .execute().data) or []
        stats["escalations"] = len(rows)
        stats["unanswered"] = sum(1 for r in rows if r.get("status") == "pending")
        stats["knowledge_gaps"] = sum(1 for r in rows if r.get("reason_type") == "knowledge_gap")
    except Exception as e:
        logger.debug(f"Morning brief escalations skipped: {e}")
    return stats


def suggest_action(stats: dict) -> str:
    n = lambda k: stats.get(k) or 0  # noqa: E731
    if n("unanswered"):
        return f"Reply to the {n('unanswered')} customer(s) still waiting for you."
    if n("knowledge_gaps"):
        return "Add the missing answers to your knowledge base so Bijou can handle them next time."
    if n("hot_leads"):
        return f"Follow up with your {n('hot_leads')} hot lead(s) today."
    if n("bookings"):
        return "Confirm your new bookings with the customers."
    if stats.get("new_conversations") == 0:
        return "Share your WhatsApp link on social media to bring in new chats."
    return "Skim yesterday's chats in your dashboard for anything worth a personal touch."


def fallback_text(business: str, stats: dict, action: str) -> str:
    v = lambda k: "-" if stats.get(k) is None else str(stats[k])  # noqa: E731
    return (
        f"Good morning! Your Bijou brief for {business} (last 24h):\n"
        f"- New conversations: {v('new_conversations')}\n"
        f"- Leads: {v('leads')} (hot: {v('hot_leads')})\n"
        f"- Bookings: {v('bookings')}\n"
        f"- Escalations: {v('escalations')} (unanswered: {v('unanswered')}, "
        f"knowledge gaps: {v('knowledge_gaps')})\n"
        f"- Messages handled by AI: {v('ai_messages')}\n"
        f"Suggested action: {action}"
    )


async def phrase(business: str, stats: dict, action: str, tenant_id: str) -> str:
    """LLM rewording of the plain text; falls back if it fails or drops a number."""
    plain = fallback_text(business, stats, action)
    try:
        from src.core.llm_gateway_v2 import llm

        result = await asyncio.wait_for(llm.complete(
            "ai://fast",
            [{"role": "user", "content": (
                "Rewrite this morning brief as one short, warm WhatsApp message to a busy "
                "small-business owner. Plain text, no markdown, under 90 words. Keep every "
                "number exactly as given and keep the suggested action. Do not add facts.\n\n"
                + plain)}],
            tenant_id=tenant_id,
        ), timeout=30)
        text = (result.text or "").strip()
        numbers = {str(x) for x in stats.values() if isinstance(x, int) and x > 0}
        if text and all(re.search(rf"\b{n}\b", text) for n in numbers):
            return text
        logger.info(f"Morning brief LLM text rejected for tenant {tenant_id}; using plain text")
    except Exception as e:
        logger.info(f"Morning brief LLM phrasing unavailable ({type(e).__name__}); using plain text")
    return plain


def claim(db, tenant_id: str, brief_date: date) -> bool:
    """Atomically claim (tenant, date). False if already claimed OR the table is
    missing / DB errors — in every non-True case nothing is sent."""
    try:
        db.table("morning_briefs").insert({
            "tenant_id": tenant_id,
            "brief_date": brief_date.isoformat(),
        }).execute()
        return True
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "23505" in msg:
            logger.debug(f"Morning brief already claimed: {tenant_id} {brief_date}")
        else:
            logger.warning(f"⚠️ Morning brief claim failed (migration applied?): {e}")
        return False


def _prepare(db, t: dict, now: datetime) -> Optional[tuple]:
    """Sync per-tenant DB work (run in a thread). Returns (jid, brief_date, stats)
    if a brief should be sent now, else None."""
    tid = t.get("id")
    settings = t.get("settings") if isinstance(t.get("settings"), dict) else {}
    if not tid or t.get("is_active") is False:
        return None
    if t.get("status") in _INACTIVE or t.get("subscription_status") in _INACTIVE:
        return None
    if settings.get("morning_brief") is False:
        return None  # per-tenant opt-out
    brief_date = due_local_date(now, tenant_tz(t))
    if brief_date is None or _handled.get(tid) == brief_date:
        return None
    _handled[tid] = brief_date
    jid = owner_jid(t)
    if not jid:
        logger.info(f"Morning brief skipped for {tid}: no owner destination")
        return None
    if not has_own_device(db, t):
        logger.info(f"Morning brief skipped for {tid}: no connected WhatsApp device of its own")
        return None
    if not claim(db, tid, brief_date):
        return None
    return jid, brief_date, aggregate(db, tid, now - timedelta(hours=24), now)


def _record(db, tid: str, brief_date: date, stats: dict, ok: bool) -> None:
    try:
        db.table("morning_briefs").update({
            "status": "sent" if ok else "failed",
            "stats": stats,
            "sent_at": datetime.now(timezone.utc).isoformat() if ok else None,
        }).eq("tenant_id", tid).eq("brief_date", brief_date.isoformat()).execute()
    except Exception as e:
        logger.debug(f"Morning brief status update skipped: {e}")


async def run_due_briefs(
    db,
    send: Callable[[str, str, str], Awaitable[bool]],
    enabled: Callable[[str], bool],
    now: Optional[datetime] = None,
) -> int:
    """Send every brief that is due right now. Returns number sent."""
    now = now or datetime.now(timezone.utc)
    try:
        tenants = await asyncio.to_thread(lambda: (db.table("tenants").select(
            "id,name,business_name,whatsapp_jid,whatsapp_connected,session_active,"
            "settings,business_hours,is_active,status,subscription_status"
        ).execute().data) or [])  # noaudit - system scheduler: all tenants, isolated per id below
    except Exception as e:
        logger.warning(f"⚠️ Morning brief tenant load failed: {e}")
        return 0

    sent = 0
    for t in tenants:
        tid = t.get("id") if isinstance(t, dict) else None
        try:
            if not tid or not enabled(tid):
                continue
            prepared = await asyncio.to_thread(_prepare, db, t, now)
            if not prepared:
                continue
            jid, brief_date, stats = prepared
            business = t.get("business_name") or t.get("name") or "your business"
            text = await phrase(business, stats, suggest_action(stats), tid)
            ok = False
            try:
                ok = bool(await send(jid, text, tid))
            except Exception as e:
                logger.error(f"❌ Morning brief send error for {tid}: {e}")
            await asyncio.to_thread(_record, db, tid, brief_date, stats, ok)
            if ok:
                sent += 1
                logger.info(f"☀️ Morning brief sent for tenant {tid} ({brief_date})")
        except Exception as e:
            # One malformed tenant must not starve the rest.
            logger.error(f"❌ Morning brief failed for tenant {tid}: {e}")
    return sent
