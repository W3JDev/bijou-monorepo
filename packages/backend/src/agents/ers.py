"""
TRACE Agent 4: Empathetic Response Synthesizer (ERS)
====================================================

Crafts the final human-like empathetic response.

Applies Behavioral Taxonomy:
1. Mirroring - Reflect customer's emotion
2. Empathic Concern - Show care about their well-being
3. Consolation - Soothe negative emotions
4. Interpretation - Provide perspective
5. Altruistic Helping - Offer practical assistance
6. Exploration - Ask clarifying questions
7. Acknowledgment - Validate their experience

Author: W3J Bijou AI
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from agents.humanizer import ConversationHumanizer
from core.multi_language import LanguageContext, MultiLanguageProcessor


class EmpatheticResponseSynthesizer:
    """
    TRACE Agent 4: Empathetic Response Synthesizer

    Generates final human-like empathetic response using:
    - Emotional state from ASI
    - Causal analysis from CAE
    - Strategic guidance from SRP
    - Behavioral taxonomy for empathy
    """

    def __init__(
        self, api_key: Optional[str] = None, custom_system_prompt: Optional[str] = None
    ):
        """
        Initialize Empathetic Response Synthesizer.

        Args:
            api_key: Google Gemini API key (defaults to env var)
            custom_system_prompt: Optional custom system prompt (e.g., W3J knowledge)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)  # type: ignore
        self.model = genai.GenerativeModel("gemini-2.5-flash")  # type: ignore

        # Initialize humanizer for natural conversation
        self.humanizer = ConversationHumanizer()

        # Initialize multi-language processor
        self.multi_language = MultiLanguageProcessor()

        # Store custom system prompt (e.g., W3J knowledge base)
        self.custom_system_prompt = custom_system_prompt

        # Response templates for different behavioral tactics
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, List[str]]:
        """
        Load response templates for behavioral taxonomy.

        Returns:
            Dictionary of behavioral tactics and example templates
        """
        return {
            "mirroring": [
                "I can hear how [emotion] you're feeling about this",
                "It sounds like you're experiencing [emotion]",
                "I understand this is making you feel [emotion]",
            ],
            "empathic_concern": [
                "I'm genuinely concerned about your situation",
                "Your experience matters to us, and I want to make this right",
                "I care about resolving this for you",
            ],
            "consolation": [
                "I'm really sorry you're going through this",
                "This must be so [emotion] for you",
                "I completely understand why you'd feel this way",
            ],
            "interpretation": [
                "Let me help you understand what's happening",
                "Here's what I can see from my side",
                "From what you've shared, it seems like...",
            ],
            "altruistic_helping": [
                "Here's exactly what I can do to help",
                "Let me take care of this for you right away",
                "I'm going to personally ensure this gets resolved",
            ],
            "exploration": [
                "To help you better, could you tell me more about...",
                "I'd like to understand your situation better - can you share...",
                "Just to make sure I help you properly, could you clarify...",
            ],
            "acknowledgment": [
                "Thank you for bringing this to our attention",
                "I appreciate you taking the time to explain this",
                "Your feedback helps us improve",
            ],
        }

    def synthesize_response(
        self,
        message: str,
        emotion: str,
        emotion_confidence: float,
        emotional_cues: List[str],
        global_cause: str,
        unmet_need: str,
        urgency_level: str,
        strategy: str,
        behavioral_taxonomy: List[str],
        response_guidance: List[str],
        knowledge_retrieved: Dict[str, List[str]],
        conversation_history: Optional[List[Dict]] = None,
        customer_name: Optional[str] = None,
        language_context: Optional[LanguageContext] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize final empathetic response.

        Args:
            message: Customer's message
            emotion: Detected emotion
            emotion_confidence: Emotion confidence score
            emotional_cues: Words/phrases that triggered emotion
            global_cause: Situational cause
            unmet_need: Customer's unmet need
            urgency_level: low/medium/high/critical
            strategy: Response strategy from SRP
            behavioral_taxonomy: Empathy behaviors to apply
            response_guidance: Guidance from SRP
            knowledge_retrieved: Relevant knowledge base entries
            conversation_history: Previous messages
            customer_name: Customer's name if known

        Returns:
            dict with:
                - response_text: Final empathetic response
                - behaviors_applied: List of empathy behaviors used
                - tone: Response tone (warm/professional/urgent)
                - confidence: Response quality score (0-1)
                - response_length: Character count
                - estimated_csat: Predicted customer satisfaction (1-5)
                - detected_language: Primary language detected
                - cultural_adaptations: Applied cultural considerations
        """
        # Detect language and cultural context if not provided
        if language_context is None:
            language_context = self.multi_language.detect_language(message)

        # Get culturally appropriate response guidelines
        response_guidelines = self.multi_language.get_response_guidelines(
            language_context
        )
        # Build conversation context
        history_text = ""
        if conversation_history:
            recent = conversation_history[-5:]
            history_text = "\n".join(
                [
                    f"{msg.get('sender', 'unknown')}: {msg.get('content', '')}"
                    for msg in recent
                ]
            )

        # Get templates for behavioral taxonomy
        templates = []
        for behavior in behavioral_taxonomy:
            behavior_key = behavior.lower().replace(" ", "_")
            if behavior_key in self.templates:
                templates.extend(self.templates[behavior_key])

        # Use custom system prompt if provided, otherwise use default
        if self.custom_system_prompt:
            base_prompt = self.custom_system_prompt
        else:
            base_prompt = "You are Bijou, an empathetic AI customer support agent. Your goal is to craft a warm, human-like response that makes the customer feel heard, understood, and helped."

        # Generate culturally aware prompt
        culturally_aware_prompt = self.multi_language.generate_culturally_aware_prompt(
            language_context, base_prompt
        )

        # Get current time for greeting context
        current_time_str = datetime.now().strftime("%A, %d %B %Y %I:%M %p")

        # Create synthesis prompt with multi-language awareness
        prompt = f"""{culturally_aware_prompt}

CURRENT TIME: {current_time_str}
(Use this to determine if you should say Good Morning, Afternoon, or Evening)

CONTEXT FOR THIS MESSAGE:

CUSTOMER MESSAGE:
{message}

EMOTIONAL ANALYSIS:
- Emotion: {emotion} (confidence: {emotion_confidence:.2f})
- Emotional Cues: {", ".join(emotional_cues)}
- Root Cause: {global_cause}
- Unmet Need: {unmet_need}
- Urgency: {urgency_level}

STRATEGIC GUIDANCE:
- Strategy: {strategy.replace("_", " ").title()}
- Behavioral Taxonomy to Apply: {", ".join(behavioral_taxonomy)}
- Response Guidance: {"; ".join(response_guidance)}

RELEVANT KNOWLEDGE:
{json.dumps(knowledge_retrieved, indent=2)}

CONVERSATION HISTORY:
{history_text if history_text else "This is the first message"}

BEHAVIORAL TEMPLATES (use as inspiration, not verbatim):
{chr(10).join(["- " + t for t in templates[:5]])}

YOUR TASK:
Write a response that:

1. **Shows Empathy First** - Start by acknowledging their emotion
   - Use Mirroring: Reflect their emotional state
   - Use Empathic Concern: Show you genuinely care
   - Use Consolation: Soothe negative feelings

2. **Addresses the Root Cause** - Explain what happened
   - Use Interpretation: Help them understand the situation
   - Reference relevant knowledge from the knowledge base
   - Be transparent and honest

3. **Provides Clear Next Steps** - Give actionable help
   - Use Altruistic Helping: Offer specific solutions
   - Be concrete about what you'll do
   - Set clear expectations

4. **Maintains Human Warmth** - Sound natural and caring
   - Use their name if available{f" ({customer_name})" if customer_name else ""}
   - Vary sentence structure
   - Avoid corporate jargon
   - Keep it concise (2-4 short paragraphs max)

TONE GUIDELINES:
- Urgency {urgency_level}: {"Act FAST, show immediate action" if urgency_level in ["high", "critical"] else "Be thorough and reassuring"}
- Emotion {emotion}: {"Validate and soothe" if emotion in ["anger", "fear", "sadness"] else "Match their energy positively"}

IMPORTANT:
- Do NOT sound robotic or scripted
- Do NOT use phrases like "I apologize for any inconvenience"
- DO sound like a caring human who wants to help
- DO be specific with solutions, not generic

Write ONLY the response text (no explanations, no labels, no meta-commentary).

LANGUAGE & CULTURAL REQUIREMENTS:
- Primary Language: {language_context.primary_language.value}
- Formality Level: {language_context.formality_level.value}
- Cultural Tone: {response_guidelines.get("tone", "professional")}
- Greeting Style: Use {response_guidelines.get("greeting_style", "standard")} appropriate for current time
- Cultural Adaptations: {"; ".join(response_guidelines.get("cultural_adaptations", []))}

MULTI-LANGUAGE GUIDELINES:
{self._get_language_specific_instructions(language_context)}"""

        try:
            # Generate response with timeout
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Analyze response quality
            quality_metrics = self._analyze_response_quality(
                response_text, behavioral_taxonomy, emotion, urgency_level
            )

            # === HUMANIZE THE RESPONSE ===
            # Detect user's tone from their message
            user_tone = self.humanizer.detect_user_tone(message)

            # Get conversation length from history
            conversation_length = (
                len(conversation_history) if conversation_history else 1
            )

            # Humanize the AI response
            humanized_data = self.humanizer.humanize_response(
                response=response_text,
                emotion=emotion,
                urgency=urgency_level,
                conversation_length=conversation_length,
                user_tone=user_tone,
            )

            return {
                "response_text": humanized_data[
                    "humanized_text"
                ],  # Use humanized version
                "original_response": response_text,  # Keep original for analysis
                "behaviors_applied": behavioral_taxonomy,
                "tone": self._determine_tone(emotion, urgency_level),
                "confidence": quality_metrics["confidence"],
                "response_length": len(humanized_data["humanized_text"]),
                "estimated_csat": quality_metrics["estimated_csat"],
                "timestamp": datetime.now().isoformat(),
                "strategy_used": strategy,
                "typing_time": humanized_data["typing_time_seconds"],
                "message_chunks": humanized_data["message_chunks"],
                "user_tone_detected": user_tone,
                "detected_language": language_context.primary_language.value,
                "cultural_adaptations": response_guidelines.get(
                    "cultural_adaptations", []
                ),
                "formality_level": language_context.formality_level.value,
            }

        except Exception as e:
            logger.error(f"Error in response synthesis: {e}")
            # Fallback response with language context
            return self._fallback_response(
                message,
                emotion,
                unmet_need,
                knowledge_retrieved,
                customer_name,
                language_context,
            )

    def _get_language_specific_instructions(
        self, language_context: LanguageContext
    ) -> str:
        """Get specific instructions based on detected language"""
        from core.multi_language import Language

        if language_context.primary_language == Language.MALAY:
            return """- Respond in proper Bahasa Malaysia
- Use respectful forms of address (Encik/Puan for formal, Abang/Kakak for casual)
- Include appropriate Islamic greetings when suitable (but don't assume religion)
- Use Malaysian business terminology correctly
- Be culturally sensitive to Islamic practices (prayer times, halal considerations)
- Maintain warm, relationship-focused tone typical in Malaysian culture"""

        elif language_context.primary_language == Language.MANDARIN:
            return """- 使用标准的简体中文回复
- 采用适当的尊称 (先生/女士 formal, 老板 business contexts)
- 体现中华文化的礼貌和尊重
- 在商业建议中考虑关系建立 (guanxi) 的重要性
- 使用马来西亚华人社区熟悉的商业术语
- 保持专业但温暖的语调"""

        elif language_context.primary_language == Language.TAMIL:
            return """- தமிழில் மரியாதையான முறையில் பதிலளிக்கவும்
- பொருத்தமான மரியாதைச் சொற்களைப் பயன்படுத்தவும் (ஐயா/அம்மா)
- குடும்ப நலன்களைக் கருத்தில் கொண்ட அறிவுரைகளை வழங்கவும்
- மலேசிய தமிழ் சமூகத்தின் பாரம்பரிய மதிப்புகளுக்கு மரியாதை காட்டவும்
- வணிக ஆலோசனைகளில் உறவுகளின் முக்கியத்துவத்தை வலியுறுத்தவும்"""

        elif language_context.primary_language == Language.MANGLISH:
            return """- Mix English with natural Malaysian expressions and particles
- Use familiar Malaysian slang appropriately (lah, lor, mah, ar)
- Reference local Malaysian culture, food, and places when relevant
- Balance casual friendliness with professional competence
- Code-switch naturally when it enhances communication
- Maintain the multicultural Malaysian business perspective"""

        else:  # English
            return """- Use clear, professional English with Malaysian business context
- Include local Malaysian references when relevant
- Maintain warm but efficient communication style
- Consider Malaysia's multicultural business environment
- Be direct but respectful in the Malaysian professional manner"""

    def _analyze_response_quality(
        self, response_text: str, behaviors: List[str], emotion: str, urgency_level: str
    ) -> Dict[str, Any]:
        """
        Analyze quality of synthesized response.

        Args:
            response_text: Generated response
            behaviors: Behavioral taxonomy applied
            emotion: Customer's emotion
            urgency_level: Urgency level

        Returns:
            Quality metrics
        """
        # Simple heuristics for quality
        length = len(response_text)
        word_count = len(response_text.split())

        # Confidence based on length and structure
        has_empathy = any(
            word in response_text.lower()
            for word in ["understand", "sorry", "apologize", "feel", "hear"]
        )
        has_action = any(
            word in response_text.lower()
            for word in ["will", "can", "help", "i'll", "let me"]
        )
        has_structure = len(response_text.split("\n")) > 1

        confidence = 0.6
        if has_empathy:
            confidence += 0.15
        if has_action:
            confidence += 0.15
        if has_structure:
            confidence += 0.10
        if 100 <= length <= 500:  # Ideal length
            confidence += 0.10

        # Estimated CSAT (simplified)
        estimated_csat = 3.0  # Base
        if has_empathy and has_action:
            estimated_csat += 1.0
        if urgency_level in ["high", "critical"] and has_action:
            estimated_csat += 0.5
        if emotion in ["anger", "sadness"] and has_empathy:
            estimated_csat += 0.5

        estimated_csat = min(5.0, estimated_csat)

        return {
            "confidence": min(1.0, confidence),
            "estimated_csat": round(estimated_csat, 1),
            "has_empathy": has_empathy,
            "has_action": has_action,
            "word_count": word_count,
        }

    def _determine_tone(self, emotion: str, urgency_level: str) -> str:
        """
        Determine appropriate response tone.

        Args:
            emotion: Customer's emotion
            urgency_level: Urgency level

        Returns:
            Tone descriptor
        """
        if urgency_level in ["high", "critical"]:
            return "urgent"
        elif emotion in ["anger", "fear"]:
            return "reassuring"
        elif emotion in ["sadness", "disgust"]:
            return "compassionate"
        elif emotion == "joy":
            return "warm"
        else:
            return "professional"

    def _fallback_response(
        self,
        message: str,
        emotion: str,
        unmet_need: str,
        knowledge_retrieved: Dict[str, List[str]],
        customer_name: Optional[str] = None,
        language_context: Optional[LanguageContext] = None,
    ) -> Dict[str, Any]:
        """
        Generate fallback response when AI fails.

        Args:
            message: Customer's message
            emotion: Detected emotion
            unmet_need: Customer's unmet need
            knowledge_retrieved: Retrieved knowledge
            customer_name: Customer's name
            language_context: Language and cultural context

        Returns:
            Fallback response with multi-language support
        """
        # Detect language if not provided
        if language_context is None:
            language_context = self.multi_language.detect_language(message)

        # Get culturally appropriate greeting
        current_hour = datetime.now().hour
        time_greeting = self.multi_language.get_time_appropriate_greeting(
            language_context, current_hour
        )

        # Build culturally appropriate response
        from core.multi_language import Language

        if language_context.primary_language == Language.MALAY:
            greeting = f"{time_greeting}! "
            if customer_name:
                greeting += f"Encik/Puan {customer_name}, "

            empathy_phrases = {
                "anger": "Saya faham betapa kecewanya Encik/Puan, dan saya minta maaf atas masalah ini.",
                "sadness": "Saya sangat kesal dengan apa yang Encik/Puan alami.",
                "fear": "Saya faham kebimbangan Encik/Puan, dan saya di sini untuk membantu.",
                "joy": "Saya gembira dapat berbicara dengan Encik/Puan!",
                "surprise": "Terima kasih kerana menghubungi kami.",
            }.get(emotion, "Saya di sini untuk membantu Encik/Puan.")

            fallback_text = f"{greeting}{empathy_phrases} Saya akan pastikan masalah ini diselesaikan dengan segera. Boleh saya tahu lebih lanjut tentang situasi ini?"

        elif language_context.primary_language == Language.MANDARIN:
            greeting = f"{time_greeting}! "
            if customer_name:
                greeting += f"{customer_name}先生/女士, "

            empathy_phrases = {
                "anger": "我理解您的失望，对此我深表歉意。",
                "sadness": "对于您遇到的问题，我深感抱歉。",
                "fear": "我理解您的担忧，我在这里帮助您。",
                "joy": "很高兴收到您的信息！",
                "surprise": "感谢您联系我们。",
            }.get(emotion, "我在这里为您提供帮助。")

            fallback_text = f"{greeting}{empathy_phrases}我会确保立即解决这个问题。可以告诉我更多关于情况的详情吗？"

        elif language_context.primary_language == Language.TAMIL:
            greeting = f"{time_greeting}! "
            if customer_name:
                greeting += f"{customer_name} ஐயா/அம்மா, "

            empathy_phrases = {
                "anger": "உங்கள் வருத்தத்தை நான் புரிந்துகொள்கிறேன், இதற்காக மன்னிக்கவும்.",
                "sadness": "நீங்கள் அனுபவிக்கும் இந்த பிரச்சனைக்கு மன்னிக்கவும்.",
                "fear": "உங்கள் கவலையை நான் புரிந்துகொள்கிறேன், உங்களுக்கு உதவ நான் இங்கே இருக்கிறேன்.",
                "joy": "உங்களிடமிருந்து செய்தி கேட்டு மகிழ்ச்சி!",
                "surprise": "எங்களைத் தொடர்பு கொண்டதற்கு நன்றி.",
            }.get(emotion, "உங்களுக்கு உதவ நான் இங்கே இருக்கிறேன்.")

            fallback_text = f"{greeting}{empathy_phrases} இந்த பிரச்சனையை உடனே தீர்க்க நான் உறுதியளிக்கிறேன். இந்த நிலைமை பற்றி மேலும் சொல்ல முடியுமா?"

        elif language_context.primary_language == Language.MANGLISH:
            greeting = f"{time_greeting}! "
            if customer_name:
                greeting += f"{customer_name}, "

            empathy_phrases = {
                "anger": "Wah, I can see you're really upset lah, so sorry about this.",
                "sadness": "Alamak, really sorry you're facing this problem lor.",
                "fear": "I understand you're worried, don't worry I'm here to help you.",
                "joy": "So happy to hear from you!",
                "surprise": "Thanks for contacting us ah.",
            }.get(emotion, "I'm here to help you solve this.")

            fallback_text = f"{greeting}{empathy_phrases} I will make sure to settle this for you ASAP. Can you tell me more about what happened ar?"

        else:  # English
            greeting = f"{time_greeting}! "
            if customer_name:
                greeting += f"{customer_name}, "

            empathy_phrases = {
                "anger": "I can hear how frustrated you are, and I'm really sorry about this.",
                "sadness": "I'm so sorry you're experiencing this.",
                "fear": "I understand this is concerning, and I'm here to help.",
                "joy": "I'm so glad to hear from you!",
                "surprise": "Thank you for reaching out.",
                "disgust": "I'm really sorry this happened.",
            }.get(emotion.lower(), "Thank you for contacting us.")

            fallback_text = f"{greeting}{empathy_phrases} Let me look into this for you right away and get back to you with a solution."

        # Add knowledge if available
        knowledge_text = ""
        if knowledge_retrieved:
            first_category = list(knowledge_retrieved.keys())[0]
            first_entry = (
                knowledge_retrieved[first_category][0]
                if knowledge_retrieved[first_category]
                else ""
            )
            if first_entry:
                if language_context.primary_language == Language.MALAY:
                    knowledge_text = f" Maklumat tambahan: {first_entry}."
                elif language_context.primary_language == Language.MANDARIN:
                    knowledge_text = f" 相关信息: {first_entry}。"
                elif language_context.primary_language == Language.TAMIL:
                    knowledge_text = f" கூடுதல் தகவல்: {first_entry}."
                else:  # English or Manglish
                    knowledge_text = f" Additional info: {first_entry}."

        final_response = fallback_text + knowledge_text

        return {
            "response_text": final_response,
            "behaviors_applied": ["Empathic Concern", "Altruistic Helping"],
            "tone": "professional",
            "confidence": 0.50,
            "response_length": len(final_response),
            "estimated_csat": 3.5,
            "timestamp": datetime.now().isoformat(),
            "fallback": True,
            "detected_language": language_context.primary_language.value,
            "cultural_adaptations": [],
            "formality_level": language_context.formality_level.value,
        }


# Example usage
if __name__ == "__main__":
    # Initialize ERS
    ers = EmpatheticResponseSynthesizer()

    # Test case: Synthesize response for frustrated customer
    result = ers.synthesize_response(
        message="Where is my package?! I ordered 2 weeks ago and still nothing!",
        emotion="anger",
        emotion_confidence=0.92,
        emotional_cues=["?!", "still nothing"],
        global_cause="Customer ordered product 2 weeks ago, experiencing shipping delay",
        unmet_need="Information about package location and delivery timeline",
        urgency_level="high",
        strategy="emotional_reaction",
        behavioral_taxonomy=["Mirroring", "Empathic Concern", "Altruistic Helping"],
        response_guidance=[
            "Validate their frustration about the delay",
            "Provide specific information about tracking",
            "Offer immediate action to resolve",
        ],
        knowledge_retrieved={
            "shipping_delays": [
                "Standard shipping typically takes 3-5 business days",
                "Check tracking number at track.example.com",
                "Contact support if delayed >7 days",
            ]
        },
        conversation_history=None,
        customer_name="Sarah",
    )

    print("=== Empathetic Response ===")
    print(result["response_text"])
    print(f"\n=== Metadata ===")
    print(f"Behaviors Applied: {', '.join(result['behaviors_applied'])}")
    print(f"Tone: {result['tone']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Estimated CSAT: {result['estimated_csat']}/5.0")
    print(f"Length: {result['response_length']} characters")
