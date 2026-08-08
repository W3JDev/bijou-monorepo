"""
Bijou AI - Tenant Manager
==========================

Multi-tenant isolation and management.

Ensures complete data isolation between different clients/businesses.
Each tenant has their own:
- Customers
- Conversations
- Knowledge base
- Settings
- Usage tracking

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
"""

import logging
import os
import re
import secrets
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _generate_slug(business_name: str) -> str:
    """Generate a URL-safe unique slug from a business name.

    The `tenants.slug` column is NOT NULL UNIQUE, so every tenant insert
    must include one. We lowercase, strip non-alphanumerics, collapse
    dashes, and append a 4-byte hex suffix for uniqueness. Falls back to
    'tenant' if the name collapses to an empty string.
    """
    base = (business_name or "").lower().strip()
    base = re.sub(r"[^a-z0-9\s-]", "", base)
    base = re.sub(r"\s+", "-", base)
    base = re.sub(r"-+", "-", base).strip("-")
    if not base:
        base = "tenant"
    return f"{base[:48]}-{secrets.token_hex(4)}"


# Map legacy / friendly plan aliases to the values accepted by
# the `tenants_subscription_tier_check` constraint.
_VALID_TIERS = {
    "freemium",
    "starter",
    "pro",
    "growth",
    "enterprise",
}
_TIER_ALIASES = {
    "free": "freemium",
    "trial": "freemium",
    "basic": "freemium",
    "starter": "starter",
    "pro": "pro",
    "growth": "growth",
    "enterprise": "enterprise",
    "freemium": "freemium",
}


def _normalize_subscription_tier(raw: str) -> str:
    """Coerce whatever the caller passed into a tier the DB accepts.

    The signup form sends `plan: "free"`, the dashboard sends
    `plan_tier: "freemium"`, Stripe webhooks send `pro`/`enterprise`. The
    DB check constraint only allows `freemium`/`starter`/`pro`/`growth`/
    `enterprise`. Map known aliases and fall back to `freemium` rather
    than 500-ing the whole signup.
    """
    key = (raw or "").strip().lower()
    mapped = _TIER_ALIASES.get(key, "freemium")
    if mapped not in _VALID_TIERS:
        return "freemium"
    return mapped


class TenantManager:
    """
    Manages multi-tenant operations and data isolation.

    Ensures tenants cannot access each other's data.
    """

    def __init__(self, supabase_client=None):
        """
        Initialize tenant manager.

        Args:
            supabase_client: Supabase client for database operations
        """
        self.supabase = supabase_client
        self.enable_multi_tenant = (
            os.getenv("ENABLE_MULTI_TENANT", "true").lower() == "true"
        )

        # Default tenant (for single-tenant deployments)
        self.default_tenant_id = os.getenv(
            "DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"
        )

        logger.info(
            f"✅ TenantManager initialized (multi_tenant={self.enable_multi_tenant})"
        )

    def get_tenant_from_whatsapp(self, whatsapp_number: str) -> Optional[str]:
        """
        Get tenant ID from WhatsApp number.

        Args:
            whatsapp_number: WhatsApp number (e.g., "+60123456789@s.whatsapp.net")

        Returns:
            Tenant ID or default tenant
        """
        if not self.enable_multi_tenant:
            return self.default_tenant_id

        if not self.supabase:
            return self.default_tenant_id

        try:
            # Extract phone number
            phone = whatsapp_number.split("@")[0].replace("+", "")

            # Look up tenant by WhatsApp number
            response = (
                self.supabase.table("tenants")
                .select("id")
                .eq("whatsapp_number", f"+{phone}")
                .eq("status", "active")
                .maybe_single()
                .execute()
            )

            rdata = getattr(response, "data", None) if response else None
            if rdata:
                return rdata["id"]

        except Exception as e:
            logger.error(f"Error fetching tenant from WhatsApp: {e}")

        return self.default_tenant_id

    def create_tenant(
        self,
        business_name: str,
        whatsapp_number: str,
        owner_email: Optional[str] = None,
        subscription_tier: str = "freemium",
    ) -> Optional[str]:
        """
        Create a new tenant with default call availability setup.

        Args:
            business_name: Business/company name
            whatsapp_number: WhatsApp business number
            owner_email: Owner's email
            subscription_tier: Initial subscription tier

        Returns:
            Tenant ID or None if failed
        """
        if not self.supabase:
            logger.error("Cannot create tenant: Supabase not configured")
            return None

        try:
            tenant_id = str(uuid.uuid4())

            # Create tenant record
            # NOTE (2026-08-05): `tenants.slug` is UNIQUE NOT NULL. The
            # google_oauth path already sets this; the password-signup
            # path was missing it, which produced the
            # `null value in column "slug" ... violates not-null constraint`
            # 500 that real signups were hitting. We now generate a slug
            # here too so any code path that goes through create_tenant()
            # works.
            #
            # NOTE (2026-08-06): `tenants.whatsapp_number` is also UNIQUE.
            # The signup form's "WhatsApp Number" field is really the
            # OWNER's contact phone — the tenant's actual WhatsApp
            # Business line is connected later via the QR flow. If we
            # blindly insert the contact phone into `whatsapp_number`,
            # any signup whose phone is already used by another tenant
            # (e.g. the founder's own primary tenant) hits a 23505 and
            # 500s. We now: (1) keep the contact phone in `owner_phone`
            # / `phone`, (2) only set `whatsapp_number` when it isn't
            # already taken by another tenant, (3) swallow the unique
            # violation defensively as a no-op rather than crashing.
            normalized_tier = _normalize_subscription_tier(subscription_tier)
            owner_phone_normalized = (
                re.sub(r"\s+", "", (whatsapp_number or "")) or None
            )
            whatsapp_number_for_tenant: Optional[str] = None
            if owner_phone_normalized:
                try:
                    taken = (
                        self.supabase.table("tenants")
                        .select("id")
                        .eq("whatsapp_number", owner_phone_normalized)
                        .limit(1)
                        .execute()
                    )
                    if not taken.data:
                        whatsapp_number_for_tenant = owner_phone_normalized
                except Exception as phone_check_err:
                    logger.warning(
                        "Could not pre-check whatsapp_number uniqueness for %s: %s",
                        owner_phone_normalized, phone_check_err,
                    )
            insert_payload = {
                "id": tenant_id,
                "name": business_name,
                "slug": _generate_slug(business_name),
                "business_name": business_name,
                "owner_email": owner_email,
                "owner_phone": owner_phone_normalized,
                "phone": owner_phone_normalized,
                "subscription_tier": normalized_tier,
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "settings": {
                    "timezone": "Asia/Kuala_Lumpur",
                    "language": "en",
                    "business_hours": {
                        "enabled": False,
                        "start": "09:00",
                        "end": "18:00",
                    },
                },
            }
            if whatsapp_number_for_tenant:
                insert_payload["whatsapp_number"] = whatsapp_number_for_tenant
            self.supabase.table("tenants").insert(insert_payload).execute()

            # Setup default call availability (Monday-Friday 9:00 AM - 5:00 PM)
            try:
                # Insert default call settings
                self.supabase.table("call_settings").insert({
                    "tenant_id": tenant_id,
                    "timezone": "Asia/Kuala_Lumpur",
                    "buffer_minutes": 15,
                    "max_calls_per_day": 8,
                    "max_calls_per_hour": 2,
                    "advance_booking_days": 30,
                    "allow_same_day_booking": True,
                    "created_at": datetime.now().isoformat()
                }).execute()

                # Insert default availability slots (Monday-Friday)
                default_slots = []
                for day in range(5):  # 0-4 = Monday to Friday
                    default_slots.append({
                        "tenant_id": tenant_id,
                        "day_of_week": day,
                        "start_time": "09:00",
                        "end_time": "17:00",
                        "timezone": "Asia/Kuala_Lumpur",
                        "is_active": True,
                        "created_at": datetime.now().isoformat()
                    })
                
                if default_slots:
                    self.supabase.table("call_availability").insert(default_slots).execute()
                    logger.info(f"✅ Setup default call availability for tenant: {tenant_id}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to setup default call availability for {tenant_id}: {e}")
                # Continue with tenant creation even if call availability setup fails

            logger.info(f"✅ Created tenant: {tenant_id} ({business_name})")
            return tenant_id

        except Exception as e:
            logger.error(f"Error creating tenant: {e}")
            return None

    def get_tenant_info(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tenant information.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tenant info dict or None
        """
        if not self.supabase:
            return None

        try:
            response = (
                self.supabase.table("tenants")
                .select("*")
                .eq("id", tenant_id)
                .maybe_single()
                .execute()
            )

            rdata = getattr(response, "data", None) if response else None
            return rdata if rdata else None

        except Exception as e:
            logger.error(f"Error fetching tenant info: {e}")
            return None

    def update_tenant_settings(self, tenant_id: str, settings: Dict[str, Any]) -> bool:
        """
        Update tenant settings.

        Args:
            tenant_id: Tenant identifier
            settings: Settings dict to update

        Returns:
            True if successful
        """
        if not self.supabase:
            return False

        try:
            self.supabase.table("tenants").update({"settings": settings}).eq(
                "id", tenant_id
            ).execute()

            logger.info(f"✅ Updated settings for tenant: {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating tenant settings: {e}")
            return False

    def list_tenants(
        self, status: Optional[str] = "active", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all tenants.

        Args:
            status: Filter by status (active, suspended, etc.)
            limit: Max results

        Returns:
            List of tenant dicts
        """
        if not self.supabase:
            return []

        try:
            query = self.supabase.table("tenants").select("*").limit(limit)

            if status:
                query = query.eq("status", status)

            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error listing tenants: {e}")
            return []

    def suspend_tenant(self, tenant_id: str, reason: str) -> bool:
        """
        Suspend a tenant (e.g., non-payment, abuse).

        Args:
            tenant_id: Tenant identifier
            reason: Suspension reason

        Returns:
            True if successful
        """
        if not self.supabase:
            return False

        try:
            self.supabase.table("tenants").update(
                {
                    "status": "suspended",
                    "suspension_reason": reason,
                    "suspended_at": datetime.now().isoformat(),
                }
            ).eq("id", tenant_id).execute()

            logger.warning(f"⚠️ Suspended tenant: {tenant_id} (reason: {reason})")
            return True

        except Exception as e:
            logger.error(f"Error suspending tenant: {e}")
            return False

    def reactivate_tenant(self, tenant_id: str) -> bool:
        """
        Reactivate a suspended tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if successful
        """
        if not self.supabase:
            return False

        try:
            self.supabase.table("tenants").update(
                {"status": "active", "suspension_reason": None, "suspended_at": None}
            ).eq("id", tenant_id).execute()

            logger.info(f"✅ Reactivated tenant: {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Error reactivating tenant: {e}")
            return False

    def is_tenant_active(self, tenant_id: str) -> bool:
        """
        Check if tenant is active.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if tenant is active
        """
        info = self.get_tenant_info(tenant_id)
        return info.get("status") == "active" if info else False

    def get_tenant_customers(self, tenant_id: str) -> List[str]:
        """
        Get list of customer JIDs for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of customer WhatsApp JIDs
        """
        if not self.supabase:
            return []

        try:
            response = (
                self.supabase.table("conversations")
                .select("chat_jid")
                .eq("tenant_id", tenant_id)
                .execute()
            )

            if response.data:
                # Get unique customer JIDs
                jids = set(row["chat_jid"] for row in response.data)
                return list(jids)

            return []

        except Exception as e:
            logger.error(f"Error fetching tenant customers: {e}")
            return []

    def ensure_tenant_isolation(
        self, tenant_id: str, chat_jid: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Ensure tenant can only access their own customer data.

        Args:
            tenant_id: Tenant identifier
            chat_jid: Customer chat JID

        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        if not self.enable_multi_tenant:
            return (True, None)

        # Get the tenant that owns this customer
        customers = self.get_tenant_customers(tenant_id)

        if chat_jid in customers:
            return (True, None)

        # Check if this is a new customer
        if not self.supabase:
            return (True, None)

        try:
            response = (
                self.supabase.table("conversations")
                .select("tenant_id")
                .eq("chat_jid", chat_jid)
                .limit(1)
                .execute()
            )

            if response.data:
                # Customer belongs to another tenant
                return (
                    False,
                    f"Access denied: Customer belongs to another account",
                )

            # New customer, allow
            return (True, None)

        except Exception as e:
            logger.error(f"Error checking tenant isolation: {e}")
            return (True, None)  # Fail open for availability

    def get_stats(self) -> Dict[str, Any]:
        """Get tenant manager statistics"""
        return {
            "multi_tenant_enabled": self.enable_multi_tenant,
            "default_tenant_id": self.default_tenant_id,
            "total_tenants": len(self.list_tenants()) if self.supabase else 0,
        }
