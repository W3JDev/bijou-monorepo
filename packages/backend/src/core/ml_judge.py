"""
W3J Bijou AI - ML Judge for Quality Assessment
==============================================

AI/ML Judge that:
- Evaluates response quality automatically
- Scores CSAT predictions
- Detects mistakes and triggers apologies
- Provides feedback for continuous learning
- Tracks improvement over time

Uses lightweight models to minimize costs.

Author: W3J Bijou AI
Version: 2.1.0
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class QualityScore(Enum):
    """Response quality levels."""

    EXCELLENT = 5
    GOOD = 4
    ACCEPTABLE = 3
    POOR = 2
    UNACCEPTABLE = 1


class MLJudge:
    """
    AI/ML Judge for evaluating response quality and triggering improvements.
    """

    def __init__(self):
        """Initialize ML Judge."""
        self.evaluation_history = []
        self.mistake_patterns = self._load_mistake_patterns()
        self.quality_thresholds = {
            "empathy_score": 0.7,
            "clarity_score": 0.8,
            "actionability_score": 0.7,
            "tone_appropriateness": 0.75,
        }

    def evaluate_response(
        self,
        user_message: str,
        bot_response: str,
        emotion: str,
        urgency: str,
        conversation_history: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation of bot response quality.

        Args:
            user_message: Customer's message
            bot_response: Bot's response
            emotion: Detected emotion
            urgency: Urgency level
            conversation_history: Previous messages

        Returns:
            Evaluation results with scores and recommendations
        """

        # Run all evaluation criteria
        empathy_score = self._evaluate_empathy(bot_response, emotion)
        clarity_score = self._evaluate_clarity(bot_response)
        actionability_score = self._evaluate_actionability(bot_response, urgency)
        tone_score = self._evaluate_tone(bot_response, emotion, urgency)
        mistake_detected = self._detect_mistakes(
            user_message, bot_response, conversation_history
        )

        # Calculate overall quality score (1-5 scale)
        overall_score = self._calculate_overall_score(
            empathy_score, clarity_score, actionability_score, tone_score
        )

        # Determine if response needs improvement
        needs_improvement = overall_score < 3.5 or mistake_detected["has_mistake"]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            empathy_score,
            clarity_score,
            actionability_score,
            tone_score,
            mistake_detected,
        )

        evaluation = {
            "overall_score": overall_score,
            "quality_level": self._get_quality_level(overall_score),
            "scores": {
                "empathy": empathy_score,
                "clarity": clarity_score,
                "actionability": actionability_score,
                "tone_appropriateness": tone_score,
            },
            "mistake_detected": mistake_detected,
            "needs_improvement": needs_improvement,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }

        # Store for learning
        self.evaluation_history.append(evaluation)

        return evaluation

    def _evaluate_empathy(self, response: str, emotion: str) -> float:
        """
        Evaluate empathy level in response (0-1).
        """
        response_lower = response.lower()

        # Empathy indicators
        empathy_phrases = [
            "understand",
            "sorry",
            "apologize",
            "hear you",
            "i get it",
            "makes sense",
            "i see",
            "feel",
            "frustrating",
            "concerning",
        ]

        # Emotion-specific empathy
        emotion_empathy = {
            "anger": ["frustrated", "upset", "disappointing"],
            "sad": ["sorry to hear", "unfortunate", "regret"],
            "fear": ["understand your concern", "reassure", "safe"],
        }

        score = 0.0

        # Check for empathy phrases
        empathy_count = sum(1 for phrase in empathy_phrases if phrase in response_lower)
        score += min(0.5, empathy_count * 0.1)

        # Check emotion-appropriate empathy
        if emotion in emotion_empathy:
            emotion_count = sum(
                1 for phrase in emotion_empathy[emotion] if phrase in response_lower
            )
            score += min(0.5, emotion_count * 0.15)

        return min(1.0, score)

    def _evaluate_clarity(self, response: str) -> float:
        """
        Evaluate clarity and readability (0-1).
        """
        # Check sentence length (shorter is better for WhatsApp)
        sentences = re.split(r"[.!?]+", response)
        avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / max(
            len(sentences), 1
        )

        clarity_score = 1.0

        # Penalize very long sentences
        if avg_sentence_length > 25:
            clarity_score -= 0.3
        elif avg_sentence_length > 15:
            clarity_score -= 0.1

        # Check for jargon/complex words
        complex_words = [
            "utilize",
            "facilitate",
            "aforementioned",
            "inconvenience",
            "subsequently",
            "heretofore",
        ]
        jargon_count = sum(1 for word in complex_words if word in response.lower())
        clarity_score -= jargon_count * 0.1

        # Check for structure (paragraphs)
        has_structure = "\n" in response or len(sentences) > 2
        if has_structure:
            clarity_score += 0.1

        return max(0.0, min(1.0, clarity_score))

    def _evaluate_actionability(self, response: str, urgency: str) -> float:
        """
        Evaluate if response provides actionable next steps (0-1).
        """
        response_lower = response.lower()

        # Action indicators
        action_phrases = [
            "can you",
            "could you",
            "please",
            "let me",
            "i'll",
            "i will",
            "next step",
            "here's what",
            "you can",
            "click",
            "go to",
        ]

        action_count = sum(1 for phrase in action_phrases if phrase in response_lower)

        score = min(0.8, action_count * 0.2)

        # Urgency check - high urgency should have immediate actions
        if urgency in ["high", "critical"]:
            has_immediate_action = any(
                phrase in response_lower
                for phrase in ["right away", "immediately", "asap", "now", "urgent"]
            )
            if has_immediate_action:
                score += 0.2

        return min(1.0, score)

    def _evaluate_tone(self, response: str, emotion: str, urgency: str) -> float:
        """
        Evaluate if tone matches customer's emotion and urgency (0-1).
        """
        response_lower = response.lower()

        # Check for inappropriate cheerfulness in negative emotions
        if emotion in ["anger", "sad", "fear"]:
            overly_happy = sum(
                1 for emoji in ["😄", "😁", "🎉", "✨"] if emoji in response
            )
            if overly_happy > 0:
                return 0.3  # Inappropriate tone

        # Check for urgency matching
        if urgency in ["high", "critical"]:
            has_urgency_language = any(
                word in response_lower
                for word in ["quickly", "asap", "priority", "urgent", "right away"]
            )
            if not has_urgency_language:
                return 0.5  # Missing urgency

        # Check for professionalism
        has_profanity = any(
            word in response_lower for word in ["damn", "hell", "crap", "wtf"]
        )
        if has_profanity:
            return 0.2  # Unprofessional

        return 0.9  # Good tone

    def _detect_mistakes(
        self, user_message: str, bot_response: str, history: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect common mistakes in responses.
        """
        mistakes = []

        # Check for contradictions with history
        if history and len(history) > 2:
            # Simple contradiction check (can be enhanced)
            if "yes" in bot_response.lower() and any(
                "no" in h.lower() for h in history[-3:]
            ):
                mistakes.append(
                    {
                        "type": "contradiction",
                        "description": "Response contradicts previous statements",
                        "severity": "high",
                    }
                )

        # Check for ignoring user's question
        if "?" in user_message and "?" not in bot_response:
            # User asked a question, bot should address it
            if not any(
                phrase in bot_response.lower()
                for phrase in ["here's", "the answer", "yes", "no", "can you"]
            ):
                mistakes.append(
                    {
                        "type": "ignored_question",
                        "description": "Failed to address user's question",
                        "severity": "medium",
                    }
                )

        # Check for hallucination (making up information)
        specific_info_patterns = [
            r"\$\d+\.\d{2}",  # Specific prices
            r"\d{1,2}:\d{2}\s?(AM|PM)",  # Specific times
            r"order\s+#?\d+",  # Order numbers
        ]
        for pattern in specific_info_patterns:
            if re.search(pattern, bot_response, re.IGNORECASE):
                # If bot mentions specific data without user providing it
                if not re.search(pattern, user_message, re.IGNORECASE):
                    mistakes.append(
                        {
                            "type": "hallucination",
                            "description": "Provided specific information not in context",
                            "severity": "critical",
                        }
                    )
                    break

        # Check for repetition
        sentences = re.split(r"[.!?]+", bot_response)
        unique_sentences = set(s.strip().lower() for s in sentences if s.strip())
        if len(sentences) > len(unique_sentences) + 1:
            mistakes.append(
                {
                    "type": "repetition",
                    "description": "Response contains repetitive content",
                    "severity": "low",
                }
            )

        return {
            "has_mistake": len(mistakes) > 0,
            "mistakes": mistakes,
            "should_apologize": any(
                m["severity"] in ["high", "critical"] for m in mistakes
            ),
        }

    def _calculate_overall_score(
        self, empathy: float, clarity: float, actionability: float, tone: float
    ) -> float:
        """Calculate weighted overall quality score (1-5)."""
        # Weights based on importance
        weighted_score = (
            empathy * 0.3 + clarity * 0.25 + actionability * 0.25 + tone * 0.20
        )

        # Convert from 0-1 to 1-5 scale
        return 1 + (weighted_score * 4)

    def _get_quality_level(self, score: float) -> str:
        """Get quality level from score."""
        if score >= 4.5:
            return "EXCELLENT"
        elif score >= 3.5:
            return "GOOD"
        elif score >= 2.5:
            return "ACCEPTABLE"
        elif score >= 1.5:
            return "POOR"
        else:
            return "UNACCEPTABLE"

    def _generate_recommendations(
        self,
        empathy: float,
        clarity: float,
        actionability: float,
        tone: float,
        mistakes: Dict[str, Any],
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        if empathy < self.quality_thresholds["empathy_score"]:
            recommendations.append(
                "Add more empathetic language to acknowledge customer's feelings"
            )

        if clarity < self.quality_thresholds["clarity_score"]:
            recommendations.append(
                "Simplify language and break into shorter sentences for better clarity"
            )

        if actionability < self.quality_thresholds["actionability_score"]:
            recommendations.append("Provide clearer next steps or actionable solutions")

        if tone < self.quality_thresholds["tone_appropriateness"]:
            recommendations.append(
                "Adjust tone to better match customer's emotional state"
            )

        if mistakes["should_apologize"]:
            recommendations.append(
                "CRITICAL: Apologize for the mistake and correct the information"
            )

        return recommendations

    def _load_mistake_patterns(self) -> Dict[str, List[str]]:
        """Load common mistake patterns."""
        return {
            "contradiction": [
                r"yes.*but.*no",
                r"no.*however.*yes",
            ],
            "hallucination": [
                r"your order #\d+",
                r"you paid \$\d+",
            ],
            "tone_mismatch": [
                r"angry.*😄",
                r"frustrated.*🎉",
            ],
        }

    def get_learning_insights(self) -> Dict[str, Any]:
        """
        Analyze evaluation history for learning insights.
        """
        if not self.evaluation_history:
            return {"message": "No evaluations yet"}

        total = len(self.evaluation_history)
        avg_scores = {
            "empathy": sum(e["scores"]["empathy"] for e in self.evaluation_history)
            / total,
            "clarity": sum(e["scores"]["clarity"] for e in self.evaluation_history)
            / total,
            "actionability": sum(
                e["scores"]["actionability"] for e in self.evaluation_history
            )
            / total,
            "tone": sum(
                e["scores"]["tone_appropriateness"] for e in self.evaluation_history
            )
            / total,
        }

        # Count quality levels
        quality_distribution = {}
        for eval in self.evaluation_history:
            level = eval["quality_level"]
            quality_distribution[level] = quality_distribution.get(level, 0) + 1

        # Common mistakes
        all_mistakes = []
        for eval in self.evaluation_history:
            if eval["mistake_detected"]["has_mistake"]:
                all_mistakes.extend(eval["mistake_detected"]["mistakes"])

        mistake_types = {}
        for mistake in all_mistakes:
            mtype = mistake["type"]
            mistake_types[mtype] = mistake_types.get(mtype, 0) + 1

        return {
            "total_evaluations": total,
            "average_scores": avg_scores,
            "quality_distribution": quality_distribution,
            "common_mistakes": mistake_types,
            "improvement_trend": self._calculate_improvement_trend(),
        }

    def _calculate_improvement_trend(self) -> str:
        """Calculate if quality is improving over time."""
        if len(self.evaluation_history) < 10:
            return "Insufficient data"

        recent = self.evaluation_history[-10:]
        older = (
            self.evaluation_history[-20:-10]
            if len(self.evaluation_history) >= 20
            else self.evaluation_history[:10]
        )

        recent_avg = sum(e["overall_score"] for e in recent) / len(recent)
        older_avg = sum(e["overall_score"] for e in older) / len(older)

        diff = recent_avg - older_avg

        if diff > 0.3:
            return "Significant improvement"
        elif diff > 0.1:
            return "Moderate improvement"
        elif diff > -0.1:
            return "Stable"
        elif diff > -0.3:
            return "Slight decline"
        else:
            return "Significant decline"
