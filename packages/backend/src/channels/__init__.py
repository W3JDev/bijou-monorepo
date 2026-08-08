"""
Channel adapters for Bijou SaaS.

- BaseChannel: abstract interface (send_text, send_image, reaction).
- BridgeAdapter: WhatsApp bridge (HTTP POST to localhost:8080).
- TelegramAdapter: Telegram (python-telegram-bot async).
- UnifiedMessage: channel-agnostic message format for webhooks.
"""

from .base import BaseChannel, UnifiedMessage
from .bridge_adapter import BridgeAdapter

try:
    from .telegram_adapter import (
        TelegramAdapter,
        create_telegram_webhook_app,
        webhook_handler as telegram_webhook_handler,
    )
except ImportError:
    TelegramAdapter = None  # type: ignore
    create_telegram_webhook_app = None  # type: ignore
    telegram_webhook_handler = None  # type: ignore

__all__ = [
    "BaseChannel",
    "BridgeAdapter",
    "TelegramAdapter",
    "UnifiedMessage",
    "create_telegram_webhook_app",
    "telegram_webhook_handler",
]
