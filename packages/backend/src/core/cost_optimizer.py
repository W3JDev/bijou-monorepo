"""
W3J Bijou AI - Cost Optimization Engine
======================================

Dramatically reduces API costs through:
- Smart caching with TTL
- Pattern-based response matching (no API call needed)
- Batch processing of similar questions
- Selective API triggers (only when confidence is low)
- Memory-first approach (check history before API)
- Request deduplication

Target: Reduce costs from $1/month to $0.10-0.20/month

Author: W3J Bijou AI
Version: 2.1.0
"""

import json
import hashlib
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum


class ResponseTriggerType(Enum):
    """Types of triggers for generating responses."""

    MEMORY_MATCH = "memory_match"  # Found similar in history
    PATTERN_MATCH = "pattern_match"  # Matched pre-defined pattern
    CACHE_HIT = "cache_hit"  # Found in cache
    API_REQUIRED = "api_required"  # Must call API
    TEMPLATE_MATCH = "template_match"  # Matched template


class CostOptimizer:
    """
    Smart cost optimization engine that minimizes API calls.
    """

    def __init__(self, cache_ttl_minutes: int = 1440):  # 24 hours default
        """
        Initialize cost optimizer.

        Args:
            cache_ttl_minutes: Cache time-to-live in minutes
        """
        self.cache_ttl_seconds = cache_ttl_minutes * 60
        self.response_cache = {}  # {hash: (response, timestamp, usage_count)}
        self.pattern_library = self._build_pattern_library()
        self.template_library = self._build_template_library()
        self.request_queue = []  # For batch processing
        self.stats = {
            "total_requests": 0,
            "api_calls": 0,
            "cache_hits": 0,
            "pattern_matches": 0,
            "template_matches": 0,
            "total_savings": 0.0,  # Estimated cost saved in USD
        }

    def should_call_api(
        self,
        message: str,
        emotion: str,
        confidence: float,
        conversation_history: Optional[List[str]] = None,
    ) -> Tuple[bool, ResponseTriggerType, Optional[str]]:
        """
        Determine if API call is needed or if we can use cached/pattern response.

        Args:
            message: Customer's message
            emotion: Detected emotion
            confidence: Emotion confidence score (0-1)
            conversation_history: Previous messages in conversation

        Returns:
            Tuple of (should_call_api, trigger_type, cached_response or None)
        """
        self.stats["total_requests"] += 1

        # Step 1: Check cache first (FASTEST - $0.00)
        cached_response = self._check_cache(message)
        if cached_response:
            self.stats["cache_hits"] += 1
            self.stats["total_savings"] += 0.0003  # ~$0.0003 per API call
            return False, ResponseTriggerType.CACHE_HIT, cached_response

        # Step 2: Check conversation history for similar patterns (FAST - $0.00)
        history_response = self._match_with_history(message, conversation_history)
        if history_response and confidence > 0.7:
            self.stats["pattern_matches"] += 1
            self.stats["total_savings"] += 0.0003
            return False, ResponseTriggerType.MEMORY_MATCH, history_response

        # Step 3: Check pattern library (INSTANT - $0.00)
        pattern_response = self._match_pattern(message, emotion)
        if pattern_response and confidence > 0.75:
            self.stats["pattern_matches"] += 1
            self.stats["total_savings"] += 0.0003
            return False, ResponseTriggerType.PATTERN_MATCH, pattern_response

        # Step 4: Check template library (INSTANT - $0.00)
        template_response = self._match_template(message, emotion)
        if template_response and confidence > 0.8:
            self.stats["template_matches"] += 1
            self.stats["total_savings"] += 0.0003
            return False, ResponseTriggerType.TEMPLATE_MATCH, template_response

        # Step 5: High confidence + neutral emotion = skip API for simple cases
        if confidence > 0.85 and emotion == "neutral":
            simple_response = self._generate_simple_response(message)
            if simple_response:
                self.stats["pattern_matches"] += 1
                self.stats["total_savings"] += 0.0003
                return False, ResponseTriggerType.PATTERN_MATCH, simple_response

        # Otherwise, we need to call API
        self.stats["api_calls"] += 1
        return True, ResponseTriggerType.API_REQUIRED, None

    def _check_cache(self, message: str) -> Optional[str]:
        """Check if message response is in cache."""
        message_hash = self._hash_message(message)

        if message_hash in self.response_cache:
            response, timestamp, usage_count = self.response_cache[message_hash]

            # Check if cache is still valid
            if time.time() - timestamp < self.cache_ttl_seconds:
                # Update usage stats
                self.response_cache[message_hash] = (
                    response,
                    timestamp,
                    usage_count + 1,
                )
                return response

            # Cache expired, remove it
            del self.response_cache[message_hash]

        return None

    def cache_response(self, message: str, response: str) -> None:
        """Store response in cache."""
        message_hash = self._hash_message(message)
        self.response_cache[message_hash] = (response, time.time(), 1)

    def _match_with_history(
        self, message: str, history: Optional[List[str]]
    ) -> Optional[str]:
        """Find similar message in conversation history."""
        if not history or len(history) < 2:
            return None

        message_lower = message.lower()
        similarity_threshold = 0.7

        for prev_message in history[-10:]:  # Check last 10 messages
            similarity = self._calculate_similarity(message_lower, prev_message.lower())
            if similarity > similarity_threshold:
                # Found similar message, could reuse or adapt response
                return None  # For now, don't auto-reuse

        return None

    def _match_pattern(self, message: str, emotion: str) -> Optional[str]:
        """Match message against pattern library."""
        message_lower = message.lower()

        for pattern_name, pattern_data in self.pattern_library.items():
            keywords = pattern_data["keywords"]
            if any(kw in message_lower for kw in keywords):
                # Check emotion match
                if (
                    emotion in pattern_data["emotions"]
                    or "all" in pattern_data["emotions"]
                ):
                    return pattern_data["response"]

        return None

    def _match_template(self, message: str, emotion: str) -> Optional[str]:
        """Match message against response templates."""
        message_lower = message.lower()

        for template_name, template_data in self.template_library.items():
            if self._fuzzy_match(message_lower, template_data["triggers"]):
                response_template = template_data["response"]
                # Could inject variables here (name, etc.)
                return response_template

        return None

    def _generate_simple_response(self, message: str) -> Optional[str]:
        """Generate simple response for straightforward questions."""
        message_lower = message.lower()

        # Greeting detection
        if any(g in message_lower for g in ["hi", "hello", "hey"]):
            return "Hey there! 👋 How can I help you today?"

        # Help/support detection
        if any(h in message_lower for h in ["help", "support", "assist"]):
            return "I'm here to help! What do you need assistance with?"

        # Basic status
        if any(
            s in message_lower
            for s in [
                "how are you",
                "how r u",
                "whats up",
                "what's up",
                "sup",
            ]
        ):
            return "All good here! 😊 How about you?"

        return None

    def _hash_message(self, message: str) -> str:
        """Create hash of message for cache key."""
        return hashlib.md5(message.lower().strip().encode()).hexdigest()

    def _calculate_similarity(self, msg1: str, msg2: str) -> float:
        """Calculate similarity between two messages (0-1)."""
        # Simple word overlap approach
        words1 = set(msg1.split())
        words2 = set(msg2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _fuzzy_match(self, message: str, triggers: List[str]) -> bool:
        """Fuzzy match message against list of triggers."""
        for trigger in triggers:
            if self._calculate_similarity(message, trigger) > 0.6:
                return True
        return False

    def _build_pattern_library(self) -> Dict[str, Any]:
        """Build library of common patterns and responses."""
        return {
            "greeting": {
                "keywords": ["hi", "hello", "hey", "greetings"],
                "emotions": ["neutral", "happy"],
                "response": "Hey! 👋 What can I help you with today?",
            },
            "order_status": {
                "keywords": ["order", "where", "track", "package", "deliver"],
                "emotions": ["neutral", "anger", "sad"],
                "response": "Let me check your order status for you. Can you share your order number?",
            },
            "billing": {
                "keywords": ["charge", "bill", "payment", "refund", "money"],
                "emotions": ["anger", "fear"],
                "response": "I can definitely help with that! Can you tell me more about the billing issue?",
            },
            "technical": {
                "keywords": ["broken", "error", "not work", "crash", "bug"],
                "emotions": ["anger", "frustration"],
                "response": "Sorry you're having tech issues! Let's fix this together. What exactly happened?",
            },
            "account": {
                "keywords": ["login", "password", "account", "access", "sign in"],
                "emotions": ["fear", "anger"],
                "response": "Let's get you back into your account. What's the issue you're facing?",
            },
            "thank_you": {
                "keywords": ["thank", "thanks", "thx", "appreciate"],
                "emotions": ["happy", "neutral"],
                "response": "You're welcome! Happy to help! 😊",
            },
        }

    def _build_template_library(self) -> Dict[str, Any]:
        """Build library of response templates."""
        return {
            "simple_greeting": {
                "triggers": ["hello", "hi", "hey"],
                "response": "Hi there! 👋 How can I help?",
            },
            "help_request": {
                "triggers": ["can you help", "i need help", "help me"],
                "response": "Absolutely! I'm here to help. What do you need?",
            },
            "availability": {
                "triggers": ["are you available", "are you there"],
                "response": "I'm here 24/7! What's on your mind?",
            },
        }

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get cost optimization statistics."""
        total_requests = self.stats["total_requests"]
        api_calls = self.stats["api_calls"]
        api_percentage = (api_calls / total_requests * 100) if total_requests > 0 else 0

        # Gemini API pricing: ~$0.075 per 1M input tokens, avg 100 tokens = $0.0000075 per call
        estimated_cost_per_call = 0.0003  # Conservative estimate
        total_cost_without_optimization = total_requests * estimated_cost_per_call
        actual_cost = api_calls * estimated_cost_per_call

        return {
            "total_requests": total_requests,
            "api_calls": api_calls,
            "cache_hits": self.stats["cache_hits"],
            "pattern_matches": self.stats["pattern_matches"],
            "template_matches": self.stats["template_matches"],
            "api_call_percentage": f"{api_percentage:.1f}%",
            "estimated_savings": f"${self.stats['total_savings']:.4f}",
            "total_cost_without_optimization": f"${total_cost_without_optimization:.4f}",
            "actual_cost_with_optimization": f"${actual_cost:.4f}",
            "monthly_projection": {
                "without_optimization": f"${total_cost_without_optimization * 30000:.2f}",
                "with_optimization": f"${actual_cost * 30000:.2f}",
            },
        }

    def batch_similar_requests(
        self, requests: List[Dict[str, str]]
    ) -> List[List[Dict[str, str]]]:
        """
        Group similar requests for batch processing.

        Args:
            requests: List of requests

        Returns:
            List of request batches (similar grouped together)
        """
        batches = []
        processed = set()

        for i, req1 in enumerate(requests):
            if i in processed:
                continue

            batch = [req1]
            processed.add(i)

            for j, req2 in enumerate(requests[i + 1 :], start=i + 1):
                if j not in processed:
                    similarity = self._calculate_similarity(
                        req1["message"], req2["message"]
                    )
                    if similarity > 0.6:
                        batch.append(req2)
                        processed.add(j)

            batches.append(batch)

        return batches


class SmartMemoryTrigger:
    """
    Triggers responses based on conversation memory to avoid unnecessary API calls.
    Implements a 3-tier confidence system.
    """

    def __init__(self, memory_system):
        """
        Initialize smart memory trigger.

        Args:
            memory_system: ConversationMemory instance
        """
        self.memory = memory_system
        self.confidence_tiers = {
            "high": 0.85,  # Use memory response directly
            "medium": 0.65,  # Use memory response with verification
            "low": 0.45,  # Use memory response + ask for confirmation
        }

    def get_cached_response(
        self, customer_jid: str, message: str
    ) -> Tuple[Optional[str], float]:
        """
        Try to get response from conversation memory.

        Args:
            customer_jid: Customer's WhatsApp JID
            message: Current message

        Returns:
            Tuple of (response, confidence) or (None, 0)
        """
        context = self.memory.get_context_summary(customer_jid)
        if not context:
            return None, 0

        # Check if we've seen similar issues before
        similar_issues = self._find_similar_issues(context, message)
        if similar_issues:
            confidence = similar_issues["confidence"]
            response = similar_issues["response"]
            return response, confidence

        return None, 0

    def _find_similar_issues(
        self, context: Dict[str, Any], message: str
    ) -> Optional[Dict[str, Any]]:
        """Find similar issues in conversation context."""
        # This would search through conversation history for similar patterns
        # Implementation depends on memory system structure
        return None
