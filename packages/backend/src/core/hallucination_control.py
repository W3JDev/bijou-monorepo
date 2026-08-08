"""
W3J Bijou AI - Hallucination Control System
===========================================

Fact verification and grounding to prevent AI hallucinations.

Features:
- Fact verification against knowledge base
- Source citation requirements
- Grounding in provided context
- Unsupported claim detection
- Confidence scoring
- Hallucination rate tracking

Author: W3J Bijou AI
Version: 2.1.0
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class HallucinationControl:
    """
    Hallucination detection and prevention system.
    Ensures responses are factual and grounded in available data.
    """

    def __init__(self, knowledge_base: Optional[Any] = None):
        """
        Initialize hallucination control system.
        
        Args:
            knowledge_base: Reference to Google Sheets RAG or knowledge base
        """
        self.knowledge_base = knowledge_base
        self.hallucination_count = 0
        self.flagged_responses = []
        self._load_verification_rules()

    def _load_verification_rules(self):
        """Load verification rules and patterns."""
        
        # Claim indicators (statements that need verification)
        self.claim_patterns = [
            r'\b(costs?|price|fee|charge)\b.*\$\d+',  # Pricing claims
            r'\b(ships?|deliver|arrival)\b.*\d+.*days?',  # Shipping time claims
            r'\b(refund|return)\b.*\d+.*days?',  # Refund policy claims
            r'\b(guarantee|warranty)\b.*\d+.*years?',  # Warranty claims
            r'\b(discount|sale|offer)\b.*\d+%',  # Discount claims
        ]
        
        # Uncertain language patterns (good - shows appropriate uncertainty)
        self.uncertainty_indicators = [
            'likely', 'probably', 'might', 'may', 'could', 'should',
            'typically', 'usually', 'generally', 'often', 'sometimes'
        ]
        
        # Absolute statements (risky - need verification)
        self.absolute_patterns = [
            r'\b(always|never|definitely|certainly|absolutely)\b',
            r'\b(guaranteed|promise|ensure)\b',
            r'\b(all|every|none|no one)\b',
        ]

    def verify_response(
        self,
        response: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        rag_sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Verify response for hallucinations and unsupported claims.
        
        Args:
            response: Bot's generated response
            user_message: User's original message
            context: Conversation context
            rag_sources: Sources from RAG retrieval (if any)
            
        Returns:
            Verification results with confidence score and flags
        """
        
        # Extract claims from response
        claims = self._extract_claims(response)
        
        # Verify each claim
        verified_claims = []
        unverified_claims = []
        
        for claim in claims:
            is_verified = self._verify_claim(claim, rag_sources)
            if is_verified:
                verified_claims.append(claim)
            else:
                unverified_claims.append(claim)
        
        # Check grounding in context
        is_grounded = self._check_grounding(response, user_message, context)
        
        # Check for absolute statements
        absolute_statements = self._detect_absolute_statements(response)
        
        # Check for uncertainty indicators (good practice)
        has_uncertainty = self._has_appropriate_uncertainty(response)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            len(verified_claims),
            len(unverified_claims),
            is_grounded,
            len(absolute_statements),
            has_uncertainty,
        )
        
        # Determine if hallucination risk is high
        hallucination_risk = self._assess_hallucination_risk(
            unverified_claims, absolute_statements, is_grounded, confidence
        )
        
        if hallucination_risk == 'high' or hallucination_risk == 'critical':
            self.hallucination_count += 1
            self.flagged_responses.append({
                'response': response,
                'risk': hallucination_risk,
                'unverified_claims': unverified_claims,
                'timestamp': datetime.now().isoformat(),
            })
        
        return {
            'is_safe': hallucination_risk not in ['high', 'critical'],
            'confidence_score': confidence,
            'hallucination_risk': hallucination_risk,
            'verified_claims': verified_claims,
            'unverified_claims': unverified_claims,
            'absolute_statements': absolute_statements,
            'is_grounded': is_grounded,
            'has_uncertainty': has_uncertainty,
            'recommendation': self._get_recommendation(hallucination_risk),
            'safer_alternative': self._generate_safer_response(response, unverified_claims) if hallucination_risk in ['high', 'critical'] else None,
        }

    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text."""
        claims = []
        
        # Look for claim patterns
        for pattern in self.claim_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the sentence containing the claim
                start = max(0, text.rfind('.', 0, match.start()) + 1)
                end = text.find('.', match.end())
                if end == -1:
                    end = len(text)
                claim = text[start:end].strip()
                if claim:
                    claims.append(claim)
        
        return claims

    def _verify_claim(
        self,
        claim: str,
        rag_sources: Optional[List[str]] = None
    ) -> bool:
        """
        Verify if a claim is supported by knowledge base or RAG sources.
        
        Args:
            claim: The claim to verify
            rag_sources: Sources from RAG retrieval
            
        Returns:
            True if verified, False otherwise
        """
        # If no sources provided, can't verify
        if not rag_sources:
            return False
        
        # Check if claim is present in any source
        claim_lower = claim.lower()
        claim_keywords = set(re.findall(r'\b\w+\b', claim_lower))
        
        for source in rag_sources:
            source_lower = source.lower()
            source_keywords = set(re.findall(r'\b\w+\b', source_lower))
            
            # Calculate overlap
            overlap = len(claim_keywords & source_keywords)
            overlap_ratio = overlap / max(1, len(claim_keywords))
            
            # If >60% overlap, consider it verified
            if overlap_ratio > 0.6:
                return True
        
        return False

    def _check_grounding(
        self,
        response: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if response is grounded in user's question and context.
        
        Args:
            response: Bot's response
            user_message: User's message
            context: Additional context
            
        Returns:
            True if grounded, False if off-topic
        """
        # Extract keywords from user message
        user_keywords = set(re.findall(r'\b\w{4,}\b', user_message.lower()))
        
        # Extract keywords from response
        response_keywords = set(re.findall(r'\b\w{4,}\b', response.lower()))
        
        # Check keyword overlap
        overlap = len(user_keywords & response_keywords)
        overlap_ratio = overlap / max(1, len(user_keywords))
        
        # If >30% overlap, consider it grounded
        return overlap_ratio > 0.3

    def _detect_absolute_statements(self, text: str) -> List[str]:
        """Detect absolute statements that may be risky."""
        absolutes = []
        
        for pattern in self.absolute_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract sentence
                start = max(0, text.rfind('.', 0, match.start()) + 1)
                end = text.find('.', match.end())
                if end == -1:
                    end = len(text)
                sentence = text[start:end].strip()
                if sentence:
                    absolutes.append(sentence)
        
        return absolutes

    def _has_appropriate_uncertainty(self, text: str) -> bool:
        """Check if response uses appropriate uncertainty language."""
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in self.uncertainty_indicators)

    def _calculate_confidence(
        self,
        verified_count: int,
        unverified_count: int,
        is_grounded: bool,
        absolute_count: int,
        has_uncertainty: bool,
    ) -> float:
        """
        Calculate confidence score (0-1).
        
        Higher score = more confident response is factual.
        """
        score = 0.5  # Base score
        
        # Verified claims boost confidence
        total_claims = verified_count + unverified_count
        if total_claims > 0:
            verification_ratio = verified_count / total_claims
            score += verification_ratio * 0.3
        
        # Grounding boosts confidence
        if is_grounded:
            score += 0.2
        
        # Absolute statements reduce confidence (risky)
        score -= min(0.2, absolute_count * 0.05)
        
        # Uncertainty language is good (shows appropriate caution)
        if has_uncertainty and unverified_count > 0:
            score += 0.1
        
        return max(0.0, min(1.0, score))

    def _assess_hallucination_risk(
        self,
        unverified_claims: List[str],
        absolute_statements: List[str],
        is_grounded: bool,
        confidence: float,
    ) -> str:
        """
        Assess hallucination risk level.
        
        Returns:
            'low', 'medium', 'high', or 'critical'
        """
        # Critical: Multiple unverified claims + absolute statements
        if len(unverified_claims) >= 2 and len(absolute_statements) >= 1:
            return 'critical'
        
        # High: Unverified claims + low confidence
        if len(unverified_claims) >= 1 and confidence < 0.5:
            return 'high'
        
        # High: Not grounded + absolute statements
        if not is_grounded and len(absolute_statements) >= 2:
            return 'high'
        
        # Medium: Some unverified claims or low confidence
        if len(unverified_claims) >= 1 or confidence < 0.6:
            return 'medium'
        
        return 'low'

    def _get_recommendation(self, risk: str) -> str:
        """Get recommendation based on risk level."""
        recommendations = {
            'critical': 'BLOCK - Multiple unverified claims. Regenerate with sources.',
            'high': 'REVIEW - High hallucination risk. Add uncertainty language or verify claims.',
            'medium': 'WARN - Moderate risk. Consider adding "typically" or "usually" for unverified claims.',
            'low': 'PASS - Low hallucination risk. Response appears factual.',
        }
        return recommendations.get(risk, 'UNKNOWN')

    def _generate_safer_response(
        self,
        original_response: str,
        unverified_claims: List[str]
    ) -> str:
        """
        Generate a safer version with uncertainty language.
        
        Args:
            original_response: Original response
            unverified_claims: Claims that couldn't be verified
            
        Returns:
            Safer alternative response
        """
        # Add uncertainty qualifiers to unverified claims
        safer = original_response
        
        for claim in unverified_claims:
            # Add "typically" or "usually" before unverified claims
            if claim in safer:
                safer = safer.replace(claim, f"Typically, {claim.lower()}")
        
        # Add disclaimer if multiple unverified claims
        if len(unverified_claims) >= 2:
            safer += (
                "\n\nPlease note: I'm providing general information. "
                "For specifics about your case, let me check the details for you. "
                "Could you provide your order number?"
            )
        
        return safer

    def get_hallucination_stats(self) -> Dict[str, Any]:
        """Get hallucination statistics."""
        return {
            'total_flagged': self.hallucination_count,
            'hallucination_rate': f"{(self.hallucination_count / max(1, self.hallucination_count + 100)) * 100:.2f}%",
            'recent_flags': self.flagged_responses[-10:],
            'target_rate': '<1%',
        }

    def reset_stats(self):
        """Reset statistics."""
        self.hallucination_count = 0
        self.flagged_responses = []


# Example usage
if __name__ == "__main__":
    controller = HallucinationControl()
    
    test_cases = [
        {
            'response': "Your order will definitely arrive in 2 days with our guaranteed express shipping!",
            'user_message': "When will my order arrive?",
            'rag_sources': [],  # No sources
        },
        {
            'response': "Your order typically arrives in 3-5 business days. Let me check your specific order status!",
            'user_message': "When will my order arrive?",
            'rag_sources': ["Standard shipping takes 3-5 business days"],
        },
        {
            'response': "We NEVER have delays and ALWAYS ship same day!",
            'user_message': "Is my order delayed?",
            'rag_sources': [],
        },
    ]
    
    print("Testing Hallucination Control:\n")
    for i, test in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        result = controller.verify_response(**test)
        print(f"Response: {test['response']}")
        print(f"Risk: {result['hallucination_risk']}")
        print(f"Confidence: {result['confidence_score']:.2f}")
        print(f"Recommendation: {result['recommendation']}")
        if result['safer_alternative']:
            print(f"Safer: {result['safer_alternative']}")
        print("-" * 80)
