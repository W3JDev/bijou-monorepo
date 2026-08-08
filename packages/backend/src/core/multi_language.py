"""
Bijou AI - Multi-Language Detection & Cultural Context System
============================================================

Comprehensive language support for Malaysian market covering:
- Bahasa Malaysia (Malay) - 60% of population
- Mandarin Chinese - 25% of population
- Tamil - 7% of population
- English/Manglish - Business language + code-switching

Features:
- Automatic language detection
- Cultural context adaptation
- Code-switching support (mixed languages)
- Formal/informal tone adjustment
- Regional business practices awareness
- Religious and cultural sensitivity

Author: W3J Bijou AI
Version: 2.2.0
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Language(Enum):
    ENGLISH = "en"
    MALAY = "ms"  # Bahasa Malaysia
    MANDARIN = "zh"  # Simplified Chinese
    TAMIL = "ta"
    MANGLISH = "en-my"  # Malaysian English (code-switching)


class Formality(Enum):
    FORMAL = "formal"
    INFORMAL = "informal"
    BUSINESS = "business"


@dataclass
class LanguageContext:
    """Language and cultural context information"""

    primary_language: Language
    secondary_language: Optional[Language] = None
    formality_level: Formality = Formality.BUSINESS
    cultural_context: Dict = None
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.cultural_context is None:
            self.cultural_context = {}


class MultiLanguageProcessor:
    """
    Multi-language detection and cultural context processor for Malaysian market
    """

    def __init__(self):
        # Language detection patterns
        self.language_patterns = {
            Language.MALAY: {
                "common_words": [
                    "saya",
                    "anda",
                    "adalah",
                    "dengan",
                    "untuk",
                    "dari",
                    "ke",
                    "pada",
                    "ini",
                    "itu",
                    "tidak",
                    "ya",
                    "boleh",
                    "mahu",
                    "nak",
                    "dah",
                    "sudah",
                    "belum",
                    "lagi",
                    "juga",
                    "terima kasih",
                    "maaf",
                    "tolong",
                    "jom",
                    "macam mana",
                    "kat mana",
                    "bila",
                    "kenapa",
                    "siapa",
                    "berapa",
                    "bagaimana",
                    "selamat",
                    "pagi",
                    "petang",
                    "malam",
                ],
                "formal_indicators": [
                    "encik",
                    "puan",
                    "dato",
                    "datuk",
                    "tan sri",
                    "tun",
                ],
                "informal_indicators": [
                    "bro",
                    "sis",
                    "abang",
                    "kakak",
                    "adik",
                    "bang",
                    "kak",
                    "eh",
                ],
                "business_terms": [
                    "syarikat",
                    "perniagaan",
                    "urusan",
                    "perkhidmatan",
                    "harga",
                    "bayaran",
                    "pelabura",  # investment
                    "hartanah",  # real estate
                    "kemudahan",  # facilities
                ],
            },
            Language.MANDARIN: {
                "common_words": [
                    "我",
                    "你",
                    "他",
                    "她",
                    "是",
                    "不",
                    "的",
                    "在",
                    "有",
                    "了",
                    "个",
                    "人",
                    "这",
                    "那",
                    "要",
                    "好",
                    "可以",
                    "什么",
                    "怎么",
                    "谢谢",
                    "对不起",
                    "没关系",
                    "多少钱",
                    "在哪里",
                    "什么时候",
                    "为什么",
                    "早上好",
                    "下午好",
                    "晚上好",
                    "再见",
                ],
                "formal_indicators": ["先生", "女士", "老板", "经理"],
                "informal_indicators": ["哥哥", "姐姐", "弟弟", "妹妹", "朋友", "老板"],
                "business_terms": ["公司", "生意", "服务", "价格", "付款", "买", "卖"],
            },
            Language.TAMIL: {
                "common_words": [
                    "நான்",
                    "நீங்கள்",
                    "அவர்",
                    "அவள்",
                    "இது",
                    "அது",
                    "என்ன",
                    "எப்படி",
                    "எங்கே",
                    "எப்போது",
                    "ஏன்",
                    "யார்",
                    "வணக்கம்",
                    "நன்றி",
                    "மன்னிக்கவும்",
                    "தயவுசெய்து",
                    "சரி",
                    "இல்லை",
                    "முடியும்",
                    "வேண்டும்",
                    "இருக்கிறது",
                    "போகிறேன்",
                    "வருகிறேன்",
                ],
                "formal_indicators": ["ஐயா", "அம்மா", "சார்"],
                "informal_indicators": ["அண்ணா", "அக்காள்", "தம்பி", "தங்கை"],
                "business_terms": ["கம்பனி", "வியாபாரம்", "சேவை", "விலை", "பணம்"],
            },
            Language.ENGLISH: {
                "common_words": [
                    "i",
                    "you",
                    "he",
                    "she",
                    "is",
                    "are",
                    "the",
                    "a",
                    "an",
                    "and",
                    "or",
                    "but",
                    "with",
                    "for",
                    "from",
                    "to",
                    "in",
                    "on",
                    "at",
                    "can",
                    "will",
                    "would",
                    "thank",
                    "please",
                    "sorry",
                    "hello",
                    "hi",
                    "good",
                    "morning",
                    "afternoon",
                    "evening",
                    "efficient",
                    "solutions",
                    "professional",
                    "inquiry",
                    "property",
                    "insurance",
                ],
                "formal_indicators": [
                    "sir",
                    "madam",
                    "mr",
                    "mrs",
                    "ms",
                    "dr",
                    "prof",
                    "dear",
                ],
                "informal_indicators": [
                    "bro",
                    "sis",
                    "dude",
                    "mate",
                    "buddy",
                    "hey",
                    "guys",
                ],
                "business_terms": [
                    "company",
                    "business",
                    "service",
                    "price",
                    "payment",
                    "buy",
                    "sell",
                    "roi",
                    "analysis",
                    "digital",
                    "transformation",
                    "solutions",
                    "professional",
                    "inquiry",
                    "premium",
                ],
            },
        }

        # Manglish (Malaysian English) patterns
        self.manglish_patterns = [
            # Common Manglish words/phrases
            r"\b(lah|lor|mah|wor|hor|meh|kah|ah)\b",
            r"\b(can|cannot|got|no got|have|no have)\b",
            r"\b(alamak|aiyo|wah|eh|har)\b",
            r"\b(makan|lepak|shiok|sien|paiseh)\b",
            # Code-switching patterns (Malay + English)
            r"(?:how much|berapa)\s+(?:harga|price)",
            r"(?:what time|pukul berapa)",
            r"(?:where|kat mana)",
            r"(?:can|boleh)\s+(?:help|tolong)",
            r"\b(boleh)\s+(?:help|assist|support)",
            r"\b(tak|tidak)\s+(?:can|cannot|able)",
            r"\b(nak|want|need)\s+(?:help|support|insurance|house|property)",
            r"\bterima kasih\s+(?:very much|so much|banyak-banyak)",
            # Mixed sentence patterns
            r"(?:hi|hello).*\b(boleh|tak|nak|lah)\b",
            r"\b(need|want).*\b(tak|boleh|nak)\b",
            r"\bfor your.*\b(help|support).*\byesterday\b",
        ]

        # Cultural context data
        self.cultural_contexts = {
            Language.MALAY: {
                "greeting_times": {
                    "morning": "Selamat pagi",
                    "afternoon": "Selamat petang",
                    "evening": "Selamat petang",
                    "night": "Selamat malam",
                },
                "politeness_level": "high",
                "business_culture": "relationship_focused",
                "religious_sensitivity": "high",
                "formality_preference": "moderate_formal",
                "common_honorifics": ["Encik", "Puan", "Dato'", "Datuk"],
                "cultural_values": [
                    "respect",
                    "harmony",
                    "face_saving",
                    "family_oriented",
                ],
            },
            Language.MANDARIN: {
                "greeting_times": {
                    "morning": "早上好",
                    "afternoon": "下午好",
                    "evening": "晚上好",
                    "night": "晚上好",
                },
                "politeness_level": "high",
                "business_culture": "hierarchical",
                "religious_sensitivity": "moderate",
                "formality_preference": "formal",
                "common_honorifics": ["先生", "女士", "老板"],
                "cultural_values": ["hierarchy", "face", "guanxi", "diligence"],
            },
            Language.TAMIL: {
                "greeting_times": {
                    "morning": "காலை வணக்கம்",
                    "afternoon": "மதியம் வணக்கம்",
                    "evening": "மாலை வணக்கம்",
                    "night": "இரவு வணக்கம்",
                },
                "politeness_level": "high",
                "business_culture": "relationship_focused",
                "religious_sensitivity": "high",
                "formality_preference": "respectful",
                "common_honorifics": ["ஐயா", "அம்மா", "சார்"],
                "cultural_values": [
                    "respect_for_elders",
                    "family",
                    "tradition",
                    "hospitality",
                ],
            },
            Language.ENGLISH: {
                "greeting_times": {
                    "morning": "Good morning",
                    "afternoon": "Good afternoon",
                    "evening": "Good evening",
                    "night": "Good evening",
                },
                "politeness_level": "moderate",
                "business_culture": "efficiency_focused",
                "religious_sensitivity": "low",
                "formality_preference": "business_casual",
                "common_honorifics": ["Sir", "Madam", "Mr.", "Ms."],
                "cultural_values": [
                    "directness",
                    "efficiency",
                    "individualism",
                    "time_conscious",
                ],
            },
            Language.MANGLISH: {
                "greeting_times": {
                    "morning": "Good morning",
                    "afternoon": "Good afternoon",
                    "evening": "Good evening",
                    "night": "Good evening",
                },
                "politeness_level": "moderate",
                "business_culture": "relationship_focused",
                "religious_sensitivity": "moderate",
                "formality_preference": "casual_business",
                "common_honorifics": ["Sir", "Madam", "Boss", "Encik", "Puan"],
                "cultural_values": [
                    "friendliness",
                    "flexibility",
                    "multicultural_harmony",
                    "practical_efficiency",
                ],
            },
        }

    def detect_language(self, text: str) -> LanguageContext:
        """
        Detect primary language and cultural context from text
        """
        text_lower = text.lower()
        language_scores = {}

        # Check for Manglish patterns first (more sophisticated detection)
        manglish_score = 0
        manglish_indicators = 0

        for pattern in self.manglish_patterns:
            matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
            if matches > 0:
                manglish_score += matches * 3  # Higher weight for Manglish
                manglish_indicators += 1

        # Strong Manglish detection for mixed language sentences
        malay_words = sum(
            1
            for word in self.language_patterns[Language.MALAY]["common_words"]
            if word.lower() in text_lower
        )
        english_base = len(
            [
                word
                for word in text_lower.split()
                if word
                in [
                    "hi",
                    "hello",
                    "need",
                    "help",
                    "want",
                    "can",
                    "for",
                    "your",
                    "with",
                    "insurance",
                    "yesterday",
                    "support",
                ]
            ]
        )

        # If we have both English and Malay elements with Manglish patterns, it's likely Manglish
        if manglish_indicators > 0 and (malay_words > 0 or english_base > 2):
            manglish_score += (malay_words + english_base) * 2
            language_scores[Language.MANGLISH] = manglish_score
        elif manglish_score > 0:
            language_scores[Language.MANGLISH] = manglish_score

        # Score each language based on word matches
        for language, patterns in self.language_patterns.items():
            score = 0
            for word in patterns["common_words"]:
                if word.lower() in text_lower:
                    score += 1

            # Bonus for business terms
            for term in patterns["business_terms"]:
                if term.lower() in text_lower:
                    score += 2

            if score > 0:
                language_scores[language] = score

        # Determine primary language with Manglish priority
        if not language_scores:
            primary_lang = Language.ENGLISH  # Default fallback
            confidence = 0.3
        else:
            # Prioritize Manglish detection if it has reasonable score
            if (
                Language.MANGLISH in language_scores
                and language_scores[Language.MANGLISH] >= 3
            ):
                primary_lang = Language.MANGLISH
                max_score = language_scores[Language.MANGLISH]
            else:
                primary_lang = max(
                    language_scores.keys(), key=lambda k: language_scores[k]
                )
                max_score = language_scores[primary_lang]

            total_words = len(text.split())
            confidence = min(0.95, max_score / max(1, total_words))

            # Boost confidence for Manglish when we have mixed indicators
            if primary_lang == Language.MANGLISH and manglish_indicators > 0:
                confidence = max(confidence, 0.5)

        # Detect formality level
        formality = self._detect_formality(text_lower, primary_lang)

        # Get cultural context
        cultural_context = self.cultural_contexts.get(primary_lang, {})

        return LanguageContext(
            primary_language=primary_lang,
            formality_level=formality,
            cultural_context=cultural_context,
            confidence_score=confidence,
        )

    def _detect_formality(self, text: str, language: Language) -> Formality:
        """Detect formality level based on language patterns"""
        text_lower = text.lower()

        # Handle Manglish formality detection
        if language == Language.MANGLISH:
            # Check for informal Manglish patterns
            informal_manglish = [
                "eh",
                "bro",
                "lah",
                "lor",
                "alamak",
                "aiyo",
                "wah",
                "hey",
            ]
            formal_manglish = ["sir", "madam", "dato", "encik", "puan"]
            business_manglish = [
                "price",
                "harga",
                "business",
                "company",
                "service",
                "insurance",
                "property",
                "house",
            ]

            informal_count = sum(1 for word in informal_manglish if word in text_lower)
            formal_count = sum(1 for word in formal_manglish if word in text_lower)
            business_count = sum(1 for word in business_manglish if word in text_lower)

            if formal_count > 0:
                return Formality.FORMAL
            elif informal_count > 0 and business_count == 0:
                return Formality.INFORMAL
            else:
                return Formality.BUSINESS

        if language not in self.language_patterns:
            return Formality.BUSINESS

        patterns = self.language_patterns[language]

        # Check for formal indicators with exact matching for titles
        formal_count = 0
        for indicator in patterns["formal_indicators"]:
            if indicator.lower() == "dato" and (
                "dato'" in text_lower or "dato " in text_lower
            ):
                formal_count += 2  # Strong formal indicator
            elif indicator.lower() in text_lower:
                formal_count += 1

        # Check for informal indicators
        informal_count = 0
        for indicator in patterns["informal_indicators"]:
            if indicator.lower() in text_lower:
                informal_count += 1

        # Special handling for "bro" which is strongly informal
        if "bro" in text_lower:
            informal_count += 2

        # Check for business terms
        business_count = sum(
            1 for term in patterns["business_terms"] if term.lower() in text_lower
        )

        # Enhanced formality detection logic
        if formal_count >= 2:  # Strong formal indicators like "Dato'"
            return Formality.FORMAL
        elif informal_count >= 2 and business_count == 0:  # Strong informal like "bro"
            return Formality.INFORMAL
        elif formal_count > informal_count:
            return Formality.FORMAL
        elif informal_count > formal_count and business_count == 0:
            return Formality.INFORMAL
        elif business_count > 0 or any(
            term in text_lower
            for term in [
                "price",
                "cost",
                "service",
                "company",
                "business",
                "professional",
                "pelabura",  # investment in Malay
                "harga",  # price in Malay
            ]
        ):
            return Formality.BUSINESS
        else:
            # Context-based detection for ambiguous cases
            if any(
                word in text_lower
                for word in ["bro", "eh", "alamak", "wah", "hai", "hey"]
            ):
                return Formality.INFORMAL
            return Formality.BUSINESS  # Default for business context

    def get_response_guidelines(self, context: LanguageContext) -> Dict:
        """
        Get response guidelines based on detected language and cultural context
        """
        guidelines = {
            "language": context.primary_language.value,
            "formality": context.formality_level.value,
            "cultural_adaptations": [],
        }

        cultural_data = context.cultural_context

        if context.primary_language == Language.MALAY:
            guidelines.update(
                {
                    "tone": "respectful and warm",
                    "greeting_style": "traditional_malay",
                    "politeness_markers": [
                        "sila",
                        "harap maaf",
                        "terima kasih banyak-banyak",
                    ],
                    "avoid_topics": ["pork", "alcohol", "gambling"],
                    "cultural_adaptations": [
                        "Use Islamic greetings when appropriate",
                        "Show respect for hierarchy and age",
                        "Be patient with decision-making process",
                        "Include family considerations in advice",
                    ],
                }
            )

        elif context.primary_language == Language.MANDARIN:
            guidelines.update(
                {
                    "tone": "respectful and professional",
                    "greeting_style": "traditional_chinese",
                    "politeness_markers": ["请", "谢谢", "不客气", "打扰了"],
                    "cultural_adaptations": [
                        "Respect hierarchy and seniority",
                        "Build relationship before business",
                        "Allow face-saving opportunities",
                        "Be thorough in explanations",
                    ],
                }
            )

        elif context.primary_language == Language.TAMIL:
            guidelines.update(
                {
                    "tone": "respectful and family-oriented",
                    "greeting_style": "traditional_tamil",
                    "politeness_markers": ["தயவுசெய்து", "நன்றி", "மன்னிக்கவும்"],
                    "cultural_adaptations": [
                        "Show respect for elders and tradition",
                        "Include family welfare considerations",
                        "Be patient with relationship building",
                        "Respect religious observances",
                    ],
                }
            )

        elif context.primary_language in [Language.ENGLISH, Language.MANGLISH]:
            guidelines.update(
                {
                    "tone": "friendly and efficient",
                    "greeting_style": "malaysian_english",
                    "politeness_markers": ["please", "thank you", "sorry"],
                    "cultural_adaptations": [
                        "Mix casual and professional tone",
                        "Use familiar Malaysian references",
                        "Be direct but respectful",
                        "Include local context and examples",
                    ],
                }
            )

        return guidelines

    def generate_culturally_aware_prompt(
        self, context: LanguageContext, base_prompt: str
    ) -> str:
        """
        Generate culturally aware system prompt based on detected language context
        """
        guidelines = self.get_response_guidelines(context)

        cultural_prompt = f"""
{base_prompt}

LANGUAGE & CULTURAL CONTEXT:
- Respond primarily in: {context.primary_language.value}
- Formality level: {context.formality_level.value}
- Tone: {guidelines.get("tone", "professional")}
- Confidence: {context.confidence_score:.2f}

CULTURAL ADAPTATIONS:
"""

        for adaptation in guidelines.get("cultural_adaptations", []):
            cultural_prompt += f"- {adaptation}\n"

        if context.primary_language == Language.MALAY:
            cultural_prompt += """
BAHASA MALAYSIA GUIDELINES:
- Use proper Malay grammar and respectful language
- Include appropriate Islamic greetings when suitable (Assalamualaikum/Waalaikumussalam)
- Use "Encik/Puan" for formal address
- Incorporate Malaysian cultural references
- Be sensitive to religious practices and Halal requirements
- Use business Malay terminology correctly
"""

        elif context.primary_language == Language.MANDARIN:
            cultural_prompt += """
中文 (MANDARIN) GUIDELINES:
- Use simplified Chinese characters (Malaysian standard)
- Incorporate respectful forms of address (您, 先生, 女士)
- Reference Malaysian Chinese cultural context
- Use traditional greetings appropriately
- Be mindful of feng shui and cultural beliefs in business advice
- Include local Malaysian Chinese business practices
"""

        elif context.primary_language == Language.TAMIL:
            cultural_prompt += """
தமிழ் (TAMIL) GUIDELINES:
- Use respectful Tamil forms and honorifics
- Reference Malaysian Tamil cultural context
- Be sensitive to Hindu customs and festivals
- Use appropriate family-oriented language
- Include traditional business practices
- Respect for elders in decision-making
"""

        elif context.primary_language == Language.MANGLISH:
            cultural_prompt += """
MANGLISH (MALAYSIAN ENGLISH) GUIDELINES:
- Mix English with local Malaysian expressions
- Use familiar particles (lah, lor, mah, ar)
- Include Malaysian slang appropriately
- Reference local places, food, and culture
- Balance casual and professional tone
- Code-switch naturally when it feels appropriate
"""

        return cultural_prompt

    def get_time_appropriate_greeting(self, context_or_language, hour: int) -> str:
        """Get culturally appropriate greeting based on time and language"""
        # Handle both LanguageContext and Language enum for backward compatibility
        if isinstance(context_or_language, Language):
            language = context_or_language
            greetings = self.cultural_contexts.get(language, {}).get(
                "greeting_times", {}
            )
        else:
            # LanguageContext object
            greetings = context_or_language.cultural_context.get("greeting_times", {})

        if 5 <= hour < 12:
            return greetings.get("morning", "Good morning")
        elif 12 <= hour < 17:
            return greetings.get("afternoon", "Good afternoon")
        elif 17 <= hour < 21:
            return greetings.get("evening", "Good evening")
        else:
            return greetings.get("night", "Good evening")

    def should_use_formal_address(self, context: LanguageContext) -> bool:
        """Determine if formal address should be used"""
        return (
            context.formality_level in [Formality.FORMAL, Formality.BUSINESS]
            and context.cultural_context.get("politeness_level") == "high"
        )

    def get_cultural_business_advice(self, context: LanguageContext) -> List[str]:
        """Get culture-specific business advice"""
        if context.primary_language == Language.MALAY:
            return [
                "Consider Halal certification for food-related businesses",
                "Respect prayer times in scheduling",
                "Build relationships through personal connections",
                "Include family considerations in business decisions",
            ]
        elif context.primary_language == Language.MANDARIN:
            return [
                "Invest time in relationship building (guanxi)",
                "Consider auspicious dates for important business events",
                "Respect hierarchical decision-making processes",
                "Focus on long-term business relationships",
            ]
        elif context.primary_language == Language.TAMIL:
            return [
                "Respect traditional values in business practices",
                "Consider festival seasons in planning",
                "Include family welfare in employee benefits",
                "Build trust through consistent relationship maintenance",
            ]
        else:
            return [
                "Leverage Malaysia's multicultural market advantage",
                "Consider all major ethnic groups in marketing",
                "Respect diverse religious and cultural practices",
                "Build inclusive business practices",
            ]


# Example usage and testing
if __name__ == "__main__":
    processor = MultiLanguageProcessor()

    # Test different language inputs
    test_messages = [
        "Selamat pagi! Saya nak tanya tentang harga rumah kat Bangsar.",
        "早上好！我想问一下这个房子的价格。",
        "வணக்கம்! இந்த வீட்டின் விலை என்ன?",
        "Hi! Can you help me with the property price ah?",
        "Alamak, how much this house cost lah? Got discount or not?",
        "Good morning, I would like to inquire about your services.",
    ]

    print("🌐 MULTI-LANGUAGE DETECTION TEST")
    print("=" * 50)

    for msg in test_messages:
        print(f"\nMessage: {msg}")
        context = processor.detect_language(msg)
        print(f"Language: {context.primary_language.value}")
        print(f"Formality: {context.formality_level.value}")
        print(f"Confidence: {context.confidence_score:.2f}")

        guidelines = processor.get_response_guidelines(context)
        print(f"Tone: {guidelines.get('tone', 'N/A')}")

        greeting = processor.get_time_appropriate_greeting(context, 10)  # 10 AM
        print(f"Appropriate greeting: {greeting}")
