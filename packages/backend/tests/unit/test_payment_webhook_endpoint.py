import pytest
import sys
import types
from fastapi import FastAPI
from fastapi.testclient import TestClient

if "supabase" not in sys.modules:
    supabase_stub = types.ModuleType("supabase")
    setattr(supabase_stub, "create_client", lambda *args, **kwargs: None)
    setattr(supabase_stub, "Client", object)          # needed by dashboard_api_simple
    sys.modules["supabase"] = supabase_stub

from src.saas import payment_api


class _FakeStripeService:
    def __init__(self, event=None, process_raises=False):
        self._event = event
        self.process_raises = process_raises
        self.process_called = False

    def verify_webhook_event(self, payload: bytes, sig_header: str):
        return self._event

    def process_webhook_event(self, event):
        self.process_called = True
        if self.process_raises:
            raise RuntimeError("background failure")
        return True


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(payment_api.router)
    return app


def test_webhook_missing_signature_returns_400(app, monkeypatch):
    fake = _FakeStripeService(event={"id": "evt_1", "type": "checkout.session.completed"})
    monkeypatch.setattr(payment_api, "get_stripe_service", lambda: fake)

    with TestClient(app) as client:
        response = client.post("/api/payment/webhook", content=b"{}")

    assert response.status_code == 400
    assert response.json()["success"] is False


def test_webhook_invalid_signature_returns_400(app, monkeypatch):
    fake = _FakeStripeService(event=None)
    monkeypatch.setattr(payment_api, "get_stripe_service", lambda: fake)

    with TestClient(app) as client:
        response = client.post(
            "/api/payment/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "invalid-signature"},
        )

    assert response.status_code == 400
    assert response.json()["success"] is False


def test_webhook_valid_signature_returns_200_and_processes(app, monkeypatch):
    fake = _FakeStripeService(event={"id": "evt_123", "type": "checkout.session.completed"})
    monkeypatch.setattr(payment_api, "get_stripe_service", lambda: fake)

    with TestClient(app) as client:
        response = client.post(
            "/api/payment/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "t=1,v1=valid"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["received"] is True
    assert response.json()["event_id"] == "evt_123"
    assert fake.process_called is True


def test_webhook_background_failure_still_returns_200(app, monkeypatch):
    fake = _FakeStripeService(
        event={"id": "evt_bg", "type": "checkout.session.completed"},
        process_raises=True,
    )
    monkeypatch.setattr(payment_api, "get_stripe_service", lambda: fake)

    with TestClient(app) as client:
        response = client.post(
            "/api/payment/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "t=1,v1=valid"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# Yearly checkout routing tests (closes coverage gap noted 2026-08-09)
# Verifies that the right Stripe Price ID is selected based on billing_interval.
# ---------------------------------------------------------------------------

# A known sentinel — set STRIPE_PRICE_PRO_YEARLY to a value that will be
# different from STRIPE_PRICE_PRO_MONTHLY so we can prove the right one is picked.
_MONTHLY_PRICE = "price_test_PRO_MONTHLY_111"
_YEARLY_PRICE = "price_test_PRO_YEARLY_222"


def _make_fake_stripe(monkeypatch, captured: dict):
    """Mock stripe module so checkout.Session.create records its kwargs."""
    class _FakeCheckoutSession:
        @staticmethod
        def create(**kwargs):
            captured["kwargs"] = kwargs
            # Return an object with .url and .id attributes (Stripe API shape)
            return types.SimpleNamespace(
                id="cs_test_123",
                url="https://stripe.test/cs_test_123",
            )

    class _FakeCheckout:
        Session = _FakeCheckoutSession

    class _FakeStripe:
        api_key = None
        checkout = _FakeCheckout
        error = types.SimpleNamespace(StripeError=type("StripeError", (Exception,), {}))

    fake_stripe = _FakeStripe()
    monkeypatch.setattr(payment_api, "_get_stripe", lambda: fake_stripe)
    return fake_stripe


def _make_fake_supabase(monkeypatch, tenant_row: dict):
    """Mock supabase.create_client so the tenant lookup returns the given row."""
    class _Query:
        def __init__(self, row):
            self.row = row

        def eq(self, *_args, **_kwargs):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            return types.SimpleNamespace(data=self.row)

    class _Table:
        def __init__(self, row):
            self.row = row

        def select(self, *_args, **_kwargs):
            return _Query(self.row)

        def update(self, *_args, **_kwargs):
            return _Query(self.row)

    class _FakeSupabase:
        def table(self, _name):
            return _Table(tenant_row)

    # NOTE: payment_api.py does `from supabase import create_client` INSIDE the
    # create_checkout_session function, not at module level. So we patch the
    # function in the supabase package directly, not on payment_api.
    monkeypatch.setattr("supabase.create_client", lambda *a, **kw: _FakeSupabase())
    return _FakeSupabase()


def test_checkout_yearly_selects_yearly_price_id(app, monkeypatch):
    """POST /api/payment/checkout with billing_interval='year' must use STRIPE_PRICE_PRO_YEARLY."""
    import os
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", _MONTHLY_PRICE)
    monkeypatch.setenv("STRIPE_PRICE_PRO_YEARLY", _YEARLY_PRICE)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")

    captured = {}
    _make_fake_stripe(monkeypatch, captured)
    # Override the verify_session FastAPI dependency (not module-level monkeypatch
    # — Depends() captures the function ref at route definition time)
    from src.core.dashboard_api_simple import verify_session
    app.dependency_overrides[verify_session] = lambda: {
        "id": "tenant_test", "owner_email": "t@test.com"
    }

    tenant_row = {
        "id": "tenant_test",
        "owner_email": "t@test.com",
        "stripe_customer_id": None,
    }
    _make_fake_supabase(monkeypatch, tenant_row)

    with TestClient(app) as client:
        response = client.post(
            "/api/payment/checkout",
            json={"plan": "pro", "billing_interval": "year"},
        )

    assert response.status_code == 200, response.text
    assert captured["kwargs"]["line_items"][0]["price"] == _YEARLY_PRICE, (
        f"yearly checkout should use STRIPE_PRICE_PRO_YEARLY ({_YEARLY_PRICE}), "
        f"got {captured['kwargs']['line_items'][0]['price']}"
    )


def test_checkout_monthly_selects_monthly_price_id(app, monkeypatch):
    """POST /api/payment/checkout with billing_interval='month' must use STRIPE_PRICE_PRO_MONTHLY."""
    import os
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", _MONTHLY_PRICE)
    monkeypatch.setenv("STRIPE_PRICE_PRO_YEARLY", _YEARLY_PRICE)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")

    captured = {}
    _make_fake_stripe(monkeypatch, captured)
    from src.core.dashboard_api_simple import verify_session
    app.dependency_overrides[verify_session] = lambda: {
        "id": "tenant_test", "owner_email": "t@test.com"
    }

    tenant_row = {
        "id": "tenant_test",
        "owner_email": "t@test.com",
        "stripe_customer_id": None,
    }
    _make_fake_supabase(monkeypatch, tenant_row)

    with TestClient(app) as client:
        response = client.post(
            "/api/payment/checkout",
            json={"plan": "pro", "billing_interval": "month"},
        )

    assert response.status_code == 200, response.text
    assert captured["kwargs"]["line_items"][0]["price"] == _MONTHLY_PRICE, (
        f"monthly checkout should use STRIPE_PRICE_PRO_MONTHLY ({_MONTHLY_PRICE}), "
        f"got {captured['kwargs']['line_items'][0]['price']}"
    )
