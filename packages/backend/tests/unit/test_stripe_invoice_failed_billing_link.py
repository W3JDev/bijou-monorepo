"""A failed-invoice email must send existing customers to fix billing, not
to the new-tenant signup form.

The bug
-------
`_handle_invoice_failed` linked its "update payment" email to
`static/onboarding.html` — the new-BUSINESS signup form. Two problems
stacked: (1) an existing tenant with a billing problem who clicked through
would submit `/api/onboarding/v2/signup` and create a SECOND, duplicate
tenant rather than fix their subscription; (2) onboarding.html's WhatsApp
step is separately broken (see test_onboarding_v2_auth.py /
onboarding_complete.py::require_signup_token) — a dead end regardless.

The fix uses the Stripe Customer Portal (`create_portal_session`, already
used elsewhere in this file for the dashboard's "Manage billing" button) —
a hosted Stripe page where the customer can actually update their card —
falling back to the dashboard's billing tab only if creating that portal
session itself fails.
"""

import sys
import types
from unittest.mock import MagicMock

if "supabase" not in sys.modules:
    supabase_stub = types.ModuleType("supabase")
    setattr(supabase_stub, "create_client", lambda *args, **kwargs: None)
    setattr(supabase_stub, "Client", object)
    sys.modules["supabase"] = supabase_stub

if "stripe" not in sys.modules:
    stripe_stub = types.ModuleType("stripe")
    stripe_stub.api_key = None
    stripe_stub.billing_portal = types.SimpleNamespace(Session=types.SimpleNamespace(create=lambda **k: None))
    sys.modules["stripe"] = stripe_stub

from src.saas.stripe_service import StripePaymentService  # noqa: E402


def _make_service(portal_result):
    """Build a StripePaymentService without running __init__ (which needs
    real Supabase/Stripe/email credentials) — only the attributes
    _handle_invoice_failed and create_portal_session actually touch."""
    svc = StripePaymentService.__new__(StripePaymentService)
    svc.supabase = MagicMock()
    svc.email_service = MagicMock()
    svc.public_url = "https://app.mybijou.xyz"
    svc.create_portal_session = MagicMock(return_value=portal_result)
    svc._record_transaction = MagicMock()

    tenant_row = {
        "id": "tenant-1",
        "email": "owner@example.com",
        "business_name": "Test Co",
        "stripe_customer_id": "cus_123",
    }
    svc.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[tenant_row]
    )
    svc.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    return svc


def _invoice():
    return {
        "customer": "cus_123",
        "id": "in_123",
        "amount_due": 4900,
        "currency": "usd",
    }


def test_failed_invoice_email_links_to_stripe_portal_not_signup_page():
    svc = _make_service(portal_result={"url": "https://billing.stripe.com/p/session_abc", "session_id": "bps_1"})

    svc._handle_invoice_failed(_invoice())

    svc.create_portal_session.assert_called_once_with("tenant-1")
    svc.email_service.send_trial_expired_email.assert_called_once()
    kwargs = svc.email_service.send_trial_expired_email.call_args.kwargs
    assert kwargs["upgrade_url"] == "https://billing.stripe.com/p/session_abc"
    assert "onboarding.html" not in kwargs["upgrade_url"]


def test_failed_invoice_email_falls_back_to_dashboard_billing_tab_if_portal_fails():
    svc = _make_service(portal_result=None)

    svc._handle_invoice_failed(_invoice())

    kwargs = svc.email_service.send_trial_expired_email.call_args.kwargs
    assert kwargs["upgrade_url"] == "https://app.mybijou.xyz/dashboard#billing"
    assert "onboarding.html" not in kwargs["upgrade_url"]
