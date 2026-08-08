"""
Payment Tool for Bijou AI
==========================

Generates Stripe payment links and supports Malaysian payment methods (FPX, DuitNow).
Enables self-serve onboarding and subscription management.

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
import os
from typing import Any, Dict, List, Optional
import stripe

logger = logging.getLogger(__name__)

class PaymentTool:
    """
    Stripe-based payment tool for Bijou AI.
    
    Features:
    - Create Checkout sessions with FPX and DuitNow support
    - Support for Google Pay and Card payments
    - Subscription and one-time payment support
    - Integration with Malaysian Ringgit (MYR)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Payment tool.
        
        Args:
            api_key: Stripe secret API key
        """
        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY")
        if self.api_key:
            stripe.api_key = self.api_key
            self._initialized = True
            logger.info("✅ Payment tool initialized with Stripe")
        else:
            self._initialized = False
            logger.warning("⚠️ STRIPE_SECRET_KEY not set - payment tool disabled")

    async def create_checkout_session(
        self,
        customer_email: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        tenant_id: Optional[str] = None,
        allow_promotion_codes: bool = True
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session.
        
        Args:
            customer_email: Customer's email address
            plan_id: Stripe Price/Plan ID
            success_url: Redirect URL after success
            cancel_url: Redirect URL after cancellation
            tenant_id: Optional tenant identifier for metadata
            allow_promotion_codes: Enable discount codes
            
        Returns:
            Dictionary with session URL or error
        """
        if not self._initialized:
            return {"success": False, "error": "Stripe not configured"}

        try:
            # Plan IDs mapping (convenience)
            plans = {
                "starter": os.getenv("STRIPE_PRICE_STARTER"),
                "pro": os.getenv("STRIPE_PRICE_PRO")
            }
            
            stripe_price_id = plans.get(plan_id, plan_id)

            # --- CREATIVE COMING SOON SYSTEM ---
            if not stripe_price_id or stripe_price_id == "your_price_id_here":
                logger.info(f"🚧 Plan '{plan_id}' is in 'Coming Soon' mode (no Price ID in .env)")
                return {
                    "success": True,
                    "is_coming_soon": True,
                    "message": f"Our {plan_id.capitalize()} plan is currently being finalized. Stay tuned for the official launch!",
                    "url": None
                }

            session = stripe.checkout.Session.create(
                customer_email=customer_email,
                payment_method_types=['card', 'fpx', 'duitnow_qr', 'google_pay'],
                line_items=[{
                    'price': stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                allow_promotion_codes=allow_promotion_codes,
                metadata={
                    'tenant_id': tenant_id or "new_onboarding",
                    'plan_type': plan_id
                }
            )

            return {
                "success": True,
                "session_id": session.id,
                "url": session.url
            }

        except Exception as e:
            logger.error(f"❌ Failed to create checkout session: {e}")
            return {"success": False, "error": str(e)}

    def get_payment_methods(self) -> List[str]:
        """Return supported payment methods"""
        return ["FPX (Malaysia Online Banking)", "DuitNow QR", "Visa/Mastercard", "Google Pay"]

    def is_available(self) -> bool:
        """Check if tool is ready for use"""
        return self._initialized
