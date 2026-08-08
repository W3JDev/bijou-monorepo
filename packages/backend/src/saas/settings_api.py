"""
Bijou AI - Tenant Settings Management API
==========================================

REST API endpoints for tenant configuration and settings.

Endpoints:
- PUT /api/settings/testing-mode - Toggle testing mode
- PUT /api/settings/ignore-list - Update ignore/private numbers
- PUT /api/settings/business-hours - Update business hours
- PUT /api/settings/auto-reply - Toggle auto-reply

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Version: 1.0.0
Date: 2026-02-07
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, validator

from supabase import create_client

from src.core.dashboard_api_simple import verify_session

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/settings", tags=["settings"])


# ════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════


def get_supabase():
    """Get Supabase admin client"""
    supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip('"')

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

    return create_client(supabase_url, supabase_key)


# ════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════


class TestingModeRequest(BaseModel):
    """Toggle testing mode and set test numbers"""

    testing_mode: bool
    test_numbers: List[str] = []

    @validator("test_numbers")
    def validate_test_numbers(cls, v):
        """Validate phone numbers"""
        validated = []
        for num in v:
            # Remove whitespace
            cleaned = num.strip()
            if cleaned:
                # Ensure it starts with +
                if not cleaned.startswith("+"):
                    cleaned = "+" + cleaned
                validated.append(cleaned)
        return validated


class TestingModeResponse(BaseModel):
    """Response after updating testing mode"""

    success: bool
    tenant_id: str
    testing_mode: bool
    test_numbers: List[str]
    message: str


class IgnoreListRequest(BaseModel):
    """Update ignore/private number list"""

    ignore_numbers: List[str] = []
    private_numbers: List[str] = []

    @validator("ignore_numbers", "private_numbers")
    def validate_numbers(cls, v):
        """Validate phone numbers"""
        validated = []
        for num in v:
            cleaned = num.strip()
            if cleaned:
                if not cleaned.startswith("+"):
                    cleaned = "+" + cleaned
                validated.append(cleaned)
        return validated


class IgnoreListResponse(BaseModel):
    """Response after updating ignore list"""

    success: bool
    tenant_id: str
    ignore_numbers: List[str]
    private_numbers: List[str]
    total_ignored: int
    message: str


class BusinessHoursSchedule(BaseModel):
    """Daily schedule"""

    start: str  # "09:00"
    end: str  # "18:00"
    enabled: bool


class BusinessHoursRequest(BaseModel):
    """Update business hours configuration"""

    enabled: bool = False  # Default OFF — tenants must explicitly enable
    timezone: str = "Asia/Kuala_Lumpur"
    schedule: Dict[str, BusinessHoursSchedule]
    out_of_hours_message: Optional[str] = None

    @validator("schedule")
    def validate_schedule(cls, v):
        """Validate schedule has all weekdays"""
        required_days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        for day in required_days:
            if day not in v:
                raise ValueError(f"Missing schedule for {day}")
        return v


class BusinessHoursResponse(BaseModel):
    """Response after updating business hours"""

    success: bool
    tenant_id: str
    business_hours: dict
    message: str


class AutoReplyRequest(BaseModel):
    """Toggle auto-reply"""

    auto_reply_enabled: bool
    welcome_message: Optional[str] = None
    manglish_mode: Optional[bool] = None


class AutoReplyResponse(BaseModel):
    """Response after updating auto-reply"""

    success: bool
    tenant_id: str
    auto_reply_enabled: bool
    welcome_message: Optional[str]
    manglish_mode: Optional[bool] = None
    message: str


# ════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ════════════════════════════════════════════════════════════════


@router.put("/testing-mode", response_model=TestingModeResponse)
async def update_testing_mode(
    request: TestingModeRequest, tenant_id: str = Depends(verify_session)
):
    """
    Toggle testing mode and set test numbers.

    When testing mode is enabled, Bijou will ONLY reply to numbers in test_numbers list.
    This protects production users during testing.

    Headers:
        X-Tenant-ID: Tenant UUID

    Body:
        testing_mode: true/false
        test_numbers: Array of phone numbers (e.g., ["+60143856929"])

    Returns:
        TestingModeResponse with updated settings
    """
    try:
        logger.info(
            f"🧪 Updating testing mode for tenant {tenant_id}: {request.testing_mode}"
        )

        supabase = get_supabase()

        # Validate tenant exists
        tenant_result = (
            supabase.table("tenants").select("id").eq("id", tenant_id).execute()
        )
        if not tenant_result.data:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        # Update tenant settings
        update_data = {
            "testing_mode": request.testing_mode,
            "test_numbers": request.test_numbers,
        }

        result = (
            supabase.table("tenants").update(update_data).eq("id", tenant_id).execute()
        )

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update testing mode")

        logger.info(
            f"✅ Testing mode updated: {request.testing_mode}, {len(request.test_numbers)} test numbers"
        )

        return TestingModeResponse(
            success=True,
            tenant_id=tenant_id,
            testing_mode=request.testing_mode,
            test_numbers=request.test_numbers,
            message=f"Testing mode {'enabled' if request.testing_mode else 'disabled'}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating testing mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")


@router.put("/ignore-list", response_model=IgnoreListResponse)
async def update_ignore_list(
    request: IgnoreListRequest, tenant_id: str = Depends(verify_session)
):
    """
    Update ignore/private number lists.

    Numbers in these lists will NEVER receive auto-replies from Bijou.
    Use this to exclude owner's personal number, test numbers, or VIP contacts.

    Headers:
        X-Tenant-ID: Tenant UUID

    Body:
        ignore_numbers: Array of numbers to ignore
        private_numbers: Array of private numbers (alias for ignore)

    Returns:
        IgnoreListResponse with updated lists
    """
    try:
        logger.info(
            f"🚫 Updating ignore list for tenant {tenant_id}: {len(request.ignore_numbers)} ignored, {len(request.private_numbers)} private"
        )

        supabase = get_supabase()

        # Validate tenant exists
        tenant_result = (
            supabase.table("tenants").select("id").eq("id", tenant_id).execute()
        )
        if not tenant_result.data:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        # Update tenant settings
        update_data = {
            "ignore_numbers": request.ignore_numbers,
            "private_numbers": request.private_numbers,
        }

        result = (
            supabase.table("tenants").update(update_data).eq("id", tenant_id).execute()
        )

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update ignore list")

        total_ignored = len(request.ignore_numbers) + len(request.private_numbers)

        logger.info(f"✅ Ignore list updated: {total_ignored} total numbers")

        return IgnoreListResponse(
            success=True,
            tenant_id=tenant_id,
            ignore_numbers=request.ignore_numbers,
            private_numbers=request.private_numbers,
            total_ignored=total_ignored,
            message=f"Ignore list updated: {total_ignored} numbers will be ignored",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating ignore list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")


@router.put("/business-hours", response_model=BusinessHoursResponse)
async def update_business_hours(
    request: BusinessHoursRequest, tenant_id: str = Depends(verify_session)
):
    """
    Update business hours configuration.

    When enabled, Bijou will only auto-reply during specified business hours.
    Outside hours, a custom out-of-hours message is sent (if provided).

    Headers:
        X-Tenant-ID: Tenant UUID

    Body:
        enabled: true/false
        timezone: Timezone string (e.g., "Asia/Kuala_Lumpur")
        schedule: Object with daily schedules
        out_of_hours_message: Custom message for outside hours

    Returns:
        BusinessHoursResponse with updated configuration
    """
    try:
        logger.info(
            f"⏰ Updating business hours for tenant {tenant_id}: {request.enabled}"
        )

        supabase = get_supabase()

        # Validate tenant exists
        tenant_result = (
            supabase.table("tenants").select("id").eq("id", tenant_id).execute()
        )
        if not tenant_result.data:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        # Convert schedule to dict for JSON storage
        schedule_dict = {}
        for day, schedule in request.schedule.items():
            schedule_dict[day] = {
                "start": schedule.start,
                "end": schedule.end,
                "enabled": schedule.enabled,
            }

        # Build business hours config
        business_hours_config = {
            "enabled": request.enabled,
            "timezone": request.timezone,
            "schedule": schedule_dict,
        }

        if request.out_of_hours_message:
            business_hours_config["out_of_hours_message"] = request.out_of_hours_message

        # Update tenant settings
        update_data = {"business_hours": business_hours_config}

        result = (
            supabase.table("tenants").update(update_data).eq("id", tenant_id).execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=500, detail="Failed to update business hours"
            )

        logger.info(f"✅ Business hours updated: {request.enabled}")

        return BusinessHoursResponse(
            success=True,
            tenant_id=tenant_id,
            business_hours=business_hours_config,
            message=f"Business hours {'enabled' if request.enabled else 'disabled'}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating business hours: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")


@router.put("/auto-reply", response_model=AutoReplyResponse)
async def update_auto_reply(
    request: AutoReplyRequest, tenant_id: str = Depends(verify_session)
):
    """
    Toggle auto-reply and set welcome message.

    When auto-reply is disabled, Bijou will NOT respond to any messages.
    Use this to temporarily pause the AI assistant.

    Headers:
        X-Tenant-ID: Tenant UUID

    Body:
        auto_reply_enabled: true/false
        welcome_message: Optional custom welcome message

    Returns:
        AutoReplyResponse with updated settings
    """
    try:
        logger.info(
            f"🔔 Updating auto-reply for tenant {tenant_id}: {request.auto_reply_enabled}"
        )

        supabase = get_supabase()

        # Validate tenant exists
        tenant_result = (
            supabase.table("tenants").select("id").eq("id", tenant_id).execute()
        )
        if not tenant_result.data:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        # Update tenant settings
        update_data = {"auto_reply_enabled": request.auto_reply_enabled}

        if request.welcome_message is not None:
            update_data["welcome_message"] = request.welcome_message

        if request.manglish_mode is not None:
            update_data["manglish_mode"] = request.manglish_mode

        result = (
            supabase.table("tenants").update(update_data).eq("id", tenant_id).execute()
        )

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update auto-reply")

        logger.info(f"✅ Auto-reply updated: {request.auto_reply_enabled}, manglish_mode={request.manglish_mode}")

        return AutoReplyResponse(
            success=True,
            tenant_id=tenant_id,
            auto_reply_enabled=request.auto_reply_enabled,
            welcome_message=request.welcome_message,
            manglish_mode=request.manglish_mode,
            message=f"Auto-reply {'enabled' if request.auto_reply_enabled else 'disabled'}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating auto-reply: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")


# ════════════════════════════════════════════════════════════════
# GET CURRENT SETTINGS
# ════════════════════════════════════════════════════════════════


@router.get("/current")
async def get_current_settings(
    resolved_tenant_id: str = Depends(verify_session),
) -> Dict[str, Any]:
    """
    Fetch the current settings for a tenant.

    Authentication:
        The tenant is resolved from the authenticated session (Supabase JWT or
        legacy magic-link token) — callers cannot supply or override the tenant
        identity via header or query param.

    Returns all configurable settings with safe defaults where values are null.
    """
    try:
        logger.info(f"⚙️ Fetching current settings for tenant {resolved_tenant_id}")

        supabase = get_supabase()

        # Try to fetch including manglish_mode; fall back if column doesn't exist yet
        manglish_mode_val = False
        try:
            result = (
                supabase.table("tenants")
                .select(
                    "id, auto_reply_enabled, welcome_message, manglish_mode, "
                    "testing_mode, test_numbers, business_hours, ignore_numbers, private_numbers"
                )
                .eq("id", resolved_tenant_id)
                .execute()
            )
            if result.data:
                manglish_mode_val = result.data[0].get("manglish_mode", False) or False
        except Exception:
            # manglish_mode column missing — fall back to query without it
            result = (
                supabase.table("tenants")
                .select(
                    "id, auto_reply_enabled, welcome_message, "
                    "testing_mode, test_numbers, business_hours, ignore_numbers, private_numbers"
                )
                .eq("id", resolved_tenant_id)
                .execute()
            )

        if not result.data:
            raise HTTPException(
                status_code=404, detail=f"Tenant {resolved_tenant_id} not found"
            )

        row = result.data[0]

        return {
            "tenant_id": resolved_tenant_id,
            "auto_reply_enabled": row.get("auto_reply_enabled", True),
            "welcome_message": row.get("welcome_message") or "",
            "manglish_mode": manglish_mode_val,
            "testing_mode": row.get("testing_mode", False),
            "test_numbers": row.get("test_numbers") or [],
            "business_hours": row.get("business_hours") or {},
            "ignore_numbers": row.get("ignore_numbers") or [],
            "private_numbers": row.get("private_numbers") or [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching settings for tenant {resolved_tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch settings: {str(e)}")


# ════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════════


@router.get("/health")
async def settings_api_health():
    """Health check for settings API"""
    try:
        supabase = get_supabase()
        return {
            "status": "healthy",
            "service": "settings_api",
            "supabase_connected": True,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "settings_api",
            "error": str(e),
        }
