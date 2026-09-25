"""Job 4 — agent output style (default tone + per-tenant override).

Covers _build_tone_instruction in src/core/bijou.py. See DIAGNOSIS-AUTH.md §4
and FIXES-AUTH.md. Pure function, so no app boot / Supabase mock needed.
"""
from src.core.bijou import _build_tone_instruction, DEFAULT_AGENT_TONE


def test_default_tone_applied_when_no_config():
    out = _build_tone_instruction(None)
    assert "## Response Tone" in out
    assert DEFAULT_AGENT_TONE in out


def test_default_tone_when_config_lacks_tone():
    out = _build_tone_instruction({"business_name": "Kedai Kopi"})
    assert DEFAULT_AGENT_TONE in out


def test_per_tenant_override_replaces_default():
    out = _build_tone_instruction({"tone": "formal"})
    assert "formal" in out
    # the default label must not leak when a tenant overrides it
    assert DEFAULT_AGENT_TONE not in out


def test_known_tone_gets_specific_guidance():
    out = _build_tone_instruction({"tone": "casual"})
    assert "texting a friend" in out


def test_unknown_tone_still_injected_generically():
    out = _build_tone_instruction({"tone": "pirate"})
    assert "pirate" in out
    assert "Adopt a pirate tone" in out


def test_blank_tone_falls_back_to_default():
    out = _build_tone_instruction({"tone": "   "})
    assert DEFAULT_AGENT_TONE in out


def test_tone_never_claims_to_override_safety():
    out = _build_tone_instruction({"tone": "casual"})
    assert "never overrides factual accuracy" in out
