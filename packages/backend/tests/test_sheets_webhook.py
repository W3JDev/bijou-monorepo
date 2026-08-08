"""
Google Sheets Webhook Integration - Testing Script
===================================================

This script tests the webhook integration with Google Apps Script.
Use this to verify webhooks are working before deploying to production.

Prerequisites:
1. Set SHEETS_WEBHOOK_URL in .env (use webhook.site for testing)
2. Optional: Set SHEETS_WEBHOOK_SECRET for authentication

Testing Steps:
1. Go to https://webhook.site/ and copy the unique URL
2. Set SHEETS_WEBHOOK_URL=<your_webhook_site_url> in .env
3. Run this script: python tests/test_sheets_webhook.py
4. Check webhook.site to see received payloads
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.integrations.sheets_webhook import sheets_webhook

# Load environment variables
load_dotenv()


async def test_message_event():
    """Test customer message webhook"""
    print("Testing customer message event...")
    
    result = await sheets_webhook.send_message_event(
        tenant_id="550e8400-e29b-41d4-a716-446655440000",
        customer_jid="60123456789@s.whatsapp.net",
        customer_phone="+60123456789",
        customer_name="Test Customer",
        message_id="msg_12345",
        message_content="Hello, I need help with my order",
        sender_type="customer",
        timestamp=datetime.utcnow().isoformat(),
    )
    
    if result:
        print("✅ Customer message webhook sent successfully")
    else:
        print("❌ Customer message webhook failed")
    
    return result


async def test_ai_response_event():
    """Test AI response webhook"""
    print("\nTesting AI response event...")
    
    result = await sheets_webhook.send_message_event(
        tenant_id="550e8400-e29b-41d4-a716-446655440000",
        customer_jid="60123456789@s.whatsapp.net",
        customer_phone="+60123456789",
        customer_name="Test Customer",
        message_id="msg_12345_response",
        message_content="Hi! I'd be happy to help with your order. Can you provide your order number?",
        sender_type="assistant",
        timestamp=datetime.utcnow().isoformat(),
    )
    
    if result:
        print("✅ AI response webhook sent successfully")
    else:
        print("❌ AI response webhook failed")
    
    return result


async def test_escalation_event():
    """Test escalation webhook"""
    print("\nTesting escalation event...")
    
    result = await sheets_webhook.send_escalation_event(
        tenant_id="550e8400-e29b-41d4-a716-446655440000",
        customer_jid="60123456789@s.whatsapp.net",
        customer_phone="+60123456789",
        customer_name="Test Customer",
        escalation_id="esc_67890",
        reason="Customer requested to speak with human agent",
        priority="high",
    )
    
    if result:
        print("✅ Escalation webhook sent successfully")
    else:
        print("❌ Escalation webhook failed")
    
    return result


async def test_status_change_event():
    """Test status change webhook"""
    print("\nTesting status change event...")
    
    result = await sheets_webhook.send_status_change_event(
        tenant_id="550e8400-e29b-41d4-a716-446655440000",
        customer_jid="60123456789@s.whatsapp.net",
        customer_phone="+60123456789",
        old_status="new",
        new_status="active",
    )
    
    if result:
        print("✅ Status change webhook sent successfully")
    else:
        print("❌ Status change webhook failed")
    
    return result


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Google Sheets Webhook Integration Tests")
    print("=" * 60)
    
    if not sheets_webhook.enabled:
        print("\n❌ Sheets webhook is DISABLED")
        print("Set SHEETS_WEBHOOK_URL in .env to enable")
        print("\nFor testing, use https://webhook.site/")
        print("1. Go to webhook.site and copy your unique URL")
        print("2. Set SHEETS_WEBHOOK_URL=<your_url> in .env")
        print("3. Run this script again")
        return
    
    print(f"\n✅ Webhook URL configured: {sheets_webhook.webhook_url[:50]}...")
    
    if sheets_webhook.webhook_secret:
        print(f"✅ Webhook secret configured: {sheets_webhook.webhook_secret[:10]}...")
    else:
        print("⚠️  Webhook secret not configured (recommended for production)")
    
    print("\n" + "=" * 60)
    print("Running Tests...")
    print("=" * 60)
    
    # Run all tests
    results = await asyncio.gather(
        test_message_event(),
        test_ai_response_event(),
        test_escalation_event(),
        test_status_change_event(),
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    test_names = [
        "Customer Message Event",
        "AI Response Event",
        "Escalation Event",
        "Status Change Event",
    ]
    
    passed = sum(results)
    total = len(results)
    
    for name, result in zip(test_names, results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Check webhook.site to see the received payloads")
        print("2. Verify payload format matches expected structure")
        print("3. Deploy Google Apps Script and update SHEETS_WEBHOOK_URL")
    else:
        print("\n⚠️  Some tests failed. Check logs above for details.")


if __name__ == "__main__":
    asyncio.run(main())
