#!/usr/bin/env python3
"""
Conversation Analyzer - AI-Powered Conversation Summarization
==============================================================

Analyzes WhatsApp conversations and generates intelligent summaries using Gemini AI.

Features:
- AI-powered topic extraction
- Sentiment analysis
- Action item detection
- Conversation categorization (demo, customer, complaint, lead)
- Multi-level export (summary, medium, full)
- Smart formatting for WhatsApp

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-01-30
Version: 1.0
"""

import logging
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

# NOTE: google.genai import is deferred to __init__ method to prevent blocking
# at module import time. The google SDK can hang on initialization.

logger = logging.getLogger(__name__)


class ConversationType(Enum):
    """Types of conversations"""

    DEMO = "demo"  # Testing/roleplay
    CUSTOMER_INQUIRY = "customer_inquiry"  # Real customer questions
    SALES_LEAD = "sales_lead"  # Buying signals detected
    SUPPORT_REQUEST = "support_request"  # Problem solving
    COMPLAINT = "complaint"  # Negative feedback
    GENERAL = "general"  # General chat
    OWNER_TESTING = "owner_testing"  # Owner testing the system


class SentimentType(Enum):
    """Sentiment categories"""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class ConversationAnalyzer:
    """
    Analyzes conversations and generates intelligent summaries.

    Uses Gemini AI to:
    - Extract key topics
    - Detect sentiment
    - Identify action items
    - Categorize conversation type
    - Generate clean summaries
    """

    def __init__(self, supabase_client=None):
        """Initialize conversation analyzer"""
        self.db = supabase_client
        self.client = None
        self.model_name = None

        # Defer Gemini initialization to first use to prevent blocking
        self._gemini_initialized = False

    def _ensure_gemini_client(self):
        """Lazily initialize Gemini client on first use"""
        if self._gemini_initialized:
            return self.client is not None

        self._gemini_initialized = True

        # Only now import google.genai (deferred import)
        try:
            from google import genai

            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
                self.model_name = "gemini-2.5-flash"
                logger.info("✅ ConversationAnalyzer initialized with Gemini 2.5 Flash")
                return True
            else:
                self.client = None
                self.model_name = None
                logger.warning("⚠️ Gemini API key not found - summaries will be basic")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")
            self.client = None
            self.model_name = None
            return False

    def analyze_conversation(
        self, chat_jid: str, max_messages: int = None, tenant_id: str = None
    ) -> Optional[Dict]:
        """
        Analyze a conversation and generate summary.

        Args:
            chat_jid: Chat JID to analyze
            max_messages: Optional limit on messages to analyze

        Returns:
            Dict with analysis results or None if error
        """
        if not self.db:
            logger.error("Database not available for analysis")
            return None

        try:
            # Fetch conversation history
            query = (
                self.db.table("conversations")
                .select("*")
                .eq("chat_jid", chat_jid)
            )
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            query = query.order("timestamp", desc=False)

            if max_messages:
                query = query.limit(max_messages)

            result = query.execute()

            if not result.data or len(result.data) == 0:
                return {
                    "error": f"No conversation found for {chat_jid}",
                    "chat_jid": chat_jid,
                }

            messages = result.data
            total = len(messages)

            # Build conversation text for AI analysis
            conversation_text = self._format_for_analysis(messages)

            # Generate AI summary if available (ensure Gemini is initialized first)
            self._ensure_gemini_client()
            if self.client and self.model_name:
                ai_analysis = self._generate_ai_summary(conversation_text, total)
            else:
                ai_analysis = self._generate_basic_summary(messages)

            # Add metadata
            ai_analysis["chat_jid"] = chat_jid
            ai_analysis["total_messages"] = total
            ai_analysis["first_message"] = messages[0].get("timestamp")
            ai_analysis["last_message"] = messages[-1].get("timestamp")
            ai_analysis["messages"] = messages  # Include for full export

            return ai_analysis

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"error": str(e), "chat_jid": chat_jid}

    def _format_for_analysis(self, messages: List[Dict]) -> str:
        """Format messages for Gemini analysis"""
        lines = []
        for msg in messages:
            timestamp = msg.get("timestamp", "")[:16]
            user_content = msg.get("message_content", "")
            ai_response = msg.get("ai_response", "")

            if user_content:
                lines.append(f"[{timestamp}] User: {user_content}")
            if ai_response:
                lines.append(f"[{timestamp}] Bijou: {ai_response}")

        return "\n".join(lines)

    def _generate_ai_summary(self, conversation_text: str, total: int) -> Dict:
        """Generate intelligent summary using Gemini"""
        if not self.client:
            return self._generate_basic_summary(
                [{"message_content": conversation_text}]
            )

        try:
            # Create analysis prompt
            prompt = f"""Analyze this WhatsApp conversation and provide a structured summary.

CONVERSATION ({total} messages):
{conversation_text[:8000]}  # Limit to ~8k chars for token management

Provide analysis in this EXACT format:

PARTICIPANT_TYPE: [owner_testing/demo/customer/sales_lead/support/complaint]
PARTICIPANT_NAME: [Extract name if mentioned, or "Unknown"]

PURPOSE: [One sentence - why did they contact Bijou?]

KEY_TOPICS:
- Topic 1
- Topic 2
- Topic 3

IMPORTANT_MOMENTS:
- First important thing that happened
- Second important thing
- Third important thing

SENTIMENT: [positive/neutral/negative/mixed]
SENTIMENT_REASON: [Why this sentiment?]

OUTCOME: [What was achieved or resolved?]

ACTION_ITEMS:
- Action 1 (if any)
- Action 2 (if any)
OR: None

NEXT_STEPS:
[What should happen next with this conversation?]

Keep it concise and business-focused. Extract value, not just summarize."""

            # Generate summary using new SDK
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt
            )
            ai_text = response.text

            # Parse structured response
            analysis = self._parse_ai_response(ai_text)
            analysis["ai_generated"] = True

            return analysis

        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            return self._generate_basic_summary(
                [{"message_content": conversation_text}]
            )

    def _parse_ai_response(self, ai_text: str) -> Dict:
        """Parse Gemini's structured response"""
        analysis = {
            "participant_type": "general",
            "participant_name": "Unknown",
            "purpose": "",
            "topics": [],
            "important_moments": [],
            "sentiment": "neutral",
            "sentiment_reason": "",
            "outcome": "",
            "action_items": [],
            "next_steps": "",
        }

        lines = ai_text.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect sections
            if line.startswith("PARTICIPANT_TYPE:"):
                analysis["participant_type"] = line.split(":", 1)[1].strip()
            elif line.startswith("PARTICIPANT_NAME:"):
                analysis["participant_name"] = line.split(":", 1)[1].strip()
            elif line.startswith("PURPOSE:"):
                analysis["purpose"] = line.split(":", 1)[1].strip()
            elif line.startswith("SENTIMENT:") and not line.startswith(
                "SENTIMENT_REASON"
            ):
                analysis["sentiment"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("SENTIMENT_REASON:"):
                analysis["sentiment_reason"] = line.split(":", 1)[1].strip()
            elif line.startswith("OUTCOME:"):
                analysis["outcome"] = line.split(":", 1)[1].strip()
            elif line.startswith("NEXT_STEPS:"):
                analysis["next_steps"] = line.split(":", 1)[1].strip()
            elif line.startswith("KEY_TOPICS:"):
                current_section = "topics"
            elif line.startswith("IMPORTANT_MOMENTS:"):
                current_section = "moments"
            elif line.startswith("ACTION_ITEMS:"):
                current_section = "actions"
            elif line.startswith("-") and current_section:
                item = line[1:].strip()
                if item.lower() != "none":
                    if current_section == "topics":
                        analysis["topics"].append(item)
                    elif current_section == "moments":
                        analysis["important_moments"].append(item)
                    elif current_section == "actions":
                        analysis["action_items"].append(item)

        return analysis

    def _generate_basic_summary(self, messages: List[Dict]) -> Dict:
        """Generate basic summary without AI (fallback)"""
        total = len(messages)
        first_msg = messages[0].get("message_content", "")[:100] if messages else ""
        last_msg = messages[-1].get("message_content", "")[:100] if messages else ""

        return {
            "participant_type": "general",
            "participant_name": "Unknown",
            "purpose": f"Conversation with {total} messages",
            "topics": ["Message exchange"],
            "important_moments": [
                f"First message: {first_msg}",
                f"Last message: {last_msg}",
            ],
            "sentiment": "neutral",
            "sentiment_reason": "Unable to analyze without AI",
            "outcome": f"Conversation concluded with {total} messages",
            "action_items": [],
            "next_steps": "Review conversation for follow-up",
            "ai_generated": False,
        }

    def format_summary(self, analysis: Dict, level: str = "summary") -> str:
        """
        Format analysis into WhatsApp-friendly text.

        Args:
            analysis: Analysis dict from analyze_conversation
            level: 'summary', 'medium', or 'full'

        Returns:
            Formatted text ready for WhatsApp
        """
        if "error" in analysis:
            return f"❌ {analysis['error']}"

        chat_jid = analysis.get("chat_jid", "Unknown")
        total = analysis.get("total_messages", 0)
        first_time = analysis.get("first_message", "")[:10]
        last_time = analysis.get("last_message", "")[:10]

        # Header
        lines = [
            "📊 CONVERSATION ANALYSIS",
            "",
            f"👤 Participant: {analysis.get('participant_name', 'Unknown')}",
            f"🏷️ Type: {analysis.get('participant_type', 'general').replace('_', ' ').title()}",
            f"📅 Period: {first_time} to {last_time}",
            f"💬 Messages: {total} total",
            "",
        ]

        # Purpose
        if analysis.get("purpose"):
            lines.extend(["🎯 PURPOSE:", analysis["purpose"], ""])

        # Key topics
        if analysis.get("topics"):
            lines.append("🔑 KEY TOPICS:")
            for topic in analysis["topics"][:5]:  # Max 5 topics
                lines.append(f"• {topic}")
            lines.append("")

        # Important moments (only in medium/full)
        if level in ["medium", "full"] and analysis.get("important_moments"):
            lines.append("💡 IMPORTANT MOMENTS:")
            for moment in analysis["important_moments"][:5]:
                lines.append(f"• {moment}")
            lines.append("")

        # Sentiment
        sentiment = analysis.get("sentiment", "neutral")
        sentiment_emoji = {
            "positive": "😊",
            "neutral": "😐",
            "negative": "😞",
            "mixed": "🤔",
        }.get(sentiment, "😐")

        lines.append(f"{sentiment_emoji} SENTIMENT: {sentiment.title()}")
        if analysis.get("sentiment_reason"):
            lines.append(f"└─ {analysis['sentiment_reason']}")
        lines.append("")

        # Outcome
        if analysis.get("outcome"):
            lines.extend(["✅ OUTCOME:", analysis["outcome"], ""])

        # Action items
        if analysis.get("action_items") and len(analysis["action_items"]) > 0:
            lines.append("📋 ACTION ITEMS:")
            for action in analysis["action_items"]:
                lines.append(f"• {action}")
            lines.append("")
        else:
            lines.append("📋 ACTION ITEMS: None")
            lines.append("")

        # Next steps
        if analysis.get("next_steps"):
            lines.extend(["🎯 NEXT STEPS:", analysis["next_steps"], ""])

        # Footer
        lines.append("---")
        lines.append(f"🔗 Chat: {chat_jid[:20]}{'...' if len(chat_jid) > 20 else ''}")

        if level == "summary":
            lines.append("")
            lines.append("💡 For full transcript: /owner export full " + chat_jid)

        if level in ["medium", "full"]:
            lines.append("")
            lines.append("--- MESSAGE TRANSCRIPT ---")
            lines.append("")

            messages = analysis.get("messages", [])
            display_count = len(messages) if level == "full" else min(20, len(messages))

            for msg in messages[:display_count]:
                timestamp = msg.get("timestamp", "")[:16]
                user_msg = msg.get("message_content", "")
                ai_msg = msg.get("ai_response", "")

                if user_msg:
                    # Truncate long messages
                    user_display = (
                        user_msg[:150] + "..." if len(user_msg) > 150 else user_msg
                    )
                    lines.append(f"[{timestamp}] User: {user_display}")

                if ai_msg:
                    ai_display = ai_msg[:150] + "..." if len(ai_msg) > 150 else ai_msg
                    lines.append(f"[{timestamp}] Bijou: {ai_display}")

                lines.append("")

            if level == "medium" and len(messages) > display_count:
                lines.append(f"... {len(messages) - display_count} more messages ...")
                lines.append("")
                lines.append(f"💡 For full transcript: /owner export full {chat_jid}")

        # AI attribution
        if analysis.get("ai_generated"):
            lines.append("")
            lines.append("🤖 Summary generated by Gemini AI")

        return "\n".join(lines)

    def get_conversation_stats(self, chat_jid: str, tenant_id: str = None) -> Optional[Dict]:
        """
        Get quick stats for a conversation.

        Args:
            chat_jid: Chat JID

        Returns:
            Dict with stats or None
        """
        if not self.db:
            return None

        try:
            _q = self.db.table("conversations").select("*").eq("chat_jid", chat_jid)
            if tenant_id:
                _q = _q.eq("tenant_id", tenant_id)
            result = _q.execute()

            if not result.data:
                return None

            messages = result.data
            total = len(messages)

            # Calculate stats
            user_messages = sum(1 for m in messages if m.get("message_content"))
            ai_messages = sum(1 for m in messages if m.get("ai_response"))

            first_time = messages[0].get("timestamp") if messages else None
            last_time = messages[-1].get("timestamp") if messages else None

            # Calculate duration
            duration_days = 0
            if first_time and last_time:
                try:
                    first_dt = datetime.fromisoformat(first_time.replace("Z", "+00:00"))
                    last_dt = datetime.fromisoformat(last_time.replace("Z", "+00:00"))
                    duration_days = (last_dt - first_dt).days
                except Exception:
                    pass

            return {
                "chat_jid": chat_jid,
                "total_messages": total,
                "user_messages": user_messages,
                "ai_messages": ai_messages,
                "first_message": first_time,
                "last_message": last_time,
                "duration_days": duration_days,
            }

        except Exception as e:
            logger.error(f"Stats generation failed: {e}")
            return None

    def export_for_training(self, chat_jid: str, tenant_id: str = None) -> Optional[str]:
        """
        Export conversation in format suitable for AI training.

        Args:
            chat_jid: Chat JID

        Returns:
            Formatted conversation string
        """
        if not self.db:
            return None

        try:
            _q = (
                self.db.table("conversations")
                .select("*")
                .eq("chat_jid", chat_jid)
            )
            if tenant_id:
                _q = _q.eq("tenant_id", tenant_id)
            result = _q.order("timestamp", desc=False).execute()

            if not result.data:
                return None

            messages = result.data
            lines = []

            for msg in messages:
                user_msg = msg.get("message_content", "")
                ai_msg = msg.get("ai_response", "")

                if user_msg and ai_msg:
                    lines.append(f"Human: {user_msg}")
                    lines.append(f"Assistant: {ai_msg}")
                    lines.append("")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Training export failed: {e}")
            return None

    def detect_conversation_type(self, messages: List[Dict]) -> ConversationType:
        """
        Detect conversation type from messages.

        Args:
            messages: List of message dicts

        Returns:
            ConversationType enum
        """
        # Simple rule-based detection (can be enhanced with AI)
        all_text = " ".join(
            [
                m.get("message_content", "").lower()
                for m in messages
                if m.get("message_content")
            ]
        )

        # Owner testing signals
        owner_signals = ["test", "/owner", "who are you", "who created"]
        if any(signal in all_text for signal in owner_signals):
            return ConversationType.OWNER_TESTING

        # Demo signals
        demo_signals = ["demo", "testing", "try", "show me", "roleplay"]
        if any(signal in all_text for signal in demo_signals):
            return ConversationType.DEMO

        # Complaint signals
        complaint_signals = [
            "complaint",
            "not working",
            "disappointed",
            "terrible",
            "worst",
        ]
        if any(signal in all_text for signal in complaint_signals):
            return ConversationType.COMPLAINT

        # Sales lead signals
        sales_signals = [
            "price",
            "how much",
            "buy",
            "purchase",
            "interested in",
            "sign up",
        ]
        if any(signal in all_text for signal in sales_signals):
            return ConversationType.SALES_LEAD

        # Support request signals
        support_signals = ["help", "how to", "problem", "issue", "can't", "not able"]
        if any(signal in all_text for signal in support_signals):
            return ConversationType.SUPPORT_REQUEST

        # Customer inquiry (default if questions detected)
        if "?" in all_text:
            return ConversationType.CUSTOMER_INQUIRY

        return ConversationType.GENERAL

    def detect_sentiment(self, messages: List[Dict]) -> SentimentType:
        """
        Detect overall sentiment from messages.

        Args:
            messages: List of message dicts

        Returns:
            SentimentType enum
        """
        all_text = " ".join(
            [
                m.get("message_content", "").lower()
                for m in messages
                if m.get("message_content")
            ]
        )

        # Simple keyword-based sentiment
        positive_keywords = [
            "thank",
            "great",
            "awesome",
            "good",
            "excellent",
            "love",
            "perfect",
            "amazing",
        ]
        negative_keywords = [
            "bad",
            "terrible",
            "worst",
            "hate",
            "disappointed",
            "angry",
            "frustrated",
        ]

        positive_count = sum(1 for word in positive_keywords if word in all_text)
        negative_count = sum(1 for word in negative_keywords if word in all_text)

        if positive_count > 0 and negative_count > 0:
            return SentimentType.MIXED
        elif positive_count > negative_count:
            return SentimentType.POSITIVE
        elif negative_count > positive_count:
            return SentimentType.NEGATIVE
        else:
            return SentimentType.NEUTRAL

    def extract_action_items(self, messages: List[Dict]) -> List[str]:
        """
        Extract potential action items from conversation.

        Args:
            messages: List of message dicts

        Returns:
            List of action item strings
        """
        actions = []

        # Look for explicit requests
        action_keywords = [
            "send me",
            "can you",
            "please",
            "need",
            "want",
            "looking for",
            "interested in",
        ]

        for msg in messages:
            content = msg.get("message_content", "").lower()
            for keyword in action_keywords:
                if keyword in content:
                    # Extract the sentence containing the keyword
                    sentences = content.split(".")
                    for sentence in sentences:
                        if keyword in sentence:
                            action = sentence.strip()
                            if action and len(action) < 200:
                                actions.append(action)
                            break

        # Remove duplicates and limit
        return list(set(actions))[:5]


def enable_conversation_analyzer():
    """Feature flag check"""
    return os.getenv("ENABLE_CONVERSATION_ANALYZER", "true").lower() == "true"
