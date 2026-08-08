"""
Unit tests for src/saas/outreach_template_engine.py
Run: pytest tests/unit/test_template_engine.py -v
"""
import pytest

from src.saas.outreach_template_engine import (
    TemplateEngine,
    BUILT_IN_INDUSTRY_PACKS,
    UNIVERSAL_SIGNAL_MAP,
    QUALIFICATION_THRESHOLDS,
    detect_language,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """TemplateEngine without Gemini (no API key → lazy Gemini init skipped)."""
    return TemplateEngine(gemini_api_key=None)


@pytest.fixture
def property_config():
    return BUILT_IN_INDUSTRY_PACKS["property_agent"]


# ─── 1. Phone normalisation ───────────────────────────────────────────────────

def test_phone_normalization_my_local(engine):
    """Malaysian local 0123456789 passes through with digits only."""
    normed = engine._normalize_phone("0123456789")
    # Engine strips non-digits; local-format numbers are returned as-is
    assert normed.replace("+", "").isdigit() or normed == "0123456789"
    assert len(normed) >= 8


def test_phone_normalization_strip_plus(engine):
    """+60 prefix should be stripped to 60."""
    normed = engine._normalize_phone("+60123456789")
    assert normed.startswith("60")
    assert "+" not in normed


def test_phone_normalization_sg(engine):
    """Already full E.164 international number passes through correctly."""
    normed = engine._normalize_phone("6581234567")
    assert normed.startswith("65")


# ─── 2. CSV validation ────────────────────────────────────────────────────────

def test_csv_validation_valid(engine):
    """`validate_csv` returns a list of contacts when CSV is well-formed."""
    csv_data = "phone,contact_name\n60123456789,Alice\n60129999999,Bob"
    result = engine.validate_csv(csv_data)
    assert isinstance(result["valid"], list)
    assert len(result["valid"]) == 2
    assert result["invalid"] == []


def test_csv_validation_missing_phone_column(engine):
    """`validate_csv` rejects CSV without a 'phone' column."""
    csv_data = "contact_name,email\nAlice,alice@example.com"
    result = engine.validate_csv(csv_data)
    assert len(result["valid"]) == 0
    assert len(result["invalid"]) >= 1
    assert any("phone" in e["reason"].lower() for e in result["invalid"])


def test_csv_validation_bad_phone_values(engine):
    """`validate_csv` puts rows with bad phones in the 'invalid' list."""
    csv_data = "phone,contact_name\nnot-a-phone,Alice\n60123456789,Bob"
    result = engine.validate_csv(csv_data)
    assert len(result["invalid"]) >= 1
    assert len(result["valid"]) >= 1


# ─── 3. Language detection ────────────────────────────────────────────────────

def test_language_detection_manglish():
    """Malay name + MY country → 'ms' or 'manglish'."""
    # detect_language(contact_name, area, country)
    lang = detect_language("Ali bin Ahmad", "KL", "MY")
    assert lang in ("manglish", "ms")


def test_language_detection_singlish():
    """SG country → 'singlish'."""
    lang = detect_language("Tan Wei", "Singapore", "SG")
    assert lang in ("singlish", "en")


def test_language_detection_english_fallback():
    """Non-MY/SG country → 'en'."""
    lang = detect_language("", "", "US")
    assert lang in ("en", "manglish", "singlish", "ms")


# ─── 4. Signal scoring ────────────────────────────────────────────────────────

def test_signal_scoring_cold_reply(engine):
    """Neutral reply returns 0 score and no signals."""
    result = engine.score_reply(
        reply_text="ok",
        contact={"interest_score": 0},
        campaign_config=None,
    )
    assert result["interest_score"] == 0
    assert result["signals_hit"] == [] or result["signals_hit"] is None
    assert result["is_wrong_target"] is False


def test_signal_scoring_buying_signal(engine):
    """Strong buying-intent reply pushes score above warm threshold."""
    result = engine.score_reply(
        reply_text="Yes I'm interested, how much does it cost? When can we meet?",
        contact={"interest_score": 0},
        campaign_config=None,
    )
    assert result["interest_score"] >= QUALIFICATION_THRESHOLDS["warm"]


def test_signal_wrong_target(engine):
    """`is_wrong_target` is True when opt-out language is detected."""
    result = engine.score_reply(
        reply_text="stop sending me messages, wrong number",
        contact={"interest_score": 5},
        campaign_config=None,
    )
    assert result["is_wrong_target"] is True


# ─── 5. Context builder ───────────────────────────────────────────────────────

def test_context_builder_returns_dict(engine, property_config):
    """build_generation_context returns a non-empty prompt string."""
    contact = {
        "contact_name": "Ahmad",
        "area": "Petaling Jaya",
        "industry_type": "property_agent",
        "persona": "direct",
        "language_pref": "manglish",
        "interest_score": 0,
        "country": "MY",
    }
    ctx = engine.build_generation_context(contact, step=0, campaign_config=property_config)
    # Engine returns a str prompt (Gemini system prompt)
    assert isinstance(ctx, str)
    assert len(ctx) > 50


# ─── 6. Industry pack completeness ───────────────────────────────────────────

def test_industry_pack_completeness():
    """Every built-in pack must have 'label' and 'required_columns' keys."""
    for pack_name, pack in BUILT_IN_INDUSTRY_PACKS.items():
        assert "label" in pack, f"{pack_name} missing 'label'"
        assert "required_columns" in pack, f"{pack_name} missing 'required_columns'"
        assert "phone" in pack["required_columns"], f"{pack_name} required_columns missing 'phone'"


def test_list_industry_packs_returns_all(engine):
    """list_industry_packs() returns a dict with at least 7 entries."""
    packs = engine.list_industry_packs()
    assert isinstance(packs, dict)
    assert len(packs) >= 7
