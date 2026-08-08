"""
Notification Groups Manager - 3-Tier Notification System
========================================================

Manages WhatsApp groups for different notification types:
1. 🚨 Escalation Queue - Customers waiting for human (URGENT)
2. 🔥 Hot Leads - High buying intent (Follow up today)
3. 📢 Customer Updates - FYI messages (Low priority)

Features:
- Auto-create groups on first deployment
- Smart routing based on message type
- Casual acknowledgment detection
- Group-specific notification formats

Author: W3J Consulting
Date: 2026-02-12
Phase: 1 - 3-Tier Notification System
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import httpx

# Use standard logging instead of loguru for consistency with Bijou
logger = logging.getLogger(__name__)


class NotificationGroupType(str, Enum):
    """Types of notification groups"""
    ESCALATION = "escalation_queue"
    HOT_LEADS = "hot_leads"
    UPDATES = "customer_updates"
    HELP_TICKETS = "help_tickets"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    URGENT = "urgent"      # Escalations - respond immediately
    HIGH = "high"          # Hot leads - follow up today
    LOW = "low"            # Updates - FYI only


class NotificationGroupsManager:
    """
    Manages 3-tier notification system with WhatsApp groups

    Workflow:
    1. On init: Check if groups exist, create if needed
    2. On notification: Route to appropriate group based on type
    3. Format message based on group type
    """

    def __init__(
        self,
        supabase_client,
        bridge_url: str,
        bridge_api_key: str,
        owner_jid: str,
        whatsapp_device_id: Optional[str] = None
    ):
        """
        Initialize notification groups manager

        Args:
            supabase_client: Supabase client for database
            bridge_url: WhatsApp bridge URL
            bridge_api_key: Bridge API authentication key
            owner_jid: Owner's WhatsApp JID to add to groups
            whatsapp_device_id: WhatsApp device ID for bridge authentication (same as used in send_message)
        """
        self.db = supabase_client
        self.bridge_url = bridge_url
        self.bridge_api_key = bridge_api_key
        self.owner_jid = owner_jid
        self.whatsapp_device_id = whatsapp_device_id

        # Group configurations
        self.group_configs = {
            NotificationGroupType.ESCALATION: {
                "name": "🚨 Bijou Escalations",
                "description": "Customers waiting for human response - URGENT",
                "emoji": "🚨"
            },
            NotificationGroupType.HOT_LEADS: {
                "name": "🔥 Bijou Hot Leads",
                "description": "High-intent buyers - Follow up today",
                "emoji": "🔥"
            },
            NotificationGroupType.UPDATES: {
                "name": "📢 Bijou Updates",
                "description": "Customer acknowledgments & FYI messages",
                "emoji": "💬"
            }
        }

        logger.info("NotificationGroupsManager initialized")

    async def setup_groups(self, tenant_id: str) -> Dict[str, str]:
        """
        DEPRECATED: Auto-creation removed (GoWA bridge doesn't support /api/group/create)

        Check if notification groups exist in database

        Args:
            tenant_id: Tenant ID

        Returns:
            Dict mapping group type to group JID (empty if not registered)
        """
        group_jids = {}

        for group_type in NotificationGroupType:
            try:
                # Check if group already exists in database
                existing = await self._get_existing_group(tenant_id, group_type.value)

                if existing:
                    group_jids[group_type.value] = existing["group_jid"]
                    logger.info(f"Found existing {group_type.value} group: {existing['group_jid']}")
                else:
                    logger.info(f"⚠️ {group_type.value} group not registered yet - waiting for manual registration")

            except Exception as e:
                logger.error(f"Error checking {group_type.value} group: {e}")

        return group_jids

    async def _get_existing_group(
        self,
        tenant_id: str,
        group_type: str
    ) -> Optional[Dict]:
        """Get existing group from database"""
        try:
            result = self.db.table("notification_groups").select("*").eq(
                "tenant_id", tenant_id
            ).eq(
                "group_type", group_type
            ).execute()

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error getting existing group: {e}")
            return None

    async def _create_whatsapp_group(
        self,
        tenant_id: str,
        group_type: NotificationGroupType
    ) -> Optional[str]:
        """
        Create WhatsApp group via bridge API

        Returns:
            Group JID if successful, None otherwise
        """
        try:
            config = self.group_configs[group_type]

            # Create group via bridge
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.bridge_url}/api/group/create",
                    json={
                        "name": config["name"],
                        "participants": [self.owner_jid]  # Add owner
                    },
                    headers={
                        "X-API-Key": self.bridge_api_key
                    },
                    timeout=30.0
                )

                response.raise_for_status()
                data = response.json()

                group_jid = data.get("group_jid")

                if not group_jid:
                    logger.error(f"No group_jid in response: {data}")
                    return None

                # Save to database
                await self._save_group_to_db(
                    tenant_id,
                    group_type.value,
                    group_jid,
                    config["name"]
                )

                # Send welcome message
                await self._send_welcome_message(group_jid, group_type)

                return group_jid

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating group: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating WhatsApp group: {e}")
            return None

    async def _save_group_to_db(
        self,
        tenant_id: str,
        group_type: str,
        group_jid: str,
        group_name: str
    ):
        """Save group info to database"""
        try:
            group_data = {
                "tenant_id": tenant_id,
                "group_type": group_type,
                "group_jid": group_jid,
                "group_name": group_name,
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True
            }

            self.db.table("notification_groups").insert(group_data).execute()
            logger.debug(f"Saved group {group_type} to database")

        except Exception as e:
            logger.error(f"Error saving group to DB: {e}")

    async def _send_welcome_message(
        self,
        group_jid: str,
        group_type: NotificationGroupType
    ):
        """Send welcome message to newly created group"""
        try:
            config = self.group_configs[group_type]

            welcome_messages = {
                NotificationGroupType.ESCALATION: """🚨 ESCALATION QUEUE ACTIVATED

This group receives URGENT escalations where customers are actively waiting for human response.

✅ What you'll see:
• Customer requests for human/manager
• Urgent issues (detected via "arjanley" / "urgent")
• Frustrated customers
• Questions Bijou can't answer

⚡ Action required:
• Respond ASAP (customer is waiting!)
• Type message directly in customer chat
• When done: Customer says "thank you" = auto-closed

Priority: URGENT - Customers are waiting!""",

                NotificationGroupType.HOT_LEADS: """🔥 HOT LEADS TRACKER ACTIVATED

This group shows high-intent buyers who should be followed up TODAY.

✅ What you'll see:
• Customers asking about prices
• Budget mentions
• Timeline indicators ("need urgent", "this month")
• "I wan buy" signals

⚡ Action required:
• Follow up within 24 hours
• Call or message to close the sale
• High conversion probability!

Priority: HIGH - Follow up today for best results!""",

                NotificationGroupType.UPDATES: """📢 CUSTOMER UPDATES ACTIVATED

This group receives FYI notifications - no immediate action needed.

✅ What you'll see:
• New customer first messages
• "Thank you" acknowledgments after you helped
• "Ok got it" confirmations
• Positive feedback

ℹ️ Action required:
• NONE - Just keeping you informed
• Read when you have time

Priority: LOW - FYI only!"""
            }

            message = welcome_messages.get(group_type, "Group created successfully!")

            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{self.bridge_url}/api/send",
                    json={
                        "to": group_jid,
                        "message": message
                    },
                    headers={
                        "X-API-Key": self.bridge_api_key
                    },
                    timeout=10.0
                )

            logger.debug(f"Sent welcome message to {group_type.value} group")

        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    async def send_notification(
        self,
        tenant_id: str,
        group_type: NotificationGroupType,
        notification_data: Dict
    ) -> bool:
        """
        Send notification to appropriate group

        Args:
            tenant_id: Tenant ID
            group_type: Which group to notify
            notification_data: Notification details
                - customer_jid: Customer's WhatsApp JID
                - customer_phone: Formatted phone number
                - customer_name: Contact name
                - message: Customer's message
                - ai_response: Bijou's response (optional)
                - reason: Why this notification (for escalations/leads)
                - context: Additional context

        Returns:
            True if sent successfully
        """
        try:
            # Get group JID
            group = await self._get_existing_group(tenant_id, group_type.value)

            if not group:
                logger.error(f"❌ NOTIFICATION FAILED: No {group_type.value} group registered for tenant {tenant_id}")
                logger.error(f"📋 Notification details: customer={notification_data.get('customer_phone')}, type={group_type.value}")
                logger.error(f"💡 FIX: Create WhatsApp group and register using 'Register group: Bijou {group_type.value.replace('_', ' ').title()}' command")
                logger.error(f"📊 Check registered groups: SELECT * FROM notification_groups WHERE tenant_id='{tenant_id}'")
                return False

            group_jid = group["group_jid"]

            # Use the same device_id that works for regular message sending
            # (This is from WHATSAPP_DEVICE_ID environment variable, NOT tenant's whatsapp_jid)
            device_id = self.whatsapp_device_id
            if device_id:
                logger.debug(f"Using whatsapp_device_id for notification: {device_id}")
            else:
                logger.warning("whatsapp_device_id not configured - notification may fail")

            # Format message based on group type
            message = self._format_notification(group_type, notification_data)

            # Send via bridge (GoWA uses Basic Auth, not X-API-Key)
            # Format: username:password encoded in Authorization header
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Parse bridge_api_key as "username:password"
                auth_parts = self.bridge_api_key.split(":", 1) if self.bridge_api_key else []
                basic_auth = (auth_parts[0], auth_parts[1]) if len(auth_parts) >= 2 else ("", "")

                # Build request payload and headers
                payload = {
                    "phone": group_jid,
                    "message": message
                }

                headers = {}
                # Add device_id header (required by GOWA bridge)
                if device_id:
                    headers["X-Device-Id"] = device_id

                response = await client.post(
                    f"{self.bridge_url}/send/message",
                    json=payload,
                    auth=basic_auth,
                    headers=headers,
                    timeout=10.0
                )

                response.raise_for_status()
                logger.info(f"✅ Sent {group_type.value} notification")

                # Track in database
                await self._track_notification(
                    tenant_id,
                    group_type.value,
                    group_jid,
                    notification_data
                )

                return True

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP ERROR sending notification to {group_type.value}")
            logger.error(f"   Status: {e.response.status_code}")
            logger.error(f"   Response: {e.response.text[:200]}")
            logger.error(f"   Bridge URL: {self.bridge_url}/send/message")
            logger.error(f"   Group JID: {group_jid if 'group_jid' in locals() else 'N/A'}")
            logger.error(f"   Auth configured: {bool(self.bridge_api_key)}")
            return False
        except httpx.RequestError as e:
            logger.error(f"❌ NETWORK ERROR sending notification to {group_type.value}")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Bridge URL: {self.bridge_url}")
            logger.error(f"   Check if bridge is running: curl {self.bridge_url}/health")
            return False
        except Exception as e:
            logger.error(f"❌ UNEXPECTED ERROR sending notification to {group_type.value}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error message: {str(e)}")
            logger.error(f"   Notification data: {notification_data}")
            return False

    def _format_notification(
        self,
        group_type: NotificationGroupType,
        data: Dict
    ) -> str:
        """Format notification message based on group type"""

        customer_phone = data.get("customer_phone", "Unknown")
        customer_name = data.get("customer_name", "Unknown")
        customer_jid = data.get("customer_jid", "")
        message = data.get("message", "")

        if group_type == NotificationGroupType.ESCALATION:
            # Escalation format - URGENT
            ai_response = data.get("ai_response", "")
            reason = data.get("reason", "Customer requested human")
            escalation_id = data.get("escalation_id", "")

            return f"""🚨 ESCALATION #{escalation_id}

📱 Phone: {customer_phone}
👤 Name: {customer_name}
🕒 Waiting: Just now

🗣️ They said:
"{message[:200]}"

🤖 Bijou responded:
"{ai_response[:150]}"

Reason: {reason}

---
🔴 RESPOND NOW - Customer waiting!
Reply directly in their chat"""

        elif group_type == NotificationGroupType.HOT_LEADS:
            # Hot lead format - HIGH PRIORITY
            reason = data.get("reason", "Buying signals detected")
            qualification = data.get("qualification", {})

            qual_text = ""
            if qualification:
                qual_text = "\n\n🎯 Qualified:\n"
                if qualification.get("budget"):
                    qual_text += f"• Budget: {qualification['budget']}\n"
                if qualification.get("location"):
                    qual_text += f"• Location: {qualification['location']}\n"
                if qualification.get("timeline"):
                    qual_text += f"• Timeline: {qualification['timeline']}\n"

            return f"""🔥 HOT LEAD ALERT!

📱 Phone: {customer_phone}
👤 Name: {customer_name}

💰 Why it's hot:
{reason}

💬 They said:
"{message[:200]}"
{qual_text}
---
💼 FOLLOW UP TODAY
Call: {customer_phone}"""

        else:  # UPDATES
            # Update format - FYI ONLY
            context = data.get("context", "")
            update_type = data.get("update_type", "message")

            if update_type == "acknowledgment":
                return f"""💬 Customer Update

📱 {customer_phone} ({customer_name})

They said: "{message}"

Context: {context}

---
ℹ️ No action needed - Just FYI"""

            elif update_type == "new_customer":
                return f"""💬 New Customer

📱 {customer_phone}
👤 {customer_name}

First message: "{message[:150]}"

---
ℹ️ Bijou is handling - FYI only"""

            else:
                return f"""💬 Customer Update

📱 {customer_phone} ({customer_name})

Message: "{message[:200]}"

---
ℹ️ FYI only"""

    async def _track_notification(
        self,
        tenant_id: str,
        group_type: str,
        group_jid: str,
        notification_data: Dict
    ):
        """Track notification in database for analytics"""
        try:
            # Map group_type to valid notification_type for database constraint
            # Database expects: 'escalation', 'hot_lead', 'new_customer', 'acknowledgment', 'update'
            notification_type_map = {
                "escalation_queue": "escalation",
                "hot_leads": "hot_lead",
                "customer_updates": "update",  # Database uses singular 'update', not 'customer_updates'
            }

            tracking_data = {
                "tenant_id": tenant_id,
                "group_type": group_type,
                "group_jid": group_jid,
                "customer_jid": notification_data.get("customer_jid"),
                "notification_type": notification_type_map.get(group_type, "update"),
                "sent_at": datetime.utcnow().isoformat()
            }

            self.db.table("notification_logs").insert(tracking_data).execute()

        except Exception as e:
            logger.error(f"Error tracking notification: {e}")

    async def add_member_to_group(
        self,
        tenant_id: str,
        group_type: NotificationGroupType,
        member_jid: str
    ) -> bool:
        """Add team member to notification group"""
        try:
            group = await self._get_existing_group(tenant_id, group_type.value)

            if not group:
                logger.warning(f"No {group_type.value} group found")
                return False

            group_jid = group["group_jid"]

            # Add via bridge
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.bridge_url}/api/group/add-member",
                    json={
                        "group_jid": group_jid,
                        "participant_jid": member_jid
                    },
                    headers={
                        "X-API-Key": self.bridge_api_key
                    },
                    timeout=10.0
                )

                response.raise_for_status()
                logger.info(f"✅ Added {member_jid} to {group_type.value} group")
                return True

        except Exception as e:
            logger.error(f"Error adding member to group: {e}")
            return False

    async def _send_setup_alert_to_owner(
        self,
        tenant_id: str,
        group_type: NotificationGroupType
    ):
        """
        FALLBACK: Alert owner/team when groups can't be auto-created
        Team can create groups manually and tell Bijou about them
        """
        try:
            alert_message = f"""🚨 SETUP NEEDED: Notification Groups

Bijou tried to create WhatsApp notification groups but failed.

**What to do:**
1. Manually create these 3 WhatsApp groups:
   • 🚨 Bijou Escalations (urgent customer issues)
   • 🔥 Bijou Hot Leads (high buying intent)
   • 📢 Bijou Updates (FYI messages)

2. Add Bijou to each group

3. Send a message to Bijou staging:
   "Register group: Bijou Escalations"
   "Register group: Bijou Hot Leads"
   "Register group: Bijou Updates"

Bijou will automatically detect and register them!

**Current missing:** {group_type.value}
**Tenant ID:** {tenant_id}"""

            # Send alert to owner
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.bridge_url}/api/send",
                    json={
                        "to": self.owner_jid,
                        "message": alert_message
                    },
                    headers={
                        "X-API-Key": self.bridge_api_key
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"✅ Sent setup alert to owner for {group_type.value}")

        except Exception as e:
            logger.error(f"Error sending setup alert: {e}")

    async def register_group_manually(
        self,
        tenant_id: str,
        group_name: str,
        group_jid: str
    ) -> bool:
        """
        Register a manually created group
        Called when owner creates groups and tells Bijou about them

        Usage: Owner sends message like "Register group: Bijou Escalations"
        Bijou extracts group name and JID, calls this function
        """
        try:
            # Map group name to type
            group_type_map = {
                "bijou escalations": NotificationGroupType.ESCALATION,
                "escalations": NotificationGroupType.ESCALATION,
                "escalation queue": NotificationGroupType.ESCALATION,

                "bijou hot leads": NotificationGroupType.HOT_LEADS,
                "hot leads": NotificationGroupType.HOT_LEADS,
                "leads": NotificationGroupType.HOT_LEADS,

                "bijou updates": NotificationGroupType.UPDATES,
                "updates": NotificationGroupType.UPDATES,
                "customer updates": NotificationGroupType.UPDATES,

                "bijou help tickets": NotificationGroupType.HELP_TICKETS,
                "help tickets": NotificationGroupType.HELP_TICKETS,
                "help ticket": NotificationGroupType.HELP_TICKETS,
                "support tickets": NotificationGroupType.HELP_TICKETS,
                "tickets": NotificationGroupType.HELP_TICKETS,
                "helpdesk": NotificationGroupType.HELP_TICKETS,
            }

            group_name_lower = group_name.lower()
            group_type = group_type_map.get(group_name_lower)

            if not group_type:
                logger.warning(f"Unknown group name: {group_name}")
                return False

            # Check if already exists
            existing = await self._get_existing_group(tenant_id, group_type.value)
            if existing:
                logger.info(f"Group {group_type.value} already registered")
                return True

            # Save to database
            await self._save_group_to_db(
                tenant_id,
                group_type.value,
                group_jid,
                group_name
            )

            # Send welcome message
            await self._send_welcome_message(group_jid, group_type)

            logger.info(f"✅ Manually registered {group_type.value} group")
            return True

        except Exception as e:
            logger.error(f"Error registering group manually: {e}")
            return False



# Helper function: Detect casual acknowledgments
def is_casual_acknowledgment(message: str) -> bool:
    """
    Detect if message is just a casual acknowledgment

    Returns True for: "thank you", "thanks", "ok", "got it", etc.
    Uses word boundary matching to avoid false positives (e.g., "spoke" matching "ok")
    """
    import re

    # Use word boundaries (\b) to match whole words only
    casual_patterns = [
        # English - single words
        r"\bok\b", r"\bokay\b", r"\b[kK]{1,2}\b",  # ok, okay, k, kk
        r"\bthanks?\b", r"\bthx\b", r"\bty\b", r"\btq\b",  # thank/thanks, thx, ty, tq
        r"\bgot it\b", r"\bnoted\b", r"\bunderstood\b",
        r"\balright\b", r"\bcool\b", r"\bgreat\b", r"\bawesome\b",

        # English - phrases (must match full phrase)
        r"thank you", r"appreciate it", r"appreciated",

        # Malay
        r"terima kasih",

        # Emojis (exact match, not regex)
    ]

    message_lower = message.lower().strip()

    # Must be SHORT (under 10 words)
    word_count = len(message_lower.split())
    if word_count > 10:
        return False

    # Check for emoji-only messages
    emoji_acknowledgments = ["👍", "🙏", "😊", "👌", "✅"]
    if any(emoji in message for emoji in emoji_acknowledgments):
        return True

    # Check if matches any casual pattern with word boundaries
    return any(re.search(pattern, message_lower) for pattern in casual_patterns)


# Example usage
if __name__ == "__main__":
    async def test():
        # Test casual acknowledgment detection
        test_messages = [
            ("Thank you so much!", True),
            ("Ok got it", True),
            ("Thanks! Really helpful", True),
            ("terima kasih", True),
            ("I want to buy a condo", False),
            ("Can you help me with pricing?", False),
        ]

        print("Testing casual acknowledgment detection:")
        for msg, expected in test_messages:
            result = is_casual_acknowledgment(msg)
            status = "✅" if result == expected else "❌"
            print(f"{status} '{msg}' -> {result} (expected {expected})")

    asyncio.run(test())
