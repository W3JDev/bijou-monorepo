"""
TRACE Agent 2: Causal Analysis Engine (CAE)
===========================================

Analyzes ROOT CAUSES of customer's emotional state using dual-granularity:
1. Local Triggers - Word-level signals (e.g., "delayed", "broken", "wait")
2. Global Cause - Situational summary (e.g., "Customer experiencing shipping delay")

Also identifies:
- Unmet needs (what customer wants)
- Urgency level (low/medium/high/critical)
- Situation type (billing/shipping/technical/etc.)

Author: W3J Bijou AI
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


class CausalAnalysisEngine:
    """
    TRACE Agent 2: Causal Analysis Engine

    Analyzes why the customer feels the way they do and what they need.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Causal Analysis Engine.

        Args:
            api_key: Google Gemini API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)  # type: ignore
        self.model = genai.GenerativeModel("gemini-2.5-flash")  # type: ignore

    def analyze_cause(
        self,
        message: str,
        emotion: str,
        emotion_confidence: float,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze root cause of customer's emotional state.

        Args:
            message: Customer's message
            emotion: Detected emotion (from ASI)
            emotion_confidence: Emotion confidence score
            conversation_history: Previous messages

        Returns:
            dict with:
                - local_triggers: List of word-level emotional triggers
                - global_cause: High-level situation summary
                - unmet_need: What customer wants/needs
                - situation_type: Category (billing/shipping/technical/etc.)
                - urgency_level: low/medium/high/critical
        """
        # Build context
        history_text = ""
        if conversation_history:
            recent = conversation_history[-5:]
            history_text = "\n".join(
                [
                    f"- {msg.get('sender', 'unknown')}: {msg.get('content', '')}"
                    for msg in recent
                ]
            )

        # Create causal analysis prompt
        prompt = f"""You are an expert at understanding WHY customers feel the way they do. Analyze this customer service situation.

CUSTOMER MESSAGE:
{message}

DETECTED EMOTION:
{emotion} (confidence: {emotion_confidence:.2f})

CONVERSATION HISTORY:
{history_text if history_text else "No prior context"}

YOUR TASK:
Perform dual-granularity causal analysis:

1. LOCAL TRIGGERS (word-level signals):
   - Identify specific words/phrases that triggered the emotion
   - Examples: "delayed", "broken", "waiting", "charged twice", "doesn't work"

2. GLOBAL CAUSE (situational summary):
   - High-level explanation of what's happening
   - Example: "Customer ordered product 2 weeks ago, experiencing shipping delay"

3. UNMET NEED:
   - What does the customer ACTUALLY want/need?
   - Examples: "Track package location", "Get refund", "Fix technical issue"

4. SITUATION TYPE:
   - Categorize: shipping | billing | technical | account | product | general

5. URGENCY LEVEL:
   - low: General question, no time pressure
   - medium: Issue needs resolution but not urgent
   - high: Customer frustrated, needs quick response
   - critical: Blocking issue, immediate action required

Respond in JSON format:
{{
  "local_triggers": ["delayed", "2 weeks", "still nothing"],
  "global_cause": "Customer ordered product 2 weeks ago, experiencing shipping delay",
  "unmet_need": "Information about package location and delivery timeline",
  "situation_type": "shipping",
  "urgency_level": "high"
}}"""

        try:
            # Generate causal analysis with timeout
            response = self.model.generate_content(prompt)

            # Check if response is valid
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")

            result = self._parse_json_response(response.text)

            # Add metadata
            result["timestamp"] = datetime.now().isoformat()

            return result

        except Exception as e:
            logger.error(f"Error in causal analysis: {e}")
            # Fallback to rule-based analysis
            return self._fallback_analysis(message, emotion)

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from Gemini response.

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed JSON dictionary
        """
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())

    def _fallback_analysis(self, message: str, emotion: str) -> Dict[str, Any]:
        """
        Simple rule-based causal analysis fallback.

        Args:
            message: Customer's message
            emotion: Detected emotion

        Returns:
            Basic causal analysis
        """
        message_lower = message.lower()

        # Detect situation type
        situation_keywords = {
            "shipping": ["ship", "deliver", "package", "track", "order", "delay"],
            "billing": ["charge", "bill", "payment", "refund", "money", "pay"],
            "technical": ["not work", "broken", "error", "bug", "crash", "problem"],
            "account": ["login", "password", "account", "access", "sign in"],
            "product": ["how to", "use", "feature", "question", "manual"],
        }

        situation_type = "general"
        for sit_type, keywords in situation_keywords.items():
            if any(kw in message_lower for kw in keywords):
                situation_type = sit_type
                break

        # Extract triggers
        trigger_words = [
            "delay",
            "wait",
            "still",
            "not",
            "broken",
            "wrong",
            "problem",
            "issue",
            "error",
            "charge",
            "refund",
            "help",
        ]
        local_triggers = [word for word in trigger_words if word in message_lower]

        # Determine urgency
        urgency = "medium"
        if emotion in ["anger", "fear"] or "!!" in message or message.isupper():
            urgency = "high"
        elif "?" in message and emotion == "neutral":
            urgency = "low"

        return {
            "local_triggers": local_triggers or ["customer inquiry"],
            "global_cause": f"Customer {emotion} about {situation_type} issue",
            "unmet_need": f"Resolution for {situation_type} concern",
            "situation_type": situation_type,
            "urgency_level": urgency,
            "timestamp": datetime.now().isoformat(),
            "fallback": True,
        }


# Example usage
if __name__ == "__main__":
    # Initialize CAE
    cae = CausalAnalysisEngine()

    # Test case: Analyze frustrated customer
    result = cae.analyze_cause(
        message="Where is my package?! I ordered 2 weeks ago and STILL nothing!",
        emotion="anger",
        emotion_confidence=0.92,
        conversation_history=None,
    )

    print("=== Causal Analysis Result ===")
    print(f"Local Triggers: {', '.join(result['local_triggers'])}")
    print(f"Global Cause: {result['global_cause']}")
    print(f"Unmet Need: {result['unmet_need']}")
    print(f"Situation Type: {result['situation_type']}")
    print(f"Urgency Level: {result['urgency_level']}")
