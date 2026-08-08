"""
Bijou AI - Command Handler
===========================

Handles in-chat commands for better UX and control.

Commands:
- @bijou [command] - In-chat commands (works anywhere)
- / commands - Slash command discovery

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
"""

import logging
import os
import re
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CommandHandler:
    """
    Handles @bijou commands and / command discovery.

    @bijou commands work in any chat (group or individual).
    / commands provide autocomplete-style help.
    """

    def __init__(
        self,
        owner_jid: str,
        admin_controller=None,
        memory_system=None,
        tool_orchestrator=None,
        db_conn=None,
        bridge_url: str = "",
        bridge_user: str = "",
        bridge_password: str = "",
    ):
        """
        Initialize command handler.

        Args:
            owner_jid: Owner's WhatsApp JID
            admin_controller: AdminController instance
            memory_system: ConversationMemory instance
            tool_orchestrator: ToolOrchestrator instance
            db_conn: Supabase client for CRM / bookings queries
            bridge_url: WhatsApp bridge base URL
            bridge_user: Bridge HTTP Basic Auth username
            bridge_password: Bridge HTTP Basic Auth password
        """
        self.owner_jid = owner_jid
        self.admin_controller = admin_controller
        self.memory = memory_system
        self.tool_orchestrator = tool_orchestrator
        self.db_conn = db_conn
        self.bridge_url = bridge_url or os.getenv("BRIDGE_URL", "")
        self.bridge_user = bridge_user or os.getenv("BRIDGE_USER", "")
        self.bridge_password = bridge_password or os.getenv("BRIDGE_PASSWORD", "")

        # Feature flag
        self.enabled = os.getenv("ENABLE_BIJOU_COMMANDS", "false").lower() == "true"

        # Track quiet mode per chat
        self.quiet_chats: Dict[str, bool] = {}

        logger.info(f"✅ CommandHandler initialized (enabled={self.enabled})")

    def is_command(self, message: str) -> bool:
        """
        Check if message is a command.

        Args:
            message: Message text

        Returns:
            True if message is a @bijou or / command
        """
        if not self.enabled:
            return False

        message_lower = message.strip().lower()
        return message_lower.startswith("@bijou") or message_lower.startswith("/")

    def parse_command(
        self, message: str, chat_jid: str, sender: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse command from message.

        Args:
            message: Message text
            chat_jid: Chat JID
            sender: Sender JID

        Returns:
            Parsed command dict or None
        """
        message = message.strip()

        # @bijou commands
        if message.lower().startswith("@bijou"):
            parts = message[6:].strip().split(maxsplit=1)
            command = parts[0].lower() if parts else "help"
            args = parts[1] if len(parts) > 1 else ""

            return {
                "type": "bijou",
                "command": command,
                "args": args,
                "chat_jid": chat_jid,
                "sender": sender,
                "is_owner": sender == self.owner_jid,
            }

        # / commands
        elif message.startswith("/"):
            parts = message[1:].strip().split(maxsplit=1)
            command = parts[0].lower() if parts else "help"
            args = parts[1] if len(parts) > 1 else ""

            return {
                "type": "slash",
                "command": command,
                "args": args,
                "chat_jid": chat_jid,
                "sender": sender,
                "is_owner": sender == self.owner_jid,
            }

        return None

    async def handle_command(
        self, message: str, chat_jid: str, sender: str, tenant_id: str = ""
    ) -> Optional[str]:
        """
        Handle a command and return response.

        Args:
            message: Message text
            chat_jid: Chat JID
            sender: Sender JID
            tenant_id: Tenant ID resolved from the incoming device (multi-tenant isolation)

        Returns:
            Response string or None if not a command
        """
        if not self.is_command(message):
            return None

        cmd = self.parse_command(message, chat_jid, sender)
        if not cmd:
            return None

        # Route to appropriate handler
        if cmd["type"] == "bijou":
            return await self._handle_bijou_command(cmd, tenant_id)
        elif cmd["type"] == "slash":
            return self._handle_slash_command(cmd)

        return None

    async def _handle_bijou_command(self, cmd: Dict[str, Any], tenant_id: str = "") -> str:
        """Handle @bijou commands"""
        command = cmd["command"]
        args = cmd["args"]
        chat_jid = cmd["chat_jid"]
        is_owner = cmd["is_owner"]

        # Help command (everyone)
        if command in ["help", "commands", ""]:
            return self._get_bijou_help(is_owner)

        # Quiet mode (everyone can use in their own chats)
        elif command == "quiet":
            self.quiet_chats[chat_jid] = True
            return (
                "🤫 **Quiet mode enabled**\n\n"
                "I'll observe this chat but won't respond unless:\n"
                "- You mention me with @bijou [command]\n"
                "- Owner uses /admin commands\n\n"
                "To resume: @bijou resume"
            )

        # Resume from quiet mode (everyone)
        elif command == "resume":
            self.quiet_chats[chat_jid] = False
            return (
                "👋 **I'm back!**\n\n"
                "I'll now respond to messages in this chat.\n"
                "To pause again: @bijou quiet"
            )

        # Status check (everyone)
        elif command == "status":
            is_quiet = self.quiet_chats.get(chat_jid, False)
            return (
                "📊 **Bijou Status**\n\n"
                f"Mode: {'🤫 Quiet (observing only)' if is_quiet else '💬 Active'}\n"
                f"Chat: {chat_jid}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "Commands: @bijou help"
            )

        # Summarize conversation (everyone)
        elif command in ["summarize", "summary"]:
            if not self.memory:
                return "❌ Memory system not available"

            history = self.memory.get_conversation_history(chat_jid, limit=20)
            if not history:
                return "📝 No conversation history found in this chat."

            # Generate summary
            summary_lines = [
                "📝 **Conversation Summary**\n",
                f"Messages: {len(history)}",
                f"Period: Last 24 hours\n",
            ]

            # Show last few exchanges
            for msg in history[-5:]:
                timestamp = msg.get("timestamp", "")
                user_msg = msg.get("user_message", "")[:50]
                summary_lines.append(f"• {user_msg}...")

            summary_lines.append("\nFor detailed analysis: @bijou insights")
            return "\n".join(summary_lines)

        # Insights (owner only)
        elif command == "insights":
            if not is_owner:
                return "🔒 This command is only available to the account owner."

            if not self.memory:
                return "❌ Memory system not available"

            context = self.memory.get_context_summary(chat_jid)
            if not context:
                return "📊 No insights available for this chat yet."

            return (
                "📊 **Chat Insights**\n\n"
                f"Total messages: {context.get('total_messages', 0)}\n"
                f"Avg sentiment: {context.get('avg_sentiment', 0):.2f}\n"
                f"Escalations: {context.get('escalation_count', 0)}\n"
                f"Last interaction: {context.get('last_interaction', 'N/A')}\n\n"
                "For full analytics: Use the dashboard"
            )

        # Remind me (everyone)
        elif command in ["remind", "reminder"]:
            if not args:
                return (
                    "⏰ **Set a Reminder**\n\n"
                    "Usage: @bijou remind [time] [message]\n"
                    "Example: @bijou remind tomorrow 2pm Follow up with John\n\n"
                    "⚠️ Note: Reminder feature coming soon!"
                )
            return "⚠️ Reminder feature coming soon! We'll notify you when it's ready."

        # ── OWNER OPERATOR COMMANDS ─────────────────────────────────────────────

        # @bijou bookings — show today's scheduled calls
        elif command == "bookings":
            if not is_owner:
                return "🔒 This command is only available to the account owner."
            return await self._cmd_bookings()

        # @bijou crm [name or phone] — look up CRM contact
        elif command == "crm":
            if not is_owner:
                return "🔒 This command is only available to the account owner."
            if not args:
                return (
                    "📋 **CRM Lookup**\n\n"
                    "Usage: @bijou crm [name or phone]\n"
                    "Example: @bijou crm Ali Ahmad\n"
                    "Example: @bijou crm 60123456789"
                )
            return await self._cmd_crm_lookup(args)

        # @bijou send [phone/name] > [message] — send WA message to a contact
        elif command == "send":
            if not is_owner:
                return "🔒 This command is only available to the account owner."
            if ">" not in args:
                return (
                    "📤 **Send Message to Contact**\n\n"
                    "Usage: @bijou send [phone or name] > [message]\n"
                    "Example: @bijou send 60123456789 > Hi Ali, your viewing is confirmed for tomorrow 2pm!\n"
                    "Example: @bijou send Ali Ahmad > Your brochure is ready, I'll send it now."
                )
            parts = args.split(">", 1)
            target, text = parts[0].strip(), parts[1].strip()
            return await self._cmd_send_to_contact(target, text)

        # @bijou confirm [booking_id or contact name] — update booking status
        elif command == "confirm":
            if not is_owner:
                return "🔒 This command is only available to the account owner."
            if not args:
                return (
                    "✅ **Confirm Booking**\n\n"
                    "Usage: @bijou confirm [booking_id]\n"
                    "Get booking IDs from: @bijou bookings"
                )
            return await self._cmd_confirm_booking(args.strip())

        # Search knowledge (everyone)
        elif command == "search":
            if not args:
                return (
                    "🔍 **Search Knowledge Base**\n\n"
                    "Usage: @bijou search [query]\n"
                    "Example: @bijou search shipping policy"
                )

            # Delegate to admin controller if available
            if self.admin_controller and hasattr(
                self.admin_controller, "_handle_kb_command"
            ):
                return await self.admin_controller._handle_kb_command("search", args)

            return f"🔍 Searching for: {args}\n\n⚠️ Knowledge base not configured yet."

        # Unknown command
        else:
            return (
                f"❓ Unknown command: {command}\n\n"
                "Try: @bijou help\n"
                "Or use: /help for all commands"
            )

    def _handle_slash_command(self, cmd: Dict[str, Any]) -> str:
        """Handle / commands (discovery and help)"""
        command = cmd["command"]
        is_owner = cmd["is_owner"]

        if command in ["help", "commands", ""]:
            return self._get_slash_help(is_owner)

        # If it's an admin command, delegate to admin controller
        if command == "admin" and self.admin_controller:
            if not is_owner:
                return "🔒 Admin commands are only available to the account owner."
            return self.admin_controller._get_help()

        # Other slash commands
        elif command == "status":
            return self._handle_bijou_command(
                {**cmd, "command": "status", "type": "bijou"}
            )

        elif command in ["quiet", "resume", "summarize", "search"]:
            return (
                f"💡 Tip: Use @bijou {command} instead of /{command}\n\n"
                f"@bijou commands work in group chats too!"
            )

        else:
            return (
                f"❓ Unknown command: /{command}\n\n"
                "Available commands:\n"
                "/help - Show all commands\n"
                "/status - Check Bijou status\n"
                f"{'/' if is_owner else ''}admin - Admin commands (owner only)\n\n"
                "💡 Most commands use @bijou prefix:\n"
                "@bijou help - Show @bijou commands"
            )

    def _get_bijou_help(self, is_owner: bool) -> str:
        """Get @bijou command help"""
        help_text = [
            "🤖 **@bijou Commands**\n",
            "**Everyone:**",
            "@bijou help - Show this help",
            "@bijou quiet - Stop responding (observe only)",
            "@bijou resume - Resume responding",
            "@bijou status - Check status",
            "@bijou summarize - Summarize this conversation",
            "@bijou search [query] - Search knowledge base",
            "@bijou remind [time] [msg] - Set reminder (coming soon)",
        ]

        if is_owner:
            help_text.extend(
                [
                    "\n**Owner Only — Operator:**",
                    "@bijou bookings - Today's scheduled calls",
                    "@bijou crm [name/phone] - Look up CRM contact",
                    "@bijou send [phone] > [msg] - Send WA to contact",
                    "@bijou confirm [ID] - Mark booking in-progress",
                    "@bijou insights - Chat analytics",
                    "@bijou report - Instant report",
                    "\n**Admin Commands:**",
                    "/admin - Full admin control panel",
                ]
            )

        help_text.append(
            "\n💡 Tip: @bijou commands work in group chats!\n"
            "Type / to see slash commands."
        )

        return "\n".join(help_text)

    # ── OPERATOR HELPER METHODS ─────────────────────────────────────────────────
    # tenant_id is ALWAYS passed in from the call chain — never derived here.
    # This guarantees strict per-tenant data isolation in a multi-tenant deployment.

    async def _cmd_bookings(self, tenant_id: str) -> str:
        """Show today's call bookings for the owner's tenant."""
        if not self.db_conn:
            return "❌ Database not connected. Bookings unavailable."
        if not tenant_id:
            return "❌ Tenant context missing — cannot fetch bookings safely."
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            result = (
                self.db_conn.table("call_bookings")
                .select("id, customer_name, customer_phone, scheduled_time, status, call_type, duration_minutes")
                .eq("tenant_id", tenant_id)
                .gte("scheduled_time", f"{today}T00:00:00")
                .lte("scheduled_time", f"{today}T23:59:59")
                .order("scheduled_time")
                .limit(10)
                .execute()
            )
            bookings = result.data or []
            if not bookings:
                return f"📞 **No calls scheduled for today ({today})**\n\nBook at your dashboard or via customer chat."
            lines = [f"📞 *Today's Calls — {today}*\n"]
            for b in bookings:
                t = datetime.fromisoformat(b["scheduled_time"].replace("Z","+00:00"))
                local_t = t.strftime("%H:%M")
                name = b.get("customer_name") or b.get("customer_phone") or "Unknown"
                status = b.get("status", "scheduled")
                ctype = b.get("call_type", "call").replace("_", " ")
                dur = b.get("duration_minutes", 30)
                status_icon = {"scheduled": "🔵", "in_progress": "🟠", "completed": "✅", "cancelled": "❌"}.get(status, "⚪")
                lines.append(f"{status_icon} {local_t} — {name} | {ctype} {dur}min")
                lines.append(f"   ID: {str(b['id'])[:8]}")
            lines.append("\n✅ Confirm: @bijou confirm [ID]")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"@bijou bookings error: {e}")
            return "❌ Could not fetch bookings. Check connection."

    async def _cmd_crm_lookup(self, query: str, tenant_id: str) -> str:
        """Look up a contact in the CRM by name or phone, scoped to tenant."""
        if not self.db_conn:
            return "❌ Database not connected. CRM lookup unavailable."
        if not tenant_id:
            return "❌ Tenant context missing — cannot search CRM safely."
        try:
            digits = re.sub(r"\D", "", query)
            base = (
                self.db_conn.table("contacts")
                .select("name, phone, jid, tag, notes, last_message_at")
                .eq("tenant_id", tenant_id)
            )
            if digits and len(digits) >= 7:
                result = base.ilike("phone", f"%{digits[-9:]}%").limit(3).execute()
            else:
                result = base.ilike("name", f"%{query}%").limit(3).execute()

            contacts = result.data or []
            if not contacts:
                return f"🔍 No CRM contact found for *{query}*\n\nAdd via dashboard → Contacts."

            lines = [f"📋 *CRM match for '{query}'*\n"]
            for c in contacts:
                name = c.get("name") or c.get("phone") or "Unknown"
                phone = c.get("phone") or ""
                tag = c.get("tag") or "lead"
                notes = c.get("notes") or ""
                lines.append(f"👤 *{name}*")
                if phone:
                    lines.append(f"   📱 {phone}")
                lines.append(f"   🏷️ {tag}")
                if notes:
                    lines.append(f"   📝 {notes[:80]}")
                lines.append("")
            lines.append(f"📤 Send msg: @bijou send {contacts[0].get('phone','')} > [message]")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"@bijou crm error: {e}")
            return "❌ CRM lookup failed."

    async def _cmd_send_to_contact(self, target: str, text: str, tenant_id: str) -> str:
        """Send a WhatsApp message to a CRM contact."""
        if not self.bridge_url:
            return "❌ Bridge URL not configured. Set BRIDGE_URL in environment."

        # Resolve phone number from digits directly, or name→contact lookup
        phone = re.sub(r"\D", "", target)
        if not phone and self.db_conn and tenant_id:
            try:
                r = (
                    self.db_conn.table("contacts")
                    .select("phone")
                    .eq("tenant_id", tenant_id)
                    .ilike("name", f"%{target}%")
                    .limit(1)
                    .execute()
                )
                if r.data:
                    phone = re.sub(r"\D", "", r.data[0].get("phone", ""))
            except Exception:
                pass
        if not phone:
            return f"❌ Could not resolve phone for *{target}*. Use a phone number directly."

        jid = f"{phone}@s.whatsapp.net"
        try:
            import base64
            auth = base64.b64encode(f"{self.bridge_user}:{self.bridge_password}".encode()).decode()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.bridge_url}/send/message",
                    headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                    json={"phone": jid, "message": text},
                )
                if resp.status_code in (200, 201):
                    return f"✅ Message sent to *+{phone}*\n\n_{text[:80]}{'...' if len(text)>80 else ''}_"
                else:
                    return f"❌ Bridge returned {resp.status_code}. Message not sent."
        except Exception as e:
            logger.error(f"@bijou send error: {e}")
            return "❌ Failed to send. Check bridge connection."

    async def _cmd_confirm_booking(self, booking_id: str, tenant_id: str) -> str:
        """Mark a booking as in-progress by short ID prefix, scoped to tenant."""
        if not self.db_conn:
            return "❌ Database not connected."
        if not tenant_id:
            return "❌ Tenant context missing — cannot update booking safely."
        try:
            r = (
                self.db_conn.table("call_bookings")
                .select("id, customer_name, scheduled_time, status")
                .eq("tenant_id", tenant_id)
                .ilike("id::text", f"{booking_id}%")
                .limit(1)
                .execute()
            )
            if not r.data:
                return f"❌ Booking *{booking_id}* not found. Check ID from @bijou bookings."
            b = r.data[0]
            if b["status"] == "completed":
                return f"ℹ️ Booking for *{b.get('customer_name','?')}* is already completed."
            self.db_conn.table("call_bookings").update({"status": "in_progress"}).eq("tenant_id", tenant_id).eq("id", b["id"]).execute()
            t = datetime.fromisoformat(b["scheduled_time"].replace("Z","+00:00"))
            return (
                f"✅ *Confirmed!*\n"
                f"Customer: {b.get('customer_name','?')}\n"
                f"Time: {t.strftime('%d %b %Y %H:%M')}\n"
                f"Status: in progress\n\n"
                f"When done: @bijou bookings"
            )
        except Exception as e:
            logger.error(f"@bijou confirm error: {e}")
            return "❌ Could not confirm booking."

    def _get_slash_help(self, is_owner: bool) -> str:
        """Get / command help"""
        help_text = [
            "⚡ **Slash Commands**\n",
            "/help - Show this help",
            "/status - Check Bijou status",
        ]

        if is_owner:
            help_text.extend(
                [
                    "/admin - Admin control panel",
                    "\n**Admin Shortcuts:**",
                    "/admin mode quiet - Observer mode",
                    "/admin mode auto - Auto-respond",
                    "/admin kb add [text] - Add knowledge",
                    "/admin report - Generate report",
                ]
            )

        help_text.extend(
            [
                "\n**For Group Chats:**",
                "Use @bijou commands instead:",
                "@bijou quiet - Pause in this chat",
                "@bijou help - Show @bijou commands",
                "\n💡 Type @bijou to see all commands",
            ]
        )

        return "\n".join(help_text)

    def is_quiet(self, chat_jid: str) -> bool:
        """
        Check if Bijou should be quiet in this chat.

        Args:
            chat_jid: Chat JID

        Returns:
            True if in quiet mode
        """
        return self.quiet_chats.get(chat_jid, False)

    def should_respond(
        self, message: str, chat_jid: str, sender: str, is_group: bool = False
    ) -> bool:
        """
        Check if Bijou should respond to a message.

        Args:
            message: Message text
            chat_jid: Chat JID
            sender: Sender JID
            is_group: True if group chat

        Returns:
            True if should respond
        """
        # Always respond to commands
        if self.is_command(message):
            return True

        # Always respond to owner in DM
        if sender == self.owner_jid and not is_group:
            return True

        # Don't respond if in quiet mode
        if self.is_quiet(chat_jid):
            return False

        # In group chats, only respond if mentioned
        if is_group:
            message_lower = message.lower()
            return (
                "@bijou" in message_lower
                or "bijou" in message_lower
                or message.startswith("/")
            )

        # Default: respond in DMs
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get command handler statistics"""
        return {
            "enabled": self.enabled,
            "quiet_chats": len(self.quiet_chats),
            "quiet_chat_list": list(self.quiet_chats.keys()),
        }
