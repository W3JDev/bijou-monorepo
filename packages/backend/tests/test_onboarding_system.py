"""
Bijou AI - Onboarding System Test Suite
========================================

Tests all components of the onboarding system:
- Email service
- Trial manager
- Stripe service
- Database schema

Usage:
    python tests/test_onboarding_system.py

Author: W3J Bijou AI
Version: 1.0.0
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_supabase():
    """Get Supabase client"""
    supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip('"')
    return create_client(supabase_url, supabase_key)


def test_database_schema():
    """Test that all tables and columns exist"""
    logger.info("=" * 60)
    logger.info("TEST 1: DATABASE SCHEMA")
    logger.info("=" * 60)
    
    supabase = get_supabase()
    
    # Test tables exist
    tables = [
        "tenants",
        "email_verification_tokens",
        "trial_notifications",
        "payment_transactions",
        "subscription_plans",
        "tenant_setup_progress"
    ]
    
    for table in tables:
        try:
            result = supabase.table(table).select("*").limit(1).execute()
            logger.info(f"✅ Table '{table}' exists")
        except Exception as e:
            logger.error(f"❌ Table '{table}' missing or error: {e}")
    
    # Test tenants columns
    tenant_columns = [
        "email_verified",
        "email_verification_token",
        "trial_start_date",
        "trial_end_date",
        "stripe_customer_id",
        "subscription_status"
    ]
    
    result = supabase.table("tenants").select("*").limit(1).execute()
    if result.data:
        tenant = result.data[0]
        for col in tenant_columns:
            if col in tenant or col in str(tenant):
                logger.info(f"✅ Column 'tenants.{col}' exists")
            else:
                logger.warning(f"⚠️ Column 'tenants.{col}' might be missing")


def test_email_service():
    """Test email service initialization"""
    logger.info("=" * 60)
    logger.info("TEST 2: EMAIL SERVICE")
    logger.info("=" * 60)
    
    try:
        from src.saas.email_service import get_email_service
        
        email_service = get_email_service()
        
        if email_service.service:
            logger.info("✅ Email service initialized (Gmail API connected)")
        else:
            logger.warning("⚠️ Email service initialized but Gmail API not connected")
            logger.warning("    Check GOOGLE_CREDENTIALS_PATH environment variable")
        
    except Exception as e:
        logger.error(f"❌ Email service failed: {e}")


def test_trial_manager():
    """Test trial manager"""
    logger.info("=" * 60)
    logger.info("TEST 3: TRIAL MANAGER")
    logger.info("=" * 60)
    
    try:
        from src.saas.trial_manager import TrialManager
        
        manager = TrialManager()
        logger.info("✅ Trial manager initialized")
        
        # Get analytics
        analytics = manager.get_trial_analytics()
        logger.info(f"   Trial analytics: {analytics}")
        
        summary = manager.get_active_trials_summary()
        logger.info(f"   Active trials: {summary.get('total_active_trials', 0)}")
        
    except Exception as e:
        logger.error(f"❌ Trial manager failed: {e}")


def test_stripe_service():
    """Test Stripe service"""
    logger.info("=" * 60)
    logger.info("TEST 4: STRIPE SERVICE")
    logger.info("=" * 60)
    
    try:
        from src.saas.stripe_service import get_stripe_service
        import stripe
        
        stripe_service = get_stripe_service()
        
        if stripe.api_key:
            logger.info("✅ Stripe service initialized (API key configured)")
        else:
            logger.warning("⚠️ Stripe API key not configured")
            logger.warning("    Set STRIPE_SECRET_KEY environment variable")
        
    except Exception as e:
        logger.error(f"❌ Stripe service failed: {e}")


def test_subscription_plans():
    """Test subscription plans in database"""
    logger.info("=" * 60)
    logger.info("TEST 5: SUBSCRIPTION PLANS")
    logger.info("=" * 60)
    
    try:
        supabase = get_supabase()
        
        result = supabase.table("subscription_plans").select("*").execute()
        
        if result.data:
            logger.info(f"✅ Found {len(result.data)} subscription plans:")
            for plan in result.data:
                price_monthly = plan.get('price_monthly_cents', 0) / 100
                logger.info(f"   - {plan['plan_name']}: ${price_monthly}/mo")
        else:
            logger.warning("⚠️ No subscription plans found")
            logger.warning("    Run database migration: database/005_trial_system.sql")
        
    except Exception as e:
        logger.error(f"❌ Failed to check plans: {e}")


def test_database_functions():
    """Test database functions"""
    logger.info("=" * 60)
    logger.info("TEST 6: DATABASE FUNCTIONS")
    logger.info("=" * 60)
    
    try:
        supabase = get_supabase()
        
        # Test get_trial_expiry_warnings function
        result = supabase.rpc("get_trial_expiry_warnings", {"days_before": 7}).execute()
        logger.info(f"✅ Function 'get_trial_expiry_warnings' works")
        logger.info(f"   Found {len(result.data) if result.data else 0} tenants needing 7-day warning")
        
        # Test get_expired_trials function
        result = supabase.rpc("get_expired_trials").execute()
        logger.info(f"✅ Function 'get_expired_trials' works")
        logger.info(f"   Found {len(result.data) if result.data else 0} expired trials")
        
    except Exception as e:
        logger.error(f"❌ Database functions failed: {e}")
        logger.error("    Run database migration: database/005_trial_system.sql")


def test_views():
    """Test analytics views"""
    logger.info("=" * 60)
    logger.info("TEST 7: ANALYTICS VIEWS")
    logger.info("=" * 60)
    
    try:
        supabase = get_supabase()
        
        # Test trial_conversion_funnel view
        result = supabase.table("trial_conversion_funnel").select("*").execute()
        if result.data:
            logger.info("✅ View 'trial_conversion_funnel' exists")
            funnel = result.data[0]
            logger.info(f"   Conversion rate: {funnel.get('trial_to_paid_conversion_rate', 0)}%")
        else:
            logger.warning("⚠️ View 'trial_conversion_funnel' empty or missing")
        
        # Test active_trials_summary view
        result = supabase.table("active_trials_summary").select("*").execute()
        if result.data:
            logger.info("✅ View 'active_trials_summary' exists")
            summary = result.data[0]
            logger.info(f"   Active trials: {summary.get('total_active_trials', 0)}")
        else:
            logger.warning("⚠️ View 'active_trials_summary' empty or missing")
        
    except Exception as e:
        logger.error(f"❌ Analytics views failed: {e}")


def main():
    """Run all tests"""
    logger.info("")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " " * 10 + "BIJOU AI - ONBOARDING SYSTEM TESTS" + " " * 14 + "║")
    logger.info("╚" + "═" * 58 + "╝")
    logger.info("")
    
    tests = [
        test_database_schema,
        test_email_service,
        test_trial_manager,
        test_stripe_service,
        test_subscription_plans,
        test_database_functions,
        test_views
    ]
    
    for test in tests:
        try:
            test()
            logger.info("")
        except Exception as e:
            logger.error(f"Test failed: {e}")
            logger.info("")
    
    logger.info("=" * 60)
    logger.info("TESTS COMPLETE")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. If any tests failed, run: database/005_trial_system.sql")
    logger.info("2. Configure STRIPE_SECRET_KEY environment variable")
    logger.info("3. Test signup flow: POST /api/onboarding/signup")
    logger.info("4. Setup cron job: python scripts/trial_cron.py")
    logger.info("")


if __name__ == "__main__":
    main()
