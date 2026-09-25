"""
Per-tenant daily budget enforcement in the LLM gateway.

The gateway historically enforced ONE daily USD cap per alias, shared by every
tenant. A single runaway tenant could therefore exhaust ai://fast's $25/day and
take AI away from every other customer — a noisy-neighbour outage in a
multi-tenant product.

These tests pin the two-cap behaviour:
  - the platform (per-alias) cap still bounds total spend
  - a per-tenant cap stops one tenant eating the whole platform cap
  - BudgetExceeded says WHICH cap was hit, because that is a different
    operational event for whoever is on call
  - callers with no tenant_id (cron, backfills, health probes) are exempt from
    the per-tenant cap but still counted against the platform cap
"""
import asyncio
import sys
import threading
from pathlib import Path

import pytest

# Make src.* importable when pytest is run from any cwd.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from src.core import llm_gateway_v2 as g  # noqa: E402
from src.core.llm_gateway_v2 import (  # noqa: E402
    BudgetExceeded,
    LLMGateway,
    ProviderError,
    _UsageTracker,
)

# These tests exercise ai://fast, and the gateway prices a call using the model
# that alias RESOLVES to — not whatever a fake dispatch claims to have used. So
# both the model name and its price are read from the loaded config.
#
# Two earlier versions of this got it wrong, in the same way each time:
#   1. a hardcoded 0.000375, copied from the gemini-2.5-flash rates
#   2. a hardcoded model name whose price no longer matched the alias, once
#      ai://fast moved to flash-lite — the expected 0.0045 against an actual
#      0.0028
# Both are the same mistake: duplicating a fact the gateway already owns. A
# routing change is not a behaviour change, and these tests are about CAPS.
ALIAS_UNDER_TEST = "ai://fast"


def _fake_model_and_cost():
    """Return (provider, model, cost of one 1000-in/1000-out call) for the alias
    tested. The provider is read too: it moved gemini -> minimax on 2026-09-26
    and a hardcoded "gemini" key sent every call to the real network."""
    gateway = LLMGateway()
    primary = gateway._config["aliases"][ALIAS_UNDER_TEST]["primary"]
    model = primary["model"]
    in_rate, out_rate = gateway._cost_per_1k(model)
    assert in_rate > 0 and out_rate > 0, (
        f"{model} (the model {ALIAS_UNDER_TEST} resolves to) is missing from "
        "cost_per_1k in llm_gateway.yaml — without a price every call costs "
        "0.0 and these cap tests would pass while testing nothing"
    )
    return primary["provider"], model, in_rate + out_rate  # 1000 tokens each way


FAKE_PROVIDER, FAKE_MODEL, COST_PER_FAKE_CALL = _fake_model_and_cost()


def _ok(text="hello", pt=1000, ct=1000, model=FAKE_MODEL):
    payload = (text, {"fake": True}, pt, ct, model)

    def fake(model, messages, opts):
        return payload

    return fake


@pytest.fixture
def gw():
    """Gateway loaded from the real YAML, with a fully faked dispatch."""
    gateway = LLMGateway.__new__(LLMGateway)  # skip __init__ to avoid file IO
    gateway._config_path = g._CONFIG_PATH
    gateway._lock = threading.Lock()
    gateway.reload()
    gateway._usage = _UsageTracker()
    gateway._dispatch_override = {FAKE_PROVIDER: _ok()}
    return gateway


def _call(gateway, alias="ai://fast", tenant_id=None):
    return asyncio.run(
        gateway.complete(alias, [{"role": "user", "content": "x"}], tenant_id=tenant_id)
    )


# -----------------------------------------------------------------------------
# 1. The noisy-neighbour fix
# -----------------------------------------------------------------------------


def test_tenant_over_its_own_cap_is_blocked(gw):
    gw._config["aliases"]["ai://fast"]["daily_budget_usd"] = 25.0
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0.0001

    _call(gw, tenant_id="tenant-a")  # spends more than the tiny per-tenant cap
    with pytest.raises(BudgetExceeded) as exc:
        _call(gw, tenant_id="tenant-a")

    assert exc.value.scope == "tenant"
    assert exc.value.tenant_id == "tenant-a"
    assert exc.value.alias == "ai://fast"


def test_one_tenant_burning_its_cap_does_not_block_another_tenant(gw):
    """The whole point: tenant A's runaway loop must not take tenant B down."""
    gw._config["aliases"]["ai://fast"]["daily_budget_usd"] = 25.0
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0.0001

    _call(gw, tenant_id="tenant-a")
    with pytest.raises(BudgetExceeded):
        _call(gw, tenant_id="tenant-a")

    r = _call(gw, tenant_id="tenant-b")
    assert r.text == "hello"


def test_platform_cap_still_applies_across_tenants(gw):
    """Per-tenant caps are additional, not a replacement — total spend is still
    bounded, even when every tenant is individually under its own cap."""
    gw._config["aliases"]["ai://fast"]["daily_budget_usd"] = COST_PER_FAKE_CALL * 1.5
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 100.0

    _call(gw, tenant_id="tenant-a")
    _call(gw, tenant_id="tenant-b")  # platform total now over the platform cap

    with pytest.raises(BudgetExceeded) as exc:
        _call(gw, tenant_id="tenant-c")
    assert exc.value.scope == "alias"
    assert exc.value.tenant_id is None


def test_tenant_spend_is_isolated_between_tenants(gw):
    gw._config["aliases"]["ai://fast"]["daily_budget_usd"] = 0
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0

    _call(gw, tenant_id="tenant-a")
    assert gw.spent_today_tenant("ai://fast", "tenant-a") == pytest.approx(
        COST_PER_FAKE_CALL
    )
    assert gw.spent_today_tenant("ai://fast", "tenant-b") == 0.0


def test_tenant_spend_is_isolated_between_aliases(gw):
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0
    _call(gw, alias="ai://fast", tenant_id="tenant-a")
    assert gw.spent_today_tenant("ai://reasoning", "tenant-a") == 0.0


# -----------------------------------------------------------------------------
# 2. Calls with no tenant_id
# -----------------------------------------------------------------------------


def test_calls_without_tenant_id_are_exempt_from_the_per_tenant_cap(gw):
    """Cron jobs, backfills and health probes carry no tenant. They must not
    crash, and must not all be squeezed into one shared tenant bucket."""
    gw._config["aliases"]["ai://fast"]["daily_budget_usd"] = 0
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0.0001

    for _ in range(3):
        assert _call(gw, tenant_id=None).text == "hello"


def test_calls_without_tenant_id_still_count_against_the_platform_cap(gw):
    gw._config["aliases"]["ai://fast"]["daily_budget_usd"] = COST_PER_FAKE_CALL * 0.5
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0

    _call(gw, tenant_id=None)
    with pytest.raises(BudgetExceeded) as exc:
        _call(gw, tenant_id=None)
    assert exc.value.scope == "alias"


# -----------------------------------------------------------------------------
# 3. Config resolution — the point of the YAML is behaviour without code changes
# -----------------------------------------------------------------------------


def test_missing_per_tenant_cap_is_derived_from_the_platform_cap(gw):
    """An alias that declares no per-tenant cap is NOT unlimited — it gets a
    fraction of the platform cap, so a new alias is protected by default."""
    cfg = gw._config["aliases"]["ai://fast"]
    cfg.pop("per_tenant_daily_budget_usd", None)
    cfg["daily_budget_usd"] = COST_PER_FAKE_CALL * 10
    # 0.55 puts the derived cap between 5 and 6 calls, so the assertion below
    # does not sit on an exact float boundary.
    gw._config["budget_defaults"] = {"per_tenant_fraction": 0.55}

    # Derived per-tenant cap = 5.5 calls' worth; platform cap = 10 calls' worth.
    # Like the platform cap, this is checked before the call, so the 6th call
    # still goes through (spend was under the cap when it started) and the 7th
    # is the one refused.
    for _ in range(6):
        _call(gw, tenant_id="tenant-a")
    with pytest.raises(BudgetExceeded) as exc:
        _call(gw, tenant_id="tenant-a")
    assert exc.value.scope == "tenant"
    assert exc.value.cap == pytest.approx(COST_PER_FAKE_CALL * 10 * 0.55)


def test_derivation_falls_back_to_the_module_default_fraction(gw):
    cfg = gw._config["aliases"]["ai://fast"]
    cfg.pop("per_tenant_daily_budget_usd", None)
    cfg["daily_budget_usd"] = 10.0
    gw._config.pop("budget_defaults", None)

    assert gw.per_tenant_budget("ai://fast") == pytest.approx(
        10.0 * g.DEFAULT_PER_TENANT_BUDGET_FRACTION
    )


def test_explicit_zero_per_tenant_cap_means_unlimited(gw):
    """0 is the documented opt-out, distinct from 'absent' which derives."""
    gw._config["aliases"]["ai://fast"]["daily_budget_usd"] = 0
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0
    for _ in range(4):
        _call(gw, tenant_id="tenant-a")
    assert gw.spent_today_tenant("ai://fast", "tenant-a") > 0


def test_unlimited_platform_cap_derives_an_unlimited_per_tenant_cap(gw):
    """Nothing sensible is a fraction of 'unlimited'; the operator must set the
    per-tenant cap explicitly in that case."""
    cfg = gw._config["aliases"]["ai://fast"]
    cfg.pop("per_tenant_daily_budget_usd", None)
    cfg["daily_budget_usd"] = 0
    assert gw.per_tenant_budget("ai://fast") == 0.0


def test_shipped_yaml_declares_a_per_tenant_cap_below_the_platform_cap():
    """Guards the real config file, not a fixture: every shipped alias must have
    a per-tenant cap that is strictly smaller than the platform cap, otherwise
    the noisy-neighbour guard is decorative."""
    with open(g._CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for alias, spec in (cfg.get("aliases") or {}).items():
        platform = float(spec.get("daily_budget_usd", 0) or 0)
        per_tenant = spec.get("per_tenant_daily_budget_usd")
        assert per_tenant is not None, f"{alias} has no per_tenant_daily_budget_usd"
        assert 0 < float(per_tenant) < platform, (
            f"{alias}: per-tenant ${per_tenant} must be >0 and < platform ${platform}"
        )


# -----------------------------------------------------------------------------
# 4. What the on-call engineer reads
# -----------------------------------------------------------------------------


def test_tenant_cap_message_names_the_tenant_and_the_cap(gw):
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0.0001
    _call(gw, tenant_id="tenant-a")
    with pytest.raises(BudgetExceeded) as exc:
        _call(gw, tenant_id="tenant-a")
    msg = str(exc.value)
    assert "tenant-a" in msg
    assert "ai://fast" in msg
    assert "tenant" in msg.lower()
    # A tenant-scoped cap must not read like a platform outage.
    assert not msg.lower().startswith("platform")


def test_platform_cap_message_says_it_is_platform_wide(gw):
    gw._config["aliases"]["ai://fast"]["daily_budget_usd"] = 0.0001
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 100.0
    _call(gw, tenant_id="tenant-a")
    with pytest.raises(BudgetExceeded) as exc:
        _call(gw, tenant_id="tenant-b")
    assert "platform" in str(exc.value).lower()
    assert "ai://fast" in str(exc.value)


def test_list_aliases_exposes_the_per_tenant_cap(gw):
    rows = {r["alias"]: r for r in gw.list_aliases()}
    assert rows["ai://fast"]["per_tenant_daily_budget_usd"] > 0


# -----------------------------------------------------------------------------
# 5. Tracker-level behaviour
# -----------------------------------------------------------------------------


def test_usage_tracker_records_tenant_spend_separately():
    t = _UsageTracker()
    t.record(alias="ai://fast", cost_usd=1.0, provider="p", model="m", latency_ms=1,
             tenant_id="a")
    t.record(alias="ai://fast", cost_usd=2.0, provider="p", model="m", latency_ms=1,
             tenant_id="b")
    assert t.spent_today("ai://fast") == pytest.approx(3.0)
    assert t.spent_today_tenant("ai://fast", "a") == pytest.approx(1.0)
    assert t.spent_today_tenant("ai://fast", "b") == pytest.approx(2.0)
    assert t.spent_today_tenant("ai://fast", None) == 0.0


def test_usage_tracker_resets_tenant_spend_on_a_new_day(monkeypatch):
    t = _UsageTracker()
    monkeypatch.setattr(_UsageTracker, "_today", staticmethod(lambda: "2026-09-05"))
    t.record(alias="ai://fast", cost_usd=1.0, provider="p", model="m", latency_ms=1,
             tenant_id="a")
    assert t.spent_today_tenant("ai://fast", "a") == pytest.approx(1.0)

    monkeypatch.setattr(_UsageTracker, "_today", staticmethod(lambda: "2026-09-06"))
    assert t.spent_today_tenant("ai://fast", "a") == 0.0
    t.record(alias="ai://fast", cost_usd=0.5, provider="p", model="m", latency_ms=1,
             tenant_id="a")
    assert t.spent_today_tenant("ai://fast", "a") == pytest.approx(0.5)


def test_failed_calls_do_not_consume_a_tenants_budget(gw):
    """A provider error costs nothing, so it must not eat the tenant's cap."""
    gw._config["aliases"]["ai://fast"]["per_tenant_daily_budget_usd"] = 0.0001

    def boom(model, messages, opts):
        raise ProviderError("rate limited", status_code=429)

    gw._dispatch_override = {name: boom for name in gw._config["providers"]}
    with pytest.raises(ProviderError):
        _call(gw, tenant_id="tenant-a")

    gw._dispatch_override = {FAKE_PROVIDER: _ok()}
    assert _call(gw, tenant_id="tenant-a").text == "hello"
