"""
Unit Tests — Missed Call Handler (Pure Logic)
=============================================

Replaced the old suite that imported the removed ``process_webhook_message``
standalone function.  Tests now target the two pure, side-effect-free helpers
extracted to module level in bijou.py:

    * ``is_missed_call(message)``         — detection predicate
    * ``build_missed_call_context()``     — AI context string builder
    * ``MISSED_CALL_SYSTEM_CONTEXT``      — sentinel constant

No async, no mocks, no external dependencies required  — pure unit tests.
"""

import pytest
from src.core.bijou import (
    is_missed_call,
    build_missed_call_context,
    MISSED_CALL_SYSTEM_CONTEXT,
)

TEST_CALLER_JID = "60198765432@s.whatsapp.net"

# ── is_missed_call — detection predicate ──────────────────────────────────────


class TestIsMissedCall:
    """is_missed_call() must detect all known bridge payload shapes."""

    # ── True cases ────────────────────────────────────────────────────────────

    def test_detects_by_message_type_field(self):
        msg = {"message_type": "missed_call", "content": "", "from": TEST_CALLER_JID}
        assert is_missed_call(msg) is True

    def test_detects_by_content_sentinel(self):
        msg = {"message_type": "", "content": "📞 MISSED_CALL", "from": TEST_CALLER_JID}
        assert is_missed_call(msg) is True

    def test_detects_by_body_sentinel_legacy(self):
        """Older bridge payloads used 'body' instead of 'content'."""
        msg = {"body": "📞 MISSED_CALL", "from": TEST_CALLER_JID}
        assert is_missed_call(msg) is True

    def test_detects_when_both_type_and_content_set(self):
        msg = {"message_type": "missed_call", "content": "📞 MISSED_CALL"}
        assert is_missed_call(msg) is True

    def test_detects_with_extra_irrelevant_fields(self):
        msg = {
            "id": "MSG_001",
            "message_type": "missed_call",
            "content": "",
            "sender": TEST_CALLER_JID,
            "timestamp": 1708704000,
            "is_from_me": False,
        }
        assert is_missed_call(msg) is True

    # ── False cases ───────────────────────────────────────────────────────────

    def test_returns_false_for_regular_text(self):
        msg = {"message_type": "text", "content": "Hello, what are your hours?"}
        assert is_missed_call(msg) is False

    def test_returns_false_for_voice_note(self):
        msg = {"message_type": "voice", "content": ""}
        assert is_missed_call(msg) is False

    def test_returns_false_for_image(self):
        msg = {"message_type": "image", "content": "Check this out"}
        assert is_missed_call(msg) is False

    def test_returns_false_for_empty_message(self):
        assert is_missed_call({}) is False

    def test_returns_false_for_partial_sentinel(self):
        """Partial match must NOT trigger — must be exact sentinel."""
        msg = {"content": "MISSED_CALL"}  # Missing emoji prefix
        assert is_missed_call(msg) is False

    def test_returns_false_for_emoji_only(self):
        msg = {"content": "📞"}
        assert is_missed_call(msg) is False

    def test_returns_false_when_content_is_none(self):
        msg = {"message_type": None, "content": None}
        assert is_missed_call(msg) is False

    def test_returns_false_for_video_call_accepted(self):
        """A *connected* call is not a missed call."""
        msg = {"message_type": "video_call", "content": ""}
        assert is_missed_call(msg) is False

    def test_returns_false_for_integer_content(self):
        """Malformed payload with non-string content must not raise."""
        msg = {"content": 12345, "message_type": "missed_call_typo"}
        # message_type doesn't match "missed_call", content coerced — no crash
        assert is_missed_call(msg) is False

    def test_case_sensitive_type_check(self):
        """'Missed_Call' (wrong case) must NOT be treated as missed call."""
        msg = {"message_type": "Missed_Call", "content": ""}
        assert is_missed_call(msg) is False


# ── build_missed_call_context — AI context string ─────────────────────────────


class TestBuildMissedCallContext:
    """build_missed_call_context() must return the exact AI system prompt."""

    def test_returns_string(self):
        result = build_missed_call_context()
        assert isinstance(result, str)

    def test_not_empty(self):
        result = build_missed_call_context()
        assert len(result) > 0

    def test_contains_missed_call_reference(self):
        result = build_missed_call_context()
        assert "tried to call" in result

    def test_contains_system_context_marker(self):
        result = build_missed_call_context()
        assert "[SYSTEM CONTEXT:" in result

    def test_contains_acknowledge_instruction(self):
        result = build_missed_call_context()
        assert "acknowledge the missed call naturally" in result

    def test_contains_escalation_instruction(self):
        result = build_missed_call_context()
        assert "escalate to a human immediately" in result

    def test_does_not_reveal_ai_identity(self):
        """Context must instruct AI NOT to identify itself unprompted."""
        result = build_missed_call_context()
        assert "Do NOT mention you are an AI" in result

    def test_matches_module_constant(self):
        """build_missed_call_context() must return the module constant."""
        assert build_missed_call_context() == MISSED_CALL_SYSTEM_CONTEXT

    def test_idempotent(self):
        """Calling twice must return same string (pure function)."""
        assert build_missed_call_context() == build_missed_call_context()

    def test_no_placeholder_text(self):
        """Context must be fully populated — no TODO/placeholder remnants."""
        result = build_missed_call_context()
        assert "TODO" not in result
        assert "PLACEHOLDER" not in result
        assert "..." not in result


# ── MISSED_CALL_SYSTEM_CONTEXT constant ───────────────────────────────────────


class TestMissedCallConstant:
    """The module-level constant must have the correct structure."""

    def test_is_string(self):
        assert isinstance(MISSED_CALL_SYSTEM_CONTEXT, str)

    def test_starts_with_system_context(self):
        assert MISSED_CALL_SYSTEM_CONTEXT.startswith("[SYSTEM CONTEXT:")

    def test_ends_with_closing_bracket(self):
        assert MISSED_CALL_SYSTEM_CONTEXT.endswith("]")

    def test_contains_all_required_sections(self):
        ctx = MISSED_CALL_SYSTEM_CONTEXT
        assert "call was not answered" in ctx
        assert "Greet them warmly" in ctx
        assert "ask how you can help" in ctx
        assert "escalate to a human immediately" in ctx

    def test_length_is_reasonable(self):
        """Context should be meaningful but not excessively long."""
        assert 100 < len(MISSED_CALL_SYSTEM_CONTEXT) < 1000


# ── Integration: detection → context pipeline ─────────────────────────────────


class TestMissedCallPipeline:
    """Simulate the logic path: detect a missed call → build context."""

    def _process(self, message):
        """Mirror exactly what process_message does inside bijou.py."""
        if is_missed_call(message):
            return build_missed_call_context()
        return None

    def test_missed_call_yields_context(self):
        msg = {"message_type": "missed_call", "content": ""}
        result = self._process(msg)
        assert result is not None
        assert "[SYSTEM CONTEXT:" in result

    def test_regular_message_yields_no_context(self):
        msg = {"message_type": "text", "content": "Hi, what are your prices?"}
        assert self._process(msg) is None

    def test_both_sentinel_shapes_yield_same_context(self):
        by_type = self._process({"message_type": "missed_call"})
        by_content = self._process({"content": "📞 MISSED_CALL"})
        by_body = self._process({"body": "📞 MISSED_CALL"})
        assert by_type == by_content == by_body

    def test_context_injected_only_once(self):
        """Pipeline must not double-inject the SYSTEM CONTEXT marker."""
        msg = {"message_type": "missed_call", "content": "📞 MISSED_CALL"}
        ctx = self._process(msg)
        assert ctx.count("[SYSTEM CONTEXT:") == 1

    def test_empty_message_produces_no_context(self):
        assert self._process({}) is None

    def test_none_values_handled_gracefully(self):
        msg = {"message_type": None, "content": None, "body": None}
        # Must not raise
        result = self._process(msg)
        assert result is None


