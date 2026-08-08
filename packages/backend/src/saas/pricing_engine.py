"""
Bijou AI - Pricing Engine
==========================

Multi-tier subscription management and usage tracking.

Canonical tiers (Signal Gem 2026 edition, RM only — USD legacy removed 2026-07-26):
- FREEMIUM: RM0/mo, 100 msg/month, 5 customers, no tools (legacy: was USD)
- STARTER: RM299/mo (alias for PRO, kept for DB backward compat — same limits as PRO)
- PRO:     RM299/mo, 3000 msg/month, unlimited customers, all tools
- GROWTH:  RM499/mo, 10000 msg/month, unlimited customers, all tools + Telegram
- ENTERPRISE: Custom (no fixed price; sales-led), unlimited everything, white-label

# 2026-07-30 sync (per pricing-drift-2026-07-30.md):
#   - PRO messages: 5000 -> 3000 (match landing + in-app marketing)
#   - GROWTH added to SubscriptionTier enum (was string-only — caused KeyError on get_usage_limits)
#   - Telegram AI tool flag added (was promised on landing, missing from engine)
#   - Currency bug fixed (was "USD", docstring says "RM only")
#   - Upgrade copy was "$29"/"$99" (pre-2026-07-26 USD strings)

This is the canonical customer-facing pricing model. Mirrors:
  - Landing site (index.html): "PRO at RM299/month"
  - In-app pricing page (pricing.html): "PRO RM299 + GROWTH RM499"
  - Trial-expired email body (email_service.py): "PRO RM299 / GROWTH RM499 / Enterprise Custom"
  - System prompt (bijou_system_prompt.txt): "THE ONLY PLAN: PRO at RM299/month"

The customer-facing canon is the 3-tier RM model above. The internal
SubscriptionTier enum retains the legacy STARTER alias for backward compat with
existing DB rows whose subscription_tier = 'starter'. New tenants should use
'pro' or 'growth' (the latter is enforced by payment_api.py via Stripe metadata).

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    """Subscription tier levels"""

    FREEMIUM = "freemium"
    STARTER = "starter"
    PRO = "pro"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


@dataclass
class UsageLimits:
    """Usage limits per subscription tier"""

    messages_per_month: int
    max_customers: int
    tool_calls_per_month: int
    knowledge_docs_max: int
    memory_retention_days: int
    enable_image_tool: bool
    enable_audio_tool: bool
    enable_calendar_tool: bool
    enable_gmail_tool: bool
    enable_custom_instructions: bool
    enable_model_switching: bool
    enable_handover_queue: bool
    enable_api_access: bool
    enable_dashboard: bool
    enable_telegram_tool: bool
    reports_frequency: str  # "none", "weekly", "daily", "realtime"


class PricingEngine:
    """
    Manages subscription tiers, usage tracking, and limit enforcement.
    """

    # Tier definitions
    TIER_LIMITS: Dict[SubscriptionTier, UsageLimits] = {
        SubscriptionTier.FREEMIUM: UsageLimits(
            messages_per_month=100,
            max_customers=5,
            tool_calls_per_month=0,
            knowledge_docs_max=10,
            memory_retention_days=30,
            enable_image_tool=False,
            enable_audio_tool=False,
            enable_calendar_tool=False,
            enable_gmail_tool=False,
            enable_custom_instructions=False,
            enable_model_switching=False,
            enable_handover_queue=False,
            enable_api_access=False,
            enable_dashboard=False,
            enable_telegram_tool=False,  # 2026-07-30: added (new field, False for free tier)
            reports_frequency="weekly",
        ),
        SubscriptionTier.STARTER: UsageLimits(
            messages_per_month=3000,  # 2026-07-30: alias for PRO, was 1000 (drift H1)
            max_customers=999999,  # 2026-07-30: was 50 — PRO = unlimited customers
            tool_calls_per_month=999999,  # 2026-07-30: was 100 — PRO = unlimited tool calls
            knowledge_docs_max=200,  # 2026-07-30: aligned to PRO (was 50)
            memory_retention_days=365,  # 2026-07-30: aligned to PRO (was 90)
            enable_image_tool=True,
            enable_audio_tool=True,
            enable_calendar_tool=True,  # 2026-07-30: aligned to PRO (was False)
            enable_gmail_tool=True,  # 2026-07-30: aligned to PRO (was False)
            enable_custom_instructions=True,
            enable_model_switching=True,
            enable_handover_queue=True,
            enable_api_access=True,  # 2026-07-30: aligned to PRO (was False)
            enable_dashboard=True,  # 2026-07-30: aligned to PRO (was False)
            enable_telegram_tool=True,  # 2026-07-30: added (new field, default True for paid tiers)
            reports_frequency="daily",
        ),
        SubscriptionTier.PRO: UsageLimits(
            messages_per_month=3000,  # 2026-07-30: was 5000 — match landing + in-app marketing (drift H1)
            max_customers=999999,  # Unlimited
            tool_calls_per_month=999999,  # Unlimited
            knowledge_docs_max=200,  # 2026-07-30: keeps current generous limit; landing says "200 documents (FAQs included)"
            memory_retention_days=365,
            enable_image_tool=True,
            enable_audio_tool=True,
            enable_calendar_tool=True,
            enable_gmail_tool=True,
            enable_custom_instructions=True,
            enable_model_switching=True,
            enable_handover_queue=True,
            enable_api_access=True,
            enable_dashboard=True,
            enable_telegram_tool=True,  # 2026-07-30: added (landing promises Telegram on PRO)
            reports_frequency="daily",
        ),
        SubscriptionTier.GROWTH: UsageLimits(
            # 2026-07-30: added to enum (was string-only — caused KeyError on get_usage_limits for growth tenants)
            messages_per_month=10000,  # matches in-app pricing.html "10,000 conversations"
            max_customers=999999,  # Unlimited
            tool_calls_per_month=999999,  # Unlimited
            knowledge_docs_max=999999,  # Unlimited
            memory_retention_days=365,
            enable_image_tool=True,
            enable_audio_tool=True,
            enable_calendar_tool=True,
            enable_gmail_tool=True,
            enable_custom_instructions=True,
            enable_model_switching=True,
            enable_handover_queue=True,
            enable_api_access=True,
            enable_dashboard=True,
            enable_telegram_tool=True,
            reports_frequency="realtime",
        ),
        SubscriptionTier.ENTERPRISE: UsageLimits(
            messages_per_month=999999,  # Unlimited
            max_customers=999999,  # Unlimited
            tool_calls_per_month=999999,  # Unlimited
            knowledge_docs_max=999999,  # Unlimited
            memory_retention_days=999999,  # Unlimited
            enable_image_tool=True,
            enable_audio_tool=True,
            enable_calendar_tool=True,
            enable_gmail_tool=True,
            enable_custom_instructions=True,
            enable_model_switching=True,
            enable_handover_queue=True,
            enable_api_access=True,
            enable_dashboard=True,
            enable_telegram_tool=True,
            reports_frequency="realtime",
        ),
    }

    # Canonical pricing in MYR (Ringgit Malaysia). 2026-07-26 USD → RM conversion.
    # 2026-07-30: GROWTH added to enum (was string-only); matches in-app pricing.html
    TIER_PRICING: Dict[SubscriptionTier, float] = {
        SubscriptionTier.FREEMIUM: 0.0,
        SubscriptionTier.STARTER: 299.0,  # legacy alias for PRO; existing DB rows
        SubscriptionTier.PRO: 299.0,      # canonical main tier (matches landing + pricing.html)
        SubscriptionTier.GROWTH: 499.0,   # 2026-07-30: added; matches in-app pricing.html
        SubscriptionTier.ENTERPRISE: 0.0, # custom — sales-led; 0 here means "quote"
    }

    def __init__(self, supabase_client=None, enable_enforcement: bool = True):
        """
        Initialize pricing engine.

        Args:
            supabase_client: Supabase client for usage tracking
            enable_enforcement: Enable usage limit enforcement (feature flag)
        """
        self.supabase = supabase_client
        self.enable_enforcement = enable_enforcement

        # Feature flag override (for testing/emergency)
        env_flag = os.getenv("ENABLE_USAGE_LIMITS", "true").lower()
        if env_flag == "false":
            self.enable_enforcement = False
            logger.warning("⚠️ Usage limit enforcement DISABLED via env flag")

    def get_tenant_tier(self, tenant_id: str) -> SubscriptionTier:
        """
        Get subscription tier for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            SubscriptionTier enum
        """
        if not self.supabase:
            # Default to freemium if no database
            return SubscriptionTier.FREEMIUM

        try:
            response = (
                self.supabase.table("tenants")
                .select("subscription_tier")
                .eq("id", tenant_id)
                .maybe_single()
                .execute()
            )

            rdata = getattr(response, "data", None) if response else None
            if rdata:
                tier_str = rdata.get("subscription_tier", "freemium")
                return SubscriptionTier(tier_str)
        except Exception as e:
            logger.error(f"Error fetching tenant tier: {e}")

        return SubscriptionTier.FREEMIUM

    def get_usage_limits(self, tenant_id: str) -> UsageLimits:
        """
        Get usage limits for a tenant based on their tier.

        Args:
            tenant_id: Tenant identifier

        Returns:
            UsageLimits object
        """
        tier = self.get_tenant_tier(tenant_id)
        return self.TIER_LIMITS[tier]

    def get_current_usage(self, tenant_id: str) -> Dict[str, int]:
        """
        Get current month's usage for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dict with usage metrics
        """
        if not self.supabase:
            return {
                "messages": 0,
                "tool_calls": 0,
                "customers": 0,
            }

        try:
            # Get usage for current month
            month_start = datetime.now().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )

            response = (
                self.supabase.table("usage_tracking")
                .select("*")
                .eq("tenant_id", tenant_id)
                .gte("created_at", month_start.isoformat())
                .execute()
            )

            messages = 0
            tool_calls = 0
            customers = set()

            if response.data:
                for record in response.data:
                    messages += record.get("message_count", 0)
                    tool_calls += record.get("tool_call_count", 0)
                    if record.get("customer_jid"):
                        customers.add(record["customer_jid"])

            return {
                "messages": messages,
                "tool_calls": tool_calls,
                "customers": len(customers),
            }
        except Exception as e:
            logger.error(f"Error fetching usage: {e}")
            return {"messages": 0, "tool_calls": 0, "customers": 0}

    def check_limit(
        self, tenant_id: str, usage_type: str, increment: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant is within usage limits.

        Args:
            tenant_id: Tenant identifier
            usage_type: Type of usage (messages, tool_calls, customers)
            increment: Amount to check (default 1)

        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        if not self.enable_enforcement:
            return (True, None)

        limits = self.get_usage_limits(tenant_id)
        current = self.get_current_usage(tenant_id)
        tier = self.get_tenant_tier(tenant_id)

        if usage_type == "messages":
            if current["messages"] + increment > limits.messages_per_month:
                return (
                    False,
                    f"📊 Monthly message limit reached ({limits.messages_per_month}).\n"
                    f"💎 Upgrade to {self._suggest_upgrade(tier)} for more messages!\n"
                    f"Visit: {os.getenv('APP_URL', '').rstrip('/')}/static/login.html",
                )

        elif usage_type == "tool_calls":
            if current["tool_calls"] + increment > limits.tool_calls_per_month:
                return (
                    False,
                    f"🛠️ Monthly tool usage limit reached ({limits.tool_calls_per_month}).\n"
                    f"💎 Upgrade to {self._suggest_upgrade(tier)} for unlimited tools!\n"
                    f"Visit: {os.getenv('APP_URL', '').rstrip('/')}/static/login.html",
                )

        elif usage_type == "customers":
            if current["customers"] + increment > limits.max_customers:
                return (
                    False,
                    f"👥 Customer limit reached ({limits.max_customers}).\n"
                    f"💎 Upgrade to {self._suggest_upgrade(tier)} for more customers!\n"
                    f"Visit: {os.getenv('APP_URL', '').rstrip('/')}/static/login.html",
                )

        return (True, None)

    def track_usage(
        self,
        tenant_id: str,
        message_count: int = 0,
        tool_call_count: int = 0,
        customer_jid: Optional[str] = None,
    ):
        """
        Track usage for billing and limit enforcement.

        Args:
            tenant_id: Tenant identifier
            message_count: Number of messages
            tool_call_count: Number of tool calls
            customer_jid: Customer JID (for customer count)
        """
        if not self.supabase:
            return

        try:
            self.supabase.table("usage_tracking").insert(
                {
                    "tenant_id": tenant_id,
                    "message_count": message_count,
                    "tool_call_count": tool_call_count,
                    "customer_jid": customer_jid,
                    "created_at": datetime.now().isoformat(),
                }
            ).execute()

            logger.debug(
                f"✅ Usage tracked: tenant={tenant_id}, messages={message_count}, "
                f"tools={tool_call_count}"
            )
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")

    def is_feature_enabled(self, tenant_id: str, feature: str) -> bool:
        """
        Check if a feature is enabled for a tenant's tier.

        Args:
            tenant_id: Tenant identifier
            feature: Feature name (e.g., "image_tool", "custom_instructions")

        Returns:
            bool: True if feature is enabled
        """
        limits = self.get_usage_limits(tenant_id)
        feature_attr = f"enable_{feature}"

        if hasattr(limits, feature_attr):
            return getattr(limits, feature_attr)

        logger.warning(f"Unknown feature: {feature}")
        return False

    def get_usage_percentage(self, tenant_id: str) -> Dict[str, float]:
        """
        Get usage as percentage of limits.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dict with percentages for each metric
        """
        limits = self.get_usage_limits(tenant_id)
        current = self.get_current_usage(tenant_id)

        return {
            "messages": (current["messages"] / limits.messages_per_month * 100)
            if limits.messages_per_month > 0
            else 0,
            "tool_calls": (current["tool_calls"] / limits.tool_calls_per_month * 100)
            if limits.tool_calls_per_month > 0
            else 0,
            "customers": (current["customers"] / limits.max_customers * 100)
            if limits.max_customers > 0
            else 0,
        }

    def should_warn_limit(self, tenant_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant should receive a warning about approaching limits.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tuple of (should_warn: bool, warning_message: Optional[str])
        """
        percentages = self.get_usage_percentage(tenant_id)
        tier = self.get_tenant_tier(tenant_id)

        # Warn at 80% usage
        for metric, pct in percentages.items():
            if pct >= 80 and pct < 100:
                return (
                    True,
                    f"⚠️ You've used {pct:.0f}% of your {metric} limit this month.\n"
                    f"💎 Consider upgrading to {self._suggest_upgrade(tier)} for peace of mind!",
                )

        return (False, None)

    def _suggest_upgrade(self, current_tier: SubscriptionTier) -> str:
        """Suggest next tier for upgrade. 2026-07-30: fixed pre-2026-07-26 USD strings."""
        if current_tier == SubscriptionTier.FREEMIUM:
            return "Starter (RM 299/mo)"
        elif current_tier == SubscriptionTier.STARTER:
            return "Pro (RM 299/mo)"
        elif current_tier == SubscriptionTier.PRO:
            return "Growth (RM 499/mo) or Enterprise (custom)"
        elif current_tier == SubscriptionTier.GROWTH:
            return "Enterprise (custom pricing)"
        return "a higher tier"

    def get_tier_info(self, tier: SubscriptionTier, billing_period: str = "monthly") -> Dict[str, Any]:
        """
        Get comprehensive information about a tier.

        Args:
            tier: SubscriptionTier enum
            billing_period: "monthly" or "yearly" (default "monthly" for backward compat).
                NOTE: The `price` field is the MONTHLY price regardless of billing_period.
                The actual charge for yearly subs is determined by the Stripe Price ID
                (see payment_api.py: STRIPE_PRICE_PRO_YEARLY), not by this engine.

        Returns:
            Dict with tier details
        """
        limits = self.TIER_LIMITS[tier]
        price = self.TIER_PRICING[tier]

        return {
            "tier": tier.value,
            "price": price,
            "currency": "MYR",  # 2026-07-30: was "USD" (drift H4) — docstring says RM only
            "billing_period": billing_period,
            "limits": {
                "messages_per_month": limits.messages_per_month,
                "max_customers": limits.max_customers
                if limits.max_customers < 999999
                else "Unlimited",
                "tool_calls_per_month": limits.tool_calls_per_month
                if limits.tool_calls_per_month < 999999
                else "Unlimited",
                "knowledge_docs_max": limits.knowledge_docs_max
                if limits.knowledge_docs_max < 999999
                else "Unlimited",
                "memory_retention_days": limits.memory_retention_days
                if limits.memory_retention_days < 999999
                else "Unlimited",
            },
            "features": {
                "image_tool": limits.enable_image_tool,
                "audio_tool": limits.enable_audio_tool,
                "calendar_tool": limits.enable_calendar_tool,
                "gmail_tool": limits.enable_gmail_tool,
                "custom_instructions": limits.enable_custom_instructions,
                "model_switching": limits.enable_model_switching,
                "handover_queue": limits.enable_handover_queue,
                "api_access": limits.enable_api_access,
                "dashboard": limits.enable_dashboard,
                "telegram_tool": limits.enable_telegram_tool,  # 2026-07-30: added
            },
            "reports_frequency": limits.reports_frequency,
        }
