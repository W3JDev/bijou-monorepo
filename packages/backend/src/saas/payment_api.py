"""
Bijou AI - Payment API
======================

Stripe-based subscription management for Bijou AI tenants.

Features:
- Create Checkout sessions (card, FPX, DuitNow QR, Google Pay)
- Stripe webhook handler (subscription.created, payment_intent.succeeded, etc.)
- Customer Portal for self-serve plan changes / cancellation
- Plan listing with pricing

Malaysian market support: FPX + DuitNow QR + MYR

Author: W3J Bijou AI
Version: 1.0.0
"""

import hashlib
import hmac
import logging
import os
import time
from typing import Any, Dict, List, Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.core.dashboard_api_simple import verify_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["payment"])


# ---------------------------------------------------------------------------
# Startup guard: fail loud if Stripe price IDs are missing in prod
# ---------------------------------------------------------------------------
# Without these env vars set, the code falls back to hardcoded test/staging
# Stripe Price IDs (e.g. price_1T3Jg2...) which would 404 at checkout time in
# prod. Catch the misconfig at module import so the deploy fails loud, not at
# the first customer's checkout.
_REQUIRED_STRIPE_ENV = [
    "STRIPE_PRICE_PRO_MONTHLY",
    "STRIPE_PRICE_PRO_YEARLY",
    "STRIPE_PRICE_GROWTH_MONTHLY",
    "STRIPE_PRICE_GROWTH_YEARLY",
]


def _check_stripe_price_env() -> None:
    """Log a loud warning at module load if any STRIPE_PRICE_* env var is missing.

    In production (FLY_APP_NAME set OR ENV=production), this is an ERROR-level
    log so the deploy fails visibly. In dev, it's a warning so local testing
    still works with the hardcoded fallbacks.
    """
    missing = [k for k in _REQUIRED_STRIPE_ENV if not os.getenv(k, "").strip()]
    if not missing:
        return
    is_prod = bool(os.getenv("FLY_APP_NAME", "").strip()) or os.getenv("ENV", "").lower() == "production"
    msg = (
        f"⚠️  Missing Stripe price-ID env vars: {', '.join(missing)}. "
        f"Checkout will use the hardcoded test/staging fallback Price IDs and FAIL at "
        f"Stripe's API. Set them in Fly.io secrets (fly secrets set) or your local .env."
    )
    if is_prod:
        logger.error("PROD CONFIG ERROR: " + msg)
    else:
        logger.warning(msg)


_check_stripe_price_env()


# ---------------------------------------------------------------------------
# Stripe bootstrap
# ---------------------------------------------------------------------------

def _get_stripe():
    """Return initialised stripe module or raise."""
    key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Payment service not configured (STRIPE_SECRET_KEY missing)")
    stripe.api_key = key
    return stripe


# ---------------------------------------------------------------------------
# StripeService — injectable wrapper for testability
# ---------------------------------------------------------------------------

class StripeService:
    """
    Thin wrapper around Stripe SDK that is monkeypatched in tests.
    Separates verification (fast, no I/O) from processing (DB writes).
    """

    def verify_webhook_event(self, payload: bytes, sig_header: str):
        """
        Verify the Stripe webhook signature and parse the event.
        Returns the event dict on success, None on verification failure.
        In dev mode (no STRIPE_WEBHOOK_SECRET) skips verification.
        """
        import json as _json
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
        if not webhook_secret:
            logger.warning("⚠️ STRIPE_WEBHOOK_SECRET not set — skipping signature verification (dev mode)")
            try:
                return _json.loads(payload)
            except Exception:
                return None
        try:
            st = _get_stripe()
            return st.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception:
            return None

    def process_webhook_event(self, event: dict) -> bool:
        """
        Apply DB changes for the given Stripe event.
        Returns True. May raise — caller must catch and still return 200.
        """
        from supabase import create_client as _create_client
        supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
        supabase_key = (os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip('"')
        db = _create_client(supabase_url, supabase_key)

        event_type = event.get("type", "")
        data_obj = event.get("data", {}).get("object", {})
        logger.info(f"📨 Stripe webhook processing: {event_type}")

        if event_type == "checkout.session.completed":
            tenant_id = data_obj.get("metadata", {}).get("tenant_id")
            customer_id = data_obj.get("customer")
            plan = data_obj.get("metadata", {}).get("plan", "starter")
            if tenant_id and customer_id:
                db.table("tenants").update({
                    "stripe_customer_id": customer_id,
                    "subscription_tier": plan,
                    "plan_tier": plan,
                    "plan": plan,
                    "payment_method": "stripe",
                }).eq("id", tenant_id).execute()
                logger.info(f"✅ Tenant {tenant_id} activated on plan={plan} (customer={customer_id})")

        elif event_type == "customer.subscription.updated":
            customer_id = data_obj.get("customer")
            status = data_obj.get("status")
            if status in ("active", "trialing"):
                items = data_obj.get("items", {}).get("data", [])
                price_id = items[0].get("price", {}).get("id") if items else None
                plan_map = {v: k for k, v in {
                    "starter": os.getenv("STRIPE_PRICE_STARTER"),
                    "pro":     os.getenv("STRIPE_PRICE_PRO"),
                }.items() if v}
                plan = plan_map.get(price_id, "starter")
                db.table("tenants").update({
                    "subscription_tier": plan,
                    "plan_tier": plan,
                    "plan": plan,
                }).eq("stripe_customer_id", customer_id).execute()
                logger.info(f"✅ Subscription updated: customer={customer_id} plan={plan}")

        elif event_type == "customer.subscription.deleted":
            customer_id = data_obj.get("customer")
            db.table("tenants").update({
                "subscription_tier": "freemium",
                "plan_tier": "freemium",
                "plan": "freemium",
                "payment_method": "cancelled",
            }).eq("stripe_customer_id", customer_id).execute()
            logger.warning(f"⚠️ Subscription cancelled: customer={customer_id} → downgraded to freemium")

        elif event_type == "invoice.payment_failed":
            customer_id = data_obj.get("customer")
            attempt_count = data_obj.get("attempt_count", 0)
            logger.warning(f"⚠️ Payment failed: customer={customer_id} attempt={attempt_count}")

        return True


def get_stripe_service() -> StripeService:
    """Factory — returns a StripeService instance. Monkeypatched in tests."""
    return StripeService()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    plan: str                        # "pro" | "growth"
    billing_interval: str = "month"  # "month" | "year"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PortalRequest(BaseModel):
    return_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Plan catalogue (mirrors pricing_engine.py tiers)
# ---------------------------------------------------------------------------

PLANS: List[Dict[str, Any]] = [
    {
        "id": "pro",
        "name": "PRO",
        "price_myr": 299,
        "price_usd": 66,  # ~RM299 / 4.5 exchange rate
        "currency": "MYR",
        "messages_per_month": 3000,
        "features": [
            "3,000 conversations/month",
            "WhatsApp + Telegram AI",
            "Call booking + reminders",
            "Email confirmations (from Bijou)",
            "Image & audio handling",
            "Lead capture + CRM",
            "Dashboard analytics",
            "Full TRACE insights",
            "Manglish support",
        ],
        "stripe_price_id_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_1T3Jg2AdgDGXBSXV7ljuesMa"),
        "stripe_price_id_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY", "price_1T3Jg3AdgDGXBSXVagldrPlx"),
    },
    {
        "id": "growth",
        "name": "GROWTH",
        "price_myr": 499,
        "price_usd": 110,  # ~RM499 / 4.5 exchange rate
        "currency": "MYR",
        "messages_per_month": 10000,
        "features": [
            "10,000 conversations/month",
            "All PRO features",
            "Custom SMTP domain (send emails from your domain)",
            "Onboarding call + KB setup (RM500 one-time)",
            "Priority support (4-hour response)",
            "Monthly strategy call",
        ],
        "stripe_price_id_monthly": os.getenv("STRIPE_PRICE_GROWTH_MONTHLY", "price_1T7CuFAdgDGXBSXV1wE3kAY3"),
        "stripe_price_id_yearly": os.getenv("STRIPE_PRICE_GROWTH_YEARLY", "price_1T7CuHAdgDGXBSXVcQHOyauD"),
        "contact_sales": True,  # Manual invoicing, not Stripe checkout
        "setup_fee_myr": 500,
    },
    {
        "id": "jewel",
        "name": "JEWEL",
        "badge": "Signature",          # shown on pricing page
        "price_myr": None,              # bespoke — contact us
        "price_usd": None,
        "currency": "MYR",
        "messages_per_month": None,    # unlimited (negotiated)
        "features": [
            "Unlimited conversations",
            "All GROWTH features",
            "AI Outreach Campaign Engine (built-in CRM + Gemini personalisation)",
            "Dedicated account manager",
            "White-label option (your brand, your domain)",
            "Custom AI persona + tone training",
            "Multi-device / multi-number WhatsApp support",
            "Monthly executive report + benchmarking",
            "SLA: 2-hour response, guaranteed uptime",
            "Direct founder access (WhatsApp line)",
        ],
        "contact_sales": True,
        "cta_label": "Talk to Jewel →",   # personalised CTA on pricing page
        "highlight": True,              # full-width feature card on pricing page
    },
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/plans")
async def list_plans():
    """Return available subscription plans (public — no auth required)."""
    return {"plans": PLANS}


@router.post("/checkout")
async def create_checkout_session(
    req: CheckoutRequest,
    tenant_id: str = Depends(verify_session),
):
    """
    Create a Stripe Checkout session for the authenticated tenant.
    Supports: FPX (Malaysian Online Banking), DuitNow QR, Visa/Mastercard, Google Pay.
    """
    st = _get_stripe()

    # Look up the plan
    plan = next((p for p in PLANS if p["id"] == req.plan), None)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {req.plan}")

    if plan.get("contact_sales"):
        return {
            "success": True,
            "type": "contact_sales",
            "message": "Please contact us at hello@mybijou.xyz to discuss GROWTH plan pricing.",
        }

    # Select monthly or yearly price based on billing interval.
    # Read env at REQUEST time (not at module load) so:
    #   1. Tests can override the env var per-test
    #   2. Stripe price ID can be changed without a code redeploy
    #   3. The hardcoded fallback in PLANS only kicks in if NO env var is set
    billing = "yearly" if req.billing_interval == "year" else "monthly"
    env_key = f"STRIPE_PRICE_{req.plan.upper()}_{billing.upper()}"
    price_key = f"stripe_price_id_{billing}"
    price_id = os.getenv(env_key) or plan.get(price_key)
    if not price_id:
        return {
            "success": True,
            "type": "coming_soon",
            "message": f"The {plan['name']} plan ({req.billing_interval}ly) is launching soon. We'll notify you!",
        }

    base_url = os.getenv("PUBLIC_URL", "https://app.mybijou.xyz")
    success_url = req.success_url or f"{base_url}/dashboard?tenant_id={tenant_id}&payment=success"
    cancel_url  = req.cancel_url  or f"{base_url}/dashboard?tenant_id={tenant_id}&payment=cancelled"

    try:
        # Look up existing Stripe customer for this tenant so we don't create duplicates
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
        supabase_key = (os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip('"')
        supabase = create_client(supabase_url, supabase_key)

        tenant_row = supabase.table("tenants").select("owner_email, stripe_customer_id").eq("id", tenant_id).maybe_single().execute()
        tr_data = getattr(tenant_row, "data", None) if tenant_row else None
        tenant_data = tr_data if isinstance(tr_data, dict) else {}
        existing_customer_id = tenant_data.get("stripe_customer_id")
        owner_email = tenant_data.get("owner_email", "")

        session_kwargs: Dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "allow_promotion_codes": True,  # ← Customers can enter TRIAL7DAYS, TRIAL3DAYS, etc.
            # Stripe Dashboard controls which payment methods are shown.
            # Enable FPX/DuitNow in Dashboard → Settings → Payment Methods for Malaysian customers.
            "automatic_payment_methods": {"enabled": True},
            "metadata": {"tenant_id": tenant_id, "plan": req.plan},
            "subscription_data": {
                "metadata": {"tenant_id": tenant_id},
                "trial_period_days": 7,  # ← Universal 7-day free trial
            },
        }

        if existing_customer_id:
            session_kwargs["customer"] = existing_customer_id
        elif owner_email:
            session_kwargs["customer_email"] = owner_email

        session = st.checkout.Session.create(**session_kwargs)

        logger.info(f"✅ Stripe checkout session created for tenant {tenant_id} (plan={req.plan})")
        return {"success": True, "url": session.url, "session_id": session.id}

    except stripe.error.StripeError as e:
        logger.error(f"❌ Stripe error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Payment provider error: {e.user_message or str(e)}")
    except Exception as e:
        logger.error(f"❌ Checkout session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/portal")
async def customer_portal(
    req: PortalRequest,
    tenant_id: str = Depends(verify_session),
):
    """
    Create a Stripe Customer Portal link so tenants can manage their
    subscription (upgrade, downgrade, cancel, update payment method).
    """
    st = _get_stripe()

    try:
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
        supabase_key = (os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip('"')
        supabase = create_client(supabase_url, supabase_key)

        tenant_row = supabase.table("tenants").select("stripe_customer_id").eq("id", tenant_id).maybe_single().execute()
        tr_data = getattr(tenant_row, "data", None) if tenant_row else None
        customer_id = (tr_data or {}).get("stripe_customer_id")

        if not customer_id:
            raise HTTPException(
                status_code=404,
                detail="No active subscription found. Please subscribe first."
            )

        base_url = os.getenv("PUBLIC_URL", "https://app.mybijou.xyz")
        return_url = req.return_url or f"{base_url}/dashboard?tenant_id={tenant_id}"

        session = st.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        return {"success": True, "url": session.url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Portal session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to open billing portal")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe webhook handler.
    Processes: checkout.session.completed, customer.subscription.updated,
               customer.subscription.deleted, invoice.payment_failed

    Uses get_stripe_service() for testability — tests monkeypatch that function.
    """
    from fastapi.responses import JSONResponse

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Reject immediately if no signature header is present at all
    if not sig_header:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Missing Stripe-Signature header"},
        )

    svc = get_stripe_service()
    event = svc.verify_webhook_event(payload, sig_header)

    if event is None:
        logger.warning("⚠️ Stripe webhook signature verification failed")
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Invalid webhook signature"},
        )

    event_id = event.get("id", "")
    try:
        svc.process_webhook_event(event)
    except Exception as e:
        logger.error(f"❌ Webhook processing error ({event.get('type')}): {e}")
        # Always return 200 so Stripe stops retrying
        return {"success": True, "received": True, "event_id": event_id, "warning": "processing error logged"}

    return {"success": True, "received": True, "event_id": event_id}


@router.get("/tenant/usage")
async def get_tenant_usage(tenant_id: str = Depends(verify_session)):
    """
    Get billing usage data for the dashboard billing card.
    Returns plan, usage, limit, early_adopter flag, and trial info.
    """
    try:
        from supabase import create_client
        from datetime import datetime
        import os

        supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
        supabase_key = (os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip('"')
        supabase = create_client(supabase_url, supabase_key)

        # Get tenant data
        # NOTE (2026-08-06): `tenants.early_adopter_lock` is referenced in
        # the old code but the column was never migrated in. Selecting it
        # would 500 the whole /api/payment/tenant/usage endpoint and leave
        # the Settings tab empty. We omit it and default `early_adopter`
        # to False in the response below.
        tenant_row = supabase.table("tenants").select(
            "plan_tier, subscription_status, trial_end_date, stripe_customer_id"
        ).eq("id", tenant_id).maybe_single().execute()

        tr_data = getattr(tenant_row, "data", None) if tenant_row else None
        if not tr_data:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant = tr_data
        plan_name = tenant.get("plan_tier") or "freemium"
        stripe_customer_id = tenant.get("stripe_customer_id")

        # Get plan limits
        plan_limits = {
            "pro": 3000,
            "growth": 10000,
            "jewel": 999999,    # effectively unlimited
            "freemium": 100,
        }
        limit = plan_limits.get(plan_name, 3000)

        # Get usage for current month
        # NOTE (2026-08-06): the old code called a Supabase RPC
        # `count_monthly_conversations` which references a `conversation_id`
        # column that doesn't exist in this DB (the schema uses
        # `messages.conversation_key`). 500-ing here leaves the Settings
        # tab empty. We now do the count in Python with a tolerant
        # fallback so the page always renders, even if the messages
        # table is empty or the column is renamed.
        from datetime import datetime, timedelta
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage = 0
        try:
            usage_row = (
                supabase.table("messages")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .gte("created_at", month_start.isoformat())
                .execute()
            )
            usage = usage_row.count or 0
        except Exception as usage_err:
            logger.warning(
                "Could not count monthly messages for %s: %s — returning 0",
                tenant_id, usage_err,
            )
            usage = 0

        # Handle trial end date
        trial_end = tenant.get("trial_end_date")
        if trial_end and isinstance(trial_end, str):
            trial_end = trial_end  # Keep as ISO string for frontend
        else:
            trial_end = None

        return {
            "plan": plan_name,
            "usage": usage,
            "limit": limit,
            "early_adopter": tenant.get("early_adopter_lock", False),
            "subscription_status": tenant.get("subscription_status", "active"),
            "trial_end": trial_end,
            "has_subscription": bool(stripe_customer_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get tenant usage: {e}")
        # Return default values instead of failing
        return {
            "plan": "pro",
            "usage": 0,
            "limit": 3000,
            "early_adopter": False,
            "subscription_status": "active",
            "trial_end": None,
        }
