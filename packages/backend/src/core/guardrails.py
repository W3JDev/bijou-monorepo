"""
W3J Bijou AI - Guardrails System
=================================

Content safety, policy compliance, and business rules enforcement.

Features:
- Harmful content detection (violence, hate speech, profanity)
- PII leakage prevention (credit cards, SSNs, passwords)
- Competitor mention blocking
- Off-topic detection
- Brand voice consistency
- Pricing/policy validation

Author: W3J Bijou AI
Version: 2.1.0
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class ViolationType(Enum):
    """Types of guardrail violations."""
    HARMFUL_CONTENT = "harmful_content"
    PII_LEAKAGE = "pii_leakage"
    COMPETITOR_MENTION = "competitor_mention"
    OFF_TOPIC = "off_topic"
    POLICY_VIOLATION = "policy_violation"
    BRAND_INCONSISTENCY = "brand_inconsistency"


class Guardrails:
    """
    Comprehensive guardrails system for content safety and compliance.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize guardrails system.
        
        Args:
            config: Optional configuration for custom rules
        """
        self.config = config or {}
        self._load_patterns()
        self.violation_count = 0
        self.blocked_responses = []

    def _load_patterns(self):
        """Load detection patterns for various violation types."""
        
        # Harmful content patterns
        self.harmful_patterns = [
            r'\b(kill|murder|suicide|weapon|bomb|explosive)\b',
            r'\b(hate|racist|sexist|discriminat)\w*',
            r'\b(fuck|shit|damn|bitch|bastard|asshole)\b',
            r'\b(violence|violent|attack|assault)\b',
        ]
        
        # PII patterns (credit cards, SSNs, etc.)
        self.pii_patterns = {
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
            'password': r'\b(password|passwd|pwd)[\s:=]+\S+',
        }
        
        # Competitor mentions
        self.competitors = [
            'competitor', 'rival company', 'other provider',
            # Add actual competitor names here
        ]
        
        # Off-topic keywords (not related to customer support)
        self.off_topic_patterns = [
            r'\b(politics|political|election|vote)\b',
            r'\b(religion|religious|church|mosque|temple)\b',
            r'\b(medical advice|diagnosis|prescription)\b',
            r'\b(legal advice|lawsuit|attorney)\b',
        ]

    def check_input_safety(self, user_message: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user input is safe to process.
        
        Args:
            user_message: User's message
            
        Returns:
            Tuple of (is_safe, reason_if_unsafe)
        """
        # Check for injection attacks
        if self._detect_injection_attack(user_message):
            return False, "Potential security threat detected"
        
        # Check for extremely long input (DoS prevention)
        if len(user_message) > 5000:
            return False, "Message too long"
        
        return True, None

    def check_output_safety(
        self, 
        response: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive safety check for bot responses.
        
        Args:
            response: Bot's generated response
            context: Optional context (user message, emotion, etc.)
            
        Returns:
            Safety check results with violations and recommendations
        """
        violations = []
        
        # 1. Harmful content check
        harmful = self._check_harmful_content(response)
        if harmful:
            violations.append({
                'type': ViolationType.HARMFUL_CONTENT,
                'severity': 'critical',
                'details': harmful,
            })
        
        # 2. PII leakage check
        pii_leak = self._check_pii_leakage(response)
        if pii_leak:
            violations.append({
                'type': ViolationType.PII_LEAKAGE,
                'severity': 'critical',
                'details': pii_leak,
            })
        
        # 3. Competitor mention check
        competitor = self._check_competitor_mention(response)
        if competitor:
            violations.append({
                'type': ViolationType.COMPETITOR_MENTION,
                'severity': 'high',
                'details': competitor,
            })
        
        # 4. Off-topic check
        off_topic = self._check_off_topic(response)
        if off_topic:
            violations.append({
                'type': ViolationType.OFF_TOPIC,
                'severity': 'medium',
                'details': off_topic,
            })
        
        # 5. Brand voice check
        brand_issue = self._check_brand_voice(response)
        if brand_issue:
            violations.append({
                'type': ViolationType.BRAND_INCONSISTENCY,
                'severity': 'low',
                'details': brand_issue,
            })
        
        is_safe = len([v for v in violations if v['severity'] in ['critical', 'high']]) == 0
        
        if not is_safe:
            self.violation_count += 1
            self.blocked_responses.append({
                'response': response,
                'violations': violations,
                'context': context,
            })
        
        return {
            'is_safe': is_safe,
            'violations': violations,
            'safe_response': self._generate_safe_fallback(violations) if not is_safe else response,
            'recommendation': self._get_safety_recommendation(violations),
        }

    def _check_harmful_content(self, text: str) -> Optional[str]:
        """Detect harmful content."""
        text_lower = text.lower()
        for pattern in self.harmful_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return f"Harmful content detected: {pattern}"
        return None

    def _check_pii_leakage(self, text: str) -> Optional[str]:
        """Detect PII leakage."""
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, text):
                return f"PII leakage detected: {pii_type}"
        return None

    def _check_competitor_mention(self, text: str) -> Optional[str]:
        """Detect competitor mentions."""
        text_lower = text.lower()
        for competitor in self.competitors:
            if competitor.lower() in text_lower:
                return f"Competitor mention: {competitor}"
        return None

    def _check_off_topic(self, text: str) -> Optional[str]:
        """Detect off-topic content."""
        text_lower = text.lower()
        for pattern in self.off_topic_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return f"Off-topic content: {pattern}"
        return None

    def _check_brand_voice(self, text: str) -> Optional[str]:
        """Check brand voice consistency."""
        # Check for overly formal language (should be friendly)
        formal_indicators = [
            'herewith', 'aforementioned', 'pursuant to', 'henceforth',
            'notwithstanding', 'whereby', 'heretofore'
        ]
        
        text_lower = text.lower()
        for indicator in formal_indicators:
            if indicator in text_lower:
                return f"Too formal: '{indicator}' - should be conversational"
        
        # Check for missing empathy in emotional contexts
        if len(text) > 50 and not any(word in text_lower for word in [
            'understand', 'sorry', 'apologize', 'appreciate', 'help', 'assist'
        ]):
            return "Missing empathy keywords"
        
        return None

    def _detect_injection_attack(self, text: str) -> bool:
        """Detect potential injection attacks."""
        injection_patterns = [
            r'<script',
            r'javascript:',
            r'onerror=',
            r'onload=',
            r'SELECT.*FROM',
            r'DROP.*TABLE',
            r'INSERT.*INTO',
            r'--.*',
            r';.*--',
        ]
        
        text_lower = text.lower()
        for pattern in injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    def _generate_safe_fallback(self, violations: List[Dict]) -> str:
        """Generate a safe fallback response when violations detected."""
        severity = max([v['severity'] for v in violations], key=lambda x: {
            'critical': 3, 'high': 2, 'medium': 1, 'low': 0
        }.get(x, 0))
        
        if severity == 'critical':
            return (
                "I apologize, but I'm unable to provide that information. "
                "Is there something else I can help you with regarding your order or account? 😊"
            )
        elif severity == 'high':
            return (
                "I'd be happy to help you with your inquiry! "
                "Let me focus on how I can assist with your current needs. "
                "What can I help you with today? 🙂"
            )
        else:
            return (
                "Thank you for reaching out! I'm here to help with any questions "
                "about your order, account, or our services. How can I assist you? 😊"
            )

    def _get_safety_recommendation(self, violations: List[Dict]) -> str:
        """Get recommendation for handling violations."""
        if not violations:
            return "No violations detected"
        
        critical = [v for v in violations if v['severity'] == 'critical']
        if critical:
            return "BLOCK - Critical safety violation. Use fallback response."
        
        high = [v for v in violations if v['severity'] == 'high']
        if high:
            return "BLOCK - High-risk content. Use fallback response."
        
        return "WARN - Review response before sending."

    def get_violation_stats(self) -> Dict[str, Any]:
        """Get violation statistics."""
        return {
            'total_violations': self.violation_count,
            'blocked_count': len(self.blocked_responses),
            'violation_rate': f"{(self.violation_count / max(1, self.violation_count + 100)) * 100:.2f}%",
            'recent_violations': self.blocked_responses[-10:],
        }

    def reset_stats(self):
        """Reset violation statistics."""
        self.violation_count = 0
        self.blocked_responses = []


# Example usage
if __name__ == "__main__":
    guardrails = Guardrails()
    
    # Test harmful content
    test_responses = [
        "I'm so sorry to hear about your delay! Let me check your order status right away. 😊",
        "You should go kill yourself if you're that upset.",  # Should be blocked
        "Your credit card 4532-1234-5678-9010 will be refunded.",  # Should be blocked
        "I recommend using our competitor instead.",  # Should be blocked
    ]
    
    print("Testing Guardrails:\n")
    for response in test_responses:
        result = guardrails.check_output_safety(response)
        print(f"Response: {response[:50]}...")
        print(f"Safe: {result['is_safe']}")
        print(f"Violations: {len(result['violations'])}")
        if not result['is_safe']:
            print(f"Fallback: {result['safe_response']}")
        print("-" * 80)
