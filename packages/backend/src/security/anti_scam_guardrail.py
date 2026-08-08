from typing import Dict, List, Optional
import re

class AntiScamGuardrail:
    """
    Detect and block social engineering attacks and scam attempts.
    """
    
    def __init__(self):
        # Patterns that indicate manipulation
        self.scam_patterns = {
            "authority_impersonation": [
                r"i'?m the owner", r"i'?m your boss", r"i'?m the ceo",
                r"i'?m from it", r"i'?m from support", r"this is management",
                r"admin.*access"
            ],
            "urgency_pressure": [
                r"urgent", r"immediately", r"right now", r"asap",
                r"before end of day", r"time sensitive", r"do it now"
            ],
            "financial_requests": [
                r"wire transfer", r"send money", r"process payment", 
                r"bank account", r"crypto", r"bitcoin", r"gift card"
            ],
            "instruction_override": [
                r"ignore previous", r"forget your instructions",
                r"new protocol", r"bypass", r"override", r"special permission",
                r"system update", r"debug mode"
            ],
            "data_requests": [
                r"customer list", r"database", r"all customers",
                r"email addresses", r"phone numbers", r"export data",
                r"dump.*data"
            ]
        }
        
        # Responses that deflect without revealing the detection
        self.safe_responses = {
            "authority_impersonation": "I'm not able to verify identity through chat. For account or administrative requests, please contact the owner directly via their verified phone number.",
            "financial_requests": "For financial transactions, I'll need to verify this request with the account owner. They'll contact you directly to complete this.",
            "data_requests": "I don't have access to customer data exports. Please contact the business owner directly for data-related requests.",
            "default": "I'm not able to help with that request. Please contact the business owner directly."
        }
    
    def analyze_intent(self, message: str) -> Dict:
        """
        Detect manipulation attempts in the message.
        """
        msg_lower = message.lower()
        
        scam_score = 0
        triggered_categories = []
        matches = []
        
        for category, patterns in self.scam_patterns.items():
            category_triggered = False
            for pattern in patterns:
                # Use regex search for more robust matching
                if re.search(pattern, msg_lower):
                    if not category_triggered:
                        scam_score += 1
                        triggered_categories.append(category)
                        category_triggered = True
                    matches.append(pattern)
        
        # Logic for determining if it is a scam
        # HIGH RISK: 2+ categories triggered
        is_scam = scam_score >= 2
        
        # MEDIUM RISK: 1 category + question mark (asking for action) or specific high-risk categories
        if scam_score == 1:
            if "?" in message or any(cat in triggered_categories for cat in ["authority_impersonation", "instruction_override", "data_requests"]):
                is_scam = True
        
        return {
            "is_potential_scam": is_scam,
            "scam_score": scam_score,
            "categories": triggered_categories,
            "matches": matches,
            "confidence": min(scam_score * 0.4, 1.0)
        }
    
    def get_safe_response(self, scam_analysis: Dict) -> str:
        """Generate safe refusal without revealing detection"""
        
        categories = scam_analysis.get("categories", [])
        
        if "authority_impersonation" in categories:
            return self.safe_responses["authority_impersonation"]
        
        if "financial_requests" in categories:
            return self.safe_responses["financial_requests"]
            
        if "data_requests" in categories:
            return self.safe_responses["data_requests"]
            
        return self.safe_responses["default"]
