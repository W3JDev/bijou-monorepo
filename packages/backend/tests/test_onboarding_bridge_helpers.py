"""Unit tests for the onboarding bridge helpers (WhatsApp reconnect fix, 2026-07-24).

These pin the two root-cause fixes:
- get_whatsapp_bridge_url() must fall back to BRIDGE_URL (the var the rest of the
  app + deployment uses); reading only WHATSAPP_BRIDGE_URL broke the QR endpoint.
- get_bridge_auth_headers() must authenticate to the (auth-gated) bridge; missing
  auth made /qr return 401 -> broken image.

Pure functions, no network/DB — safe to run anywhere.
"""
import base64
import importlib

import pytest

m = importlib.import_module("src.saas.onboarding_api")

BRIDGE_ENV = ["WHATSAPP_BRIDGE_URL", "BRIDGE_URL", "BRIDGE_API_KEY", "BRIDGE_USER", "BRIDGE_PASSWORD"]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in BRIDGE_ENV:
        monkeypatch.delenv(k, raising=False)


def test_url_falls_back_to_bridge_url(monkeypatch):
    # staging reality: only BRIDGE_URL is set
    monkeypatch.setenv("BRIDGE_URL", "https://bijou-bridge-staging-v2.fly.dev/")
    assert m.get_whatsapp_bridge_url() == "https://bijou-bridge-staging-v2.fly.dev"


def test_url_prefers_whatsapp_bridge_url(monkeypatch):
    monkeypatch.setenv("BRIDGE_URL", "https://fallback.example.com")
    monkeypatch.setenv("WHATSAPP_BRIDGE_URL", "https://primary.example.com")
    assert m.get_whatsapp_bridge_url() == "https://primary.example.com"


def test_url_raises_when_unset():
    with pytest.raises(RuntimeError):
        m.get_whatsapp_bridge_url()


def test_auth_basic_from_api_key_user_pass(monkeypatch):
    monkeypatch.setenv("BRIDGE_API_KEY", "bijou:secretpw")
    expected = "Basic " + base64.b64encode(b"bijou:secretpw").decode()
    assert m.get_bridge_auth_headers() == {"Authorization": expected}


def test_auth_basic_from_user_password(monkeypatch):
    monkeypatch.setenv("BRIDGE_USER", "u")
    monkeypatch.setenv("BRIDGE_PASSWORD", "p")
    expected = "Basic " + base64.b64encode(b"u:p").decode()
    assert m.get_bridge_auth_headers() == {"Authorization": expected}


def test_auth_plain_api_key_is_x_api_key(monkeypatch):
    monkeypatch.setenv("BRIDGE_API_KEY", "plainkey")
    assert m.get_bridge_auth_headers() == {"X-API-Key": "plainkey"}


def test_auth_empty_when_unconfigured():
    # No creds -> empty dict, not a crash (endpoint still returns bridge's own error)
    assert m.get_bridge_auth_headers() == {}
