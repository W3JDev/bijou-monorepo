"""
E2E Test: Calendar Booking Flow
================================

Tests complete booking pipeline: WhatsApp → AI → Cal.com → Reminders

Prerequisites:
- Test tenant with calendar configured
- Your WhatsApp number for receiving test messages
- Cal.com API key in environment

Author: W3J Consulting
Date: 2026-03-04
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
BIJOU_URL = os.getenv("BIJOU_URL", "https://app.mybijou.xyz")
BRIDGE_URL = os.getenv("BRIDGE_URL", "https://bijou-bridge-production-v2.fly.dev")
BRIDGE_USER = os.getenv("BRIDGE_USER", "bijou-prod")
BRIDGE_PASSWORD = os.getenv("BRIDGE_PASSWORD")
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID")
TEST_PHONE = os.getenv("TEST_PHONE")  # Your WhatsApp number (e.g., "+60123456789")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log_success(msg: str):
    print(f"{GREEN}✅ {msg}{RESET}")


def log_error(msg: str):
    print(f"{RED}❌ {msg}{RESET}")


def log_info(msg: str):
    print(f"{YELLOW}ℹ️  {msg}{RESET}")


async def send_whatsapp_message(phone: str, message: str) -> Dict:
    """Send WhatsApp message via bridge."""
    import base64

    auth_str = base64.b64encode(f"{BRIDGE_USER}:{BRIDGE_PASSWORD}".encode()).decode()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BRIDGE_URL}/send/message",
                json={"to": phone, "message": message},
                headers={"Authorization": f"Basic {auth_str}"},
                timeout=30.0
            )

            if response.status_code == 200:
                log_success(f"Message sent to {phone}")
                return response.json()
            else:
                log_error(f"Failed to send message: {response.status_code} - {response.text}")
                return {}

        except Exception as e:
            log_error(f"WhatsApp send error: {e}")
            return {}


async def get_recent_bookings(tenant_id: str, hours: int = 24) -> List[Dict]:
    """Fetch recent bookings from database."""
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

    result = supabase.table("call_bookings") \
        .select("*") \
        .eq("tenant_id", tenant_id) \
        .gte("created_at", cutoff_time) \
        .order("created_at", desc=True) \
        .execute()

    return result.data or []


async def check_reminders(booking_id: str) -> List[Dict]:
    """Check if reminders were created for booking."""
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    result = supabase.table("call_booking_reminders") \
        .select("*") \
        .eq("booking_id", booking_id) \
        .execute()

    return result.data or []


async def test_e2e_booking():
    """
    Complete E2E test flow:
    1. Send booking request via WhatsApp
    2. Wait for AI to process
    3. Verify booking created in database
    4. Check Cal.com API for booking
    5. Verify reminders scheduled
    """

    print("\n" + "="*60)
    print("🧪 E2E Calendar Booking Test")
    print("="*60 + "\n")

    # Validate prerequisites
    if not all([TEST_TENANT_ID, TEST_PHONE, BRIDGE_PASSWORD]):
        log_error("Missing environment variables!")
        log_info("Required: TEST_TENANT_ID, TEST_PHONE, BRIDGE_PASSWORD")
        return False

    log_info(f"Test Tenant: {TEST_TENANT_ID[:8]}...")
    log_info(f"Test Phone: {TEST_PHONE}")

    # Step 1: Send booking request
    print("\n--- STEP 1: Send Booking Request ---")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%A")
    test_message = f"I want to book a viewing {tomorrow} at 2pm"

    log_info(f"Sending: '{test_message}'")
    result = await send_whatsapp_message(TEST_PHONE, test_message)

    if not result:
        log_error("Failed to send WhatsApp message")
        return False

    # Step 2: Wait for AI processing
    print("\n--- STEP 2: Wait for AI Processing ---")
    for i in range(10, 0, -1):
        print(f"⏳ Waiting {i}s for AI to process...", end="\r")
        await asyncio.sleep(1)
    print("\n")

    # Step 3: Check database for booking
    print("--- STEP 3: Verify Booking in Database ---")
    bookings = await get_recent_bookings(TEST_TENANT_ID, hours=1)

    if not bookings:
        log_error("No bookings found in last hour")
        log_info("Check logs: fly logs --app bijou-production | grep booking")
        return False

    latest_booking = bookings[0]
    booking_id = latest_booking['id']

    log_success(f"Booking created: {booking_id}")
    log_info(f"  Customer: {latest_booking.get('customer_name', 'N/A')}")
    log_info(f"  Phone: {latest_booking.get('customer_phone', 'N/A')}")
    log_info(f"  Requested time: {latest_booking.get('requested_time', 'N/A')}")
    log_info(f"  Status: {latest_booking.get('status', 'N/A')}")

    # Step 4: Check Cal.com integration
    print("\n--- STEP 4: Verify Cal.com Booking ---")

    cal_event_id = latest_booking.get('cal_event_id')
    if cal_event_id:
        log_success(f"Cal.com event ID: {cal_event_id}")
    else:
        log_error("No Cal.com event ID (check if Cal.com integration failed)")

    # Step 5: Verify reminders
    print("\n--- STEP 5: Check Reminder System ---")
    reminders = await check_reminders(booking_id)

    if not reminders:
        log_error("No reminders scheduled")
        log_info("Expected: 24h and 1h reminders")
        return False

    log_success(f"{len(reminders)} reminder(s) scheduled")

    for reminder in reminders:
        hours_before = reminder.get('hours_before', 'N/A')
        status = reminder.get('status', 'N/A')
        send_at = reminder.get('scheduled_for', 'N/A')

        log_info(f"  Reminder: {hours_before}h before → {status} (send at {send_at})")

    # Final summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    checks = {
        "WhatsApp message sent": result is not None,
        "Booking created in DB": bool(bookings),
        "Cal.com event created": bool(cal_event_id),
        "Reminders scheduled": len(reminders) >= 2,
    }

    for check, passed in checks.items():
        status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
        print(f"{status} - {check}")

    all_passed = all(checks.values())

    if all_passed:
        print(f"\n{GREEN}🎉 ALL TESTS PASSED!{RESET}\n")
    else:
        print(f"\n{RED}⚠️  SOME TESTS FAILED{RESET}\n")

    return all_passed


async def test_booking_conflict():
    """Test: AI handles booking conflicts (slot already taken)."""

    print("\n" + "="*60)
    print("🧪 Booking Conflict Test")
    print("="*60 + "\n")

    # Send first booking
    log_info("Booking slot 1...")
    await send_whatsapp_message(TEST_PHONE, "Book tomorrow 2pm")
    await asyncio.sleep(10)

    # Try to book same slot
    log_info("Attempting to book same slot...")
    await send_whatsapp_message(TEST_PHONE, "Book tomorrow 2pm")
    await asyncio.sleep(10)

    # Manual verification (would need to check conversation history)
    log_info("Check WhatsApp messages - AI should suggest alternative time")
    print("\n✅ Conflict test sent - manual verification needed\n")


async def test_reminder_delivery():
    """Test: Reminders are actually sent (requires waiting)."""

    print("\n" + "="*60)
    print("🧪 Reminder Delivery Test (Long-running)")
    print("="*60 + "\n")

    log_info("This test requires booking a slot 1-2 hours from now")
    log_info("Then waiting to verify reminder is sent")
    log_info("Estimated time: 2 hours")

    proceed = input("\nProceed with reminder test? (y/N): ")

    if proceed.lower() != 'y':
        log_info("Skipping reminder delivery test")
        return

    # Book slot 1.5 hours from now
    test_time = (datetime.now() + timedelta(hours=1, minutes=30)).strftime("%I:%M %p")
    await send_whatsapp_message(TEST_PHONE, f"Book viewing today at {test_time}")

    log_info("Booking created. Waiting 30 minutes for 1h reminder...")
    await asyncio.sleep(30 * 60)  # Wait 30 minutes

    # Check if reminder was sent
    bookings = await get_recent_bookings(TEST_TENANT_ID, hours=2)
    if bookings:
        booking_id = bookings[0]['id']
        reminders = await check_reminders(booking_id)

        sent_reminders = [r for r in reminders if r['status'] == 'sent']

        if sent_reminders:
            log_success("1h reminder was delivered!")
        else:
            log_error("1h reminder not sent yet (check logs)")


# CLI Interface
async def main():
    """Run E2E tests."""

    if len(sys.argv) > 1:
        test_name = sys.argv[1]

        if test_name == "booking":
            await test_e2e_booking()
        elif test_name == "conflict":
            await test_booking_conflict()
        elif test_name == "reminder":
            await test_reminder_delivery()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: booking, conflict, reminder")
    else:
        # Run all safe tests
        await test_e2e_booking()
        await test_booking_conflict()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        log_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
