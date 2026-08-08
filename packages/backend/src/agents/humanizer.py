"""
Bijou AI - Conversation Humanizer Agent
=======================================

Responsible for post-processing AI responses to make them feel more natural,
less robotic, and contextually appropriate.

Features:
- Removes robotic prefixes ("As an AI...", "I apologize...")
- Controls introduction frequency (prevents repetitive "Hi, I'm Bijou")
- Adapts tone based on user's conversation style
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class ConversationHumanizer:
    """
    Humanizes AI responses and manages conversational flow.
    """

    def __init__(self):
        self.robotic_prefixes = [
            r"^as an ai language model,?",
            r"^i understand (that)?",
            r"^i apologize for the (confusion|inconvenience|delay)",
            r"^i'm sorry to hear (that|about)",
            r"^thank you for (reaching out|contacting us)",
            r"^hello,?",
            r"^hi,?",
            r"^greetings,?",
        ]
        
        # Track when we last introduced ourselves in a chat
        self._last_intro_time: Dict[str, datetime] = {}

    def should_introduce(self, chat_jid: str, conversation_history: List[Dict]) -> bool:
        """
        Determine if we should include an introduction greeting.
        
        Rules:
        1. If we haven't introduced ourselves in this session (last 24h), YES.
        2. If conversation history shows we already greeted recently, NO.
        """
        now = datetime.now()
        
        # Check in-memory cache first
        last_intro = self._last_intro_time.get(chat_jid)
        if last_intro and (now - last_intro) < timedelta(hours=24):
            return False

        # Check history for recent intros from bot
        # Assuming history is sorted old -> new
        if conversation_history:
            recent_msgs = conversation_history[-10:] # Check last 10 messages
            for msg in recent_msgs:
                # Check if message is from us and contains intro words
                if msg.get('role') == 'assistant' or msg.get('sender') == 'bot':
                    content = msg.get('content', '').lower()
                    if "i'm bijou" in content or "i am bijou" in content:
                        self._last_intro_time[chat_jid] = now # Update cache
                        return False
        
        # Update cache that we are about to introduce (or at least we decided it's needed)
        # Realistically, the caller should call `mark_introduced` after sending, 
        # but for now we'll assume if we say yes, we're doing it.
        # However, to be safe, let's just return True and let caller handle.
        return True

    def mark_introduced(self, chat_jid: str):
        """Call this when we successfully send an intro."""
        self._last_intro_time[chat_jid] = datetime.now()

    def humanize_response(
        self,
        response: str,
        emotion: str,
        urgency: str,
        conversation_length: int,
        user_tone: str = "neutral"
    ) -> Dict[str, Any]:
        """
        Transform raw AI output into human-like text.
        """
        humanized_text = response

        # 1. Strip robotic prefixes if conversation is ongoing
        if conversation_length > 1:
            humanized_text = self._strip_prefixes(humanized_text)

        # 2. Adjust for urgency
        if urgency == "high":
            # high urgency -> shorter, punchier sentences
            humanized_text = self._shorten_sentences(humanized_text)

        # 3. Simulate typing time (heuristic)
        # Average reading speed ~20 chars/sec + thinking time
        typing_time = 1.0 + (len(humanized_text) / 25.0)

        return {
            "humanized_text": humanized_text,
            "typing_time_seconds": round(typing_time, 2),
            "original_text": response,
            "message_chunks": [humanized_text] # Simple single chunk for now
        }

    def detect_user_tone(self, message: str) -> str:
        """
        Simple heuristic to detect if user is formal or casual.
        """
        text = message.lower()
        if any(w in text for w in ["u", "ur", "thx", "pls", "lol", "k"]):
            return "casual"
        if len(text.split()) > 15 and any(w in text for w in ["regarding", "however", "therefore"]):
            return "formal"
        return "neutral"

    def _strip_prefixes(self, text: str) -> str:
        """Remove common robotic starter phrases."""
        cleaned = text.strip()
        for pattern in self.robotic_prefixes:
            # removing case-insensitive match at start of string
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        
        # Capitalize first letter if it got lowercased by stripping
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        return cleaned

    def _shorten_sentences(self, text: str) -> str:
        """Break long compound sentences for high urgency."""
        # Replace ", and " with ". "
        return text.replace(", and ", ". ").replace(", but ", ". ")
