#!/usr/bin/env python3
"""
Owner Notifications - Proactive WhatsApp Alerts for Business Owners
===================================================================

Sends real-time WhatsApp notifications to business owners when important
events happen, eliminating the need for manual status checks.

Features:
- New conversation alerts (when customer first messages)
- Hot lead detection (buying signals, urgency, high-value inquiries)
- Daily summary reports (conversations, leads, escalations)
- Real-time escalation alerts (customer wants human, complaints)
- Smart message sending (owner can reply via Bijou)

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-01-30
Version: 1.0
"""

import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of owner notifications"""

    NEW_CONVERSATION = "new_conversation"  # First message from new customer
    HOT_LEAD = "hot_lead"  # Buying signals detected
    ESCALATION = "escalation"  # Customer wants human
    COMPLAINT = "complaint"  # Negative sentiment detected
    DAILY_SUMMARY = "daily_summary"  # End of day report
    APPOINTMENT_REQUEST = "appointment_request"  # Booking request
    HIGH_VALUE = "high_value"  # Big order/inquiry


class OwnerNotificationSystem:
    """
    Proactive notification system for business owners.

    Sends WhatsApp messages to owner when important events occur,
    making Bijou truly proactive instead of reactive.
    """

    def __init__(
        self,
        owner_jid: str,
        bridge_url: str,
        supabase_client=None,
        analyzer=None,
        send_message_callback=None,
    ):
        """
        Initialize owner notification system

        Args:
            owner_jid: Owner's WhatsApp JID
            bridge_url: WhatsApp bridge URL for sending messages (deprecated - use callback)
            supabase_client: Database connection
            analyzer: ConversationAnalyzer instance for smart summaries
            send_message_callback: Direct message sending function (preferred over HTTP)
        """
        self.owner_jid = owner_jid
        self.bridge_url = bridge_url
        self.db = supabase_client
        self.analyzer = analyzer
        self.send_message_callback = send_message_callback

        # Track what we've already notified to avoid spam
        self.notified_conversations = set()
        self.last_daily_summary = None

        # Notification settings (can be configured per tenant)
        self.settings = {
            "notify_new_conversations": True,
            "notify_hot_leads": True,
            "notify_escalations": True,
            "notify_complaints": True,
            "daily_summary_enabled": True,
            "daily_summary_time": "20:00",  # 8 PM
            "quiet_hours_start": "23:00",  # 11 PM
            "quiet_hours_end": "08:00",  # 8 AM
        }

        logger.info(f"✅ OwnerNotificationSystem initialized for {owner_jid}")

    async def notify_new_conversation(
        self, 
        chat_jid: str, 
        first_message: str, 
        ai_response: str,
        sender_jid: str = None,  # ← NEW: Actual sender phone number
        from_name: str = None,   # ← NEW: Contact name from WhatsApp
    ) -> bool:
        """
        Notify owner when new customer starts conversation

        Args:
            chat_jid: Customer's WhatsApp JID
            first_message: First message from customer
            ai_response: Bijou's response
            sender_jid: Actual sender JID (overrides chat_jid for phone number)
            from_name: Contact name from WhatsApp

        Returns:
            True if notification sent successfully
        """
        if not self.settings["notify_new_conversations"]:
            return False

        # Check if already notified
        if chat_jid in self.notified_conversations:
            return False

        # Format phone number for display (use sender_jid if available, fallback to chat_jid)
        phone = self._format_phone_number(sender_jid if sender_jid else chat_jid)
        
        # Format contact name
        contact_name = from_name if from_name else "Unknown"

        # Build notification message
        message = f"""🔔 NEW CUSTOMER CONVERSATION

📱 Phone: {phone}
👤 Name: {contact_name}

💬 Their message:
"{first_message[:200]}{"..." if len(first_message) > 200 else ""}"

🤖 Bijou responded:
"{ai_response[:200]}{"..." if len(ai_response) > 200 else ""}"

---
Quick Actions:
• View full chat: /owner export {chat_jid}
• Take over: /owner send {chat_jid} [your message]
• Mark handled: /owner close {chat_jid}"""

        # Send notification
        success = await self._send_to_owner(message)

        if success:
            self.notified_conversations.add(chat_jid)
            self._log_notification(chat_jid, NotificationType.NEW_CONVERSATION)

        return success

    async def notify_hot_lead(
        self, 
        chat_jid: str, 
        reason: str, 
        conversation_summary: str,
        sender_jid: str = None,  # ← NEW: Actual sender phone number
        from_name: str = None,   # ← NEW: Contact name from WhatsApp
    ) -> bool:
        """
        Notify owner about hot lead (high buying intent)

        Args:
            chat_jid: Customer's WhatsApp JID
            reason: Why this is a hot lead
            conversation_summary: Brief summary of conversation
            sender_jid: Actual sender JID (overrides chat_jid for phone number)
            from_name: Contact name from WhatsApp

        Returns:
            True if notification sent
        """
        if not self.settings["notify_hot_leads"]:
            return False

        # Format phone number and contact name
        phone = self._format_phone_number(sender_jid if sender_jid else chat_jid)
        contact_name = from_name if from_name else "Unknown"

        message = f"""🔥 HOT LEAD ALERT!

📱 Phone: {phone}
👤 Name: {contact_name}

🎯 Why it's hot:
{reason}

💬 Conversation:
{conversation_summary[:300]}{"..." if len(conversation_summary) > 300 else ""}

---
⚡ ACTION NEEDED:
Reply now: /owner send {chat_jid} [your message]

Or view details: /owner export {chat_jid}"""

        success = await self._send_to_owner(message)

        if success:
            self._log_notification(chat_jid, NotificationType.HOT_LEAD)

        return success

    async def notify_escalation(
        self,
        chat_jid: str,
        trigger: str,
        conversation_context: str,
        tenant_id: str = None,
        sender_jid: str = None,  # ← NEW: Actual sender phone number
        from_name: str = None,   # ← NEW: Contact name from WhatsApp
    ) -> bool:
        """
        Notify owner when customer requests human

        Args:
            chat_jid: Customer's WhatsApp JID
            trigger: What triggered escalation
            conversation_context: Recent conversation
            tenant_id: Tenant ID for multi-tenant support
            sender_jid: Actual sender JID (overrides chat_jid for phone number)
            from_name: Contact name from WhatsApp

        Returns:
            True if notification sent
        """
        if not self.settings["notify_escalations"]:
            return False

        # Format phone number and contact name
        phone = self._format_phone_number(sender_jid if sender_jid else chat_jid)
        contact_name = from_name if from_name else "Unknown"

        message = f"""⚠️ HUMAN HANDOVER REQUESTED

📱 Phone: {phone}
👤 Name: {contact_name}

🗣️ They said:
"{trigger}"

💬 Recent conversation:
{conversation_context[:250]}{"..." if len(conversation_context) > 250 else ""}

---
🔴 URGENT - Customer waiting for human response

Reply: /owner send {chat_jid} [your message]
Or: /owner assign {chat_jid} [team member]"""

        success = await self._send_to_owner(message)

        if success:
            self._log_notification(chat_jid, NotificationType.ESCALATION)

        return success

    async def notify_complaint(
        self, chat_jid: str, complaint_text: str, sentiment_score: str
    ) -> bool:
        """
        Notify owner about customer complaint

        Args:
            chat_jid: Customer's WhatsApp JID
            complaint_text: The complaint message
            sentiment_score: Negative sentiment indicator

        Returns:
            True if notification sent
        """
        if not self.settings["notify_complaints"]:
            return False

        phone = self._format_phone_number(chat_jid)

        message = f"""😞 COMPLAINT DETECTED

📱 Customer: {phone}

😠 Sentiment: {sentiment_score}

💬 Their complaint:
"{complaint_text[:300]}{"..." if len(complaint_text) > 300 else ""}"

---
⚠️ URGENT - Needs immediate attention

Respond personally: /owner send {chat_jid} [your message]
View history: /owner export {chat_jid}"""

        success = await self._send_to_owner(message)

        if success:
            self._log_notification(chat_jid, NotificationType.COMPLAINT)

        return success

    async def send_daily_summary(self) -> bool:
        """
        Send end-of-day summary to owner

        Returns:
            True if summary sent successfully
        """
        if not self.settings["daily_summary_enabled"]:
            return False

        # Check if already sent today
        today = datetime.now().date()
        if self.last_daily_summary and self.last_daily_summary == today:
            return False

        # Get today's stats
        stats = await self._get_daily_stats()

        if not stats:
            logger.warning("Failed to get daily stats")
            return False

        # Build summary message
        message = self._format_daily_summary(stats)

        # Send to owner
        success = await self._send_to_owner(message)

        if success:
            self.last_daily_summary = today
            self._log_notification("daily", NotificationType.DAILY_SUMMARY)

        return success

    async def notify_appointment_request(self, chat_jid: str, details: Dict) -> bool:
        """
        Notify owner about appointment/booking request

        Args:
            chat_jid: Customer's WhatsApp JID
            details: Appointment details (date, time, guests, etc.)

        Returns:
            True if notification sent
        """
        phone = self._format_phone_number(chat_jid)

        # Format appointment details
        details_text = "\n".join([f"• {k.title()}: {v}" for k, v in details.items()])

        message = f"""📅 APPOINTMENT REQUEST

📱 Customer: {phone}

📋 Details:
{details_text}

---
✅ Confirm: /owner send {chat_jid} [confirmation message]
❌ Decline: /owner send {chat_jid} [alternative suggestion]

View chat: /owner export {chat_jid}"""

        success = await self._send_to_owner(message)

        if success:
            self._log_notification(chat_jid, NotificationType.APPOINTMENT_REQUEST)

        return success

    def detect_notification_triggers(
        self, message: str, conversation_history: List[Dict] = None
    ) -> List[NotificationType]:
        """
        Analyze message and detect what notifications should be sent

        Args:
            message: Customer's message
            conversation_history: Previous messages in conversation

        Returns:
            List of notification types to trigger
        """
        triggers = []
        message_lower = message.lower()

        # Hot lead signals
        hot_lead_keywords = [
            "how much",
            "price",
            "buy",
            "purchase",
            "order",
            "interested",
            "when can",
            "available",
            "book",
            "reserve",
            "urgent",
        ]
        if any(keyword in message_lower for keyword in hot_lead_keywords):
            triggers.append(NotificationType.HOT_LEAD)

        # Escalation signals
        escalation_keywords = [
            "speak to",
            "talk to human",
            "real person",
            "manager",
            "not helping",
            "doesn't understand",
        ]
        if any(keyword in message_lower for keyword in escalation_keywords):
            triggers.append(NotificationType.ESCALATION)

        # Complaint signals
        complaint_keywords = [
            "disappointed",
            "terrible",
            "worst",
            "bad service",
            "complaint",
            "angry",
            "frustrated",
            "unacceptable",
        ]
        if any(keyword in message_lower for keyword in complaint_keywords):
            triggers.append(NotificationType.COMPLAINT)

        # Appointment signals
        appointment_keywords = [
            "book",
            "reserve",
            "appointment",
            "reservation",
            "table for",
            "people on",
            "schedule",
        ]
        if any(keyword in message_lower for keyword in appointment_keywords):
            triggers.append(NotificationType.APPOINTMENT_REQUEST)

        # New conversation (if no history)
        if not conversation_history or len(conversation_history) <= 1:
            triggers.append(NotificationType.NEW_CONVERSATION)

        return triggers

    async def _send_to_owner(self, message: str) -> bool:
        """
        Send WhatsApp message to owner

        Args:
            message: Message to send

        Returns:
            True if sent successfully
        """
        # Check quiet hours
        if self._is_quiet_hours():
            logger.info("Skipping notification - quiet hours active")
            return False

        try:
            import os

            # Normalize owner JID (remove @lid suffix if present, ensure @s.whatsapp.net)
            owner_jid = self.owner_jid
            if "@lid" in owner_jid:
                # Convert linked device to main number
                # Extract base JID from owner_jid environment
                owner_phone = os.getenv("OWNER_WHATSAPP_JID", "")
                if not owner_phone:
                    logger.error("❌ OWNER_WHATSAPP_JID not set - cannot send owner notification")
                    return False
                owner_jid = owner_phone
                logger.info(
                    f"📱 Normalized owner JID from {self.owner_jid} to {owner_jid}"
                )

            logger.info(f"📨 Sending notification to owner: {owner_jid}")
            logger.debug(f"   Message preview: {message[:100]}...")

            # Use direct send_message callback if available (preferred - bypasses HTTP)
            if self.send_message_callback:
                try:
                    # Find a tenant to send FROM
                    tenant_id = None
                    if self.db:
                        try:
                            result = (
                                self.db.table("tenants")
                                .select("id")
                                .not_.is_("whatsapp_connected_at", "null")
                                .limit(1)
                                .execute()
                            )
                            if result.data:
                                tenant_id = result.data[0]["id"]
                        except Exception as db_error:
                            logger.warning(
                                f"Could not find connected tenant: {db_error}"
                            )

                    if not tenant_id:
                        tenant_id = os.getenv(
                            "DEFAULT_TENANT_ID", "87dcc712-1eb3-4772-a682-d74f67d13f92"
                        )

                    # Send using Bijou's internal send_message (already works for customers)
                    success = self.send_message_callback(
                        owner_jid, message, channel="whatsapp", tenant_id=tenant_id
                    )

                    if success:
                        logger.info(
                            f"✅ Owner notification sent to {owner_jid} (via callback)"
                        )
                        return True
                    else:
                        logger.error(f"❌ send_message_callback returned False")
                        return False

                except Exception as callback_error:
                    logger.error(
                        f"❌ send_message_callback failed: {callback_error}",
                        exc_info=True,
                    )
                    return False
            else:
                # Fallback: HTTP bridge (old method - has timeout issues)
                logger.warning(
                    "⚠️ send_message_callback not available, using HTTP bridge (may timeout)"
                )
                import asyncio

                import httpx

                url = f"{self.bridge_url}/api/send"

                tenant_id = None
                if self.db:
                    try:
                        result = (
                            self.db.table("tenants")
                            .select("id")
                            .not_.is_("whatsapp_connected_at", "null")
                            .limit(1)
                            .execute()
                        )
                        if result.data:
                            tenant_id = result.data[0]["id"]
                    except Exception as db_error:
                        logger.warning(f"Could not find connected tenant: {db_error}")

                if not tenant_id:
                    tenant_id = os.getenv(
                        "DEFAULT_TENANT_ID", "87dcc712-1eb3-4772-a682-d74f67d13f92"
                    )

                payload = {
                    "tenant_id": tenant_id,
                    "recipient": owner_jid,
                    "message": message,
                }

                async with httpx.AsyncClient(timeout=30.0) as client:
                    try:
                        response = await client.post(url, json=payload)
                        if response.status_code == 200:
                            logger.info(f"✅ Owner notification sent via HTTP bridge")
                            return True
                        else:
                            logger.error(
                                f"❌ HTTP bridge failed: {response.status_code} - {response.text}"
                            )
                            return False
                    except Exception as http_error:
                        logger.error(
                            f"❌ HTTP bridge error: {http_error}", exc_info=True
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Error sending owner notification: {e}", exc_info=True)
            return False

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        now = datetime.now().time()
        start = datetime.strptime(self.settings["quiet_hours_start"], "%H:%M").time()
        end = datetime.strptime(self.settings["quiet_hours_end"], "%H:%M").time()

        if start < end:
            return start <= now <= end
        else:  # Quiet hours cross midnight
            return now >= start or now <= end

    async def _get_daily_stats(self) -> Optional[Dict]:
        """Get statistics for today's conversations"""
        if not self.db:
            return None

        try:
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # Query conversations from today
            result = (
                self.db.table("conversations")  # noaudit - system-level owner report; intentionally reads across all tenants for today's summary
                .select("*")
                .gte("timestamp", today_start.isoformat())
                .execute()
            )

            if not result.data:
                return {
                    "total_conversations": 0,
                    "new_customers": 0,
                    "total_messages": 0,
                    "escalations": 0,
                    "top_topics": [],
                }

            messages = result.data

            # Calculate stats
            unique_customers = len(set(m.get("chat_jid") for m in messages))
            total_messages = len(messages)

            # Count escalations (simplified - check for handover triggers)
            escalations = sum(
                1
                for m in messages
                if any(
                    word in m.get("message_content", "").lower()
                    for word in ["human", "person", "manager"]
                )
            )

            # Extract top topics (simplified)
            all_messages_text = " ".join(
                [m.get("message_content", "") for m in messages]
            ).lower()
            topics = []
            topic_keywords = [
                ("delivery", "🚚 Delivery inquiries"),
                ("price", "💰 Pricing questions"),
                ("menu", "📋 Menu requests"),
                ("booking", "📅 Booking requests"),
                ("hours", "🕐 Operating hours"),
            ]
            for keyword, label in topic_keywords:
                if keyword in all_messages_text:
                    topics.append(label)

            return {
                "total_conversations": unique_customers,
                "new_customers": unique_customers,  # Simplified
                "total_messages": total_messages,
                "escalations": escalations,
                "top_topics": topics[:5],
                "messages": messages,  # For detailed analysis
            }

        except Exception as e:
            logger.error(f"Failed to get daily stats: {e}")
            return None

    def _format_daily_summary(self, stats: Dict) -> str:
        """Format daily summary message"""
        today = datetime.now().strftime("%b %d, %Y")

        # Get hot leads from messages (simplified)
        hot_leads = []
        if "messages" in stats:
            # Look for buying signals in messages
            for msg in stats["messages"]:
                content = msg.get("message_content", "").lower()
                if any(
                    word in content
                    for word in ["book", "reserve", "order", "buy", "price"]
                ):
                    chat_jid = msg.get("chat_jid")
                    if chat_jid and chat_jid not in [l.get("jid") for l in hot_leads]:
                        hot_leads.append(
                            {
                                "jid": chat_jid,
                                "phone": self._format_phone_number(chat_jid),
                                "snippet": content[:50],
                            }
                        )
                        if len(hot_leads) >= 3:
                            break

        message_parts = [
            f"📊 DAILY REPORT - {today}",
            "",
            f"💬 Total Conversations: {stats['total_conversations']}",
            f"🆕 New Customers: {stats['new_customers']}",
            f"📨 Messages: {stats['total_messages']}",
            f"⚠️ Escalations: {stats['escalations']}",
            "",
        ]

        # Add top topics
        if stats.get("top_topics"):
            message_parts.append("🔥 TOP INQUIRIES:")
            for topic in stats["top_topics"]:
                message_parts.append(f"  {topic}")
            message_parts.append("")

        # Add hot leads
        if hot_leads:
            message_parts.append("💎 HOT LEADS TODAY:")
            for lead in hot_leads:
                message_parts.append(f"  • {lead['phone']}")
                message_parts.append(f'    "{lead["snippet"]}..."')
            message_parts.append("")

        # Footer
        message_parts.extend(
            [
                "---",
                "View details: /owner report today",
                "Export conversations: /owner export [jid]",
            ]
        )

        return "\n".join(message_parts)

    def _format_phone_number(self, jid: str) -> str:
        """Format JID as readable phone number"""
        # Extract number from JID (format: 60123456789@s.whatsapp.net)
        number = jid.split("@")[0]

        # Add + prefix if not present
        if not number.startswith("+"):
            number = f"+{number}"

        return number

    def _log_notification(self, chat_jid: str, notification_type: NotificationType):
        """Log notification to database for tracking"""
        if not self.db:
            return

        try:
            self.db.table("owner_notifications").insert(
                {
                    "chat_jid": chat_jid,
                    "notification_type": notification_type.value,
                    "sent_at": datetime.now().isoformat(),
                    "owner_jid": self.owner_jid,
                }
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to log notification: {e}")

    def should_notify_daily_summary(self) -> bool:
        """Check if it's time to send daily summary"""
        if not self.settings["daily_summary_enabled"]:
            return False

        now = datetime.now()
        target_time = datetime.strptime(
            self.settings["daily_summary_time"], "%H:%M"
        ).time()

        # Check if current time matches target (within 5 minute window)
        current_time = now.time()
        target_dt = datetime.combine(now.date(), target_time)
        window_start = (target_dt - timedelta(minutes=2)).time()
        window_end = (target_dt + timedelta(minutes=3)).time()

        is_time = window_start <= current_time <= window_end

        # Check if not already sent today
        today = now.date()
        not_sent = self.last_daily_summary != today

        return is_time and not_sent

    def update_settings(self, settings: Dict):
        """Update notification settings"""
        self.settings.update(settings)
        logger.info(f"Notification settings updated: {settings}")


def enable_owner_notifications():
    """Feature flag check"""
    return os.getenv("ENABLE_OWNER_NOTIFICATIONS", "true").lower() == "true"
