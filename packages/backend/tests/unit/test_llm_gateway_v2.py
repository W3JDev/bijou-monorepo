"""
Tests for the LLM Gateway v2 — aliases, fallback chain, budget, privacy, and
observability.

The gateway is a pure orchestration layer: it owns the alias→provider policy
file, the fallback order, the budget counter, and the structured log. The
provider calls themselves are faked via a per-test dispatch override, so these
tests run with zero network and zero external API keys.

Coverage:
  - 4 aliases resolve to their declared primary
  - Fallback chain fires on 429 / 5xx and stops on first success
  - Privacy: ai://private never falls back to openrouter even if declared
  - Budget: spending cap returns BudgetExceeded and 429s the caller
  - Observability: every successful call writes a structured row with
    provider / model / alias / latency_ms / tokens / cost / fallback_reason
  - Unknown alias and NoProviderAvailable paths
  - _UsageTracker / drain_buffer / spent_today
  - The migration file exists and has the expected table name

Total: 25 tests.
"""
import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Make src.* importable when pytest is run from any cwd.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import llm_gateway_v2 as g  # noqa: E402
from src.core.llm_gateway_v2 import (  # noqa: E402
    BudgetExceeded,
    LLMGateway,
    NoProviderAvailable,
    ProviderError,
    _call_gemini,
    _call_openai_compatible,
    _read_env_keys,
    _UsageTracker,
)


# -----------------------------------------------------------------------------
# Helpers — fake provider dispatch.
# -----------------------------------------------------------------------------


def _ok(text="hello", pt=10, ct=5, model="m1"):
    """Build a fake adapter callable that returns a successful result tuple."""
    payload = (text, {"fake": True}, pt, ct, model)

    def fake(model, messages, opts):
        return payload

    return fake


def _err(status_code=429, message="rate limit"):
    """Build a fake adapter that raises ProviderError."""

    def fake(model, messages, opts):
        raise ProviderError(message, status_code=status_code)

    return fake


@pytest.fixture
def fresh_gateway():
    """Build a gateway whose dispatch is fully faked — zero network."""
    gw = LLMGateway.__new__(LLMGateway)  # skip __init__ to avoid file IO
    gw._config_path = g._CONFIG_PATH
    gw._lock = __import__("threading").Lock()
    # Reload from the real YAML — same file the runtime uses.
    gw.reload()
    gw._usage = _UsageTracker()
    gw._dispatch_override = {}
    return gw


def _set_dispatch(gw, **per_provider):
    """Inject fake adapters by provider name. Every provider declared in the
    gateway config that is NOT named here is stubbed to raise a no-key
    ProviderError (status None) so tests stay hermetic (no network) and un-faked
    fallbacks are simply skipped by the rotator. Needed now that the standard
    aliases fan out to minimax/vercel/google_openai/cloudflare — without this the
    suite would hit real endpoints for any provider whose key happens to be set."""
    dispatch = {
        name: _err(None, "not configured in test")
        for name in (gw._config.get("providers") or {})
    }
    dispatch.update(per_provider)
    gw._dispatch_override = dispatch


# -----------------------------------------------------------------------------
# 1. Each alias resolves to its primary
# -----------------------------------------------------------------------------


def test_fast_alias_routes_to_minimax_primary(fresh_gateway):
    _set_dispatch(fresh_gateway, minimax=_ok("fast reply", model="MiniMax-M3"))
    r = asyncio.run(
        fresh_gateway.complete("ai://fast", [{"role": "user", "content": "hi"}])
    )
    assert r.provider == "minimax"
    assert r.text == "fast reply"
    assert r.alias == "ai://fast"
    assert r.fallback_reason is None  # primary answered


def test_reasoning_alias_routes_to_minimax_primary(fresh_gateway):
    _set_dispatch(fresh_gateway, minimax=_ok("reasoning reply"))
    r = asyncio.run(
        fresh_gateway.complete("ai://reasoning", [{"role": "user", "content": "x"}])
    )
    assert r.provider == "minimax"
    assert r.alias == "ai://reasoning"


def test_extract_alias_routes_to_minimax_primary(fresh_gateway):
    _set_dispatch(fresh_gateway, minimax=_ok('{"intent":"buy"}'))
    r = asyncio.run(
        fresh_gateway.complete("ai://extract", [{"role": "user", "content": "x"}])
    )
    assert r.provider == "minimax"
    assert r.alias == "ai://extract"


def test_private_alias_routes_to_gemini_primary(fresh_gateway):
    _set_dispatch(fresh_gateway, gemini=_ok("private reply"))
    r = asyncio.run(
        fresh_gateway.complete("ai://private", [{"role": "user", "content": "x"}])
    )
    assert r.provider == "gemini"
    assert r.alias == "ai://private"


# -----------------------------------------------------------------------------
# 2. Fallback chain — primary 429 -> next provider
# -----------------------------------------------------------------------------


def test_fallback_on_429_uses_next_provider(fresh_gateway):
    _set_dispatch(
        fresh_gateway,
        minimax=_err(429, "quota"),
        openrouter=_ok("from openrouter", model="google/gemini-2.5-flash"),
    )
    r = asyncio.run(
        fresh_gateway.complete("ai://fast", [{"role": "user", "content": "hi"}])
    )
    assert r.provider == "openrouter"
    assert r.fallback_reason == "http_429"
    assert r.text == "from openrouter"


def test_fallback_on_503_uses_next_provider(fresh_gateway):
    _set_dispatch(
        fresh_gateway,
        minimax=_err(503, "down"),
        openrouter=_ok("ok"),
    )
    r = asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    assert r.provider == "openrouter"
    assert r.fallback_reason == "http_503"


def test_fallback_chain_walks_through_all_entries(fresh_gateway):
    _set_dispatch(
        fresh_gateway,
        minimax=_err(429),
        openrouter=_err(502),
        openai_compatible=_ok("final", model="gpt-4o-mini"),
    )
    r = asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    assert r.provider == "openai_compatible"
    assert r.fallback_reason == "http_502"  # last failure that triggered the move


def test_provider_side_403_falls_through(fresh_gateway):
    """A suspended key (403) — like the real Gemini outage — is a PROVIDER-side
    failure: a different provider can still serve the request, so the rotator
    must fall through, not surface the error. (2026-09-21 fix — previously 403
    aborted and the agent replied "I'm having trouble processing your request".)"""
    _set_dispatch(
        fresh_gateway,
        minimax=_err(403, "key suspended"),
        vercel=_ok("from vercel", model="google/gemini-2.5-flash"),
    )
    r = asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    assert r.provider == "vercel"
    assert r.fallback_reason == "http_403"
    assert r.text == "from vercel"


def test_400_also_falls_through_because_providers_disagree(fresh_gateway):
    """We do NOT hard-stop on 400. Google's OpenAI-compat endpoint returns 400 for
    a bad API key, so treating 400 as fatal would abort the chain on an auth
    failure a sibling provider could serve. 400 falls through like any other."""
    _set_dispatch(
        fresh_gateway,
        minimax=_err(400, "please pass a valid api key"),
        vercel=_ok("from vercel", model="google/gemini-2.5-flash"),
    )
    r = asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    assert r.provider == "vercel"
    assert r.text == "from vercel"


def test_keyless_provider_is_skipped_not_fatal(fresh_gateway):
    """A fallback provider with no API key raises ProviderError(status_code=None).
    That must SKIP to the next provider (so the chain reaches a configured one),
    never abort — otherwise adding MiniMax as the first fallback with no key set
    would break every reply."""
    _set_dispatch(
        fresh_gateway,
        minimax=_err(403, "suspended"),
        vercel=_err(None, "no key"),
        google_openai=_err(None, "no key"),
        openrouter=_ok("reached openrouter"),
    )
    r = asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    assert r.provider == "openrouter"
    assert r.text == "reached openrouter"
    # The no-key skips must NOT clobber the informative 403 reason.
    assert r.fallback_reason == "http_403"


def test_all_providers_failing_raises_last_error(fresh_gateway):
    _set_dispatch(
        fresh_gateway,
        minimax=_err(500),
        openrouter=_err(503),
        openai_compatible=_err(429),
    )
    with pytest.raises(ProviderError) as exc:
        asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    assert exc.value.status_code == 429


# -----------------------------------------------------------------------------
# 3. Privacy — ai://private must NEVER fall back to OpenRouter
# -----------------------------------------------------------------------------


def test_private_alias_skips_openrouter_even_if_listed(fresh_gateway):
    """Even if someone (incorrectly) added openrouter to private's fallbacks,
    the strict-privacy gate must filter it out before it ever gets called."""
    # Hand-craft a config with openrouter sneaking in.
    fresh_gateway._config["aliases"]["ai://private"]["fallbacks"].insert(
        0, {"provider": "openrouter", "model": "x", "max_output_tokens": 100, "temperature": 0.3}
    )
    _set_dispatch(
        fresh_gateway,
        gemini=_err(429),
        openrouter=_ok("leak"),  # must NOT be called
        openai_compatible=_ok("safe", model="gpt-4o-mini"),
    )
    r = asyncio.run(
        fresh_gateway.complete("ai://private", [{"role": "user", "content": "ssn: 123"}])
    )
    assert r.provider == "openai_compatible"
    assert "leak" not in r.text


def test_private_alias_with_no_strict_fallback_raises(fresh_gateway):
    """If only OpenRouter is in the chain and privacy=strict, the alias has
    zero usable providers and must raise NoProviderAvailable — better to
    refuse than to leak to a multi-tenant aggregator."""
    # Replace BOTH primary and fallbacks with only-strict-incompatible providers,
    # AND mock the strict providers' dispatch to error, so the loop walks the
    # whole chain and the privacy filter blocks every entry.
    fresh_gateway._config["aliases"]["ai://private"]["primary"] = {
        "provider": "openrouter", "model": "x", "max_output_tokens": 100, "temperature": 0.3
    }
    fresh_gateway._config["aliases"]["ai://private"]["fallbacks"] = [
        {"provider": "openrouter", "model": "y", "max_output_tokens": 100, "temperature": 0.3}
    ]
    _set_dispatch(fresh_gateway, openrouter=_ok("leak"))  # must never be called
    with pytest.raises(NoProviderAvailable):
        asyncio.run(
            fresh_gateway.complete("ai://private", [{"role": "user", "content": "x"}])
        )


# -----------------------------------------------------------------------------
# 4. Budget enforcement
# -----------------------------------------------------------------------------


def test_budget_exceeded_raises_after_spending_cap(fresh_gateway):
    """If the alias's daily_budget_usd is $0.0001 and we record $0.0001, the next
    call must raise BudgetExceeded without hitting any provider."""
    # Force a tiny budget.
    fresh_gateway._config["aliases"]["ai://fast"]["daily_budget_usd"] = 0.0001
    _set_dispatch(fresh_gateway, minimax=_ok("first", pt=1000, ct=1000, model="MiniMax-M3"))
    # First call: 1000 * 0.000075 + 1000 * 0.0003 = $0.000375 — well over budget.
    asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    # Now the next call must be blocked.
    with pytest.raises(BudgetExceeded) as exc:
        asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    assert exc.value.alias == "ai://fast"


def test_budget_zero_means_unlimited(fresh_gateway):
    """A daily_budget_usd of 0 (or missing) means 'no cap'."""
    fresh_gateway._config["aliases"]["ai://fast"]["daily_budget_usd"] = 0
    _set_dispatch(fresh_gateway, minimax=_ok("ok", pt=1_000_000, ct=1_000_000))
    # Should not raise even with huge cost.
    r = asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    assert r.text == "ok"


def test_spent_today_isolated_per_alias(fresh_gateway):
    """Spending on ai://fast must NOT consume ai://reasoning's budget."""
    fresh_gateway._config["aliases"]["ai://fast"]["daily_budget_usd"] = 0.01
    _set_dispatch(fresh_gateway, minimax=_ok("ok", pt=1000, ct=1000, model="MiniMax-M3"))
    asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    # reasoning budget untouched
    assert fresh_gateway.spent_today("ai://reasoning") == 0.0


# -----------------------------------------------------------------------------
# 5. Structured log fields
# -----------------------------------------------------------------------------


def test_completion_result_has_all_observability_fields(fresh_gateway):
    _set_dispatch(fresh_gateway, minimax=_ok("hi", pt=12, ct=7, model="MiniMax-M3"))
    r = asyncio.run(
        fresh_gateway.complete(
            "ai://fast",
            [{"role": "user", "content": "x"}],
            tenant_id="11111111-1111-1111-1111-111111111111",
        )
    )
    # Every documented field is present and typed correctly.
    assert r.provider == "minimax"
    assert r.model == "MiniMax-M3"
    assert r.alias == "ai://fast"
    assert r.fallback_reason is None
    assert r.prompt_tokens == 12
    assert r.completion_tokens == 7
    assert r.cost_usd > 0.0  # we have cost data for MiniMax-M3
    assert r.latency_ms >= 0
    assert isinstance(r.text, str)


def test_drain_buffer_returns_one_row_per_successful_call(fresh_gateway):
    _set_dispatch(fresh_gateway, minimax=_ok("ok1"))
    asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "a"}]))
    asyncio.run(fresh_gateway.complete("ai://reasoning", [{"role": "user", "content": "b"}]))
    rows = fresh_gateway.drain_usage()
    assert len(rows) == 2
    aliases = sorted({r["alias"] for r in rows})
    assert aliases == ["ai://fast", "ai://reasoning"]
    for row in rows:
        assert {"alias", "provider", "model", "latency_ms", "cost_usd"} <= row.keys()


def test_drain_buffer_is_idempotent(fresh_gateway):
    _set_dispatch(fresh_gateway, minimax=_ok("ok"))
    asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    first = fresh_gateway.drain_usage()
    second = fresh_gateway.drain_usage()
    assert len(first) == 1
    assert len(second) == 0  # already drained


def test_fallback_records_fallback_reason_in_buffer(fresh_gateway):
    _set_dispatch(fresh_gateway, minimax=_err(429), openrouter=_ok("ok"))
    asyncio.run(fresh_gateway.complete("ai://fast", [{"role": "user", "content": "x"}]))
    rows = fresh_gateway.drain_usage()
    assert len(rows) == 1
    assert rows[0]["fallback_reason"] == "http_429"
    assert rows[0]["provider"] == "openrouter"


# -----------------------------------------------------------------------------
# 6. Config / unknown alias / NoProviderAvailable
# -----------------------------------------------------------------------------


def test_unknown_alias_raises_no_provider_available(fresh_gateway):
    with pytest.raises(NoProviderAvailable) as exc:
        asyncio.run(fresh_gateway.complete("ai://nope", [{"role": "user", "content": "x"}]))
    assert "ai://nope" in str(exc.value)


def test_empty_messages_raises_value_error(fresh_gateway):
    with pytest.raises(ValueError):
        asyncio.run(fresh_gateway.complete("ai://fast", []))


def test_list_aliases_returns_all_six(fresh_gateway):
    aliases = {a["alias"] for a in fresh_gateway.list_aliases()}
    # The four core aliases (fast/reasoning/extract/private) plus helpdesk + vision.
    assert aliases == {
        "ai://fast",
        "ai://reasoning",
        "ai://extract",
        "ai://private",
        "ai://helpdesk",
        "ai://vision",
    }


# -----------------------------------------------------------------------------
# 7. env-key reading
# -----------------------------------------------------------------------------


def test_read_env_keys_returns_first_set(monkeypatch):
    monkeypatch.setenv("MY_KEY_A", "value_a")
    monkeypatch.setenv("MY_KEY_B", "value_b")
    monkeypatch.delenv("MY_KEY_C", raising=False)
    out = _read_env_keys("MY_KEY_C|MY_KEY_A|MY_KEY_B")
    assert out == ["value_a", "value_b"]


def test_read_env_keys_handles_comma_separated(monkeypatch):
    monkeypatch.setenv("K1", "v1")
    monkeypatch.setenv("K2", "v2")
    out = _read_env_keys("K1,K2")
    assert out == ["v1", "v2"]


# -----------------------------------------------------------------------------
# 8. Migration file
# -----------------------------------------------------------------------------


def test_llm_usage_migration_exists():
    """The migration file for public.llm_usage must exist in migrations-py/."""
    p = ROOT / "migrations-py" / "add_llm_usage.sql"
    assert p.exists(), f"missing {p}"
    body = p.read_text(encoding="utf-8")
    assert "create table if not exists public.llm_usage" in body
    assert "alias" in body and "provider" in body and "cost_usd" in body


# -----------------------------------------------------------------------------
# 9. Real adapters (smoke test only — fail gracefully on missing key)
# -----------------------------------------------------------------------------


def test_gemini_adapter_raises_without_key(monkeypatch):
    """The real _call_gemini should raise ProviderError if no key is set."""
    for k in ("GEMINI_API_KEY", "GEMINI_API_KEYS", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ProviderError):
        _call_gemini("gemini-2.5-flash", [{"role": "user", "content": "x"}], {})


def test_openai_compatible_adapter_raises_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ProviderError):
        _call_openai_compatible("https://api.openai.com/v1", None, "gpt-4o-mini", [{"role": "user", "content": "x"}], {})


# -----------------------------------------------------------------------------
# 10. Cost estimation
# -----------------------------------------------------------------------------


def test_cost_estimation_uses_yaml_table(fresh_gateway):
    """The estimator must READ the table, not carry its own copy of the rates.

    This test used to hardcode $0.000075/$0.0003 for gemini-2.5-flash. That is
    the table duplicated into the test, so correcting the table broke the test
    — even though nothing about the estimator changed. (The old numbers were
    wrong as well: the published gemini-2.5-flash price is $0.30/$2.50 per 1M,
    not $0.075/$0.30.)

    Rates now come from _cost_per_1k, so this asserts the arithmetic and the
    lookup, which is what the name promises. A wrong VALUE in the YAML is a
    pricing question, checked where the rates are documented, not here.
    """
    model = "gemini-3.6-flash"
    in_rate, out_rate = fresh_gateway._cost_per_1k(model)
    assert in_rate > 0 and out_rate > 0, f"{model} missing from cost_per_1k"

    cost = fresh_gateway._estimate_cost(model, prompt_tokens=1000, completion_tokens=500)
    expected = (1000 / 1000.0) * in_rate + (500 / 1000.0) * out_rate
    assert abs(cost - expected) < 1e-9


def test_cost_estimation_returns_zero_for_unknown_model(fresh_gateway):
    cost = fresh_gateway._estimate_cost("no/such-model", 1000, 1000)
    assert cost == 0.0


# -----------------------------------------------------------------------------
# 11. Gemini is dead (2026-09-26) — regression guards
# -----------------------------------------------------------------------------


def test_no_standard_alias_depends_on_native_gemini(fresh_gateway):
    """Every Gemini key is revoked. A standard alias that lists native `gemini`
    costs a failing round-trip per call; one led by it is a silent outage.
    ai://private is the deliberate exception: it stays strict-only rather than
    falling back to a non-strict provider (MiniMax is not strict)."""
    for name, cfg in fresh_gateway._config["aliases"].items():
        chain = [cfg["primary"]] + list(cfg.get("fallbacks") or [])
        if cfg.get("privacy") == "strict":
            assert all(e["provider"] in g.STRICT_PRIVACY_PROVIDERS for e in chain), name
            continue
        assert cfg["primary"]["provider"] == "minimax", name
        assert not any(e["provider"] == "gemini" for e in chain), name


class _FakeResp:
    status_code = 200
    text = ""

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _fake_client(sent, data):
    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, headers=None):
            sent["payload"] = json
            return _FakeResp(data)

    return _Client


def test_openai_compatible_forwards_tools_and_strips_think(monkeypatch):
    """_call_openai_compatible used to DROP `tools`, so once Gemini died no
    provider in ai://reasoning could call a single tool. It must forward
    OpenAI-format tools, skip Gemini-shaped ones, and never leak <think>."""
    sent = {}
    monkeypatch.setattr(g.httpx, "Client", _fake_client(sent, {
        "choices": [{"message": {"content": "<think>plan</think>\nHi boss"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2},
    }))
    fn_tool = {"type": "function", "function": {"name": "book", "parameters": {"type": "object"}}}
    gemini_tool = {"function_declarations": [{"name": "old"}]}
    text, _raw, pt, ct, _model = _call_openai_compatible(
        "https://x/v1", "k", "MiniMax-M3", [{"role": "user", "content": "hi"}],
        {"tools": [fn_tool, gemini_tool]},
    )
    assert sent["payload"]["tools"] == [fn_tool]
    assert text == "Hi boss"
    assert (pt, ct) == (3, 2)


def test_openai_compatible_omits_tools_key_when_none(monkeypatch):
    sent = {}
    monkeypatch.setattr(g.httpx, "Client", _fake_client(sent, {
        "choices": [{"message": {"content": "ok"}}],
    }))
    _call_openai_compatible(
        "https://x/v1", "k", "m", [{"role": "user", "content": "hi"}], {"tools": None}
    )
    assert "tools" not in sent["payload"]


def test_sync_text_model_works_with_and_without_running_loop(monkeypatch):
    """SyncTextModel replaces genai.GenerativeModel for sync callers. It must
    work from plain sync code (TRACE agents in worker threads) AND from sync
    code called inside a running loop (owner commands in process_message),
    where a bare asyncio.run would raise."""
    calls = []

    class _FakeGW:
        async def complete(self, alias, messages, **opts):
            calls.append((alias, messages[0]["content"], opts))
            return SimpleNamespace(text="ok")

    monkeypatch.setattr(g, "llm", _FakeGW())
    model = g.SyncTextModel("ai://extract", max_output_tokens=7)
    assert model.generate_content("a").text == "ok"

    async def _inside_loop():
        return model.generate_content("b").text

    assert asyncio.run(_inside_loop()) == "ok"
    assert calls == [("ai://extract", "a", {"max_output_tokens": 7}),
                     ("ai://extract", "b", {"max_output_tokens": 7})]
