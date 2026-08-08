#!/usr/bin/env python3
"""
Lead Converter - Property Agent Handover & CTA Enhancement
==========================================================

Addresses critical gaps from bijou_feedback.md:
1. Human agent handover for qualified property leads
2. Follow-up scheduling mechanism
3. Clear CTAs (Call-to-Action) at conversation endpoints

Author: AI Lead Engineer
Date: 2026-01-30
Version: 1.0
"""

import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LeadStatus(Enum):
    """Lead qualification status"""

    COLD = "cold"  # Just browsing
    WARM = "warm"  # Interested, needs info
    HOT = "hot"  # Ready to view/buy
    QUALIFIED = "qualified"  # All info collected, ready for agent


class PropertyType(Enum):
    """Property types from conversation"""

    CONDO = "condo"
    APARTMENT = "apartment"
    LANDED = "landed"
    AFFORDABLE = "affordable"  # 廉价屋
    COMMERCIAL = "commercial"
    UNKNOWN = "unknown"


class LeadConverter:
    """
    Converts qualified conversations into property agent handovers

    Features:
    - Detects qualification signals (budget, location, timeline)
    - Triggers human agent handover at optimal moments
    - Generates clear CTAs with next steps
    - Schedules follow-ups for warm leads
    """

    def __init__(
        self,
        handover_system=None,
        supabase_client=None,
        send_message_callback=None,
        owner_jid: Optional[str] = None,
    ):
        """Initialize lead converter"""
        self.handover_system = handover_system
        self.db = supabase_client
        self.send_message = send_message_callback
        self.owner_jid = owner_jid or os.getenv("OWNER_WHATSAPP_JID")

        # Lead qualification criteria
        self.qualification_signals = {
            "budget": [
                "rm",
                "ringgit",
                "price",
                "budget",
                "afford",
                "harga",
                "berapa",
            ],
            "location": [
                "area",
                "location",
                "where",
                "near",
                "lokasi",
                "kawasan",
                "dekat",
            ],
            "timeline": [
                "when",
                "soon",
                "urgent",
                "now",
                "asap",
                "bila",
                "segera",
                "cepat",
            ],
            "property_type": [
                "condo",
                "apartment",
                "house",
                "landed",
                "rumah",
                "flat",
                "廉价屋",
            ],
            "viewing_intent": [
                "view",
                "see",
                "visit",
                "show",
                "tengok",
                "lihat",
                "tunjuk",
            ],
        }

        # Handover triggers (high-intent phrases)
        self.handover_triggers = [
            "speak to agent",
            "talk to agent",
            "human agent",
            "property agent",
            "view property",
            "book viewing",
            "schedule visit",
            "want to see",
            "jumpa ejen",
            "cakap dengan ejen",
            "nak tengok",
            "boleh jumpa",
        ]

        logger.info("✅ LeadConverter initialized")

    def analyze_lead_quality(
        self,
        customer_jid: str = None,
        conversation_history: List[Dict[str, str]] = None,
        latest_message: str = None
    ) -> Tuple[LeadStatus, Dict[str, any]]:
        """
        Analyze conversation to determine lead quality

        Args:
            customer_jid: Customer WhatsApp JID (optional)
            conversation_history: List of conversation messages
            latest_message: Most recent message (optional)

        Returns:
            (LeadStatus, qualification_data)
        """
        if conversation_history is None:
            conversation_history = []

        # FIXED: More precise filter - only skip meta-questions about OUR actions
        # Don't drop valid customer intent like "Did you have 3-bedroom units?"
        meta_question_patterns = [
            "did you inform", "have you told", "have you notified",
            "did you contact", "have you contacted", "did you tell",
            "already informed", "already told", "already notified",
            "waiting for you to", "when will you inform", "when will you tell",
            "are you going to contact", "will you contact", "will you inform"
        ]

        message_text = (latest_message or "").lower()
        # Only skip if it's clearly a meta-question (checking on our follow-up actions)
        if any(pattern in message_text for pattern in meta_question_patterns):
            logger.debug(f"⏭️ Skipping lead analysis - meta-question about our actions: '{latest_message}'")
            # Initialize qualification_data before return (was missing before)
            qualification_data = {
                "budget": None,
                "location": None,
                "timeline": None,
                "property_type": PropertyType.UNKNOWN,
                "messages_count": len(conversation_history),
                "engagement_score": 0,
            }
            return LeadStatus.COLD, qualification_data

        signals_detected = {
            "budget": False,
            "location": False,
            "timeline": False,
            "property_type": False,
            "viewing_intent": False,
        }

        qualification_data = {
            "budget": None,
            "location": None,
            "timeline": None,
            "property_type": PropertyType.UNKNOWN,
            "messages_count": len(conversation_history),
            "engagement_score": 0,
        }

        # Analyze conversation for signals
        full_text = " ".join(
            [msg.get("content", "").lower() for msg in conversation_history]
        )

        for signal_type, keywords in self.qualification_signals.items():
            for keyword in keywords:
                if keyword in full_text:
                    signals_detected[signal_type] = True
                    qualification_data["engagement_score"] += 10
                    break

        # Detect property type
        if "condo" in full_text or "apartment" in full_text:
            qualification_data["property_type"] = PropertyType.CONDO
        elif "landed" in full_text or "rumah" in full_text:
            qualification_data["property_type"] = PropertyType.LANDED
        elif "廉价屋" in full_text or "affordable" in full_text:
            qualification_data["property_type"] = PropertyType.AFFORDABLE

        # Calculate lead status
        signals_count = sum(signals_detected.values())

        if signals_count >= 4:
            return LeadStatus.QUALIFIED, qualification_data
        elif signals_count >= 3:
            return LeadStatus.HOT, qualification_data
        elif signals_count >= 2:
            return LeadStatus.WARM, qualification_data
        else:
            return LeadStatus.COLD, qualification_data

    def should_trigger_handover(
        self, message: str, lead_status: LeadStatus
    ) -> Tuple[bool, str]:
        """
        Determine if message should trigger agent handover

        Returns:
            (should_handover, reason)
        """
        message_lower = message.lower()

        # Explicit handover request
        for trigger in self.handover_triggers:
            if trigger in message_lower:
                return True, f"Explicit request: '{trigger}'"

        # Qualified lead + viewing intent
        if lead_status == LeadStatus.QUALIFIED:
            if any(
                word in message_lower
                for word in ["view", "see", "visit", "tengok", "lihat"]
            ):
                return True, "Qualified lead requesting viewing"

        # Hot lead asking for next steps
        if lead_status == LeadStatus.HOT:
            if any(
                word in message_lower
                for word in ["next", "what now", "how", "apa lagi", "macam mana"]
            ):
                return True, "Hot lead asking for next steps"

        return False, ""

    def generate_cta(self, lead_status: LeadStatus, qualification_data: Dict) -> str:
        """Generate appropriate CTA based on lead quality"""

        if lead_status == LeadStatus.QUALIFIED:
            return self._cta_qualified(qualification_data)
        elif lead_status == LeadStatus.HOT:
            return self._cta_hot(qualification_data)
        elif lead_status == LeadStatus.WARM:
            return self._cta_warm(qualification_data)
        else:
            return self._cta_cold()

    def _cta_qualified(self, data: Dict) -> str:
        """CTA for qualified leads - immediate agent connection"""
        property_type = data.get("property_type", PropertyType.UNKNOWN).value

        return f"""Great! You seem ready to move forward with your {property_type} search! 🏡

**NEXT STEPS:**
1️⃣ I'll connect you with our property specialist
2️⃣ They'll arrange a viewing at your convenience
3️⃣ Get personalized recommendations based on your needs

*Connecting you to our agent now...* ⚡

Would you like me to schedule a callback for today or tomorrow?"""

    def _cta_hot(self, data: Dict) -> str:
        """CTA for hot leads - gentle push to agent"""
        return """I can see you're seriously interested! 🎯

**Want to take the next step?**
✅ Speak with our property specialist (FREE consultation)
✅ Get exact pricing & availability
✅ Schedule property viewings

Just say "connect me with an agent" and I'll get someone on the line! 📞

Or continue chatting with me if you have more questions. 😊"""

    def _cta_warm(self, data: Dict) -> str:
        """CTA for warm leads - info + soft CTA"""
        return """Here's what I can help you with next:

📋 **More Information**
• Detailed property listings
• Pricing comparisons
• Neighborhood insights

👤 **Speak to a Specialist**
• FREE consultation
• Personalized recommendations
• Schedule viewings

💬 **Keep Chatting**
• Ask me anything about properties
• No pressure, just info!

What would you prefer? 😊"""

    def _cta_cold(self) -> str:
        """CTA for cold leads - keep them engaged"""
        return """Thanks for chatting! 😊

**Feel free to:**
🔍 Browse more properties
❓ Ask me any questions
📱 Save my number for later

When you're ready to view properties, just let me know and I'll connect you with our specialist! 🏡

Is there anything else I can help you with today?"""

    def trigger_agent_handover(
        self,
        chat_jid: str,
        customer_name: str,
        qualification_data: Dict,
        conversation_summary: str,
    ) -> bool:
        """
        Trigger handover to human property agent

        Returns:
            Success status
        """
        if not self.handover_system:
            logger.warning("⚠️ Handover system not available")
            return False

        try:
            # Create escalation with property-specific context
            context = {
                "customer_name": customer_name,
                "qualification": qualification_data,
                "summary": conversation_summary,
                "lead_status": "qualified",
                "property_interest": qualification_data.get("property_type", "unknown"),
                "engagement_score": qualification_data.get("engagement_score", 0),
            }

            # Escalate with HIGH priority for qualified leads
            escalation_id = self.handover_system.escalate(
                chat_jid=chat_jid,
                reason="Qualified property lead requesting agent",
                priority="high",
                customer_context=context,
            )

            # Send confirmation to customer
            if self.send_message:
                confirmation = """✅ **Agent Connection Requested!**

Our property specialist will reach out to you within the next 15-30 minutes.

In the meantime:
📱 Keep your phone handy
💬 Feel free to continue chatting with me
📋 I'll share your details with the agent

Looking forward to helping you find your dream property! 🏡"""

                self.send_message(chat_jid, confirmation)

            # Notify owner
            if self.owner_jid and self.send_message:
                owner_alert = f"""🔥 **QUALIFIED LEAD ALERT!**

**Customer:** {customer_name}
**Chat:** {chat_jid}
**Property Interest:** {qualification_data.get("property_type", "Unknown")}
**Engagement Score:** {qualification_data.get("engagement_score", 0)}

**Summary:**
{conversation_summary[:200]}...

**Action Required:** Contact customer within 15-30 minutes
**Escalation ID:** {escalation_id}"""

                self.send_message(self.owner_jid, owner_alert)

            logger.info(f"✅ Agent handover triggered for {chat_jid}")
            return True

        except Exception as e:
            logger.error(f"❌ Handover failed: {e}")
            return False

    def schedule_follow_up(
        self,
        chat_jid: str,
        lead_status: LeadStatus,
        delay_hours: int = 72,
        tenant_id: str = None,
    ) -> bool:
        """
        Schedule follow-up message for warm/hot leads

        Returns:
            Success status
        """
        if not self.db:
            logger.warning("⚠️ Database not available for follow-up scheduling")
            return False

        try:
            follow_up_time = datetime.now() + timedelta(hours=delay_hours)

            follow_up_data = {
                "chat_jid": chat_jid,
                "lead_status": lead_status.value,
                "scheduled_at": follow_up_time.isoformat(),
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
            if tenant_id:
                follow_up_data["tenant_id"] = tenant_id

            # Store in database
            result = self.db.table("follow_ups").insert(follow_up_data).execute()

            if result:
                logger.info(
                    f"✅ Follow-up scheduled for {chat_jid} at {follow_up_time}"
                )
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"❌ Follow-up scheduling failed: {e}")
            return False

    def get_pending_follow_ups(self, tenant_id: str) -> List[Dict]:
        """Get all pending follow-ups that are due for a specific tenant"""
        if not self.db:
            return []

        try:
            now = datetime.now().isoformat()

            result = (
                self.db.table("follow_ups")
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("status", "pending")
                .lte("scheduled_at", now)
                .execute()
            )

            return result.data if result else []

        except Exception as e:
            logger.error(f"❌ Failed to get follow-ups: {e}")
            return []

    def send_follow_up_message(self, chat_jid: str, lead_status: LeadStatus) -> bool:
        """Send follow-up message to warm/hot lead (generic, works any business type)"""
        if not self.send_message:
            return False

        if lead_status == LeadStatus.HOT:
            message = """Hi again! 👋

Just checking in — are you still interested? 😊

Our team is ready to help you right now. Reply *Yes* and I'll connect you with a specialist straight away! 📞"""

        elif lead_status == LeadStatus.WARM:
            message = """Hi there! 😊

Hope you're doing well!

I noticed we haven't connected in a while. I'm still here if you have any questions or need help.

Just reply and I'll pick up right where we left off! 🙌"""

        else:
            message = """Hi! 👋

Just a quick follow-up from our last chat.

Feel free to reach out anytime if you need anything — happy to help! 😊"""

        try:
            self.send_message(chat_jid, message)
            logger.info(f"✅ Follow-up sent to {chat_jid}")
            return True
        except Exception as e:
            logger.error(f"❌ Follow-up send failed: {e}")
            return False


def enable_lead_conversion():
    """Feature flag check for lead conversion"""
    return os.getenv("ENABLE_LEAD_CONVERSION", "false").lower() == "true"
