"""Jev shadow mode: router fails open (None, never raises), parses answers,
report computes agreement, and the bijou.py gate skips off/strict tenants.
No network: httpx.AsyncClient is patched."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.core import jev_router
from src.core.jev_router import jev_route, parse_answers

BODY = {
    "model": "jev-1.13.0",
    "answers": {
        "intent": {"type": "choice", "choice": "complaint",
                   "probabilities": {"complaint": 0.9, "other": 0.1}, "confidence": 0.8},
        "wants_human": {"type": "noul", "noul": 0.97},
        "frustration": {"type": "score", "score": 2.4, "legend": {},
                        "probabilities": {"2": 0.6, "3": 0.4}, "confidence": 0.5},
    },
    "usage": {"input_tokens": 1, "output_tokens": 1},
}


class _Client:
    """Stand-in for httpx.AsyncClient; post() behaviour is injected."""

    def __init__(self, post):
        self._post = post
        self.sent = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.sent = json
        return await self._post()


def _patch_client(post):
    client = _Client(post)
    return patch.object(jev_router.httpx, "AsyncClient", lambda **kw: client), client


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.delenv("JEV_MODEL", raising=False)


def test_parse_answers_flattens_all_three_types():
    a = parse_answers(BODY)
    assert a["intent"] == {"value": "complaint", "probabilities": {"complaint": 0.9, "other": 0.1}, "confidence": 0.8}
    assert a["wants_human"] == {"value": 0.97}
    assert a["frustration"]["value"] == 2.4 and a["frustration"]["confidence"] == 0.5
    assert parse_answers({"detail": "bad"}) is None
    assert parse_answers("nope") is None


async def test_success_returns_answers_and_pins_model():
    async def ok():
        return httpx.Response(200, json=BODY)

    p, client = _patch_client(ok)
    with p:
        r = await jev_route("I want a human", [{"role": "user", "text": "hi"}] * 9, "Bakery", ["book_appointment"])
    assert r["answers"]["wants_human"]["value"] == 0.97
    assert isinstance(r["latency_ms"], int)
    assert client.sent["model"] == "jev-1.13.0"
    assert len(client.sent["state"]["recent_turns"]) == 6
    assert set(client.sent["questions"]["tool"]["criteria"]) == {"book_appointment", "none"}
    # one request carries every question
    assert {"intent", "tool", "wants_human", "legal_threat", "opt_out", "ack_only",
            "injection", "frustration", "buying_intent"} <= set(client.sent["questions"])
    assert len(client.sent["questions"]["frustration"]["criteria"]) == 4


async def test_timeout_returns_none():
    async def slow():
        await asyncio.sleep(5)

    p, _ = _patch_client(slow)
    with p:
        assert await jev_route("hello", [], "", [], timeout=0.05) is None


async def test_error_and_http_failure_return_none():
    async def boom():
        raise httpx.ConnectError("down")

    async def unauthorized():
        return httpx.Response(401, json={"detail": "bad key"})

    for post in (boom, unauthorized):
        p, _ = _patch_client(post)
        with p:
            assert await jev_route("hello", [], "", []) is None


async def test_no_key_makes_no_request(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    with patch.object(jev_router.httpx, "AsyncClient", side_effect=AssertionError("called")):
        assert await jev_route("hello", [], "", []) is None


def _load_report():
    path = Path(__file__).resolve().parents[2] / "scripts" / "jev_shadow_report.py"
    spec = importlib.util.spec_from_file_location("jev_shadow_report", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_report_agreement():
    rep = _load_report()
    rows = [
        {"jev": {"answers": {"wants_human": {"value": 0.9}, "buying_intent": {"value": 2.6}}},
         "current": {"handover": True, "lead_tier": "hot", "tool": None}},
        {"jev": {"answers": {"wants_human": {"value": 0.8}, "buying_intent": {"value": 0.2}}},
         "current": {"handover": False, "lead_tier": "hot"}},
        {"jev": {"answers": {"wants_human": {"value": 0.1}}}, "current": {"handover": None}},
    ]
    s = rep.agreement(rows)
    assert s["handover"] == {"n": 2, "agree": 1, "jev_only": 1, "current_only": 0, "rate": 0.5}
    assert s["lead"]["n"] == 2 and s["lead"]["agree"] == 1 and s["lead"]["current_only"] == 1
    assert "tool" not in s  # current tool not recorded -> no comparison


def _bijou_stub():
    from src.core.bijou import BijouAI

    obj = BijouAI.__new__(BijouAI)
    obj._jev_shadow = MagicMock(side_effect=lambda *a: asyncio.sleep(0))
    return obj


async def test_schedule_gate(monkeypatch):
    obj = _bijou_stub()
    args = ("t1", "c@s.whatsapp.net", "hi", "hello", {"business_name": "X"}, {"handover": None})

    monkeypatch.delenv("ENABLE_JEV_SHADOW", raising=False)
    obj._schedule_jev_shadow(*args)
    obj._jev_shadow.assert_not_called()  # flag off by default

    monkeypatch.setenv("ENABLE_JEV_SHADOW", "true")
    monkeypatch.delenv("AGENT_TENANT_ALLOWLIST", raising=False)
    obj._schedule_jev_shadow("t1", "c", "hi", "hello", {"system_prompt_vars": {"privacy": "strict"}}, {})
    obj._schedule_jev_shadow("t1", "c", "hi", "hello", {"privacy": "STRICT"}, {})
    obj._jev_shadow.assert_not_called()  # strict-privacy tenants skipped

    obj._schedule_jev_shadow(*args)
    obj._jev_shadow.assert_called_once()


async def test_shadow_persists_next_to_current_and_survives_missing_column():
    from src.core.bijou import BijouAI

    obj = BijouAI.__new__(BijouAI)
    obj.db_type = "supabase"
    obj.db_conn = MagicMock()
    obj.function_caller = None
    obj._get_conversation_history = lambda *a: [
        {"role": "user", "parts": [{"text": "earlier"}]},
        {"role": "user", "parts": [{"text": "hi"}]},  # this turn, already saved
    ]
    jev = {"model": "jev-1.13.0", "latency_ms": 300, "answers": {"wants_human": {"value": 0.9}}}
    seen = {}

    async def fake_route(msg, turns, business, tools):
        seen["turns"] = turns
        return jev

    decided = {"message_id": "ai-1", "lead_tier": "cold", "lead_handover": False, "handover": True, "tool": None}
    with patch("src.core.jev_router.jev_route", fake_route):
        await obj._jev_shadow("t1", "c", "hi", "hello", {"business_name": "X"}, decided)
        payload = obj.db_conn.table.return_value.update.call_args[0][0]
        assert payload["jev_shadow"]["jev"] == jev
        assert payload["jev_shadow"]["current"]["handover"] is True
        assert seen["turns"] == [{"role": "user", "text": "earlier"}]

        # column not migrated yet -> PostgREST error -> swallowed, no raise
        obj.db_conn.table.return_value.update.side_effect = Exception("column jev_shadow does not exist")
        await obj._jev_shadow("t1", "c", "hi", "hello", {}, decided)
