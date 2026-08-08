#!/usr/bin/env python3
"""
Multi-Channel Test Script for Bijou AI
=======================================

Tests both WhatsApp and Telegram webhook endpoints locally.
Sends mock messages to localhost:5000/webhook/... to verify AI responds.

Usage:
    python ops/test_channels.py [--url URL] [--whatsapp] [--telegram] [--all]

Examples:
    python ops/test_channels.py --all                    # Test both channels
    python ops/test_channels.py --whatsapp              # Test WhatsApp only
    python ops/test_channels.py --telegram              # Test Telegram only
    python ops/test_channels.py --url http://localhost:8080 --all

Author: W3J Bijou Enterprise
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, Optional

import requests

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log_success(msg: str):
    print(f"{GREEN}✅ {msg}{RESET}")


def log_error(msg: str):
    print(f"{RED}❌ {msg}{RESET}")


def log_info(msg: str):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def log_warn(msg: str):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def test_health(base_url: str) -> bool:
    """Test the health endpoint to ensure server is running."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_success(f"Health check passed: {data.get('status', 'unknown')}")
            return True
        else:
            log_error(f"Health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        log_error(f"Cannot connect to {base_url} - is the server running?")
        return False
    except Exception as e:
        log_error(f"Health check error: {e}")
        return False


def create_mock_whatsapp_message(
    content: str,
    chat_jid: str = "60123456789@s.whatsapp.net",
    sender: str = "60123456789@s.whatsapp.net",
    message_id: Optional[str] = None,
) -> Dict:
    """
    Create a mock WhatsApp webhook message payload.

    Format matches the WebhookMessage model in bijou.py.
    """
    if message_id is None:
        message_id = f"wa_test_{int(time.time() * 1000)}"

    return {
        "id": message_id,
        "chat_jid": chat_jid,
        "sender": sender,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        "is_from_me": False,
        "media_type": None,
        "filename": None,
    }


def create_mock_telegram_update(
    content: str,
    chat_id: int = 123456789,
    user_id: int = 987654321,
    username: str = "test_user",
    message_id: Optional[int] = None,
) -> Dict:
    """
    Create a mock Telegram webhook update payload.

    Format matches Telegram Bot API Update structure.
    See: https://core.telegram.org/bots/api#update
    """
    if message_id is None:
        message_id = int(time.time())

    return {
        "update_id": int(time.time() * 1000),
        "message": {
            "message_id": message_id,
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": username,
                "language_code": "en",
            },
            "chat": {
                "id": chat_id,
                "first_name": "Test",
                "last_name": "User",
                "username": username,
                "type": "private",
            },
            "date": int(datetime.utcnow().timestamp()),
            "text": content,
        },
    }


def test_whatsapp_webhook(base_url: str, message: str = "Hello from WhatsApp test!") -> bool:
    """
    Test the WhatsApp webhook endpoint.

    Sends a mock WhatsApp message and checks if it's processed.
    """
    log_info(f"Testing WhatsApp webhook with message: '{message}'")

    payload = create_mock_whatsapp_message(content=message)

    try:
        response = requests.post(
            f"{base_url}/webhook/message",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            if status == "success":
                log_success(f"WhatsApp webhook processed: {data}")
                return True
            elif status == "skipped":
                log_warn(f"WhatsApp webhook skipped (already processed): {data}")
                return True
            else:
                log_error(f"WhatsApp webhook returned unexpected status: {data}")
                return False
        else:
            log_error(f"WhatsApp webhook failed: HTTP {response.status_code}")
            log_error(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        log_error("WhatsApp webhook timed out (30s) - AI processing may be slow")
        return False
    except Exception as e:
        log_error(f"WhatsApp webhook error: {e}")
        return False


def test_telegram_webhook(base_url: str, message: str = "Hello from Telegram test!") -> bool:
    """
    Test the Telegram webhook endpoint.

    Sends a mock Telegram update and checks if it's processed.
    """
    log_info(f"Testing Telegram webhook with message: '{message}'")

    payload = create_mock_telegram_update(content=message)

    try:
        response = requests.post(
            f"{base_url}/webhook/telegram",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            if status == "success":
                log_success(f"Telegram webhook processed: {data}")
                return True
            elif status == "skipped":
                log_warn(f"Telegram webhook skipped (already processed): {data}")
                return True
            elif status == "ok":
                # Non-message updates return "ok"
                log_info(f"Telegram webhook acknowledged: {data}")
                return True
            else:
                log_error(f"Telegram webhook returned unexpected status: {data}")
                return False
        elif response.status_code == 400:
            data = response.json()
            if "not enabled" in data.get("detail", ""):
                log_warn("Telegram is not enabled (TELEGRAM_BOT_TOKEN not set)")
                return True  # Not a failure, just not configured
            log_error(f"Telegram webhook failed: {data}")
            return False
        else:
            log_error(f"Telegram webhook failed: HTTP {response.status_code}")
            log_error(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        log_error("Telegram webhook timed out (30s) - AI processing may be slow")
        return False
    except Exception as e:
        log_error(f"Telegram webhook error: {e}")
        return False


def test_multilingual_messages(base_url: str) -> Dict[str, bool]:
    """
    Test messages in multiple languages to verify language detection.

    Returns dict of language -> success status.
    """
    test_messages = {
        "English": "Hello, how can I help you today?",
        "Malay": "Apa khabar? Saya nak tanya tentang perkhidmatan anda.",
        "Mandarin": "你好，我想了解你们的服务",
        "Tamil": "வணக்கம், நான் உங்கள் சேவைகளைப் பற்றி தெரிந்து கொள்ள விரும்புகிறேன்",
        "Manglish": "Eh boss, how much this one ah? Got discount or not?",
        "Bengali": "আমি আপনার সেবা সম্পর্কে জানতে চাই",
    }

    results = {}
    for lang, message in test_messages.items():
        log_info(f"Testing {lang} message...")
        payload = create_mock_whatsapp_message(
            content=message,
            message_id=f"lang_test_{lang.lower()}_{int(time.time() * 1000)}",
        )

        try:
            response = requests.post(
                f"{base_url}/webhook/message",
                json=payload,
                timeout=30,
            )
            results[lang] = response.status_code == 200
            if results[lang]:
                log_success(f"{lang}: Processed")
            else:
                log_error(f"{lang}: Failed (HTTP {response.status_code})")

            # Small delay to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            results[lang] = False
            log_error(f"{lang}: Error - {e}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Test Bijou AI multi-channel webhooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python ops/test_channels.py --all
    python ops/test_channels.py --whatsapp --message "Custom test message"
    python ops/test_channels.py --url http://localhost:8080 --telegram
    python ops/test_channels.py --multilingual
        """,
    )

    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="Base URL of Bijou AI server (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--whatsapp", "-w",
        action="store_true",
        help="Test WhatsApp webhook",
    )
    parser.add_argument(
        "--telegram", "-t",
        action="store_true",
        help="Test Telegram webhook",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Test all channels",
    )
    parser.add_argument(
        "--multilingual", "-m",
        action="store_true",
        help="Run multilingual message tests",
    )
    parser.add_argument(
        "--message", "-msg",
        default=None,
        help="Custom message to send (default: channel-specific test message)",
    )

    args = parser.parse_args()

    # Default to --all if no specific channel selected
    if not (args.whatsapp or args.telegram or args.all or args.multilingual):
        args.all = True

    print("=" * 60)
    print("🧪 BIJOU AI MULTI-CHANNEL TEST")
    print("=" * 60)
    print(f"Target: {args.url}")
    print("=" * 60)

    # Health check first
    if not test_health(args.url):
        log_error("Server health check failed. Exiting.")
        sys.exit(1)

    print()

    results = {}

    # Test WhatsApp
    if args.whatsapp or args.all:
        print("-" * 40)
        print("📱 WHATSAPP CHANNEL TEST")
        print("-" * 40)
        wa_msg = args.message or "Hello from WhatsApp test! What services do you offer?"
        results["whatsapp"] = test_whatsapp_webhook(args.url, wa_msg)
        print()

    # Test Telegram
    if args.telegram or args.all:
        print("-" * 40)
        print("📱 TELEGRAM CHANNEL TEST")
        print("-" * 40)
        tg_msg = args.message or "Hello from Telegram test! Tell me about W3J Consulting."
        results["telegram"] = test_telegram_webhook(args.url, tg_msg)
        print()

    # Multilingual tests
    if args.multilingual:
        print("-" * 40)
        print("🌐 MULTILINGUAL MESSAGE TESTS")
        print("-" * 40)
        lang_results = test_multilingual_messages(args.url)
        results["multilingual"] = all(lang_results.values())
        print()

    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    for test_name, success in results.items():
        if success:
            log_success(f"{test_name.upper()}: PASSED")
            passed += 1
        else:
            log_error(f"{test_name.upper()}: FAILED")
            failed += 1

    print()
    print(f"Total: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
