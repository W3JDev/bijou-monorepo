"""
Dashboard Settings Endpoints - Calendar & Email Config
=======================================================

API endpoints for tenants to configure their Cal.com and SMTP credentials
through the dashboard UI (self-service).

Author: W3J Consulting
Date: 2026-03-03
"""

import logging
from typing import Dict, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from supabase import Client

logger = logging.getLogger(__name__)


# ==================== MODELS ====================


class CalendarConfigRequest(BaseModel):
    """Request body for updating Cal.com configuration"""
    cal_username: str = Field(..., description="Cal.com username")
    cal_api_key: str = Field(..., description="Cal.com API key")
    default_event_type_id: Optional[int] = Field(None, description="Default event type ID")
    send_confirmation_email: bool = Field(True, description="Send email confirmations")


class EmailConfigRequest(BaseModel):
    """Request body for updating SMTP configuration"""
    smtp_host: str = Field(..., description="SMTP server hostname")
    smtp_port: int = Field(587, description="SMTP port (587, 465, or 25)")
    smtp_user: str = Field(..., description="SMTP username")
    smtp_pass: str = Field(..., description="SMTP password or app password")
    smtp_use_tls: bool = Field(True, description="Use TLS encryption")
    from_email: str = Field(..., description="Sender email address")
    from_name: str = Field(..., description="Sender name")
    reply_to_email: Optional[str] = Field(None, description="Reply-to email address")


# ==================== HELPER FUNCTIONS ====================


def get_calendar_config(supabase: Client, tenant_id: str) -> Optional[Dict]:
    """
    Fetch tenant's Cal.com configuration from database.

    Args:
        supabase: Supabase client
        tenant_id: Tenant UUID

    Returns:
        Dict with calendar config or None if not found
    """
    try:
        result = supabase.table("tenant_calendars")\
            .select("*")\
            .eq("tenant_id", tenant_id)\
            .eq("is_active", True)\
            .limit(1)\
            .execute()

        if result.data and len(result.data) > 0:
            config = result.data[0]
            # Mask API key for security (show only last 4 chars)
            if config.get("cal_api_key"):
                masked = "*" * (len(config["cal_api_key"]) - 4) + config["cal_api_key"][-4:]
                config["cal_api_key_masked"] = masked
                config.pop("cal_api_key", None)  # Don't send full key to frontend

            # Strip OAuth tokens — never expose to frontend
            config.pop("oauth_access_token",  None)
            config.pop("oauth_refresh_token", None)

            logger.debug(f"📅 Retrieved calendar config for tenant {tenant_id}")
            return config
        else:
            logger.debug(f"📅 No calendar config found for tenant {tenant_id}")
            return None

    except Exception as e:
        logger.error(f"❌ Failed to fetch calendar config for tenant {tenant_id}: {e}")
        raise


def upsert_calendar_config(supabase: Client, tenant_id: str, data: CalendarConfigRequest) -> Dict:
    """
    Insert or update tenant's Cal.com configuration.

    Args:
        supabase: Supabase client
        tenant_id: Tenant UUID
        data: Calendar configuration data

    Returns:
        Dict with success status
    """
    try:
        # Check if config exists
        existing = supabase.table("tenant_calendars")\
            .select("id")\
            .eq("tenant_id", tenant_id)\
            .limit(1)\
            .execute()

        payload = {
            "tenant_id": tenant_id,
            "provider": "cal.com",
            "cal_username": data.cal_username,
            "cal_api_key": data.cal_api_key,
            "default_event_type_id": data.default_event_type_id,
            "send_confirmation_email": data.send_confirmation_email,
            "is_active": True
        }

        if existing.data and len(existing.data) > 0:
            # Update existing
            result = supabase.table("tenant_calendars")\
                .update(payload)\
                .eq("tenant_id", tenant_id)\
                .execute()
            logger.info(f"✅ Updated calendar config for tenant {tenant_id}")
        else:
            # Insert new
            result = supabase.table("tenant_calendars")\
                .insert(payload)\
                .execute()
            logger.info(f"✅ Created calendar config for tenant {tenant_id}")

        return {
            "success": True,
            "message": "Calendar configuration saved successfully",
            "tenant_id": tenant_id
        }

    except Exception as e:
        logger.error(f"❌ Failed to save calendar config for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save calendar configuration: {str(e)}")


def get_email_config(supabase: Client, tenant_id: str) -> Optional[Dict]:
    """
    Fetch tenant's SMTP configuration from database.

    Args:
        supabase: Supabase client
        tenant_id: Tenant UUID

    Returns:
        Dict with email config or None if not found
    """
    try:
        result = supabase.table("tenant_email_config")\
            .select("*")\
            .eq("tenant_id", tenant_id)\
            .eq("is_active", True)\
            .limit(1)\
            .execute()

        if result.data and len(result.data) > 0:
            config = result.data[0]
            # Mask SMTP password for security
            if config.get("smtp_pass"):
                config["smtp_pass_masked"] = "*" * 8
                config.pop("smtp_pass", None)  # Don't send password to frontend

            logger.debug(f"📧 Retrieved email config for tenant {tenant_id}")
            return config
        else:
            logger.debug(f"📧 No email config found for tenant {tenant_id}")
            return None

    except Exception as e:
        logger.error(f"❌ Failed to fetch email config for tenant {tenant_id}: {e}")
        raise


def upsert_email_config(supabase: Client, tenant_id: str, data: EmailConfigRequest) -> Dict:
    """
    Insert or update tenant's SMTP configuration.

    Args:
        supabase: Supabase client
        tenant_id: Tenant UUID
        data: Email configuration data

    Returns:
        Dict with success status
    """
    try:
        # Check if config exists
        existing = supabase.table("tenant_email_config")\
            .select("id")\
            .eq("tenant_id", tenant_id)\
            .limit(1)\
            .execute()

        payload = {
            "tenant_id": tenant_id,
            "smtp_host": data.smtp_host,
            "smtp_port": data.smtp_port,
            "smtp_user": data.smtp_user,
            "smtp_pass": data.smtp_pass,
            "smtp_use_tls": data.smtp_use_tls,
            "from_email": data.from_email,
            "from_name": data.from_name,
            "reply_to_email": data.reply_to_email,
            "is_active": True
        }

        if existing.data and len(existing.data) > 0:
            # Update existing
            result = supabase.table("tenant_email_config")\
                .update(payload)\
                .eq("tenant_id", tenant_id)\
                .execute()
            logger.info(f"✅ Updated email config for tenant {tenant_id}")
        else:
            # Insert new
            result = supabase.table("tenant_email_config")\
                .insert(payload)\
                .execute()
            logger.info(f"✅ Created email config for tenant {tenant_id}")

        return {
            "success": True,
            "message": "Email configuration saved successfully",
            "tenant_id": tenant_id
        }

    except Exception as e:
        logger.error(f"❌ Failed to save email config for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save email configuration: {str(e)}")
