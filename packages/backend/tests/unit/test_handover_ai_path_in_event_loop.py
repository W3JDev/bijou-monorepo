"""Regression: the AI handover detector must actually run from inside the
async message handler, not silently fall back to keywords.

detect_handover_intent() is sync and calls asyncio.run() on the gateway.
process_message is async, so calling it directly raised "asyncio.run() cannot
be called from a running event loop", the except swallowed it, and every
check degraded to _keyword_fallback. bijou.py now calls it via
asyncio.to_thread (2026-09-26).
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.saas.ai_handover_detector import detect_handover_intent

MSG = "I really need to speak with a real person about my refund please"
AI_REASON = "explicit request for a person"


def _fake_gateway():
    return AsyncMock(
        return_value=SimpleNamespace(
            text='{"wants_human": true, "reason": "%s", "urgency": "high"}' % AI_REASON
        )
    )


def test_ai_path_runs_when_called_via_to_thread_from_event_loop():
    async def handler():
        return await asyncio.to_thread(detect_handover_intent, MSG)

    with patch("src.core.llm_gateway_v2.llm.complete", _fake_gateway()):
        wants_human, reason, urgency = asyncio.run(handler())

    assert wants_human is True
    assert reason == AI_REASON  # AI answer, not the keyword fallback's reason
    assert urgency == "high"


def test_direct_call_from_event_loop_falls_back_to_keywords():
    """Documents the original bug so the to_thread wrapper is not removed."""

    async def handler():
        return detect_handover_intent(MSG)

    with patch("src.core.llm_gateway_v2.llm.complete", _fake_gateway()):
        _, reason, _ = asyncio.run(handler())

    assert reason != AI_REASON
