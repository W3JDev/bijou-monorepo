"""
TRACE Agent 3: Strategic Response Planner (SRP)
===============================================

Determines the optimal empathetic strategy and retrieves relevant knowledge.

Strategy Types:
1. Emotional Reaction (ER) - Mirror and validate emotions
2. Interpretation (IN) - Reframe perspective with understanding
3. Exploration (EX) - Guide customer to clarify needs

Uses RAG (Retrieval-Augmented Generation) to find:
- Similar past conversations
- FAQ answers
- Product knowledge
- Best practices

Author: W3J Bijou AI
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import google.generativeai as genai


class StrategicResponsePlanner:
    """
    TRACE Agent 3: Strategic Response Planner

    Selects empathetic strategy and retrieves relevant knowledge
    from the knowledge base (Google Sheets) using RAG.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Strategic Response Planner.

        Args:
            api_key: Google Gemini API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)  # type: ignore
        self.model = genai.GenerativeModel("gemini-2.5-flash")  # type: ignore

        # Knowledge base (will be replaced with Google Sheets RAG)
        self.knowledge_base = self._load_default_knowledge()

    def _load_default_knowledge(self) -> Dict[str, List[str]]:
        """
        Load default knowledge base.

        In production, this will be replaced with Google Sheets integration.

        Returns:
            Dictionary of knowledge categories and responses
        """
        return {
            "shipping_delays": [
                "Standard shipping typically takes 3-5 business days",
                "Check tracking number at track.example.com",
                "Contact support if delayed >7 days",
            ],
            "refund_policy": [
                "Full refunds within 30 days of purchase",
                "Refunds processed in 5-7 business days",
                "Contact billing@example.com for refund status",
            ],
            "account_issues": [
                "Reset password at account.example.com/reset",
                "Check spam folder for verification email",
                "Contact support@example.com if issues persist",
            ],
            "product_questions": [
                "Consult product manual at docs.example.com",
                "Watch tutorial videos at youtube.com/example",
                "Live chat available 9am-5pm EST",
            ],
        }

    def plan_strategy(
        self,
        message: str,
        emotion: str,
        emotion_confidence: float,
        global_cause: str,
        unmet_need: str,
        urgency_level: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Select optimal empathetic response strategy.

        Args:
            message: Customer's message
            emotion: Detected emotion (from ASI)
            emotion_confidence: Confidence score 0-1
            global_cause: Situational cause (from CAE)
            unmet_need: Customer's unmet need (from CAE)
            urgency_level: low/medium/high/critical
            conversation_history: Previous messages for context

        Returns:
            dict with:
                - strategy: 'emotional_reaction' | 'interpretation' | 'exploration'
                - rationale: Why this strategy was chosen
                - knowledge_retrieved: Relevant KB entries
                - response_guidance: How to craft the response
                - behavioral_taxonomy: Empathy behaviors to use
                - confidence: Strategy confidence score (0-1)
        """
        # Build context
        history_text = ""
        if conversation_history:
            recent = conversation_history[-5:]  # Last 5 messages
            history_text = "\n".join(
                [
                    f"- {msg.get('sender', 'unknown')}: {msg.get('content', '')}"
                    for msg in recent
                ]
            )

        # Retrieve relevant knowledge
        knowledge = self._retrieve_knowledge(message, global_cause, unmet_need)

        # Create strategy selection prompt
        prompt = f"""You are an empathy strategy expert. Analyze this customer support situation and select the optimal response strategy.

CUSTOMER MESSAGE:
{message}

EMOTIONAL STATE:
- Emotion: {emotion} (confidence: {emotion_confidence:.2f})
- Root Cause: {global_cause}
- Unmet Need: {unmet_need}
- Urgency: {urgency_level}

CONVERSATION HISTORY:
{history_text if history_text else "No prior messages"}

AVAILABLE KNOWLEDGE:
{json.dumps(knowledge, indent=2)}

STRATEGY OPTIONS:

1. EMOTIONAL REACTION (ER)
   - When: Strong negative emotions (anger, fear, sadness)
   - Goal: Validate feelings, show understanding
   - Behaviors: Mirroring, Empathic Concern, Consolation
   - Example: "I completely understand how frustrating this must be for you..."

2. INTERPRETATION (IN)
   - When: Customer needs perspective shift or reassurance
   - Goal: Reframe situation with empathy
   - Behaviors: Interpretation, Altruistic Helping
   - Example: "I can see why you'd feel that way. Let me help clarify..."

3. EXPLORATION (EX)
   - When: Unclear needs or complex situations
   - Goal: Guide customer to clarify their needs
   - Behaviors: Exploration, Acknowledgment
   - Example: "Thank you for sharing. To help you better, could you tell me more about..."

YOUR TASK:
Select ONE strategy and provide:
1. Strategy name (emotional_reaction, interpretation, or exploration)
2. Rationale (2-3 sentences explaining WHY)
3. Behavioral taxonomy to use (list 2-3 from above)
4. Response guidance (2-3 bullet points on how to craft the response)
5. Confidence score (0-1, how sure you are this is the right strategy)

Respond in JSON format:
{{
  "strategy": "emotional_reaction|interpretation|exploration",
  "rationale": "explanation here",
  "behavioral_taxonomy": ["Mirroring", "Empathic Concern"],
  "response_guidance": ["point 1", "point 2", "point 3"],
  "confidence": 0.85
}}"""

        try:
            # Generate strategic response
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)

            # Add knowledge to result
            result["knowledge_retrieved"] = knowledge
            result["timestamp"] = datetime.now().isoformat()

            return result

        except Exception as e:
            print(f"Error in strategy planning: {e}")
            # Fallback strategy
            return self._fallback_strategy(emotion, urgency_level, knowledge)

    def _retrieve_knowledge(
        self, message: str, global_cause: str, unmet_need: str
    ) -> Dict[str, List[str]]:
        """
        Retrieve relevant knowledge from the knowledge base.

        Uses simple keyword matching. In production, this will use
        semantic search with embeddings.

        Args:
            message: Customer's message
            global_cause: Situational cause
            unmet_need: Customer's unmet need

        Returns:
            Dictionary of relevant knowledge entries
        """
        text_to_search = f"{message} {global_cause} {unmet_need}".lower()

        relevant_knowledge = {}

        # Simple keyword matching
        keywords = {
            "shipping_delays": [
                "ship",
                "deliver",
                "track",
                "delay",
                "package",
                "order",
            ],
            "refund_policy": ["refund", "money back", "return", "cancel", "reimburs"],
            "account_issues": [
                "login",
                "password",
                "account",
                "access",
                "verify",
                "email",
            ],
            "product_questions": [
                "how to",
                "how do",
                "use",
                "manual",
                "tutorial",
                "help",
            ],
        }

        for category, category_keywords in keywords.items():
            if any(keyword in text_to_search for keyword in category_keywords):
                relevant_knowledge[category] = self.knowledge_base.get(category, [])

        # If no matches, return general helpful info
        if not relevant_knowledge:
            relevant_knowledge["general"] = [
                "We're here to help with any questions",
                "Support available via email: support@example.com",
                "Check our FAQ at help.example.com",
            ]

        return relevant_knowledge

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

    def _fallback_strategy(
        self, emotion: str, urgency_level: str, knowledge: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Fallback strategy when AI fails.

        Args:
            emotion: Detected emotion
            urgency_level: Urgency level
            knowledge: Retrieved knowledge

        Returns:
            Default strategy
        """
        # Rule-based fallback
        negative_emotions = ["anger", "fear", "sadness", "disgust"]

        if emotion.lower() in negative_emotions or urgency_level in [
            "high",
            "critical",
        ]:
            strategy = "emotional_reaction"
            rationale = "Customer shows strong negative emotion, validation needed"
            behaviors = ["Mirroring", "Empathic Concern", "Consolation"]
        else:
            strategy = "interpretation"
            rationale = "Standard situation, provide helpful reframing"
            behaviors = ["Interpretation", "Altruistic Helping"]

        return {
            "strategy": strategy,
            "rationale": rationale,
            "behavioral_taxonomy": behaviors,
            "response_guidance": [
                "Acknowledge the customer's situation",
                "Provide relevant information from knowledge base",
                "Offer clear next steps",
            ],
            "knowledge_retrieved": knowledge,
            "confidence": 0.70,
            "timestamp": datetime.now().isoformat(),
            "fallback": True,
        }

    def update_knowledge_base(self, category: str, entries: List[str]):
        """
        Update knowledge base with new entries.

        In production, this will sync with Google Sheets.

        Args:
            category: Knowledge category
            entries: List of knowledge entries
        """
        self.knowledge_base[category] = entries
        print(f"Updated knowledge base: {category} ({len(entries)} entries)")


# Example usage
if __name__ == "__main__":
    # Initialize SRP
    srp = StrategicResponsePlanner()

    # Test case: Frustrated customer with shipping delay
    result = srp.plan_strategy(
        message="Where is my package?! I ordered 2 weeks ago and still nothing!",
        emotion="anger",
        emotion_confidence=0.92,
        global_cause="Customer ordered product 2 weeks ago, experiencing shipping delay",
        unmet_need="Information about package location and delivery timeline",
        urgency_level="high",
        conversation_history=None,
    )

    print("=== Strategic Response Plan ===")
    print(f"Strategy: {result['strategy']}")
    print(f"Rationale: {result['rationale']}")
    print(f"Behavioral Taxonomy: {', '.join(result['behavioral_taxonomy'])}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"\nResponse Guidance:")
    for i, guidance in enumerate(result["response_guidance"], 1):
        print(f"  {i}. {guidance}")
    print(f"\nKnowledge Retrieved:")
    for category, entries in result["knowledge_retrieved"].items():
        print(f"  {category}:")
        for entry in entries:
            print(f"    - {entry}")
