#!/usr/bin/env python3
"""
Proactive Messaging System for Bijou AI
=========================================

Enables automated, scheduled, and campaign-based outbound messaging.
Core features:
1. Lead follow-up scheduler (auto-follow up after X days)
2. Silence detection & re-engagement (detect inactive customers)
3. Campaign messaging (broadcast to segments)

Author: W3J Bijou AI
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of proactive messages"""
    LEAD_FOLLOWUP = "lead_followup"
    SILENCE_REENGAGEMENT = "silence_reengagement"
    CAMPAIGN = "campaign"
    REMINDER = "reminder"
    CALL_REMINDER_24H = "call_reminder_24h"
    CALL_REMINDER_1H = "call_reminder_1h"
    OWNER_NOTIFICATION = "owner_notification"
    CUSTOM = "custom"


class MessageStatus(Enum):
    """Status of scheduled messages"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledMessage:
    """Represents a scheduled proactive message"""
    id: str
    tenant_id: str
    recipient: str  # chat_jid or phone number
    message_type: MessageType
    content: str
    scheduled_time: datetime
    status: MessageStatus
    created_at: datetime
    sent_at: Optional[datetime] = None
    metadata: Optional[Dict] = None


@dataclass
class SilenceRule:
    """Rules for detecting and re-engaging silent customers"""
    tenant_id: str
    silence_days: int  # Days of inactivity before triggering
    message_template: str
    enabled: bool = True
    last_check: Optional[datetime] = None


@dataclass
class Campaign:
    """Marketing campaign configuration"""
    id: str
    tenant_id: str
    name: str
    message_template: str
    target_segment: str  # "all", "active", "inactive", or custom filter
    scheduled_time: datetime
    status: MessageStatus
    recipients: List[str]
    sent_count: int = 0
    failed_count: int = 0


class ProactiveMessagingSystem:
    """
    Manages all proactive outbound messaging for Bijou AI.
    Handles scheduling, silence detection, and campaign execution.
    """

    def __init__(self, db_connection, channel_adapter):
        """
        Initialize the proactive messaging system.

        Args:
            db_connection: Database connection for persistence
            channel_adapter: Bridge/Telegram adapter for sending messages
        """
        self.db = db_connection
        self.channel = channel_adapter
        self.scheduled_messages: Dict[str, ScheduledMessage] = {}
        self.silence_rules: Dict[str, SilenceRule] = {}
        self.campaigns: Dict[str, Campaign] = {}
        self.running = False
        self._task: Optional[asyncio.Task] = None

        logger.info("ProactiveMessagingSystem initialized")

    async def start(self):
        """Start the proactive messaging scheduler"""
        if self.running:
            logger.warning("ProactiveMessagingSystem already running")
            return

        self.running = True

        # Load existing scheduled messages from database
        await self._load_scheduled_messages()

        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("✅ ProactiveMessagingSystem started")

    async def stop(self):
        """Stop the proactive messaging scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 ProactiveMessagingSystem stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop - checks every minute for messages to send"""
        logger.info("📅 Scheduler loop started")

        while self.running:
            try:
                await self._load_scheduled_messages()
                await self._process_scheduled_messages()
                await self._check_silence_rules()
                await self._process_campaigns()
                await self._process_lead_followups()

                # Sleep for 1 minute before next check
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Continue even on error

    async def _process_scheduled_messages(self):
        """Process and send scheduled messages that are due"""
        now = datetime.utcnow()

        messages_to_send = [
            msg for msg in self.scheduled_messages.values()
            if msg.status == MessageStatus.SCHEDULED and msg.scheduled_time <= now
        ]

        processed_count = 0
        for msg in messages_to_send:
            try:
                # Handle owner notifications specially
                if msg.recipient == "owner":
                    success = await self._send_owner_notification(msg.tenant_id, msg.content)
                else:
                    success = await self._send_message(msg.recipient, msg.content)

                if success:
                    msg.status = MessageStatus.SENT
                    msg.sent_at = now
                    processed_count += 1

                    # Log different types of reminders
                    if msg.message_type == MessageType.CALL_REMINDER_24H:
                        logger.info(f"✅ Sent 24h call reminder {msg.id} to {msg.recipient}")
                    elif msg.message_type == MessageType.CALL_REMINDER_1H:
                        logger.info(f"⏰ Sent 1h call reminder {msg.id} to {msg.recipient}")
                    elif msg.message_type == MessageType.OWNER_NOTIFICATION:
                        logger.info(f"📬 Sent owner notification {msg.id}")
                    else:
                        logger.info(f"✅ Sent scheduled message {msg.id} to {msg.recipient}")
                else:
                    msg.status = MessageStatus.FAILED
                    logger.error(f"❌ Failed to send message {msg.id}")

                # Update database
                await self._update_message_status(msg)

                # Remove from memory after processing
                if msg.id in self.scheduled_messages:
                    del self.scheduled_messages[msg.id]

            except Exception as e:
                logger.error(f"❌ Error sending message {msg.id}: {e}")
                msg.status = MessageStatus.FAILED
                await self._update_message_status(msg)

        if processed_count > 0:
            logger.info(f"📬 Processed {processed_count} call reminders and notifications")

        return processed_count

    async def _check_silence_rules(self):
        """Check for silent customers and trigger re-engagement"""
        now = datetime.utcnow()

        for rule in self.silence_rules.values():
            if not rule.enabled:
                continue

            # Skip if checked recently (within last hour)
            if rule.last_check and (now - rule.last_check).seconds < 3600:
                continue

            try:
                # Find silent customers for this tenant
                silent_customers = await self._find_silent_customers(
                    rule.tenant_id,
                    rule.silence_days
                )

                # Schedule re-engagement messages
                for customer in silent_customers:
                    await self.schedule_message(
                        tenant_id=rule.tenant_id,
                        recipient=customer,
                        message_type=MessageType.SILENCE_REENGAGEMENT,
                        content=rule.message_template,
                        delay_minutes=0  # Send immediately
                    )

                rule.last_check = now
                logger.info(
                    f"🔍 Silence check for tenant {rule.tenant_id}: "
                    f"found {len(silent_customers)} silent customers"
                )

            except Exception as e:
                logger.error(f"❌ Error checking silence rule: {e}")

    async def _process_campaigns(self):
        """Process and execute scheduled campaigns"""
        now = datetime.utcnow()

        campaigns_to_run = [
            campaign for campaign in self.campaigns.values()
            if campaign.status == MessageStatus.SCHEDULED and campaign.scheduled_time <= now
        ]

        for campaign in campaigns_to_run:
            try:
                logger.info(f"🚀 Starting campaign: {campaign.name}")

                # Send to all recipients
                for recipient in campaign.recipients:
                    try:
                        success = await self._send_message(recipient, campaign.message_template)
                        if success:
                            campaign.sent_count += 1
                        else:
                            campaign.failed_count += 1

                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.error(f"❌ Campaign send error for {recipient}: {e}")
                        campaign.failed_count += 1

                campaign.status = MessageStatus.SENT
                logger.info(
                    f"✅ Campaign '{campaign.name}' complete: "
                    f"{campaign.sent_count} sent, {campaign.failed_count} failed"
                )

                # Update database
                await self._update_campaign_status(campaign)

            except Exception as e:
                logger.error(f"❌ Error processing campaign {campaign.id}: {e}")

    async def _process_lead_followups(self) -> int:
        """Process due lead follow-up nudges from the follow_ups table."""
        if not hasattr(self.db, 'table'):
            return 0  # Supabase only

        try:
            now = datetime.utcnow().isoformat()
            result = self.db.table("follow_ups") \
                .select("*") \
                .eq("status", "pending") \
                .lte("scheduled_at", now) \
                .execute()  # noaudit - system scheduler: loads all tenants' due follow-ups; isolated per tenant_id

            due = result.data or []
            if not due:
                return 0

            sent_count = 0
            for row in due:
                chat_jid    = row.get("chat_jid")
                tenant_id   = row.get("tenant_id")
                lead_status = row.get("lead_status", "warm")
                row_id      = row.get("id")
                # Use custom message if set by tenant (stored in metadata jsonb), otherwise pick by lead status
                custom_msg  = (row.get("metadata") or {}).get("message_override")

                if not chat_jid or not row_id:
                    continue

                if custom_msg:
                    message = custom_msg
                elif lead_status == "hot":
                    message = (
                        "Hi again! \ud83d\udc4b\n\n"
                        "Just checking in \u2014 are you still interested? \ud83d\ude0a\n\n"
                        "Our team is ready to help you right now. "
                        "Reply *Yes* and I'll connect you with a specialist straight away! \ud83d\udcde"
                    )
                elif lead_status == "warm":
                    message = (
                        "Hi there! \ud83d\ude0a\n\n"
                        "Hope you're doing well! I noticed we haven't connected in a while.\n\n"
                        "I'm still here if you have any questions or need help. "
                        "Just reply and I'll pick up right where we left off! \ud83d\ude4c"
                    )
                else:
                    message = (
                        "Hi! \ud83d\udc4b\n\n"
                        "Just a quick follow-up from our last chat.\n\n"
                        "Feel free to reach out anytime if you need anything \u2014 happy to help! \ud83d\ude0a"
                    )

                try:
                    success = await self._send_message(chat_jid, message)
                    new_status = "sent" if success else "failed"
                    update = {"status": new_status, "message_sent_at": datetime.utcnow().isoformat()}
                    if not success:
                        update["notes"] = "send_message returned False"
                    self.db.table("follow_ups").update(update).eq("id", row_id).execute()
                    if success:
                        sent_count += 1
                        logger.info(f"\u2705 Lead follow-up sent to {chat_jid} (tenant={tenant_id}, status={lead_status})")
                    else:
                        logger.warning(f"\u26a0\ufe0f Lead follow-up failed for {chat_jid}")
                except Exception as send_err:
                    logger.error(f"\u274c Lead follow-up error for {chat_jid}: {send_err}")
                    self.db.table("follow_ups").update({
                        "status": "failed",
                        "notes": str(send_err)[:200],
                    }).eq("id", row_id).execute()

            if sent_count:
                logger.info(f"\ud83d\udce8 Sent {sent_count} lead follow-up nudges")
            return sent_count

        except Exception as e:
            logger.error(f"\u274c _process_lead_followups error: {e}")
            return 0

    async def schedule_message(
        self,
        tenant_id: str,
        recipient: str,
        message_type: MessageType,
        content: str,
        delay_minutes: int = 0,
        metadata: Optional[Dict] = None
    ) -> ScheduledMessage:
        """
        Schedule a message to be sent later.

        Args:
            tenant_id: Tenant ID
            recipient: Recipient chat_jid or phone
            message_type: Type of message
            content: Message content
            delay_minutes: Minutes to wait before sending (0 = immediate)
            metadata: Optional metadata

        Returns:
            ScheduledMessage object
        """
        now = datetime.utcnow()
        scheduled_time = now + timedelta(minutes=delay_minutes)

        msg = ScheduledMessage(
            id=f"{tenant_id}_{recipient}_{int(now.timestamp())}",
            tenant_id=tenant_id,
            recipient=recipient,
            message_type=message_type,
            content=content,
            scheduled_time=scheduled_time,
            status=MessageStatus.SCHEDULED,
            created_at=now,
            metadata=metadata
        )

        self.scheduled_messages[msg.id] = msg
        await self._save_scheduled_message(msg)

        logger.info(
            f"📅 Scheduled {message_type.value} message for {recipient} "
            f"at {scheduled_time} ({delay_minutes}min delay)"
        )

        return msg

    async def create_campaign(
        self,
        tenant_id: str,
        name: str,
        message_template: str,
        target_segment: str,
        scheduled_time: datetime,
        recipients: Optional[List[str]] = None
    ) -> Campaign:
        """
        Create a new marketing campaign.

        Args:
            tenant_id: Tenant ID
            name: Campaign name
            message_template: Message template
            target_segment: Target segment ("all", "active", "inactive")
            scheduled_time: When to send
            recipients: Optional explicit recipient list

        Returns:
            Campaign object
        """
        # If no recipients provided, fetch based on segment
        if recipients is None:
            recipients = await self._get_segment_recipients(tenant_id, target_segment)

        campaign = Campaign(
            id=f"campaign_{tenant_id}_{int(datetime.utcnow().timestamp())}",
            tenant_id=tenant_id,
            name=name,
            message_template=message_template,
            target_segment=target_segment,
            scheduled_time=scheduled_time,
            status=MessageStatus.SCHEDULED,
            recipients=recipients
        )

        self.campaigns[campaign.id] = campaign
        await self._save_campaign(campaign)

        logger.info(
            f"📢 Created campaign '{name}' for {len(recipients)} recipients, "
            f"scheduled for {scheduled_time}"
        )

        return campaign

    async def set_silence_rule(
        self,
        tenant_id: str,
        silence_days: int,
        message_template: str
    ):
        """
        Set up a silence detection rule for a tenant.

        Args:
            tenant_id: Tenant ID
            silence_days: Days of inactivity before triggering
            message_template: Message to send when re-engaging
        """
        rule = SilenceRule(
            tenant_id=tenant_id,
            silence_days=silence_days,
            message_template=message_template,
            enabled=True
        )

        self.silence_rules[tenant_id] = rule
        await self._save_silence_rule(rule)

        logger.info(
            f"🔕 Silence rule set for tenant {tenant_id}: "
            f"{silence_days} days silence → re-engage"
        )

    # ==================== HELPER METHODS ====================

    async def _load_scheduled_messages(self):
        """Load scheduled messages from database that are due for processing"""
        try:
            now = datetime.utcnow()

            if hasattr(self.db, 'table'):  # Supabase
                try:
                    result = self.db.table("scheduled_messages").select("*").eq(  # noaudit - system scheduler: loads all tenants' due messages; each processed per-tenant via msg.tenant_id
                        "status", MessageStatus.SCHEDULED.value
                    ).lte("scheduled_time", now.isoformat()).execute()
                except Exception as db_error:
                    if "could not find" in str(db_error).lower():
                        logger.warning(f"⚠️ Skipping scheduled message load due to schema issue: {db_error}")
                        return []  # Return empty list until schema is fixed
                    else:
                        raise db_error

                for row in result.data:
                    if row["id"] not in self.scheduled_messages:
                        # Convert to ScheduledMessage object
                        msg = ScheduledMessage(
                            id=row["id"],
                            tenant_id=row["tenant_id"],
                            recipient=row["recipient"],
                            message_type=MessageType(row["message_type"]),
                            content=row["content"],
                            scheduled_time=datetime.fromisoformat(row["scheduled_time"].replace('Z', '+00:00')),
                            status=MessageStatus(row["status"]),
                            created_at=datetime.fromisoformat(row["created_at"].replace('Z', '+00:00')),
                            sent_at=datetime.fromisoformat(row["sent_at"].replace('Z', '+00:00')) if row["sent_at"] else None,
                            metadata=json.loads(row["metadata"]) if row["metadata"] else None
                        )
                        self.scheduled_messages[msg.id] = msg

            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    SELECT * FROM scheduled_messages
                    WHERE status = ? AND scheduled_time <= ?
                    """,
                    (MessageStatus.SCHEDULED.value, now.isoformat())
                )

                for row in cursor.fetchall():
                    msg_id = row[0]
                    if msg_id not in self.scheduled_messages:
                        # Convert to ScheduledMessage object
                        msg = ScheduledMessage(
                            id=row[0],
                            tenant_id=row[1],
                            recipient=row[2],
                            message_type=MessageType(row[3]),
                            content=row[4],
                            scheduled_time=datetime.fromisoformat(row[5]),
                            status=MessageStatus(row[6]),
                            created_at=datetime.fromisoformat(row[7]),
                            sent_at=datetime.fromisoformat(row[8]) if row[8] else None,
                            metadata=json.loads(row[9]) if row[9] else None
                        )
                        self.scheduled_messages[msg.id] = msg

            logger.debug(f"📥 Loaded {len(self.scheduled_messages)} scheduled messages for processing")

        except Exception as e:
            logger.error(f"❌ Error loading scheduled messages: {e}")

    async def _send_owner_notification(self, tenant_id: str, message: str) -> bool:
        """Send notification to business owner"""
        try:
            # Get tenant information to find owner's JID
            if hasattr(self.db, 'table'):  # Supabase
                result = self.db.table("tenants").select("whatsapp_jid").eq("id", tenant_id).execute()
                if result.data and len(result.data) > 0:
                    owner_jid = result.data[0]["whatsapp_jid"]
                    success = await self._send_message(owner_jid, message)
                    if success:
                        logger.info(f"📬 Sent owner notification to {owner_jid}")
                    return success
            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute("SELECT whatsapp_jid FROM tenants WHERE id = ?", (tenant_id,))
                result = cursor.fetchone()
                if result:
                    owner_jid = result[0]
                    success = await self._send_message(owner_jid, message)
                    if success:
                        logger.info(f"📬 Sent owner notification to {owner_jid}")
                    return success

            logger.warning(f"⚠️ No owner JID found for tenant {tenant_id}")
            return False

        except Exception as e:
            logger.error(f"❌ Error sending owner notification: {e}")
            return False

    async def schedule_call_reminders(
        self,
        tenant_id: str,
        booking_id: str,
        customer_jid: str,
        customer_name: str,
        call_time: datetime,
        call_type: str,
        duration_minutes: int,
        business_name: str
    ):
        """
        Schedule call reminder messages for a booking.

        Args:
            tenant_id: Tenant ID
            booking_id: Call booking ID
            customer_jid: Customer WhatsApp JID
            customer_name: Customer name
            call_time: Scheduled call time
            call_type: Type of call
            duration_minutes: Call duration
            business_name: Business name for branding
        """
        try:
            now = datetime.utcnow()
            formatted_date = call_time.strftime("%A, %B %d, %Y")
            formatted_time = call_time.strftime("%I:%M %p UTC")

            # 24-hour reminder
            reminder_24h_time = call_time - timedelta(hours=24)
            if reminder_24h_time > now:
                reminder_24h_delay = int((reminder_24h_time - now).total_seconds() / 60)
                reminder_24h_msg = f"""🔔 *Reminder: Call Tomorrow*

Hi {customer_name},

This is a friendly reminder that you have a {call_type.replace('_', ' ').title()} call scheduled with {business_name} tomorrow:

📅 *Date:* {formatted_date}
🕐 *Time:* {formatted_time}
⏰ *Duration:* {duration_minutes} minutes

Please make sure you're available and ready for the call. We look forward to connecting with you!

📞 *Need to reschedule?* Contact us as soon as possible.
💼 *Preparation:* Please have any relevant materials ready.

Best regards,
{business_name}"""

                await self.schedule_message(
                    tenant_id=tenant_id,
                    recipient=customer_jid,
                    message_type=MessageType.CALL_REMINDER_24H,
                    content=reminder_24h_msg,
                    delay_minutes=reminder_24h_delay,
                    metadata={"booking_id": booking_id, "reminder_type": "24h"}
                )
                logger.info(f"📅 Scheduled 24h reminder for booking {booking_id}")

            # 1-hour reminder
            reminder_1h_time = call_time - timedelta(hours=1)
            if reminder_1h_time > now:
                reminder_1h_delay = int((reminder_1h_time - now).total_seconds() / 60)
                reminder_1h_msg = f"""⏰ *Reminder: Call Starting Soon*

Hi {customer_name},

Your {call_type.replace('_', ' ').title()} call with {business_name} is starting in 1 hour:

🕐 *Time:* {formatted_time}
⏰ *Duration:* {duration_minutes} minutes

Please be ready and available. We'll initiate the call at the scheduled time.

🎯 *Final Preparations:*
• Ensure you have a stable internet connection
• Have your questions or topics ready
• Join the call promptly at the scheduled time

Thank you!
{business_name}"""

                await self.schedule_message(
                    tenant_id=tenant_id,
                    recipient=customer_jid,
                    message_type=MessageType.CALL_REMINDER_1H,
                    content=reminder_1h_msg,
                    delay_minutes=reminder_1h_delay,
                    metadata={"booking_id": booking_id, "reminder_type": "1h"}
                )
                logger.info(f"⏰ Scheduled 1h reminder for booking {booking_id}")

                # Schedule owner notification (1 hour before call)
                owner_notification = f"""📞 *Upcoming Call - {business_name}*

You have a call starting in 1 hour:

👤 *Customer:* {customer_name}
📅 *Time:* {formatted_time}
⏰ *Duration:* {duration_minutes} minutes
📋 *Type:* {call_type.replace('_', ' ').title()}

The customer has been reminded and should be ready for the call.

🔗 *Booking ID:* {booking_id}"""

                await self.schedule_message(
                    tenant_id=tenant_id,
                    recipient="owner",  # Special recipient for owner notifications
                    message_type=MessageType.OWNER_NOTIFICATION,
                    content=owner_notification,
                    delay_minutes=reminder_1h_delay,
                    metadata={"booking_id": booking_id, "notification_type": "call_starting"}
                )
                logger.info(f"📬 Scheduled owner notification for booking {booking_id}")

        except Exception as e:
            logger.error(f"❌ Error scheduling call reminders: {e}")

    async def send_daily_call_digest(self, tenant_id: str):
        """Send daily digest of upcoming calls to business owner"""
        try:
            now = datetime.utcnow()
            tomorrow = now + timedelta(days=1)

            # Get upcoming calls for tomorrow
            if hasattr(self.db, 'table'):  # Supabase
                result = self.db.table("call_bookings").select("*").eq(
                    "tenant_id", tenant_id
                ).gte("scheduled_time", now.isoformat()).lt(
                    "scheduled_time", tomorrow.isoformat()
                ).eq("status", "scheduled").execute()

                upcoming_calls = result.data
            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    SELECT * FROM call_bookings
                    WHERE tenant_id = ? AND scheduled_time >= ? AND scheduled_time < ?
                    AND status = 'scheduled'
                    ORDER BY scheduled_time ASC
                    """,
                    (tenant_id, now.isoformat(), tomorrow.isoformat())
                )
                upcoming_calls = cursor.fetchall()

            if not upcoming_calls:
                return  # No calls to report

            # Get business name
            business_name = "Your Business"
            if hasattr(self.db, 'table'):  # Supabase
                result = self.db.table("tenants").select("name").eq("id", tenant_id).execute()
                if result.data:
                    business_name = result.data[0]["name"]

            # Build digest message
            digest_msg = f"""📊 *Daily Call Digest - {business_name}*

You have {len(upcoming_calls)} call(s) scheduled for today:

"""

            for i, call in enumerate(upcoming_calls, 1):
                if hasattr(self.db, 'table'):  # Supabase data
                    call_time = datetime.fromisoformat(call["scheduled_time"].replace('Z', '+00:00'))
                    customer_name = call["customer_name"]
                    call_type = call["call_type"]
                    duration = call["duration_minutes"]
                else:  # SQLite data
                    call_time = datetime.fromisoformat(call[5])  # scheduled_time
                    customer_name = call[3]  # customer_name
                    call_type = call[7]  # call_type
                    duration = call[6]  # duration_minutes

                formatted_time = call_time.strftime("%I:%M %p")

                digest_msg += f"""📞 *Call #{i}*
• Customer: {customer_name}
• Time: {formatted_time}
• Type: {call_type.replace('_', ' ').title()}
• Duration: {duration} minutes

"""

            digest_msg += """🎯 *Reminder:*
All customers will receive automatic reminders 24h and 1h before their calls.

Have a great day!
Bijou AI"""

            # Send digest to owner
            await self._send_owner_notification(tenant_id, digest_msg)
            logger.info(f"📊 Sent daily call digest for tenant {tenant_id} ({len(upcoming_calls)} calls)")

        except Exception as e:
            logger.error(f"❌ Error sending daily call digest: {e}")

    async def _send_message(self, recipient: str, content: str) -> bool:
        """Send a message via the channel adapter"""
        try:
            return self.channel.send_text(recipient, content)
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")
            return False

    async def _find_silent_customers(self, tenant_id: str, days: int) -> List[str]:
        """Find customers who haven't messaged in X days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            if hasattr(self.db, 'table'):  # Supabase
                result = self.db.table("customer_activity").select("customer_jid").eq(
                    "tenant_id", tenant_id
                ).lt("last_message_at", cutoff_date.isoformat()).execute()
                return [row["customer_jid"] for row in result.data]
            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    SELECT customer_jid FROM customer_activity
                    WHERE tenant_id = ? AND last_message_at < ?
                    """,
                    (tenant_id, cutoff_date.isoformat())
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error finding silent customers: {e}")
            return []

    async def _get_segment_recipients(self, tenant_id: str, segment: str) -> List[str]:
        """Get recipients for a target segment"""
        try:
            if segment == "all":
                # Get all customers for this tenant
                if hasattr(self.db, 'table'):  # Supabase
                    result = self.db.table("customer_activity").select("customer_jid").eq(
                        "tenant_id", tenant_id
                    ).execute()
                    return [row["customer_jid"] for row in result.data]
                else:  # SQLite
                    cursor = self.db.cursor()
                    cursor.execute(
                        "SELECT customer_jid FROM customer_activity WHERE tenant_id = ?",
                        (tenant_id,)
                    )
                    return [row[0] for row in cursor.fetchall()]

            elif segment == "active":
                # Active in last 7 days
                cutoff = datetime.utcnow() - timedelta(days=7)
                if hasattr(self.db, 'table'):  # Supabase
                    result = self.db.table("customer_activity").select("customer_jid").eq(
                        "tenant_id", tenant_id
                    ).gt("last_message_at", cutoff.isoformat()).execute()
                    return [row["customer_jid"] for row in result.data]
                else:  # SQLite
                    cursor = self.db.cursor()
                    cursor.execute(
                        """
                        SELECT customer_jid FROM customer_activity
                        WHERE tenant_id = ? AND last_message_at > ?
                        """,
                        (tenant_id, cutoff.isoformat())
                    )
                    return [row[0] for row in cursor.fetchall()]

            elif segment == "inactive":
                # Inactive for 30+ days
                cutoff = datetime.utcnow() - timedelta(days=30)
                if hasattr(self.db, 'table'):  # Supabase
                    result = self.db.table("customer_activity").select("customer_jid").eq(
                        "tenant_id", tenant_id
                    ).lt("last_message_at", cutoff.isoformat()).execute()
                    return [row["customer_jid"] for row in result.data]
                else:  # SQLite
                    cursor = self.db.cursor()
                    cursor.execute(
                        """
                        SELECT customer_jid FROM customer_activity
                        WHERE tenant_id = ? AND last_message_at < ?
                        """,
                        (tenant_id, cutoff.isoformat())
                    )
                    return [row[0] for row in cursor.fetchall()]

            return []
        except Exception as e:
            logger.error(f"❌ Error getting segment recipients: {e}")
            return []

    async def _save_scheduled_message(self, msg: ScheduledMessage):
        """Save scheduled message to database"""
        try:
            data = {
                "id": msg.id,
                "tenant_id": msg.tenant_id,
                "recipient": msg.recipient,
                "message_type": msg.message_type.value,
                "content": msg.content,
                "scheduled_time": msg.scheduled_time.isoformat(),
                "status": msg.status.value,
                "created_at": msg.created_at.isoformat(),
                "metadata": json.dumps(msg.metadata) if msg.metadata else None
            }

            if hasattr(self.db, 'table'):  # Supabase
                try:
                    self.db.table("scheduled_messages").upsert(data).execute()
                except Exception as db_error:
                    if "could not find" in str(db_error).lower():
                        logger.warning(f"⚠️ Skipping message save due to schema issue: {db_error}")
                        return  # Skip save until schema is fixed
                    else:
                        raise db_error
            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO scheduled_messages
                    (id, tenant_id, recipient, message_type, content, scheduled_time, status, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (data["id"], data["tenant_id"], data["recipient"], data["message_type"],
                     data["content"], data["scheduled_time"], data["status"], data["created_at"],
                     data["metadata"])
                )
                self.db.commit()
        except Exception as e:
            logger.error(f"❌ Error saving scheduled message: {e}")

    async def _update_message_status(self, msg: ScheduledMessage):
        """Update message status in database"""
        try:
            if hasattr(self.db, 'table'):  # Supabase
                try:
                    self.db.table("scheduled_messages").update({
                        "status": msg.status.value,
                        "sent_at": msg.sent_at.isoformat() if msg.sent_at else None
                    }).eq("tenant_id", msg.tenant_id).eq("id", msg.id).execute()
                except Exception as db_error:
                    if "could not find" in str(db_error).lower():
                        logger.warning(f"⚠️ Skipping message status update due to schema issue: {db_error}")
                        return  # Skip update until schema is fixed
                    else:
                        raise db_error
            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute(
                    "UPDATE scheduled_messages SET status = ?, sent_at = ? WHERE id = ?",
                    (msg.status.value, msg.sent_at.isoformat() if msg.sent_at else None, msg.id)
                )
                self.db.commit()
        except Exception as e:
            logger.error(f"❌ Error updating message status: {e}")

    async def _save_campaign(self, campaign: Campaign):
        """Save campaign to database"""
        try:
            data = {
                "id": campaign.id,
                "tenant_id": campaign.tenant_id,
                "name": campaign.name,
                "message_template": campaign.message_template,
                "target_segment": campaign.target_segment,
                "scheduled_time": campaign.scheduled_time.isoformat(),
                "status": campaign.status.value,
                "recipients": json.dumps(campaign.recipients),
                "sent_count": campaign.sent_count,
                "failed_count": campaign.failed_count
            }

            if hasattr(self.db, 'table'):  # Supabase
                self.db.table("campaigns").upsert(data).execute()
            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO campaigns
                    (id, tenant_id, name, message_template, target_segment, scheduled_time,
                     status, recipients, sent_count, failed_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (data["id"], data["tenant_id"], data["name"], data["message_template"],
                     data["target_segment"], data["scheduled_time"], data["status"],
                     data["recipients"], data["sent_count"], data["failed_count"])
                )
                self.db.commit()
        except Exception as e:
            logger.error(f"❌ Error saving campaign: {e}")

    async def _update_campaign_status(self, campaign: Campaign):
        """Update campaign status in database"""
        try:
            if hasattr(self.db, 'table'):  # Supabase
                self.db.table("campaigns").update({
                    "status": campaign.status.value,
                    "sent_count": campaign.sent_count,
                    "failed_count": campaign.failed_count
                }).eq("tenant_id", campaign.tenant_id).eq("id", campaign.id).execute()
            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    UPDATE campaigns
                    SET status = ?, sent_count = ?, failed_count = ?
                    WHERE id = ?
                    """,
                    (campaign.status.value, campaign.sent_count, campaign.failed_count, campaign.id)
                )
                self.db.commit()
        except Exception as e:
            logger.error(f"❌ Error updating campaign status: {e}")

    async def _save_silence_rule(self, rule: SilenceRule):
        """Save silence rule to database"""
        try:
            data = {
                "tenant_id": rule.tenant_id,
                "silence_days": rule.silence_days,
                "message_template": rule.message_template,
                "enabled": rule.enabled,
                "last_check": rule.last_check.isoformat() if rule.last_check else None
            }

            if hasattr(self.db, 'table'):  # Supabase
                self.db.table("silence_rules").upsert(data).execute()
            else:  # SQLite
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO silence_rules
                    (tenant_id, silence_days, message_template, enabled, last_check)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (data["tenant_id"], data["silence_days"], data["message_template"],
                     data["enabled"], data["last_check"])
                )
                self.db.commit()
        except Exception as e:
            logger.error(f"❌ Error saving silence rule: {e}")
