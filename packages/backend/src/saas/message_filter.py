"""
Bijou AI - Message Filter System
=================================

Intelligent message filtering for testing mode, ignore lists, and business hours.

Features:
- Testing mode: Only reply to designated test numbers
- Ignore/Private list: Never auto-reply to specific numbers
- Business hours enforcement
- Auto-reply toggle
- Welcome message management

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Version: 1.0.0
Date: 2026-02-07
"""

import logging
import os
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class MessageFilter:
    """
    Filters incoming messages based on tenant rules.

    Determines whether Bijou should auto-reply to a message based on:
    - Testing mode status
    - Ignore/private number lists
    - Business hours
    - Auto-reply enabled/disabled
    """

    def __init__(self, supabase_client=None):
        """
        Initialize message filter.

        Args:
            supabase_client: Supabase client for tenant data
        """
        self.supabase = supabase_client
        logger.info("✅ MessageFilter initialized")

    def should_reply(
        self, tenant_id: str, sender_number: str, is_first_message: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if Bijou should reply to this message.

        Args:
            tenant_id: UUID of the tenant
            sender_number: WhatsApp number of sender (without @s.whatsapp.net)
            is_first_message: Whether this is first contact from this number

        Returns:
            Tuple of (should_reply: bool, reason: str or None)
            - If should_reply is False, reason explains why
            - If should_reply is True, reason is None
        """
        try:
            # Get tenant configuration
            tenant = self._get_tenant_config(tenant_id)
            if not tenant:
                logger.warning(f"❌ Tenant {tenant_id} not found")
                return False, "Tenant not found"

            # Check 1: Auto-reply disabled
            if not tenant.get("auto_reply_enabled", False):
                logger.debug(f"🔇 Auto-reply disabled for tenant {tenant_id}")
                return False, "Auto-reply disabled by tenant"

            # Check 2: Testing mode
            if tenant.get("testing_mode", False):
                test_numbers = tenant.get("test_numbers", [])

                # Normalize sender number (remove any formatting)
                normalized_sender = self._normalize_number(sender_number)

                # Check if sender is in test numbers list
                is_test_number = any(
                    self._normalize_number(num) == normalized_sender
                    for num in test_numbers
                )

                if not is_test_number:
                    logger.debug(
                        f"🧪 Testing mode active - {sender_number} not in test list"
                    )
                    return False, "Testing mode: Not a test number"

            # Check 3: Ignore list (private numbers)
            ignore_numbers = tenant.get("ignore_numbers", []) + tenant.get(
                "private_numbers", []
            )
            normalized_sender = self._normalize_number(sender_number)

            is_ignored = any(
                self._normalize_number(num) == normalized_sender
                for num in ignore_numbers
            )

            if is_ignored:
                logger.debug(f"🚫 {sender_number} is in ignore/private list")
                return False, "Number in ignore/private list"

            # Check 4: Business hours
            business_hours = tenant.get("business_hours")
            disable_business_hours = (
                os.getenv("DISABLE_BUSINESS_HOURS", "false").lower() == "true"
            )

            # Business hours are DISABLED by default for all tenants.
            # Only block replies if: flag not overridden, enabled is EXACTLY True (not truthy),
            # and a schedule is present.
            bh_enabled = business_hours.get("enabled") if isinstance(business_hours, dict) else None
            if (not disable_business_hours and
                isinstance(business_hours, dict) and
                bh_enabled is True and
                business_hours.get("schedule")):

                is_business_hours = self._is_within_business_hours(business_hours)

                if not is_business_hours:
                    # AI stays silent outside business hours (no bot-like auto-replies)
                    # Urgent messages (escalations) bypass this in bijou.py
                    logger.debug(f"⏰ Outside business hours for tenant {tenant_id}")
                    return False, "OUTSIDE_HOURS"

            # All checks passed - should reply
            logger.debug(f"✅ Message from {sender_number} passed all filters")
            return True, None

        except Exception as e:
            logger.error(f"❌ Error in message filter: {e}", exc_info=True)
            # On error, default to allowing reply (fail-open)
            return True, None

    def get_welcome_message(self, tenant_id: str) -> Optional[str]:
        """
        Get custom welcome message for tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Welcome message text or None if not set
        """
        try:
            tenant = self._get_tenant_config(tenant_id)
            if tenant:
                return tenant.get("welcome_message")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting welcome message: {e}")
            return None

    def _get_tenant_config(self, tenant_id: str) -> Optional[Dict]:
        """
        Get tenant configuration from database.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Dict with tenant config or None if not found
        """
        try:
            if not self.supabase:
                logger.warning("No Supabase client available")
                return None

            result = (
                self.supabase.table("tenants")
                .select(
                    "id, testing_mode, test_numbers, ignore_numbers, "
                    "private_numbers, business_hours, auto_reply_enabled, "
                    "welcome_message, handover_primary"
                )
                .eq("id", tenant_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return result.data[0]

            return None

        except Exception as e:
            logger.error(f"❌ Error fetching tenant config: {e}", exc_info=True)
            return None

    def _normalize_number(self, number: str) -> str:
        """
        Normalize phone number for comparison.

        Removes spaces, dashes, plus signs, and @s.whatsapp.net suffix.

        Args:
            number: Phone number in any format

        Returns:
            Normalized number (digits only)
        """
        if not number:
            return ""

        # Remove WhatsApp suffix if present
        number = number.replace("@s.whatsapp.net", "")
        number = number.replace("@g.us", "")

        # Remove all non-digit characters
        normalized = "".join(filter(str.isdigit, number))

        return normalized

    def _is_within_business_hours(self, business_hours: Dict) -> bool:
        """
        Check if current time is within business hours.

        Args:
            business_hours: Dict with timezone and schedule

        Returns:
            True if within business hours, False otherwise
        """
        try:
            # Get timezone
            timezone_str = business_hours.get("timezone", "Asia/Kuala_Lumpur")
            tz = ZoneInfo(timezone_str)

            # Get current time in tenant's timezone
            now = datetime.now(tz)
            current_day = now.strftime("%A").lower()
            current_time = now.time()

            # Get schedule for current day
            schedule = business_hours.get("schedule", {})
            day_schedule = schedule.get(current_day, {})

            # Check if this day is enabled
            if not day_schedule.get("enabled", True):
                return False

            # Parse start and end times
            start_str = day_schedule.get("start", "09:00")
            end_str = day_schedule.get("end", "18:00")

            start_time = time.fromisoformat(start_str)
            end_time = time.fromisoformat(end_str)

            # Check if current time is within range
            if start_time <= current_time <= end_time:
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error checking business hours: {e}", exc_info=True)
            # On error, assume within business hours (fail-open)
            return True

    def update_tenant_config(
        self,
        tenant_id: str,
        testing_mode: Optional[bool] = None,
        test_numbers: Optional[List[str]] = None,
        ignore_numbers: Optional[List[str]] = None,
        auto_reply_enabled: Optional[bool] = None,
        business_hours: Optional[Dict] = None,
        welcome_message: Optional[str] = None,
    ) -> bool:
        """
        Update tenant filter configuration.

        Args:
            tenant_id: UUID of the tenant
            testing_mode: Enable/disable testing mode
            test_numbers: List of test numbers
            ignore_numbers: List of numbers to ignore
            auto_reply_enabled: Enable/disable auto-reply
            business_hours: Business hours configuration
            welcome_message: Custom welcome message

        Returns:
            True if update successful, False otherwise
        """
        try:
            if not self.supabase:
                logger.error("No Supabase client available")
                return False

            # Build update dict with only provided values
            update_data = {}

            if testing_mode is not None:
                update_data["testing_mode"] = testing_mode

            if test_numbers is not None:
                update_data["test_numbers"] = test_numbers

            if ignore_numbers is not None:
                update_data["ignore_numbers"] = ignore_numbers
                update_data["private_numbers"] = ignore_numbers  # Sync both fields

            if auto_reply_enabled is not None:
                update_data["auto_reply_enabled"] = auto_reply_enabled

            if business_hours is not None:
                update_data["business_hours"] = business_hours

            if welcome_message is not None:
                update_data["welcome_message"] = welcome_message

            if not update_data:
                logger.warning("No data provided for update")
                return False

            # Update tenant
            result = (
                self.supabase.table("tenants")
                .update(update_data)
                .eq("id", tenant_id)
                .execute()
            )

            if result.data:
                logger.info(f"✅ Updated tenant {tenant_id} filter config")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error updating tenant config: {e}", exc_info=True)
            return False

    def get_filter_status(self, tenant_id: str) -> Dict:
        """
        Get current filter status for a tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Dict with filter status information
        """
        tenant = self._get_tenant_config(tenant_id)

        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        business_hours = tenant.get("business_hours", {})
        is_business_hours = self._is_within_business_hours(business_hours)

        return {
            "success": True,
            "tenant_id": tenant_id,
            "auto_reply_enabled": tenant.get("auto_reply_enabled", True),
            "testing_mode": tenant.get("testing_mode", False),
            "test_numbers": tenant.get("test_numbers", []),
            "ignore_numbers": tenant.get("ignore_numbers", []),
            "private_numbers": tenant.get("private_numbers", []),
            "business_hours_enabled": business_hours.get("enabled", False),  # Fixed: default False not True
            "currently_within_business_hours": is_business_hours,
            "has_welcome_message": bool(tenant.get("welcome_message")),
        }

    async def check_keyword_templates(
        self,
        tenant_id: str,
        message_content: str,
    ) -> Optional[str]:
        """
        Check if the incoming message matches any active keyword-triggered template.

        Queries the ``message_templates`` table for the tenant's active templates
        that have ``trigger_keywords`` defined.  Matching is case-insensitive and
        checks whether any keyword appears as a whole word (or substring) in the
        message.

        Args:
            tenant_id: UUID of the owning tenant.
            message_content: The raw incoming message text.

        Returns:
            The template body string if a keyword match is found, else ``None``.
        """
        if not tenant_id or not message_content:
            return None

        try:
            result = (
                self.supabase.table("message_templates")
                .select("trigger_keywords, template_content")
                .eq("tenant_id", tenant_id)
                .eq("is_active", True)
                .eq("trigger_mode", "keyword_auto")
                .execute()
            )

            templates = result.data if result.data else []
            if not templates:
                return None

            message_lower = message_content.lower().strip()

            for template in templates:
                keywords = template.get("trigger_keywords") or []
                body = template.get("template_content", "")

                if not keywords or not body:
                    continue

                for keyword in keywords:
                    if not keyword:
                        continue
                    if keyword.lower() in message_lower:
                        logger.info(
                            f"🎯 Keyword template matched keyword='{keyword}' "
                            f"for tenant {tenant_id}"
                        )
                        return body

            return None

        except Exception as exc:
            logger.warning(
                f"⚠️ check_keyword_templates failed (non-fatal) "
                f"for tenant {tenant_id}: {exc}"
            )
            return None
