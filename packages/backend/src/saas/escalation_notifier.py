"""
Escalation Notifier - Multi-Channel Agent Notifications
========================================================

Sends notifications to human agents via multiple channels when
escalations are created or require attention.

Channels:
- Email (Gmail API)
- WhatsApp (via bridge)
- SMS (Twilio)
- Telegram (Bot API)

Author: W3J Consulting
Date: 2026-02-11
Phase: 5 - Human Escalation Enhancements
"""

import os
import asyncio
import smtplib
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

# Use loguru if available, otherwise fall back to standard logging
try:
    from loguru import logger
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class NotificationChannel(str, Enum):
    """Supported notification channels"""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    TELEGRAM = "telegram"


class EscalationNotifier:
    """
    Multi-channel notification service for escalations

    Features:
    - Multiple notification channels
    - Retry mechanism for failed notifications
    - Template-based messages
    - Notification tracking
    - Priority-based routing
    """

    def __init__(
        self,
        supabase_client,
        whatsapp_bridge_url: Optional[str] = None,
        twilio_client=None,
        telegram_bot_token: Optional[str] = None
    ):
        """
        Initialize notifier

        Args:
            supabase_client: Supabase client
            whatsapp_bridge_url: WhatsApp bridge URL
            twilio_client: Twilio client (optional)
            telegram_bot_token: Telegram bot token (optional)
        """
        self.db = supabase_client
        self.whatsapp_bridge_url = whatsapp_bridge_url or os.getenv("BRIDGE_URL")
        self.twilio = twilio_client
        self.telegram_token = telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")

        # Track which channels are available
        self.available_channels = {
            NotificationChannel.EMAIL: True,  # Gmail API assumed available
            NotificationChannel.WHATSAPP: bool(self.whatsapp_bridge_url),
            NotificationChannel.SMS: bool(self.twilio),
            NotificationChannel.TELEGRAM: bool(self.telegram_token)
        }

        logger.info(f"Notifier initialized: {self.available_channels}")

    async def notify_agent(
        self,
        escalation_id: str,
        tenant_id: str,
        agent_data: Dict,
        escalation_data: Dict,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """
        Notify agent about escalation via specified channels

        Args:
            escalation_id: Escalation ID
            tenant_id: Tenant ID
            agent_data: Agent information (email, phone, etc.)
            escalation_data: Escalation details
            channels: List of channels to use (or use all available)

        Returns:
            Dict mapping channel to success status
        """
        # Determine channels to use
        if not channels:
            # Use all available channels based on agent preferences
            channels = self._get_agent_notification_channels(agent_data)

        results = {}

        # Try each channel with retry logic
        for channel in channels:
            if not self.available_channels.get(channel):
                logger.warning(f"Channel {channel} not available, skipping")
                results[channel.value] = False
                continue

            # Create notification context
            context = self._build_notification_context(
                escalation_data,
                agent_data
            )

            # Send with retry logic (max 3 attempts)
            success, error_msg = await self._send_with_retry(
                channel,
                agent_data,
                context,
                escalation_id,
                tenant_id
            )

            results[channel.value] = success

        # Update escalation with notification info
        await self._update_escalation_notifications(
            escalation_id,
            tenant_id,
            channels,
            results
        )

        return results

    async def _send_with_retry(
        self,
        channel: NotificationChannel,
        agent_data: Dict,
        context: Dict,
        escalation_id: str,
        tenant_id: str,
        max_retries: int = 3
    ) -> tuple[bool, Optional[str]]:
        """
        Send notification with exponential backoff retry logic

        Retry delays: 1s, 2s, 4s

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        last_error = None
        recipient = agent_data.get(self._get_recipient_field(channel), "unknown")

        for attempt in range(max_retries):
            try:
                # Send notification based on channel
                if channel == NotificationChannel.EMAIL:
                    success = await self._send_email(agent_data, context)
                elif channel == NotificationChannel.WHATSAPP:
                    success = await self._send_whatsapp(agent_data, context)
                elif channel == NotificationChannel.SMS:
                    success = await self._send_sms(agent_data, context)
                elif channel == NotificationChannel.TELEGRAM:
                    success = await self._send_telegram(agent_data, context)
                else:
                    success = False

                # Track attempt in database
                await self._track_notification(
                    escalation_id,
                    tenant_id,
                    channel.value,
                    recipient,
                    success,
                    error_message=last_error,
                    retry_count=attempt
                )

                if success:
                    logger.info(f"✅ {channel.value} notification sent to {recipient} (attempt {attempt + 1})")
                    return (True, None)

                # If not successful and not last attempt, retry with backoff
                if attempt < max_retries - 1:
                    delay = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(f"⚠️ {channel.value} failed, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)

            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ {channel.value} notification error (attempt {attempt + 1}): {e}")

                # Track failed attempt
                await self._track_notification(
                    escalation_id,
                    tenant_id,
                    channel.value,
                    recipient,
                    False,
                    error_message=str(e),
                    retry_count=attempt
                )

                # Retry with exponential backoff
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    await asyncio.sleep(delay)

        logger.error(f"❌ {channel.value} notification failed after {max_retries} attempts")
        return (False, last_error)

    async def send_escalation_notification(
        self,
        tenant_id: str,
        escalation_id: str,
        escalation_data: Dict,
        customer_name: str = "Customer",
        customer_phone: str = "",
        escalation_reason: str = "Customer needs assistance",
        priority: str = "normal"
    ) -> Dict[str, bool]:
        """
        Convenience method to send escalation notification using business profile data

        Fetches handover contacts from business_profiles table and sends notifications

        Args:
            tenant_id: Tenant ID
            escalation_id: Escalation ID
            escalation_data: Full escalation data
            customer_name: Customer name (optional)
            customer_phone: Customer phone (optional)
            escalation_reason: Reason for escalation
            priority: Priority level (normal, high, urgent)

        Returns:
            Dict mapping channel to success status
        """
        try:
            # Fetch business profile for handover contacts
            profile_response = self.db.table("business_profiles") \
                .select("*") \
                .eq("tenant_id", tenant_id) \
                .execute()

            if not profile_response.data or len(profile_response.data) == 0:
                logger.warning(f"⚠️ No business profile found for tenant {tenant_id}. Cannot send notifications.")
                return {"error": False}

            profile = profile_response.data[0]
            handover_contacts = profile.get("handover_contacts", [])

            if not handover_contacts or len(handover_contacts) == 0:
                logger.warning(f"⚠️ No handover contacts configured for tenant {tenant_id}")
                return {"error": False}

            # Use first handover contact
            primary_contact = handover_contacts[0]

            agent_data = {
                "agent_name": primary_contact.get("name", profile.get("owner_name", "Agent")),
                "email": primary_contact.get("email"),
                "phone_number": primary_contact.get("phone"),
                "whatsapp_number": primary_contact.get("phone"),  # Use same number for WhatsApp
                "notification_preferences": ["email", "whatsapp"]  # Default to email + WhatsApp
            }

            # Send notification
            return await self.notify_agent(
                escalation_id,
                tenant_id,
                agent_data,
                escalation_data
            )

        except Exception as e:
            logger.error(f"❌ Error sending escalation notification: {e}")
            return {"error": False}

    def _get_agent_notification_channels(self, agent_data: Dict) -> List[NotificationChannel]:
        """Determine which channels to use for agent"""
        channels = []

        # Email is always included if available
        if agent_data.get("email"):
            channels.append(NotificationChannel.EMAIL)

        # Check agent notification preferences
        preferences = agent_data.get("notification_preferences", [])

        if "whatsapp" in preferences and agent_data.get("whatsapp_number"):
            channels.append(NotificationChannel.WHATSAPP)

        if "sms" in preferences and agent_data.get("phone_number"):
            channels.append(NotificationChannel.SMS)

        if "telegram" in preferences and agent_data.get("telegram_id"):
            channels.append(NotificationChannel.TELEGRAM)

        # Default to WhatsApp + Email if no preferences set
        if not channels:
            if agent_data.get("email"):
                channels.append(NotificationChannel.EMAIL)
            if agent_data.get("whatsapp_number"):
                channels.append(NotificationChannel.WHATSAPP)

        return channels

    def _build_notification_context(
        self,
        escalation_data: Dict,
        agent_data: Dict
    ) -> Dict:
        """Build notification message context"""
        context = {
            "customer_jid": escalation_data.get("chat_jid", "Unknown"),
            "customer_name": escalation_data.get("customer_context", {}).get("name", "Customer"),
            "reason": escalation_data.get("reason", "No reason provided"),
            "priority": escalation_data.get("priority", "normal").upper(),
            "escalation_type": escalation_data.get("escalation_type", "general"),
            "escalation_id": escalation_data.get("id"),
            "agent_name": agent_data.get("agent_name", "Agent"),
            "conversation_preview": self._get_conversation_preview(escalation_data),
            "created_at": escalation_data.get("created_at"),
            "dashboard_url": self._get_dashboard_url(escalation_data.get("id"))
        }

        return context

    def _get_conversation_preview(self, escalation_data: Dict) -> str:
        """Extract last few messages for context"""
        conversation_context = escalation_data.get("conversation_context", {})
        messages = conversation_context.get("recent_messages", [])

        if not messages:
            return "No recent messages available"

        # Get last 3 messages
        preview_lines = []
        for msg in messages[-3:]:
            sender = "Customer" if not msg.get("is_from_me") else "Bot"
            text = msg.get("message_content", "")[:100]  # Truncate long messages
            preview_lines.append(f"{sender}: {text}")

        return "\n".join(preview_lines)

    def _get_dashboard_url(self, escalation_id: str) -> str:
        """Generate dashboard URL for escalation"""
        base_url = os.getenv("DASHBOARD_URL", "https://mybijou.xyz/dashboard")
        return f"{base_url}/escalations/{escalation_id}"

    async def _send_email(self, agent_data: Dict, context: Dict) -> bool:
        """
        Send email notification via SMTP

        Uses environment variables:
        - SMTP_HOST (default: smtp.gmail.com)
        - SMTP_PORT (default: 587)
        - SMTP_USER
        - SMTP_PASSWORD
        - SMTP_USE_TLS (default: true) - TLS on port 587
        - SMTP_USE_SSL (default: false) - SSL on port 465
        - EMAIL_FROM (default: same as SMTP_USER)
        """
        recipient = agent_data.get("email")
        if not recipient:
            logger.warning("No email address provided for agent")
            return False

        # Get SMTP credentials from environment
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        smtp_use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
        email_from = os.getenv("EMAIL_FROM", smtp_user)

        if not smtp_user or not smtp_password:
            logger.warning("⚠️ SMTP credentials not configured. Email notifications disabled.")
            return False

        try:
            # Build email content
            subject = f"[URGENT] Customer Escalation - {context['customer_name']}"

            # HTML body for better formatting
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #e74c3c; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .detail-box {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #e74c3c; }}
        .detail-box strong {{ color: #e74c3c; }}
        .conversation {{ background-color: #fff; border: 1px solid #ddd; padding: 15px; margin: 10px 0; font-family: monospace; white-space: pre-wrap; }}
        .action-button {{ display: inline-block; padding: 12px 24px; background-color: #e74c3c; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 Customer Escalation Alert</h1>
    </div>
    <div class="content">
        <p>Hello {context['agent_name']},</p>
        <p>A customer needs human assistance:</p>

        <div class="detail-box">
            <strong>Customer:</strong> {context['customer_name']}<br>
            <strong>Phone:</strong> {context['customer_jid']}<br>
            <strong>Issue:</strong> {context['reason']}<br>
            <strong>Priority:</strong> {context['priority']}<br>
            <strong>Type:</strong> {context['escalation_type']}
        </div>

        <h3>Recent Conversation:</h3>
        <div class="conversation">{context['conversation_preview']}</div>

        <a href="{context['dashboard_url']}" class="action-button">View in Dashboard →</a>

        <div class="footer">
            This is an automated notification from Bijou AI.<br>
            Escalation ID: {context['escalation_id']}<br>
            Sent: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        </div>
    </div>
</body>
</html>
"""

            # Plain text fallback
            text_body = f"""
[URGENT] Customer Escalation

A customer needs human assistance:

Customer: {context['customer_name']}
Phone: {context['customer_jid']}
Issue: {context['reason']}
Priority: {context['priority']}

Recent Conversation:
{context['conversation_preview']}

View conversation: {context['dashboard_url']}

This is an automated notification from Bijou AI.
"""

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = email_from
            msg['To'] = recipient
            msg['X-Priority'] = '1' if context['priority'].upper() == 'URGENT' else '3'

            # Attach both versions
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            await self._send_smtp_email(
                smtp_host, smtp_port, smtp_user, smtp_password, msg,
                smtp_use_tls=smtp_use_tls,
                smtp_use_ssl=smtp_use_ssl
            )

            logger.info(f"✅ Email notification sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"❌ Error sending email to {recipient}: {e}")
            return False

    async def _send_smtp_email(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        message: MIMEMultipart,
        smtp_use_tls: bool = True,
        smtp_use_ssl: bool = False
    ) -> None:
        """
        Send email via SMTP with TLS/SSL support

        Supports:
        - Port 587 with STARTTLS (smtp_use_tls=true)
        - Port 465 with SSL (smtp_use_ssl=true)
        - Port 25 plaintext (both false)

        Runs in thread pool since smtplib is synchronous
        """
        def _send_sync():
            """Synchronous SMTP send"""
            try:
                # Choose connection method based on SSL/TLS flags
                if smtp_use_ssl:
                    # Port 465: Use SMTP_SSL (implicit SSL)
                    server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
                else:
                    # Port 587 or 25: Use SMTP (plaintext or explicit TLS)
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)

                with server as conn:
                    # Upgrade to TLS if requested (port 587)
                    if smtp_use_tls and not smtp_use_ssl:
                        conn.starttls()

                    # Authenticate
                    conn.login(smtp_user, smtp_password)

                    # Send message
                    conn.send_message(message)

            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"❌ SMTP Authentication failed to {smtp_host}:{smtp_port}: {e}")
                raise
            except smtplib.SMTPException as e:
                logger.error(f"❌ SMTP error sending to {smtp_host}:{smtp_port}: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ Unexpected error sending email: {e}")
                raise

        # Run synchronous SMTP in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_sync)

    async def _send_whatsapp(self, agent_data: Dict, context: Dict) -> bool:
        """Send WhatsApp notification via bridge"""
        try:
            import httpx

            recipient = agent_data.get("whatsapp_number")
            if not recipient:
                logger.warning("No WhatsApp number for agent")
                return False

            # Build WhatsApp message
            message = f"""🚨 *New Escalation Alert*

*Priority:* {context['priority']}
*Customer:* {context['customer_name']}
*Reason:* {context['reason']}

*Recent Messages:*
{context['conversation_preview']}

Reply '@bijou resume' when resolved.

Dashboard: {context['dashboard_url']}
"""

            # Send via bridge
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.whatsapp_bridge_url}/send",
                    json={
                        "to": recipient,
                        "message": message
                    },
                    timeout=10.0
                )

                response.raise_for_status()
                logger.info(f"WhatsApp notification sent to {recipient}")
                return True

        except Exception as e:
            logger.error(f"Error sending WhatsApp: {e}")
            return False

    async def _send_sms(self, agent_data: Dict, context: Dict) -> bool:
        """
        Send SMS notification via Twilio (optional fallback)

        Uses environment variables:
        - TWILIO_ACCOUNT_SID
        - TWILIO_AUTH_TOKEN
        - TWILIO_FROM_NUMBER
        """
        recipient = agent_data.get("phone_number")
        if not recipient:
            logger.warning("No phone number for agent")
            return False

        # Get Twilio credentials from environment
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not all([account_sid, auth_token, from_number]):
            logger.warning("⚠️ Twilio credentials not configured. SMS notifications disabled.")
            return False

        try:
            import httpx

            # Build SMS message (160 chars max for single SMS)
            message = f"🚨 Customer escalation: {context['customer_name']} needs help. Check dashboard."

            # Twilio API endpoint
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

            # Create Basic Auth header
            auth_str = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_str}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            # Send SMS via Twilio REST API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    data={
                        "From": from_number,
                        "To": recipient,
                        "Body": message
                    },
                    timeout=10.0
                )

                response.raise_for_status()
                logger.info(f"✅ SMS notification sent to {recipient}")
                return True

        except Exception as e:
            logger.error(f"❌ Error sending SMS to {recipient}: {e}")
            return False

    async def _send_telegram(self, agent_data: Dict, context: Dict) -> bool:
        """Send Telegram notification via Bot API"""
        try:
            import httpx

            recipient = agent_data.get("telegram_id")
            if not recipient:
                logger.warning("No Telegram ID for agent")
                return False

            # Build Telegram message with markdown
            message = f"""🚨 **New Escalation Alert**

**Priority:** {context['priority']}
**Customer:** {context['customer_name']}
**Reason:** {context['reason']}

**Recent Conversation:**
{context['conversation_preview']}

[View in Dashboard]({context['dashboard_url']})
"""

            # Send via Telegram Bot API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                    json={
                        "chat_id": recipient,
                        "text": message,
                        "parse_mode": "Markdown"
                    },
                    timeout=10.0
                )

                response.raise_for_status()
                logger.info(f"Telegram notification sent to {recipient}")
                return True

        except Exception as e:
            logger.error(f"Error sending Telegram: {e}")
            return False

    async def _track_notification(
        self,
        escalation_id: str,
        tenant_id: str,
        channel: str,
        recipient: str,
        success: bool,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> None:
        """
        Track notification attempt in database

        Always logs to escalation_notifications table regardless of success/failure.
        This provides full audit trail of all notification attempts.
        """
        try:
            notification_data = {
                "escalation_id": escalation_id,
                "tenant_id": tenant_id,
                "channel": channel,
                "recipient": recipient,
                "status": "sent" if success else "failed",
                "error_message": error_message,
                "retry_count": retry_count,
                "sent_at": datetime.utcnow().isoformat() if success else None
            }

            self.db.table("escalation_notifications").insert(notification_data).execute()
            logger.info(f"📝 Notification attempt logged: {channel} to {recipient} - {'✅ sent' if success else '❌ failed'}")

        except Exception as e:
            # Never let logging failure block notification flow
            logger.error(f"❌ Error tracking notification (non-fatal): {e}")

    async def _update_escalation_notifications(
        self,
        escalation_id: str,
        tenant_id: str,
        channels: List[NotificationChannel],
        results: Dict[str, bool]
    ) -> None:
        """Update escalation with notification info"""
        try:
            notification_channels = [ch.value for ch in channels if results.get(ch.value)]

            self.db.table("escalations").update({
                "notification_channels": notification_channels,
                "notification_sent_at": datetime.utcnow().isoformat()
            }).eq("tenant_id", tenant_id).eq("id", escalation_id).execute()

        except Exception as e:
            logger.error(f"Error updating escalation: {e}")

    def _get_recipient_field(self, channel: NotificationChannel) -> str:
        """Get the agent data field for recipient based on channel"""
        mapping = {
            NotificationChannel.EMAIL: "email",
            NotificationChannel.WHATSAPP: "whatsapp_number",
            NotificationChannel.SMS: "phone_number",
            NotificationChannel.TELEGRAM: "telegram_id"
        }
        return mapping.get(channel, "email")

    # =====================================================
    # PHASE 3: ESCALATION TIMEOUT & PRE-WARNING SYSTEM
    # =====================================================

    async def check_and_send_escalation_warnings(self) -> Dict[str, int]:
        """
        PHASE 3: Check for escalations nearing timeout and send pre-warning messages

        This method:
        1. Finds escalations where: (triggered_at + timeout - 5min) <= NOW() AND warning_sent = FALSE
        2. Sends WhatsApp pre-warning: "We're working on this. If unresolved in 5 min, connecting human agent."
        3. Marks warning_sent = TRUE, warning_sent_at = NOW()

        Returns:
            Dict with counts: {"warnings_sent": N, "errors": M}
        """
        try:
            # Query: Find escalations that need pre-warning
            # WHERE status IN ('pending', 'in_progress')
            # AND warning_sent = FALSE
            # AND (escalation_triggered_at + (escalation_timeout_minutes * 1 min) - 5 min) <= NOW()

            response = self.db.table("escalations").select("*").in_(
                "status", ["pending", "in_progress"]
            ).eq("warning_sent", False).is_(
                "escalation_triggered_at", "not.is.null"
            ).execute()

            escalations = response.data if response.data else []

            warnings_sent = 0
            errors = 0
            current_time = datetime.utcnow()

            for esc in escalations:
                try:
                    # Calculate if we should send warning
                    triggered_at = datetime.fromisoformat(
                        esc["escalation_triggered_at"].replace("Z", "+00:00")
                    )
                    timeout_minutes = esc.get("escalation_timeout_minutes", 30)
                    warning_threshold = triggered_at.timestamp() + (timeout_minutes * 60 - 5 * 60)

                    if current_time.timestamp() >= warning_threshold:
                        # Send pre-warning message to customer
                        success = await self._send_escalation_warning_to_customer(
                            chat_jid=esc["chat_jid"],
                            tenant_id=esc["tenant_id"],
                            escalation_id=esc["id"],
                            remaining_minutes=5
                        )

                        if success:
                            # Mark warning as sent
                            self.db.table("escalations").update({
                                "warning_sent": True,
                                "warning_sent_at": current_time.isoformat()
                            }).eq("id", esc["id"]).eq("tenant_id", esc["tenant_id"]).execute()

                            warnings_sent += 1
                            logger.info(f"✅ Pre-warning sent for escalation {esc['id']} (tenant: {esc['tenant_id']})")
                        else:
                            errors += 1
                            logger.warning(f"⚠️ Failed to send pre-warning for escalation {esc['id']}")

                except Exception as e:
                    errors += 1
                    logger.error(f"❌ Error processing escalation {esc.get('id')}: {e}")

            logger.info(f"📊 Escalation warning check complete: {warnings_sent} warnings sent, {errors} errors")
            return {"warnings_sent": warnings_sent, "errors": errors}

        except Exception as e:
            logger.error(f"❌ Critical error in check_and_send_escalation_warnings: {e}")
            return {"warnings_sent": 0, "errors": 1}

    async def _send_escalation_warning_to_customer(
        self,
        chat_jid: str,
        tenant_id: str,
        escalation_id: str,
        remaining_minutes: int = 5
    ) -> bool:
        """
        Send pre-warning message to customer via WhatsApp

        Message: "We're working on this. If unresolved in 5 minutes, we'll connect you with a human agent."
        """
        if not self.whatsapp_bridge_url:
            logger.warning("⚠️ WhatsApp bridge not configured, skipping pre-warning message")
            return False

        try:
            # Get bridge auth credentials
            bridge_user = os.getenv("BRIDGE_USER", "bijou")
            bridge_password = os.getenv("BRIDGE_PASSWORD", "")

            if not bridge_password:
                logger.warning("⚠️ Bridge API credentials missing, skipping pre-warning")
                return False

            # Build Basic Auth header
            auth_str = base64.b64encode(f"{bridge_user}:{bridge_password}".encode()).decode()

            # PrewarningMessage
            warning_message = f"👋 We're working on this issue. If we can't resolve it in {remaining_minutes} minute(s), we'll connect you with a human agent. Thank you for your patience!"

            # Prepare WhatsApp API call via bridge
            payload = {
                "jid": chat_jid,
                "message": warning_message,
                "from_number": None  # Let bridge determine sender
            }

            headers = {
                "Authorization": f"Basic {auth_str}",
                "Content-Type": "application/json"
            }

            # Call bridge /send/message endpoint
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.whatsapp_bridge_url}/send/message",
                    json=payload,
                    headers=headers
                )

                if resp.status_code in [200, 201]:
                    logger.info(f"✅ Pre-warning sent to {chat_jid}")
                    return True
                else:
                    logger.error(f"❌ Bridge error sending pre-warning: {resp.status_code} - {resp.text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error sending pre-warning message: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Test notifier
    import asyncio

    async def test():
        notifier = EscalationNotifier(
            supabase_client=None,  # Would be real client
            whatsapp_bridge_url="https://whatsapp-bridge.example.com"
        )

        agent_data = {
            "agent_name": "John Doe",
            "email": "john@example.com",
            "whatsapp_number": "+60123456789",
            "notification_preferences": ["email", "whatsapp"]
        }

        escalation_data = {
            "id": "test-123",
            "chat_jid": "+60198765432@s.whatsapp.net",
            "reason": "Customer requested human agent",
            "priority": "high",
            "escalation_type": "general",
            "customer_context": {
                "name": "Jane Customer"
            },
            "conversation_context": {
                "recent_messages": [
                    {"message_content": "I need help with my order", "is_from_me": False},
                    {"message_content": "I can help you with that", "is_from_me": True},
                    {"message_content": "I want to speak to a human", "is_from_me": False}
                ]
            }
        }

        results = await notifier.notify_agent(
            "test-123",
            "tenant-123",
            agent_data,
            escalation_data
        )

        print(f"Notification results: {results}")

    asyncio.run(test())
