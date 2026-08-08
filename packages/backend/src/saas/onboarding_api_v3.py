"""
Bijou AI - Enhanced Onboarding API with Email Verification
===========================================================

Complete onboarding flow:
1. POST /api/onboarding/signup → Create tenant, send verification email
2. GET /api/onboarding/verify-email?token=XXX → Verify email, start trial
3. GET /api/onboarding/resend-verification/{tenant_id} → Resend email
4. GET /api/onboarding/status/{token} → Check status
5. GET /api/onboarding/qr/{token} → Get WhatsApp QR
6. POST /api/onboarding/complete/{token} → Mark complete

Author: W3J Bijou AI
Version: 3.0.0 (Email Verification + Trial)
"""

import logging
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional
import asyncio

import httpx
from fastapi import APIRouter, HTTPException, Response, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, validator

from supabase import create_client

# Import our new services
from src.saas.email_service import get_email_service
from src.saas.trial_manager import TrialManager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

# ════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════

class SignupRequest(BaseModel):
    """Property agent signup form data"""
    business_name: str
    email: EmailStr
    phone: str

    @validator("business_name")
    def validate_business_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Business name must be at least 2 characters")
        return v.strip()

    @validator("phone")
    def validate_phone(cls, v):
        cleaned = re.sub(r"\\D", "", v)
        if len(cleaned) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        return cleaned


class SignupResponse(BaseModel):
    """Response after successful signup"""
    success: bool
    tenant_id: str
    message: str
    next_step: str


class StatusResponse(BaseModel):
    """Onboarding status"""
    tenant_id: str
    business_name: str
    email: Optional[str] = None
    email_verified: bool
    whatsapp_connected: bool
    onboarding_completed: bool
    trial_active: bool
    trial_days_remaining: Optional[int] = None
    current_step: str
    onboarding_checklist: dict


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


def generate_token(length: int = 32) -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(length)


def generate_slug(business_name: str) -> str:
    """Generate URL-friendly slug from business name"""
    slug = business_name.lower().strip()
    slug = re.sub(r"[^a-z0-9\\s-]", "", slug)
    slug = re.sub(r"\\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    suffix = secrets.token_hex(4)
    return f"{slug}-{suffix}"


def get_public_url() -> str:
    """Get public URL for this service"""
    return (os.getenv("PUBLIC_URL") or os.getenv("APP_URL", "")).rstrip("/")


# ════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ════════════════════════════════════════════════════════════════

@router.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest):
    """
    Step 1: Create tenant and send verification email
    """
    logger.info(f"🆕 New signup: {request.business_name} ({request.email})")

    try:
        supabase = get_supabase()
        email_service = get_email_service()

        # Check if email already exists
        existing = supabase.table("tenants").select("id, email").eq("email", request.email).execute()

        if existing.data:
            logger.warning(f"⚠️ Duplicate signup attempt: {request.email}")
            raise HTTPException(
                status_code=400,
                detail=f"Email {request.email} is already registered. Please contact support or use a different email."
            )

        # Generate tokens
        signup_token = generate_token()
        email_token = generate_token()
        slug = generate_slug(request.business_name)

        # Create tenant record
        tenant_data = {
            "name": request.business_name,
            "slug": slug,
            "business_name": request.business_name,
            "email": request.email,
            "phone": request.phone,
            "status": "pending",  # Changes to 'active' after email verify
            "plan": "trial",
            "signup_token": signup_token,
            "email_verification_token": email_token,
            "email_verified": False,
            "onboarding_completed": False,
            "trial_days": 14,
            "created_by": "self-signup",
            "created_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("tenants").insert(tenant_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create tenant record")

        tenant_id = result.data[0]["id"]
        logger.info(f"✅ Tenant created: {tenant_id}")

        # Create tenant_users entry (owner)
        user_data = {
            "tenant_id": tenant_id,
            "email": request.email,
            "role": "owner",
            "is_main_contact": True,
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table("tenant_users").insert(user_data).execute()

        # Create email verification token record
        token_expiry = datetime.utcnow() + timedelta(hours=24)
        supabase.table("email_verification_tokens").insert({
            "tenant_id": tenant_id,
            "email": request.email,
            "token": email_token,
            "expires_at": token_expiry.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # Send verification email
        public_url = get_public_url()
        email_sent = email_service.send_verification_email(
            to=request.email,
            business_name=request.business_name,
            verification_token=email_token,
            public_url=public_url
        )

        if not email_sent:
            logger.warning(f"⚠️ Failed to send verification email to {request.email}")

        return SignupResponse(
            success=True,
            tenant_id=tenant_id,
            message="Account created! Please check your email to verify and start your 14-day trial.",
            next_step="verify_email"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Signup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(token: str = Query(...)):
    """
    Step 2: Verify email and start trial
    """
    logger.info(f"📧 Email verification attempt: {token[:10]}...")

    try:
        supabase = get_supabase()

        # Find token
        token_result = supabase.table("email_verification_tokens").select("*").eq("token", token).execute()

        if not token_result.data:
            return "<html><body><h1>❌ Invalid verification link</h1><p>This link is invalid or has expired.</p></body></html>"

        token_data = token_result.data[0]

        # Check if already verified
        if token_data.get("verified_at"):
            return "<html><body><h1>✅ Already Verified</h1><p>Your email was already verified. You can close this window.</p></body></html>"

        # Check expiry
        expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", ""))
        if datetime.utcnow() > expires_at:
            return "<html><body><h1>⏰ Link Expired</h1><p>This verification link has expired. Please request a new one.</p></body></html>"

        tenant_id = token_data["tenant_id"]

        # Update tenant - email verified
        supabase.table("tenants").update({
            "email_verified": True,
            "email_verified_at": datetime.utcnow().isoformat(),
            "status": "active",  # Activate tenant
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", tenant_id).execute()

        # Mark token as verified
        supabase.table("email_verification_tokens").update({
            "verified_at": datetime.utcnow().isoformat()
        }).eq("token", token).execute()

        logger.info(f"✅ Email verified for tenant {tenant_id}")

        # Start trial (triggers database function)
        trial_manager = TrialManager()
        trial_manager.start_trial(tenant_id)

        # Get signup token for redirect
        tenant_result = supabase.table("tenants").select("signup_token, business_name").eq("id", tenant_id).execute()
        signup_token = tenant_result.data[0]["signup_token"]
        business_name = tenant_result.data[0]["business_name"]

        # Redirect to onboarding page (WhatsApp connection)
        public_url = get_public_url()
        onboarding_url = f"{public_url}/onboard/{signup_token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Verified - Bijou AI</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #10b981 0%, #059669 100%); margin: 0; padding: 40px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                h1 {{ color: #10b981; margin-top: 0; }}
                .button {{ display: inline-block; background: #10b981; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 20px; }}
                .button:hover {{ background: #059669; }}
                .checkmark {{ font-size: 60px; color: #10b981; text-align: center; }}
            </style>
            <meta http-equiv="refresh" content="3;url={onboarding_url}">
        </head>
        <body>
            <div class="container">
                <div class="checkmark">✅</div>
                <h1>Email Verified!</h1>
                <p>Great news, <strong>{business_name}</strong>!</p>
                <p>Your 14-day free trial has started. Redirecting you to WhatsApp setup...</p>
                <a href="{onboarding_url}" class="button">Continue to WhatsApp Setup →</a>
                <p style="font-size: 12px; color: #6b7280; margin-top: 30px;">If you're not redirected automatically, click the button above.</p>
            </div>
        </body>
        </html>
        """

        return html

    except Exception as e:
        logger.error(f"❌ Email verification failed: {e}", exc_info=True)
        return "<html><body><h1>❌ Verification Failed</h1><p>Something went wrong. Please contact support.</p></body></html>"


@router.post("/resend-verification/{tenant_id}")
async def resend_verification(tenant_id: str):
    """
    Resend verification email
    """
    try:
        supabase = get_supabase()

        # Get tenant
        result = supabase.table("tenants").select("*").eq("id", tenant_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant = result.data[0]

        # Check if already verified
        if tenant.get("email_verified"):
            raise HTTPException(status_code=400, detail="Email already verified")

        # Check resend count
        token_result = supabase.table("email_verification_tokens").select("resent_count").eq("tenant_id", tenant_id).order("created_at", desc=True).limit(1).execute()

        if token_result.data and token_result.data[0].get("resent_count", 0) >= 5:
            raise HTTPException(status_code=429, detail="Maximum resend limit reached. Please contact support.")

        # Generate new token
        email_token = generate_token()
        token_expiry = datetime.utcnow() + timedelta(hours=24)

        # Create new token record
        supabase.table("email_verification_tokens").insert({
            "tenant_id": tenant_id,
            "email": tenant["email"],
            "token": email_token,
            "expires_at": token_expiry.isoformat(),
            "resent_count": (token_result.data[0].get("resent_count", 0) if token_result.data else 0) + 1,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # Update tenant token
        supabase.table("tenants").update({
            "email_verification_token": email_token
        }).eq("id", tenant_id).execute()

        # Send email
        email_service = get_email_service()
        public_url = get_public_url()

        email_sent = email_service.send_verification_email(
            to=tenant["email"],
            business_name=tenant["business_name"],
            verification_token=email_token,
            public_url=public_url
        )

        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send email")

        return {"success": True, "message": "Verification email sent"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{token}", response_model=StatusResponse)
async def get_status(token: str):
    """
    Get onboarding status
    """
    try:
        supabase = get_supabase()

        # Find tenant by signup token
        result = supabase.table("tenants").select("*").eq("signup_token", token).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Invalid token")

        tenant = result.data[0]

        # Calculate trial days remaining
        trial_days_remaining = None
        trial_active = False

        if tenant.get("trial_end_date"):
            trial_end = datetime.fromisoformat(tenant["trial_end_date"].replace("Z", ""))
            days_remaining = (trial_end - datetime.utcnow()).days
            trial_days_remaining = max(0, days_remaining)
            trial_active = days_remaining > 0 and tenant.get("is_trial", False)

        # Determine current step
        if not tenant.get("email_verified"):
            current_step = "verify_email"
        elif not tenant.get("whatsapp_connected_at"):
            current_step = "connect_whatsapp"
        elif not tenant.get("onboarding_completed"):
            current_step = "setup_complete"
        else:
            current_step = "complete"

        return StatusResponse(
            tenant_id=tenant["id"],
            business_name=tenant["business_name"],
            email=tenant["email"],
            email_verified=tenant.get("email_verified", False),
            whatsapp_connected=bool(tenant.get("whatsapp_connected_at")),
            onboarding_completed=tenant.get("onboarding_completed", False),
            trial_active=trial_active,
            trial_days_remaining=trial_days_remaining,
            current_step=current_step,
            onboarding_checklist=tenant.get("onboarding_checklist", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "onboarding-api",
        "version": "3.0.0"
    }
