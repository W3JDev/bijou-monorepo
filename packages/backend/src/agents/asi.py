"""
TRACE Agent 1: Affective State Identifier (ASI)
===============================================

Detects emotional state using Ekman's 6 universal emotions:
1. Joy - Happiness, pleasure, contentment
2. Anger - Frustration, irritation, rage
3. Sadness - Disappointment, grief, sorrow
4. Fear - Worry, anxiety, concern
5. Disgust - Displeasure, revulsion
6. Surprise - Astonishment, shock
7. Neutral - No strong emotion detected

Target: ≥44% emotion accuracy (I-ACC metric from research papers)

Author: W3J Bijou AI
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


class AffectiveStateIdentifier:
    """
    TRACE Agent 1: Affective State Identifier

    Detects customer's emotional state from message text using
    Ekman's universal emotions model.
    """

    EKMAN_EMOTIONS = [
        "joy",
        "anger",
        "sadness",
        "fear",
        "disgust",
        "surprise",
        "neutral",
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Affective State Identifier.

        Args:
            api_key: Google Gemini API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def identify_emotion(
        self, message: str, conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Identify primary emotion from customer message.

        Args:
            message: Customer's message text
            conversation_history: Previous messages for context

        Returns:
            dict with:
                - emotion: Primary emotion (from EKMAN_EMOTIONS)
                - confidence: Confidence score 0-1
                - emotional_cues: List of words/phrases that triggered detection
                - reasoning: Explanation of detection
                - intensity: low/medium/high
        """
        # Build context from history
        history_text = ""
        if conversation_history:
            recent = conversation_history[-5:]  # Last 5 messages
            history_text = "\n".join(
                [
                    f"- {msg.get('sender', 'unknown')}: {msg.get('content', '')}"
                    for msg in recent
                ]
            )

        # Create emotion detection prompt
        prompt = f"""You are an expert emotion analyst. Analyze this customer service message and identify the PRIMARY emotion.

CUSTOMER MESSAGE:
{message}

CONVERSATION HISTORY:
{history_text if history_text else "No prior context"}

EMOTION OPTIONS (Ekman's Universal Emotions):
1. joy - Happiness, pleasure, satisfaction, delight
2. anger - Frustration, irritation, annoyance, rage
3. sadness - Disappointment, sorrow, grief, unhappiness
4. fear - Worry, anxiety, concern, apprehension
5. disgust - Displeasure, revulsion, distaste
6. surprise - Astonishment, shock, unexpectedness
7. neutral - No strong emotion, calm, matter-of-fact

YOUR TASK:
1. Identify the PRIMARY emotion (choose ONE from above)
2. Rate confidence (0-1, how sure you are)
3. List emotional cues (specific words/phrases that indicate the emotion)
4. Provide brief reasoning
5. Rate intensity (low/medium/high)

GUIDELINES:
- Focus on EXPLICIT emotional signals (exclamation marks, caps, strong words)
- Consider context from conversation history
- If multiple emotions, choose the DOMINANT one
- Use "neutral" only if truly no emotion is present

Respond in JSON format:
{{
  "emotion": "one of the 7 emotions above",
  "confidence": 0.85,
  "emotional_cues": ["!!", "frustrated", "STILL waiting"],
  "reasoning": "Brief explanation of why this emotion was detected",
  "intensity": "low|medium|high"
}}"""

        try:
            # Generate emotion analysis with timeout
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)

            # Validate emotion
            if result["emotion"].lower() not in self.EKMAN_EMOTIONS:
                result["emotion"] = "neutral"

            # Add metadata
            result["timestamp"] = datetime.now().isoformat()
            result["emotion"] = result["emotion"].lower()

            return result

        except Exception as e:
            logger.error(f"Error in emotion detection: {e}")
            # Fallback to simple rule-based detection
            return self._fallback_detection(message)

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

    def _fallback_detection(self, message: str) -> Dict[str, Any]:
        """
        Simple rule-based emotion detection fallback.

        Args:
            message: Customer's message

        Returns:
            Basic emotion detection result
        """
        message_lower = message.lower()

        # Simple keyword matching
        anger_words = [
            "angry",
            "frustrated",
            "terrible",
            "horrible",
            "worst",
            "unacceptable",
            "!!",
        ]
        sadness_words = ["sad", "disappointed", "unhappy", "sorry", "upset"]
        fear_words = ["worried", "concerned", "afraid", "nervous", "anxious"]
        joy_words = ["happy", "great", "excellent", "thanks", "perfect", "love"]

        emotion = "neutral"
        cues = []
        confidence = 0.6

        if any(word in message_lower for word in anger_words) or "!" in message:
            emotion = "anger"
            cues = [word for word in anger_words if word in message_lower]
            if "!!" in message or message.isupper():
                confidence = 0.8
        elif any(word in message_lower for word in sadness_words):
            emotion = "sadness"
            cues = [word for word in sadness_words if word in message_lower]
        elif any(word in message_lower for word in fear_words):
            emotion = "fear"
            cues = [word for word in fear_words if word in message_lower]
        elif any(word in message_lower for word in joy_words):
            emotion = "joy"
            cues = [word for word in joy_words if word in message_lower]

        return {
            "emotion": emotion,
            "confidence": confidence,
            "emotional_cues": cues or ["neutral tone"],
            "reasoning": f"Rule-based detection identified {emotion} based on keywords",
            "intensity": "medium",
            "timestamp": datetime.now().isoformat(),
            "fallback": True,
        }


# Example usage
if __name__ == "__main__":
    # Initialize ASI
    asi = AffectiveStateIdentifier()

    # Test case: Angry customer
    result = asi.identify_emotion(
        "Where is my package?! I ordered 2 weeks ago and STILL nothing!",
        conversation_history=None,
    )

    print("=== Emotion Detection Result ===")
    print(f"Emotion: {result['emotion'].title()}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Intensity: {result['intensity']}")
    print(f"Emotional Cues: {', '.join(result['emotional_cues'])}")
    print(f"Reasoning: {result['reasoning']}")
