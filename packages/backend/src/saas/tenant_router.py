"""
Bijou AI - Tenant Router (Phase 2)
===================================

Routes incoming WhatsApp messages to the correct tenant context.

Features:
- Phone number to tenant mapping
- Tenant identification from messages
- Context isolation enforcement
- Usage tracking and limits
- Tenant status validation

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-01-30
"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TenantRouter:
    """
    Routes messages to correct tenant and enforces isolation.

    Central component for multi-tenant message processing.
    Identifies tenant from phone number and sets context.
    """

    def __init__(self, supabase_client=None, tenant_manager=None):
        """
        Initialize tenant router.

        Args:
            supabase_client: Supabase client for database operations
            tenant_manager: TenantManager instance for tenant operations
        """
        # If no Supabase client provided, try to create one
        if supabase_client is None:
            try:
                from supabase import Client, create_client

                # Check for multiple possible env variable names
                supabase_url = os.getenv("SUPABASE_URL") or os.getenv(
                    "NEXT_PUBLIC_SUPABASE_URL"
                )
                supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv(
                    "SUPABASE_SERVICE_ROLE_KEY"
                )

                if supabase_url and supabase_key:
                    supabase_client = create_client(supabase_url, supabase_key)
                    logger.info("✅ Auto-initialized Supabase client")
                else:
                    logger.warning(
                        f"⚠️ Missing Supabase credentials: URL={bool(supabase_url)}, KEY={bool(supabase_key)}"
                    )
            except Exception as e:
                logger.warning(f"⚠️ Could not auto-initialize Supabase: {e}")

        self.supabase = supabase_client
        self.tenant_manager = tenant_manager

        # Enable/disable multi-tenant routing
        self.multi_tenant_enabled = (
            os.getenv("ENABLE_MULTI_TENANT", "false").lower() == "true"
        )

        # Default tenant (for single-tenant mode)
        self.default_tenant_id = os.getenv(
            "DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"
        )
        
        # Demo tenant for unregistered numbers (allows demo experience)
        # Set DEMO_TENANT_ID to enable demo mode for unknown numbers
        self.demo_tenant_id = os.getenv("DEMO_TENANT_ID")
        self.demo_tenant_enabled = (
            os.getenv("ENABLE_DEMO_TENANT", "false").lower() == "true"
        )

        # Cache for tenant lookups (phone -> tenant_id)
        self._tenant_cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps = {}

        logger.info(
            f"✅ TenantRouter initialized (multi_tenant={self.multi_tenant_enabled}, demo_tenant={self.demo_tenant_enabled})"
        )

    async def route_message(
        self, message: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """
        Route incoming message to correct tenant.

        Args:
            message: Webhook message dict with chat_jid, sender, content, etc.

        Returns:
            Tuple of (tenant_id, tenant_config, error_message)
        """
        # Extract phone number from message
        chat_jid = message.get("chat_jid", "")
        sender = message.get("sender", "")
        business_jid = message.get("business_jid", "")

        # If multi-tenant disabled, use default tenant
        if not self.multi_tenant_enabled:
            logger.debug(f"🔀 Multi-tenant disabled, using default tenant")
            return (self.default_tenant_id, None, None)

        # Identify tenant from phone number
        tenant_id = await self.identify_tenant(chat_jid, sender, business_jid)

        if not tenant_id:
            error_msg = f"❌ Could not identify tenant for {chat_jid}"
            logger.error(error_msg)
            return (None, None, error_msg)

        # Validate tenant is active
        is_valid, validation_error = await self.validate_tenant(tenant_id)
        if not is_valid:
            return (None, None, validation_error)

        # Load tenant configuration
        tenant_config = await self.load_tenant_config(tenant_id)

        # Check usage limits
        within_limits, limit_error = await self.check_usage_limits(tenant_id)
        if not within_limits:
            return (tenant_id, tenant_config, limit_error)

        # Track usage
        await self.track_message(tenant_id, message)

        logger.info(
            f"🏢 Routed message to tenant: {tenant_config.get('name', tenant_id)} "
            f"({tenant_config.get('business_name', 'unknown')})"
        )

        return (tenant_id, tenant_config, None)

    async def identify_tenant(
        self, chat_jid: str, sender: str, business_jid: str = None, device_id: str = None
    ) -> Optional[str]:
        """
        Identify tenant from phone number.

        Checks:
        1. Cache (fast path)
        2. Database lookup by phone number
        3. Default tenant fallback

        Args:
            chat_jid: Chat JID (could be group or individual or LID)
            sender: Sender JID (actual phone number - customer's phone)
            business_jid: Business WhatsApp JID (for group messages)
            device_id: Device ID from bridge (business WhatsApp account - PRIORITY for tenant routing)

        Returns:
            Tenant ID or None
        """
        # Detect if this is a group message or LID (linked device)
        is_group = "@lid" in chat_jid or "@g.us" in chat_jid
        
        # ✅ CRITICAL FIX: Tenant routing priority order
        # 1. device_id (business WhatsApp account from bridge) - HIGHEST PRIORITY
        # 2. business_jid (for group messages)
        # 3. sender (customer phone - fallback, but this finds CUSTOMER's tenant, not business!)
        #
        # PROBLEM: Using sender (customer phone) routes to wrong tenant because customer
        # phone numbers aren't registered as tenants - only business WhatsApp accounts are!
        #
        # SOLUTION: Always use device_id first (the business account receiving the message)
        if device_id:
            lookup_jid = device_id
            logger.debug(f"🎯 Using device_id for tenant lookup: {device_id}")
        elif is_group and business_jid:
            lookup_jid = business_jid
            logger.debug(f"👥 Using business_jid for group message: {business_jid}")
        elif sender:
            lookup_jid = sender
            logger.debug(f"📱 Using sender as fallback: {sender}")
        else:
            lookup_jid = chat_jid
            logger.debug(f"💬 Using chat_jid as last resort: {chat_jid}")

        # Debug logging
        logger.debug(
            f"🔍 Tenant lookup - chat_jid={chat_jid}, sender={sender}, "
            f"business_jid={business_jid}, device_id={device_id}, is_group={is_group}, lookup_jid={lookup_jid}"
        )

        # Try cache first
        cache_key = self._get_cache_key(lookup_jid)
        cached_tenant = self._get_from_cache(cache_key)
        if cached_tenant:
            logger.debug(f"🎯 Tenant found in cache: {cached_tenant}")
            return cached_tenant

        # 🔥 CRITICAL FIX: Multi-tenant WhatsApp routing with GOWA bridge
        # GOWA webhooks send device_id as WhatsApp JID (e.g., "60174106981@s.whatsapp.net")
        # instead of our custom device_id ("bijou-{tenant_id}").
        # Solution: Lookup device in whatsapp_devices table by whatsapp_jid first.
        if device_id and self.supabase:
            try:
                # Normalize device_id to JID format
                normalized_jid = device_id if "@s.whatsapp.net" in device_id else f"{device_id.replace('+', '')}@s.whatsapp.net"
                
                logger.debug(f"🔍 Looking up tenant via whatsapp_devices.whatsapp_jid: {normalized_jid}")
                
                device_response = (
                    self.supabase.table("whatsapp_devices")
                    .select("tenant_id, device_id")
                    .eq("whatsapp_jid", normalized_jid)
                    .order("created_at", desc=True)  # Most recent if multiple exist
                    .limit(1)
                    .execute()
                )
                
                if device_response.data and len(device_response.data) > 0:
                    tenant_id = device_response.data[0]["tenant_id"]
                    device_custom_id = device_response.data[0]["device_id"]
                    
                    logger.info(
                        f"✅ Tenant identified from whatsapp_devices: {tenant_id} "
                        f"(device: {device_custom_id}, whatsapp_jid: {normalized_jid})"
                    )
                    
                    # Cache the result
                    self._set_cache(cache_key, tenant_id)
                    return tenant_id
                else:
                    logger.debug(f"🔍 No device found in whatsapp_devices for JID {normalized_jid}, falling back to tenant lookup")
            except Exception as e:
                logger.error(f"❌ Error looking up device by whatsapp_jid: {e}")
                # Fall through to existing tenant lookup logic

        # Extract phone number (remove @s.whatsapp.net suffix)
        phone = self._normalize_phone(lookup_jid)

        if not self.supabase:
            logger.warning("⚠️ No Supabase client, using default tenant")
            return self.default_tenant_id

        try:
            # Look up tenant by phone number (try whatsapp_jid first, then fall back to phone)
            # Try multiple JID format variations to handle device suffixes
            
            # Extract base phone without device suffix (e.g., "60174106981" from "60174106981:25@s.whatsapp.net")
            base_phone = phone.lstrip("+")  # Remove + prefix
            
            # Build list of JID variations to try
            jid_variations = [
                lookup_jid,  # Original JID with device suffix (e.g., "60174106981:25@s.whatsapp.net")
                f"{base_phone}@s.whatsapp.net",  # Without + prefix, no device suffix
                f"{phone}@s.whatsapp.net",  # With + prefix, no device suffix
            ]
            
            # Try each JID variation
            response = None
            for jid_variant in jid_variations:
                response = (
                    self.supabase.table("tenants")
                    .select("id, name, business_name, status")
                    .eq("whatsapp_jid", jid_variant)
                    .execute()
                )
                
                if response.data:
                    logger.debug(f"✅ Found tenant using JID variant: {jid_variant}")
                    break

            # If not found by whatsapp_jid, try phone field
            if not response or not response.data:
                response = (
                    self.supabase.table("tenants")
                    .select("id, name, business_name, status")
                    .eq("phone", phone)
                    .execute()
                )

            # Get first result if multiple found
            if response.data:
                response.data = (
                    response.data[0]
                    if isinstance(response.data, list)
                    else response.data
                )

            if response.data and (
                isinstance(response.data, dict) or len(response.data) > 0
            ):
                tenant_id = (
                    response.data["id"]
                    if isinstance(response.data, dict)
                    else response.data[0]["id"]
                )

                # Cache the result
                self._set_cache(cache_key, tenant_id)

                tenant_name = (
                    response.data["name"]
                    if isinstance(response.data, dict)
                    else response.data[0]["name"]
                )
                tenant_type = (
                    response.data.get("business_name", "general")
                    if isinstance(response.data, dict)
                    else response.data[0].get("business_name", "general")
                )
                logger.info(
                    f"🔍 Identified tenant: {tenant_name} "
                    f"(type: {tenant_type}) from phone: {phone}"
                )

                # Opportunistically record the device JID so future messages
                # use the fast whatsapp_devices path instead of this fallback.
                # Only write when business_jid is available (old bridge sends it).
                if business_jid:
                    _norm_jid = re.sub(r":(\d+)@", "@", business_jid)
                    await self._upsert_device(
                        tenant_id=tenant_id,
                        whatsapp_jid=_norm_jid,
                        business_jid_raw=business_jid,
                    )

                return tenant_id

            # No tenant found, check if this is a customer JID
            # (might belong to an existing tenant's customer)
            tenant_id = await self._identify_from_customer(chat_jid)
            if tenant_id:
                return tenant_id

            # In multi-tenant mode with demo tenant enabled, use demo tenant for unknown numbers
            # This allows people to try Bijou without full onboarding
            if self.multi_tenant_enabled and self.demo_tenant_enabled and self.demo_tenant_id:
                logger.info(
                    f"🎮 No tenant mapping found for phone {phone}. "
                    f"Using DEMO tenant: {self.demo_tenant_id}"
                )
                # Cache this so subsequent messages also go to demo tenant
                self._set_cache(cache_key, self.demo_tenant_id)
                return self.demo_tenant_id
            
            # In multi-tenant mode without demo, do NOT silently fall back to default tenant.
            # This prevents one tenant's customers from leaking into another tenant's inbox.
            if self.multi_tenant_enabled:
                logger.warning(
                    f"⚠️ No tenant mapping found for phone {phone} in multi-tenant mode. "
                    f"Message will not be assigned to a tenant until onboarding is complete."
                )
                return None

            # Single-tenant / legacy mode: safe to use default tenant
            logger.warning(
                f"⚠️ No tenant found for {phone}, using default tenant (single-tenant mode)"
            )
            return self.default_tenant_id

        except Exception as e:
            logger.error(f"❌ Error identifying tenant: {e}")
            # In multi-tenant mode, avoid unsafe fallback on unexpected errors
            if self.multi_tenant_enabled:
                return None
            return self.default_tenant_id

    async def _identify_from_customer(self, chat_jid: str) -> Optional[str]:
        """
        Try to identify tenant from existing customer conversations.

        Args:
            chat_jid: Customer's chat JID

        Returns:
            Tenant ID or None
        """
        if not self.supabase:
            return None

        try:
            # Look for existing conversations with this customer
            response = (
                self.supabase.table("conversations")
                .select("tenant_id")
                .eq("chat_jid", chat_jid)
                .limit(1)
                .execute()
            )

            if response.data and response.data[0].get("tenant_id"):
                tenant_id = response.data[0]["tenant_id"]
                logger.info(f"🔍 Identified tenant from existing customer: {tenant_id}")
                return tenant_id

            return None

        except Exception as e:
            logger.error(f"❌ Error identifying from customer: {e}")
            return None

    async def validate_tenant(self, tenant_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate tenant is active and in good standing.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.supabase:
            return (True, None)  # Fail open if no database

        try:
            response = (
                self.supabase.table("tenants")
                .select("status, subscription_tier, trial_ends_at")
                .eq("id", tenant_id)
                .maybe_single()
                .execute()
            )

            rdata = getattr(response, "data", None) if response else None
            if not rdata:
                return (False, "Tenant not found")

            status = rdata.get("status", "")

            # Check if tenant is active
            if status == "suspended":
                return (
                    False,
                    "⚠️ Account suspended. Please contact support to reactivate.",
                )

            if status == "cancelled":
                return (False, "❌ Account cancelled. Please resubscribe to continue.")

            # Check trial expiration
            if status == "trial":
                trial_ends = response.data.get("trial_ends_at")
                if trial_ends:
                    from datetime import datetime

                    trial_end_date = datetime.fromisoformat(
                        trial_ends.replace("Z", "+00:00")
                    )
                    if datetime.now() > trial_end_date:
                        return (
                            False,
                            "⏰ Free trial expired. Please upgrade to continue.",
                        )

            return (True, None)

        except Exception as e:
            logger.error(f"❌ Error validating tenant: {e}")
            # Fail open for availability
            return (True, None)

    async def load_tenant_config(self, tenant_id: str) -> Dict[str, Any]:
        """
        Load tenant configuration and settings.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tenant config dict
        """
        if not self.supabase:
            return {"id": tenant_id, "name": "Default Tenant"}

        try:
            response = (
                self.supabase.table("tenants")
                .select("*")
                .eq("id", tenant_id)
                .maybe_single()
                .execute()
            )

            rdata = getattr(response, "data", None) if response else None
            if rdata:
                return rdata

            return {"id": tenant_id}

        except Exception as e:
            logger.error(f"❌ Error loading tenant config: {e}")
            return {"id": tenant_id}

    async def check_usage_limits(self, tenant_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant is within usage limits.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tuple of (within_limits, error_message)
        """
        if not self.supabase:
            return (True, None)

        try:
            response = (
                self.supabase.table("tenants")
                .select(
                    "monthly_message_limit, current_month_messages, subscription_tier"
                )
                .eq("id", tenant_id)
                .maybe_single()
                .execute()
            )

            rdata = getattr(response, "data", None) if response else None
            if not rdata:
                return (True, None)

            limit = rdata.get("monthly_message_limit", 1000)
            current = rdata.get("current_month_messages", 0)
            tier = rdata.get("subscription_tier", "starter")

            # Check if limit reached
            if current >= limit:
                logger.warning(
                    f"⚠️ Tenant {tenant_id} reached message limit ({current}/{limit})"
                )

                return (
                    False,
                    f"📊 Monthly message limit reached ({current}/{limit}). "
                    f"Please upgrade your plan to continue.",
                )

            # Warn if approaching limit (90%)
            if current >= (limit * 0.9):
                logger.warning(
                    f"⚠️ Tenant {tenant_id} approaching limit "
                    f"({current}/{limit} - {(current / limit) * 100:.1f}%)"
                )

            return (True, None)

        except Exception as e:
            logger.error(f"❌ Error checking usage limits: {e}")
            return (True, None)  # Fail open

    async def track_message(self, tenant_id: str, message: Dict[str, Any]) -> None:
        """
        Track message usage for tenant.

        Updates current_month_messages counter.

        Args:
            tenant_id: Tenant identifier
            message: Message dict
        """
        if not self.supabase:
            return

        try:
            # Increment message counter
            await self.supabase.rpc(
                "increment_tenant_messages", {"p_tenant_id": tenant_id}
            ).execute()

            logger.debug(f"📊 Tracked message for tenant: {tenant_id}")

        except Exception as e:
            # Non-critical, just log
            logger.warning(f"⚠️ Could not track message usage: {e}")

    def _normalize_phone(self, jid: str) -> str:
        """
        Normalize phone number from JID.

        Args:
            jid: WhatsApp JID (e.g., "+60123456789@s.whatsapp.net" or "60123456789:2@s.whatsapp.net")

        Returns:
            Normalized phone (e.g., "+60123456789")
        """
        # Remove @s.whatsapp.net or @lid suffix
        phone = jid.split("@")[0]

        # ✅ FIX: Remove device suffix (e.g., :2, :21 from linked devices)
        # WhatsApp uses :N suffix for multi-device (WhatsApp Web/Desktop)
        if ":" in phone:
            phone = phone.split(":")[0]

        # Ensure it starts with +
        if not phone.startswith("+"):
            phone = "+" + phone

        return phone

    def _get_cache_key(self, jid: str) -> str:
        """Generate cache key from JID"""
        return f"tenant:{self._normalize_phone(jid)}"

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Get tenant ID from cache if not expired"""
        if key not in self._tenant_cache:
            return None

        # Check if expired
        timestamp = self._cache_timestamps.get(key, 0)
        age = datetime.now().timestamp() - timestamp

        if age > self._cache_ttl:
            # Expired, remove from cache
            del self._tenant_cache[key]
            del self._cache_timestamps[key]
            return None

        return self._tenant_cache[key]

    def _set_cache(self, key: str, tenant_id: str) -> None:
        """Set tenant ID in cache"""
        self._tenant_cache[key] = tenant_id
        self._cache_timestamps[key] = datetime.now().timestamp()

    def get_tenant_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Get tenant by phone number (sync). Used by process_message for routing.

        Queries Supabase tenants table. Supports multiple schema variants:
        - phone_number (phase2 migration)
        - whatsapp_jid, owner_phone (main schema)

        Args:
            phone: Normalized phone (e.g. +60123456789).

        Returns:
            Tenant dict with id, name, etc. or None. Falls back to default tenant.
        """
        phone = self._normalize_phone(phone) if "@" in phone else phone
        if not phone.startswith("+"):
            phone = "+" + phone

        # Try cache first
        cache_key = self._get_cache_key(phone)
        cached_id = self._get_from_cache(cache_key)
        if cached_id:
            return {"id": cached_id, "name": "Cached Tenant"}

        if not self.supabase:
            return {
                "id": self.default_tenant_id,
                "name": "Default Tenant",
            }

        try:
            # Try phone_number (phase2 schema)
            try:
                response = (
                    self.supabase.table("tenants")
                    .select("id, name, business_name, status")
                    .eq("phone_number", phone)
                    .limit(1)
                    .execute()
                )
                if response.data and len(response.data) > 0:
                    row = response.data[0]
                    self._set_cache(cache_key, row["id"])
                    return dict(row)
            except Exception as col_err:
                logger.debug(f"Column 'phone_number' may not exist in tenants table: {col_err}")

            # Try whatsapp_jid or owner_phone (main schema)
            for col, val in [
                ("whatsapp_jid", phone),
                ("whatsapp_jid", f"{phone}@s.whatsapp.net"),
                ("owner_phone", phone),
            ]:
                try:
                    r = (
                        self.supabase.table("tenants")
                        .select("id, name")
                        .eq(col, val)
                        .limit(1)
                        .execute()
                    )
                    if r.data and len(r.data) > 0:
                        row = r.data[0]
                        self._set_cache(cache_key, row["id"])
                        return dict(row)
                except Exception as col_scan_err:
                    logger.debug(f"Column '{col}' lookup failed for tenant phone {phone}: {col_scan_err}")

            logger.warning(f"⚠️ No tenant found for {phone}, using default tenant")
            return {
                "id": self.default_tenant_id,
                "name": "Default Tenant",
            }

        except Exception as e:
            logger.error(f"❌ get_tenant_by_phone error: {e}")
            return {
                "id": self.default_tenant_id,
                "name": "Default Tenant",
            }

    def clear_cache(self) -> None:
        """Clear tenant cache"""
        self._tenant_cache.clear()
        self._cache_timestamps.clear()
        logger.info("🗑️ Tenant cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return {
            "multi_tenant_enabled": self.multi_tenant_enabled,
            "default_tenant_id": self.default_tenant_id,
            "cache_size": len(self._tenant_cache),
            "cache_ttl": self._cache_ttl,
        }

    async def get_tenant_id_by_identifier(self, identifier: str) -> Optional[str]:
        """
        Get tenant ID by WhatsApp phone number or Telegram username.

        Args:
            identifier: WhatsApp phone (starts with '+') or Telegram handle (alphanumeric)

        Returns:
            Tenant ID or None if not found
        """
        if not self.supabase:
            logger.error("❌ No Supabase client available")
            return None

        try:
            # Determine if identifier is WhatsApp (starts with +) or Telegram
            if identifier.startswith("+"):
                # WhatsApp lookup
                response = (
                    self.supabase.table("tenants")
                    .select("id")
                    .eq("whatsapp_number", identifier)
                    .limit(1)
                    .execute()
                )
            else:
                # Telegram lookup
                response = (
                    self.supabase.table("tenants")
                    .select("id")
                    .eq("telegram_username", identifier)
                    .limit(1)
                    .execute()
                )

            if response.data and len(response.data) > 0:
                tenant_id = response.data[0]["id"]
                logger.info(f"🔍 Found tenant {tenant_id} for identifier: {identifier}")
                return tenant_id
            else:
                logger.warning(f"⚠️ No tenant found for identifier: {identifier}")
                return None

        except Exception as e:
            logger.error(
                f"❌ Error looking up tenant by identifier '{identifier}': {e}"
            )
            return None

    async def get_client_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get client configuration for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict with client config or None if not found
        """
        if not self.supabase:
            logger.error("❌ No Supabase client available")
            return None

        try:
            # Fetch client config from client_configs table
            response = (
                self.supabase.table("client_configs")
                .select("*")
                .eq("tenant_id", tenant_id)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                config = response.data[0]
                # Extract business_name from system_prompt_vars if it exists
                system_vars = config.get("system_prompt_vars", {})
                if isinstance(system_vars, dict):
                    config["business_name"] = system_vars.get(
                        "business_name", "Unknown"
                    )

                logger.info(
                    f"📋 Loaded config for tenant {tenant_id}: "
                    f"{config.get('business_name', 'Unknown')}"
                )
                return config
            else:
                logger.warning(f"⚠️ No client config found for tenant: {tenant_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Error loading client config for {tenant_id}: {e}")
            return None

    async def _upsert_device(
        self,
        tenant_id: str,
        whatsapp_jid: str,
        business_jid_raw: Optional[str] = None,
    ) -> None:
        """
        Ensure the resolved device JID is persisted in `whatsapp_devices`.

        Called opportunistically after a successful tenant identification so that
        newly seen devices (e.g. after a re-pair or number change) are recorded
        without requiring manual intervention.

        Uses an upsert on `whatsapp_jid` to avoid duplicate rows.  All failures
        are swallowed and logged — this is a best-effort write, never blocking.

        Args:
            tenant_id:        Tenant UUID that owns the device.
            whatsapp_jid:     Normalized device JID (no :N suffix), e.g.
                              ``60174106981@s.whatsapp.net``.
            business_jid_raw: Optional raw value from bridge payload (stored for
                              diagnostics, not used for lookups).
        """
        if not self.supabase or not tenant_id or not whatsapp_jid:
            return

        try:
            self.supabase.table("whatsapp_devices").upsert(
                {
                    "tenant_id": tenant_id,
                    "whatsapp_jid": whatsapp_jid,
                    # Store the raw business_jid for diagnostics / audit trail.
                    # business_jid_raw may be None for calls via the old lookup path.
                    **({"notes": f"raw:{business_jid_raw}"} if business_jid_raw else {}),
                },
                on_conflict="whatsapp_jid",
            ).execute()
            logger.debug(
                f"_upsert_device: upserted {whatsapp_jid} → tenant {tenant_id}"
            )
        except Exception as exc:
            # Non-fatal — never break message processing over a bookkeeping write.
            logger.warning(f"_upsert_device: failed to upsert {whatsapp_jid}: {exc}")
