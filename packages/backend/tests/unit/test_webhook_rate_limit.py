"""Backpressure on the bridge -> backend webhooks (CVE-2026-003).

The gap
-------
`/webhook/message` and `/webhook/connection` authenticate the caller but had no
rate limit of any kind. The only middleware on the app is CORS and a no-cache
header pass, and the per-chat limiter in `process_message` runs INSIDE the
background task — after the 200 has already been returned. So an authenticated
flood was accepted at 100% and queued unbounded background work.

tests/security/test_call_security.py has asserted this since February and
failed. It was left failing on purpose rather than retargeted at something that
happened to pass; this module is the unit-level cover for the fix.

Why two buckets
---------------
A purely per-device limit is defeated by varying the device id, which costs an
attacker nothing — the CVE test does exactly that, 100 requests with 100
distinct ids. So the global ceiling is the one that actually stops a flood, and
the per-device bucket exists for the different failure of ONE runaway tenant
eating everyone else's allowance.

These tests drive the bucket directly rather than through HTTP, so they assert
on the algorithm and not on how fast the machine happens to be.
"""

import pytest

from src.core import bijou
from src.core.bijou import (
    _bucket_setting,
    _check_webhook_rate_limit,
    _reset_webhook_rate_limits,
    _webhook_take_token,
)
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def clean_buckets():
    _reset_webhook_rate_limits()
    yield
    _reset_webhook_rate_limits()


class TestTokenBucket:
    def test_burst_up_to_capacity_is_allowed(self):
        """The capacity exists to absorb a bridge reconnect replaying its
        queue. Legitimate bursts must not be shed."""
        allowed = sum(_webhook_take_token("k", capacity=10, refill_per_sec=0) for _ in range(10))
        assert allowed == 10

    def test_the_request_after_capacity_is_refused(self):
        for _ in range(10):
            _webhook_take_token("k", capacity=10, refill_per_sec=0)
        assert _webhook_take_token("k", capacity=10, refill_per_sec=0) is False

    def test_refill_restores_capacity(self, monkeypatch):
        """Driven off a fake clock — asserting on real elapsed time is flaky."""
        now = [1000.0]
        monkeypatch.setattr(bijou.time, "monotonic", lambda: now[0])

        for _ in range(5):
            assert _webhook_take_token("k", capacity=5, refill_per_sec=10) is True
        assert _webhook_take_token("k", capacity=5, refill_per_sec=10) is False

        now[0] += 0.2          # 0.2s * 10/s = 2 tokens
        assert _webhook_take_token("k", capacity=5, refill_per_sec=10) is True
        assert _webhook_take_token("k", capacity=5, refill_per_sec=10) is True
        assert _webhook_take_token("k", capacity=5, refill_per_sec=10) is False

    def test_refill_never_exceeds_capacity(self, monkeypatch):
        """Otherwise a long quiet period banks an unlimited burst, and the
        limiter stops limiting exactly when traffic resumes."""
        now = [1000.0]
        monkeypatch.setattr(bijou.time, "monotonic", lambda: now[0])

        _webhook_take_token("k", capacity=3, refill_per_sec=10)
        now[0] += 3600
        allowed = sum(_webhook_take_token("k", capacity=3, refill_per_sec=10) for _ in range(20))
        assert allowed == 3

    def test_keys_are_independent(self):
        for _ in range(5):
            _webhook_take_token("a", capacity=5, refill_per_sec=0)
        assert _webhook_take_token("a", capacity=5, refill_per_sec=0) is False
        assert _webhook_take_token("b", capacity=5, refill_per_sec=0) is True

    def test_zero_capacity_disables_the_limiter(self):
        """The documented opt-out for a deployment that outgrows the default.
        It must be a true bypass, not a bucket of size zero that refuses
        everything."""
        assert all(_webhook_take_token("k", capacity=0, refill_per_sec=0) for _ in range(100))


class TestTheLimiterDoesNotLeak:
    def test_bucket_table_is_bounded(self, monkeypatch):
        """An unbounded dict keyed by attacker-controlled device ids would
        recreate the very memory exhaustion this code exists to prevent."""
        monkeypatch.setattr(bijou, "_WEBHOOK_BUCKET_MAX_KEYS", 50)
        now = [1000.0]
        monkeypatch.setattr(bijou.time, "monotonic", lambda: now[0])

        for i in range(50):
            _webhook_take_token(f"device::{i}", capacity=5, refill_per_sec=1)

        now[0] += 400  # every existing bucket is now idle past the 300s cutoff
        _webhook_take_token("device::fresh", capacity=5, refill_per_sec=1)

        assert len(bijou._WEBHOOK_BUCKETS) <= 50

    def test_saturation_sheds_load_rather_than_growing(self, monkeypatch):
        """When nothing is evictable the answer is 429, never 'grow anyway'."""
        monkeypatch.setattr(bijou, "_WEBHOOK_BUCKET_MAX_KEYS", 10)
        now = [1000.0]
        monkeypatch.setattr(bijou.time, "monotonic", lambda: now[0])

        for i in range(10):
            _webhook_take_token(f"device::{i}", capacity=5, refill_per_sec=1)

        # No time passes, so no bucket is idle enough to evict.
        assert _webhook_take_token("device::new", capacity=5, refill_per_sec=1) is False
        assert len(bijou._WEBHOOK_BUCKETS) == 10


class TestHttpBehaviour:
    def test_over_limit_raises_429_with_retry_after(self, monkeypatch):
        """429 + Retry-After, not a silent drop: a well-behaved caller
        redelivers instead of losing a customer's WhatsApp message."""
        monkeypatch.setenv("WEBHOOK_RATE_CAPACITY", "2")
        monkeypatch.setenv("WEBHOOK_RATE_REFILL_PER_SEC", "0")

        _check_webhook_rate_limit("global")
        _check_webhook_rate_limit("global")

        with pytest.raises(HTTPException) as exc:
            _check_webhook_rate_limit("global")

        assert exc.value.status_code == 429
        assert exc.value.headers.get("Retry-After") == "1"

    def test_global_and_device_budgets_are_separate(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_RATE_CAPACITY", "1")
        monkeypatch.setenv("WEBHOOK_RATE_REFILL_PER_SEC", "0")
        monkeypatch.setenv("WEBHOOK_DEVICE_RATE_CAPACITY", "5")
        monkeypatch.setenv("WEBHOOK_DEVICE_REFILL_PER_SEC", "0")

        _check_webhook_rate_limit("global")
        with pytest.raises(HTTPException):
            _check_webhook_rate_limit("global")

        # The device budget is untouched by the global one being spent.
        _check_webhook_rate_limit("device", "dev-1")

    def test_one_noisy_device_does_not_spend_another_devices_budget(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_DEVICE_RATE_CAPACITY", "2")
        monkeypatch.setenv("WEBHOOK_DEVICE_REFILL_PER_SEC", "0")

        _check_webhook_rate_limit("device", "noisy")
        _check_webhook_rate_limit("device", "noisy")
        with pytest.raises(HTTPException):
            _check_webhook_rate_limit("device", "noisy")

        _check_webhook_rate_limit("device", "quiet")  # must not raise


class TestConfiguration:
    def test_default_is_used_when_unset(self, monkeypatch):
        monkeypatch.delenv("WEBHOOK_RATE_CAPACITY", raising=False)
        assert _bucket_setting("WEBHOOK_RATE_CAPACITY", 60.0) == 60.0

    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_RATE_CAPACITY", "5")
        assert _bucket_setting("WEBHOOK_RATE_CAPACITY", 60.0) == 5.0

    def test_garbage_falls_back_to_the_default_rather_than_crashing(self, monkeypatch):
        """A typo in a compose file must not take inbound WhatsApp down, and
        must not silently disable the limiter either."""
        monkeypatch.setenv("WEBHOOK_RATE_CAPACITY", "not-a-number")
        assert _bucket_setting("WEBHOOK_RATE_CAPACITY", 60.0) == 60.0

    def test_empty_string_is_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_RATE_CAPACITY", "")
        assert _bucket_setting("WEBHOOK_RATE_CAPACITY", 60.0) == 60.0
