"""
src/core/ticket_manager.py
==========================
Help Ticket System — tracks every message posted to the
"Bijou Help Tickets" WhatsApp group as a numbered ticket.

Features:
  - Auto-numbers tickets: TKT-0001, TKT-0002 …  (per-tenant)
  - Stores ticket in help_tickets table (Supabase)
  - Detects urgent keywords → escalates immediately
  - Owner can: close, escalate, add note via group message
  - Notifies BIJOU_OWNER_WA on escalation

Author: W3J Consulting
Date: 2026-03-06
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword banks
# ---------------------------------------------------------------------------
URGENT_KEYWORDS: list[str] = [
    "urgent", "emergency", "cannot login", "can't login", "data loss",
    "api down", "service down", "payment fail", "billing issue",
    "need help now", "stuck", "broken", "not working", "still not fixed",
    "tolong", "tak boleh", "rosak", "masalah besar",
]

TICKET_COMMANDS: dict[str, str] = {
    "@bijou close": "closed",
    "@bijou done": "closed",
    "@bijou escalate": "escalated",
    "@bijou urgent": "escalated",
    "@bijou resolved": "closed",
}


# ---------------------------------------------------------------------------
# TicketManager
# ---------------------------------------------------------------------------

class TicketManager:
    """
    Manages help-desk tickets in the Bijou Help Tickets WA group.

    Usage (in bijou.py):
        tm = TicketManager(supabase_client)
        ticket = await tm.handle_group_message(
            tenant_id, chat_jid, sender_jid, sender_name, message_text
        )
    """

    def __init__(self, supabase_client) -> None:
        self.db = supabase_client
        self.owner_wa: str = os.getenv("BIJOU_OWNER_WA", "").strip()
        self.bridge_url: str = os.getenv("BRIDGE_URL", "").rstrip("/")
        self.bridge_user: str = os.getenv("BRIDGE_USER", "")
        self.bridge_pass: str = os.getenv("BRIDGE_PASSWORD", "")
        self.support_device: str = os.getenv("SUPPORT_WA_DEVICE_ID", "")

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def handle_group_message(
        self,
        tenant_id: str,
        group_jid: str,
        sender_jid: str,
        sender_name: str,
        content: str,
    ) -> dict:
        """
        Called for every message in the Help Tickets group.

        Returns a dict with:
            action   : "created" | "command" | "ignore"
            ticket   : ticket row dict (if action != "ignore")
            reply    : text to send back to the group
        """
        content_stripped = content.strip()

        # 1. Owner commands: @bijou close TKT-XXXX / @bijou escalate TKT-XXXX
        cmd_result = await self._try_owner_command(tenant_id, content_stripped, sender_jid)
        if cmd_result:
            return cmd_result

        # 2. New ticket — any non-command message becomes a ticket
        ticket = await self._create_ticket(
            tenant_id=tenant_id,
            group_jid=group_jid,
            sender_jid=sender_jid,
            sender_name=sender_name,
            message=content_stripped,
        )

        if not ticket:
            return {"action": "ignore", "reply": None}

        is_urgent = self._is_urgent(content_stripped)
        if is_urgent:
            ticket = await self._escalate(ticket, reason="urgent keywords detected")

        reply = self._build_ticket_reply(ticket, is_urgent)
        return {"action": "created", "ticket": ticket, "reply": reply}

    async def get_open_tickets(self, tenant_id: str) -> list[dict]:
        """Return all open/in_progress tickets for tenant."""
        try:
            result = (
                self.db.table("help_tickets")
                .select("*")
                .eq("tenant_id", tenant_id)
                .in_("status", ["open", "in_progress", "escalated"])
                .order("created_at", desc=False)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"❌ TicketManager.get_open_tickets: {e}")
            return []

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------

    async def _create_ticket(
        self,
        tenant_id: str,
        group_jid: str,
        sender_jid: str,
        sender_name: str,
        message: str,
    ) -> Optional[dict]:
        try:
            # Get next ticket number (simple increment per tenant)
            existing = (
                self.db.table("help_tickets")
                .select("ticket_number")
                .eq("tenant_id", tenant_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            last_num = 0
            if existing.data:
                last_str = existing.data[0]["ticket_number"]  # "TKT-0042"
                m = re.search(r"(\d+)$", last_str)
                if m:
                    last_num = int(m.group(1))
            ticket_number = f"TKT-{(last_num + 1):04d}"

            row = {
                "tenant_id": tenant_id,
                "ticket_number": ticket_number,
                "group_jid": group_jid,
                "sender_jid": sender_jid,
                "sender_name": sender_name or "",
                "message": message[:2000],
                "status": "open",
                "priority": "normal",
            }
            result = self.db.table("help_tickets").insert(row).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ TicketManager._create_ticket: {e}")
            return None

    async def _escalate(self, ticket: dict, reason: str = "") -> dict:
        """Mark ticket as escalated and notify owner."""
        try:
            result = (
                self.db.table("help_tickets")
                .update({
                    "status": "escalated",
                    "priority": "urgent",
                    "escalated_at": datetime.utcnow().isoformat(),
                    "notes": reason,
                })
                .eq("id", ticket["id"])
                .execute()
            )
            updated = result.data[0] if result.data else ticket
            # Notify owner via WA
            asyncio.create_task(self._notify_owner(updated, reason))
            return updated
        except Exception as e:
            logger.error(f"❌ TicketManager._escalate: {e}")
            return ticket

    async def _notify_owner(self, ticket: dict, reason: str = "") -> None:
        """Send owner a WA message linking to the escalated ticket."""
        if not self.owner_wa or not self.bridge_url:
            return
        try:
            msg = (
                f"🚨 *Help Ticket Escalated*\n\n"
                f"🎫 *{ticket['ticket_number']}*\n"
                f"👤 *From:* {ticket.get('sender_name') or ticket.get('sender_jid', '—')}\n"
                f"⚡ *Reason:* {reason or 'manual escalation'}\n\n"
                f"📝 *Message:*\n{ticket['message'][:400]}\n\n"
                f"Reply in the Help Tickets group or handle via dashboard."
            )
            jid = f"{self.owner_wa}@s.whatsapp.net"
            auth = base64.b64encode(
                f"{self.bridge_user}:{self.bridge_pass}".encode()
            ).decode()
            payload: dict = {"jid": jid, "text": msg}
            if self.support_device:
                payload["device_id"] = self.support_device
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.bridge_url}/send/message",
                    json=payload,
                    headers={"Authorization": f"Basic {auth}"},
                )
            logger.info(f"✅ Owner notified for {ticket['ticket_number']}")
        except Exception as e:
            logger.warning(f"⚠️ Owner WA notify failed (non-fatal): {e}")

    async def _try_owner_command(
        self, tenant_id: str, content: str, sender_jid: str
    ) -> Optional[dict]:
        """
        Parse owner commands like:
            @bijou close TKT-0003
            @bijou escalate TKT-0003
            @bijou note TKT-0003 Customer will call back
        Returns result dict or None.
        """
        content_lower = content.lower().strip()

        # Detect command keyword
        matched_cmd = None
        for cmd_key, new_status in TICKET_COMMANDS.items():
            if content_lower.startswith(cmd_key):
                matched_cmd = (cmd_key, new_status)
                break

        # @bijou note TKT-XXXX <text>
        if content_lower.startswith("@bijou note"):
            remainder = content[len("@bijou note"):].strip()
            m = re.match(r"(TKT-\d+)\s*(.*)", remainder, re.IGNORECASE)
            if m:
                ticket_num, note_text = m.group(1).upper(), m.group(2).strip()
                ticket = await self._get_ticket_by_number(tenant_id, ticket_num)
                if ticket:
                    await self._update_ticket(ticket["id"], {"notes": note_text, "status": "in_progress"})
                    return {
                        "action": "command",
                        "ticket": ticket,
                        "reply": f"📝 Note added to {ticket_num}.",
                    }
            return None

        if not matched_cmd:
            return None

        cmd_key, new_status = matched_cmd
        remainder = content[len(cmd_key):].strip()
        m = re.match(r"(TKT-\d+)", remainder, re.IGNORECASE)
        if not m:
            return None

        ticket_num = m.group(1).upper()
        ticket = await self._get_ticket_by_number(tenant_id, ticket_num)
        if not ticket:
            return {
                "action": "command",
                "ticket": None,
                "reply": f"❌ Ticket {ticket_num} not found.",
            }

        updates: dict = {"status": new_status}
        if new_status == "escalated":
            updates["escalated_at"] = datetime.utcnow().isoformat()
            updates["priority"] = "urgent"
            asyncio.create_task(self._notify_owner(ticket, f"manual escalation by owner"))
        elif new_status == "closed":
            updates["closed_at"] = datetime.utcnow().isoformat()

        await self._update_ticket(ticket["id"], updates)
        emoji = "✅" if new_status == "closed" else "🚨"
        return {
            "action": "command",
            "ticket": ticket,
            "reply": f"{emoji} {ticket_num} marked *{new_status}*.",
        }

    async def _get_ticket_by_number(
        self, tenant_id: str, ticket_number: str
    ) -> Optional[dict]:
        try:
            result = (
                self.db.table("help_tickets")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("ticket_number", ticket_number)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ _get_ticket_by_number: {e}")
            return None

    async def _update_ticket(self, ticket_id: str, updates: dict) -> None:
        try:
            self.db.table("help_tickets").update(updates).eq("id", ticket_id).execute()
        except Exception as e:
            logger.error(f"❌ _update_ticket: {e}")

    def _is_urgent(self, text: str) -> bool:
        lower = text.lower()
        return any(kw in lower for kw in URGENT_KEYWORDS)

    def _build_ticket_reply(self, ticket: dict, is_urgent: bool) -> str:
        tnum = ticket["ticket_number"]
        if is_urgent:
            return (
                f"🚨 *Ticket {tnum} — URGENT*\n\n"
                f"Your issue has been flagged as urgent and our team has been alerted.\n"
                f"We'll respond ASAP. Please stand by! 🙏"
            )
        return (
            f"✅ *Ticket {tnum} Created*\n\n"
            f"We've received your message and will get back to you shortly.\n"
            f"Reference: *{tnum}*\n\n"
            f"_Our team monitors this group during business hours (9am–6pm)._"
        )
