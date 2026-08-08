"""Unit tests for cultural term pre-filter (v299 validation)

Tests to verify that the Bengali/Malay pre-filter correctly handles:
1. Casual cultural terms (vaia, bhai, sayang, etc.) - should NOT escalate
2. Explicit escalation requests - SHOULD escalate
3. Casual terms + explicit requests - explicit should WIN
4. Performance requirements (<10ms for pre-filter)

Author: W3J Bijou AI
Version: v299
Date: 2026-02-13
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from src.saas.ai_handover_detector import detect_handover_intent


class TestPreFilterV299:
    """Tests to verify v299 pre-filter is working correctly"""
    
    @pytest.mark.parametrize("message,should_escalate,reason_keyword", [
        # ===== CASUAL TERMS THAT SHOULD NOT ESCALATE =====
        # Bengali casual terms
        ("vaia help me", False, "casual"),
        ("thanks bhai", False, "casual"),
        ("acha bro", False, "casual"),
        ("Okh vaia thik ase boilo", False, "casual"),
        ("Akhn Ki kortam vaia Oita bolo 1tu bujai", False, "casual"),
        ("vaia can you help", False, "casual"),
        ("boss where is my order", False, "casual"),
        
        # Malay casual terms
        ("ok sayang", False, "casual"),
        ("terima kasih abang", False, "casual"),
        ("kakak boleh tolong saya", False, "casual"),
        
        # English casual terms
        ("thanks bruh", False, "casual"),
        ("ok boss", False, "casual"),
        
        # ===== EXPLICIT REQUESTS THAT SHOULD ESCALATE =====
        ("I need to speak to the owner NOW", True, "owner"),
        ("speak to manager", True, "manager"),
        ("talk to owner", True, "owner"),
        ("connect me to real person", True, "real person"),
        ("I want to talk to a human person", True, "human person"),
        ("not ai please", True, "not ai"),
        ("I need him to call me", True, "i need him"),
        ("transfer me to someone", True, "transfer"),
        
        # ===== CASUAL + EXPLICIT (EXPLICIT SHOULD WIN) =====
        ("vaia I need to talk to the owner", True, "owner"),
        ("bhai speak to manager please", True, "manager"),
        ("sayang connect me to owner", True, "owner"),
        ("boss I want to talk to actual person", True, "actual person"),
        ("vaia transfer me to real person", True, "real person"),
    ])
    def test_pre_filter_accuracy(self, message, should_escalate, reason_keyword):
        """Test pre-filter handles cultural terms and escalations correctly"""
        needs_handover, detected_reason, urgency = detect_handover_intent(message)
        
        if should_escalate:
            assert needs_handover == True, \
                f"'{message}' should escalate (has explicit keyword '{reason_keyword}')"
            assert reason_keyword.lower() in detected_reason.lower(), \
                f"Expected reason to contain '{reason_keyword}', got '{detected_reason}'"
        else:
            assert needs_handover == False, \
                f"'{message}' should NOT escalate (casual term only)"
            assert any(kw in detected_reason.lower() for kw in ["casual", "normal", "conversational"]), \
                f"Expected casual/normal/conversational in reason, got '{detected_reason}'"
    
    def test_pre_filter_performance(self):
        """Pre-filter should be fast (<10ms) since it skips AI analysis"""
        import time
        
        # Test pre-filter speed (should not call Gemini API)
        start = time.time()
        needs_handover, reason, urgency = detect_handover_intent("vaia help me")
        duration = time.time() - start
        
        # Pre-filter should skip AI, be instant
        assert duration < 0.01, \
            f"Pre-filter too slow: {duration*1000:.2f}ms (should be <10ms)"
        
        # Verify it was pre-filtered (not AI analyzed)
        assert needs_handover == False
        assert "casual" in reason.lower() or "normal" in reason.lower()
    
    def test_empty_and_short_messages(self):
        """Test pre-filter handles edge cases"""
        # Empty message
        needs_handover, reason, urgency = detect_handover_intent("")
        assert needs_handover == False, "Empty message should not escalate"
        
        # Very short message (< 15 chars)
        needs_handover, reason, urgency = detect_handover_intent("ok")
        assert needs_handover == False, "Short acknowledgment should not escalate"
        assert "short" in reason.lower() or "acknowledgment" in reason.lower()
        
        # Emoji only
        needs_handover, reason, urgency = detect_handover_intent("👍❤️")
        assert needs_handover == False, "Emoji-only should not escalate"
    
    def test_urgency_levels(self):
        """Test that urgency is correctly assigned"""
        # Normal urgency
        needs_handover, reason, urgency = detect_handover_intent("speak to owner")
        if needs_handover:
            assert urgency in ["normal", "high", "urgent"], \
                f"Expected valid urgency level, got '{urgency}'"
        
        # High urgency (with NOW/URGENT keywords)
        needs_handover, reason, urgency = detect_handover_intent("I need to speak to owner NOW")
        if needs_handover:
            assert urgency in ["high", "urgent"], \
                f"'NOW' keyword should trigger high/urgent, got '{urgency}'"
    
    @pytest.mark.parametrize("message", [
        "vaia",  # Just the term alone
        "bhai",
        "sayang",
        "boss",
    ])
    def test_standalone_casual_terms(self, message):
        """Standalone casual terms should not escalate"""
        needs_handover, reason, urgency = detect_handover_intent(message)
        assert needs_handover == False, \
            f"Standalone '{message}' should not escalate"


class TestHistoricalRegressions:
    """Prevent bugs that were fixed from coming back"""
    
    def test_false_positive_messages_v294(self):
        """Regression: Ensure v294 false escalation bug stays fixed
        
        These messages caused false escalations before v294.
        They should NEVER escalate again.
        """
        false_positive_messages = [
            "Okh vaia thik ase boilo",  # Historical false positive #1
            "Akhn Ki kortam vaia Oita bolo 1tu bujai",  # Historical false positive #2
            "ok sayang",  # Historical false positive #3
            "vaia help me",  # Historical false positive #4
            "thanks bhai",
            "acha boss",
        ]
        
        for msg in false_positive_messages:
            needs_handover, reason, urgency = detect_handover_intent(msg)
            assert needs_handover == False, \
                f"REGRESSION: '{msg}' escalated (should be blocked by pre-filter)"
            assert any(kw in reason.lower() for kw in ["casual", "normal", "short"]), \
                f"Expected pre-filter reason for '{msg}', got '{reason}'"
    
    def test_explicit_escalations_still_work(self):
        """Regression: Ensure we didn't break actual escalations
        
        These should ALWAYS escalate, even with v299 pre-filter.
        """
        must_escalate_messages = [
            "I need to speak to the owner NOW",
            "speak to manager",
            "connect me to real person",
            "I want to talk to actual person",
        ]
        
        for msg in must_escalate_messages:
            needs_handover, reason, urgency = detect_handover_intent(msg)
            assert needs_handover == True, \
                f"REGRESSION: '{msg}' NOT escalated (should always escalate)"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
