"""
Bijou AI - Trial Manager
========================

Manages trial lifecycle:
- Start trials after email verification
- Send expiry warnings (7d, 3d, 1d)
- Handle trial expiration
- Track trial conversions

Runs as background worker (cron job or scheduler).

Author: W3J Bijou AI
Version: 1.0.0
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

from supabase import create_client

from src.saas.email_service import get_email_service

logger = logging.getLogger(__name__)


class TrialManager:
    """Manages trial lifecycle and notifications"""

    def __init__(self):
        self.supabase = self._get_supabase()
        self.email_service = get_email_service()
        self.public_url = (os.getenv("PUBLIC_URL") or os.getenv("APP_URL", "")).rstrip("/")

    def _get_supabase(self):
        """Initialize Supabase client"""
        supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip('"')

        if not supabase_url or not supabase_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

        return create_client(supabase_url, supabase_key)

    def start_trial(self, tenant_id: str) -> bool:
        """
        Start trial for a tenant (called after email verification)

        Args:
            tenant_id: UUID of the tenant

        Returns:
            bool: True if trial started successfully
        """
        try:
            # Get tenant
            result = self.supabase.table("tenants").select("*").eq("id", tenant_id).execute()

            if not result.data:
                logger.error(f"Tenant {tenant_id} not found")
                return False

            tenant = result.data[0]

            # Check if email is verified
            if not tenant.get("email_verified"):
                logger.warning(f"Cannot start trial - email not verified for {tenant_id}")
                return False

            # Calculate trial period (14 days default)
            trial_days = tenant.get("trial_days", 14)
            trial_start = datetime.utcnow()
            trial_end = trial_start + timedelta(days=trial_days)

            # Update tenant record
            self.supabase.table("tenants").update({
                "trial_start_date": trial_start.isoformat(),
                "trial_end_date": trial_end.isoformat(),
                "is_trial": True,
                "subscription_status": "trial",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", tenant_id).execute()

            logger.info(f"✅ Trial started for {tenant['business_name']} until {trial_end.date()}")

            # Send welcome email
            onboarding_url = f"{self.public_url}/onboard/{tenant['signup_token']}"
            self.email_service.send_welcome_email(
                to=tenant["email"],
                business_name=tenant["business_name"],
                onboarding_url=onboarding_url
            )

            # Record notification
            self._record_notification(tenant_id, "welcome", email_sent=True)

            return True

        except Exception as e:
            logger.error(f"Failed to start trial for {tenant_id}: {e}", exc_info=True)
            return False

    def check_trial_expiry_warnings(self):
        """
        Check for trials needing expiry warnings (7d, 3d, 1d before)
        Run this every 6 hours via cron/scheduler
        """
        logger.info("🔍 Checking for trial expiry warnings...")

        warnings_sent = 0

        for days_before in [7, 3, 1]:
            try:
                # Use database function to get tenants needing warning
                result = self.supabase.rpc(
                    "get_trial_expiry_warnings",
                    {"days_before": days_before}
                ).execute()

                if not result.data:
                    logger.debug(f"No tenants need {days_before}-day warning")
                    continue

                for tenant in result.data:
                    try:
                        # Send warning email
                        upgrade_url = f"{self.public_url}/static/login.html"

                        success = self.email_service.send_trial_expiry_warning(
                            to=tenant["email"],
                            business_name=tenant["business_name"],
                            days_remaining=days_before,
                            upgrade_url=upgrade_url
                        )

                        if success:
                            # Record notification
                            self._record_notification(
                                tenant["tenant_id"],
                                f"trial_{days_before}days",
                                email_sent=True
                            )
                            warnings_sent += 1
                            logger.info(f"✅ Sent {days_before}-day warning to {tenant['business_name']}")

                    except Exception as e:
                        logger.error(f"Failed to send warning to {tenant['tenant_id']}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Failed to check {days_before}-day warnings: {e}")
                continue

        logger.info(f"✅ Sent {warnings_sent} trial expiry warnings")
        return warnings_sent

    def check_expired_trials(self):
        """
        Check for expired trials and notify/pause
        Run this daily via cron/scheduler
        """
        logger.info("🔍 Checking for expired trials...")

        try:
            # Get expired trials using database function
            result = self.supabase.rpc("get_expired_trials").execute()

            if not result.data:
                logger.info("No expired trials found")
                return 0

            expired_count = 0

            for tenant in result.data:
                try:
                    tenant_id = tenant["tenant_id"]

                    # Update subscription status to 'expired'
                    self.supabase.table("tenants").update({
                        "subscription_status": "expired",
                        "is_trial": False,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", tenant_id).execute()

                    # Send expiry notification
                    upgrade_url = f"{self.public_url}/static/login.html"

                    success = self.email_service.send_trial_expired_email(
                        to=tenant["email"],
                        business_name=tenant["business_name"],
                        upgrade_url=upgrade_url
                    )

                    if success:
                        self._record_notification(
                            tenant_id,
                            "trial_expired",
                            email_sent=True
                        )

                    expired_count += 1
                    logger.info(f"✅ Trial expired for {tenant['business_name']}")

                except Exception as e:
                    logger.error(f"Failed to handle expired trial {tenant['tenant_id']}: {e}")
                    continue

            logger.info(f"✅ Processed {expired_count} expired trials")
            return expired_count

        except Exception as e:
            logger.error(f"Failed to check expired trials: {e}", exc_info=True)
            return 0

    def get_trial_analytics(self) -> Dict[str, Any]:
        """
        Get trial conversion analytics

        Returns:
            dict: Analytics data including conversion rates
        """
        try:
            # Get conversion funnel from view
            result = self.supabase.table("trial_conversion_funnel").select("*").execute()

            if result.data:
                return result.data[0]

            return {}

        except Exception as e:
            logger.error(f"Failed to get trial analytics: {e}")
            return {}

    def get_active_trials_summary(self) -> Dict[str, Any]:
        """Get summary of active trials"""
        try:
            result = self.supabase.table("active_trials_summary").select("*").execute()

            if result.data:
                return result.data[0]

            return {}

        except Exception as e:
            logger.error(f"Failed to get active trials summary: {e}")
            return {}

    def extend_trial(self, tenant_id: str, extra_days: int = 7) -> bool:
        """
        Extend trial period for a tenant

        Args:
            tenant_id: UUID of the tenant
            extra_days: Number of days to extend (default: 7)
        """
        try:
            # Get current trial end date
            result = self.supabase.table("tenants").select("trial_end_date").eq("id", tenant_id).execute()

            if not result.data:
                logger.error(f"Tenant {tenant_id} not found")
                return False

            current_end = datetime.fromisoformat(result.data[0]["trial_end_date"].replace("Z", ""))
            new_end = current_end + timedelta(days=extra_days)

            # Update trial end date
            self.supabase.table("tenants").update({
                "trial_end_date": new_end.isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", tenant_id).execute()

            logger.info(f"✅ Trial extended by {extra_days} days for {tenant_id} (new end: {new_end.date()})")
            return True

        except Exception as e:
            logger.error(f"Failed to extend trial for {tenant_id}: {e}", exc_info=True)
            return False

    def _record_notification(
        self,
        tenant_id: str,
        notification_type: str,
        email_sent: bool = False,
        whatsapp_sent: bool = False,
        metadata: Dict = None
    ):
        """Record that a notification was sent"""
        try:
            self.supabase.table("trial_notifications").insert({
                "tenant_id": tenant_id,
                "notification_type": notification_type,
                "email_sent": email_sent,
                "whatsapp_sent": whatsapp_sent,
                "metadata": metadata or {},
                "sent_at": datetime.utcnow().isoformat()
            }).execute()

        except Exception as e:
            logger.warning(f"Failed to record notification: {e}")


def run_trial_checks():
    """
    Main function to run all trial checks
    Call this from a cron job or scheduler
    """
    logger.info("=" * 60)
    logger.info("TRIAL MANAGER - Starting scheduled checks")
    logger.info("=" * 60)

    manager = TrialManager()

    # Check for expiry warnings
    warnings = manager.check_trial_expiry_warnings()

    # Check for expired trials
    expired = manager.check_expired_trials()

    # Get analytics
    analytics = manager.get_trial_analytics()
    active_summary = manager.get_active_trials_summary()

    logger.info("=" * 60)
    logger.info("TRIAL MANAGER - Summary")
    logger.info("=" * 60)
    logger.info(f"Warnings sent: {warnings}")
    logger.info(f"Trials expired: {expired}")
    logger.info(f"Active trials: {active_summary.get('total_active_trials', 0)}")
    logger.info(f"Expiring soon (3d): {active_summary.get('expiring_soon', 0)}")
    logger.info(f"Trial → Paid conversion rate: {analytics.get('trial_to_paid_conversion_rate', 0)}%")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run checks
    run_trial_checks()
