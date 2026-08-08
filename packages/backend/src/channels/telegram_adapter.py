#!/usr/bin/env python3
"""
Telegram Adapter - python-telegram-bot channel.
================================================

Implements BaseChannel for Telegram. Uses async python-telegram-bot.
Provides webhook_handler to convert TG updates into UnifiedMessage format.

Author: W3J Bijou Enterprise
Architecture: docs/SAAS_ARCHITECTURE.md
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Callable, Optional

from dotenv import load_dotenv

from .base import BaseChannel, UnifiedMessage

load_dotenv()

logger = logging.getLogger(__name__)

# Optional: python-telegram-bot (add to requirements: python-telegram-bot>=22.0)
try:
    from telegram import Bot, Update
    from telegram.ext import Application, MessageHandler, filters
    from telegram.request import HTTPXRequest

    TG_AVAILABLE = True
except ImportError:
    TG_AVAILABLE = False
    Bot = None
    Update = None
    Application = None


class TelegramAdapter(BaseChannel):
    """
    Channel adapter for Telegram using python-telegram-bot (async).
    """

    def __init__(
        self,
        token: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the Telegram adapter.

        Args:
            token: Bot token. Defaults to TELEGRAM_BOT_TOKEN env.
            timeout: Request timeout in seconds.
        """
        if not TG_AVAILABLE:
            raise ImportError(
                "python-telegram-bot not installed. Run: pip install python-telegram-bot>=22.0"
            )
        self._token = (token or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
        if not self._token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set")
        self._timeout = timeout
        self._bot = Bot(
            token=self._token,
            request=HTTPXRequest(read_timeout=timeout, write_timeout=timeout),
        )

    def send_text(self, recipient: str, text: str) -> bool:
        """
        Send a text message to the recipient (chat_id) using sync HTTP.

        Args:
            recipient: Telegram chat_id (str or int as string).
            text: Message body.

        Returns:
            True if sent successfully, False otherwise.
        """
        import httpx

        try:
            # Strip markdown formatting for cleaner Telegram display
            text = (
                text.replace("**", "")
                .replace("__", "")
                .replace("*", "")
                .replace("_", "")
            )

            chat_id = int(recipient) if recipient.isdigit() else recipient
            url = f"https://api.telegram.org/bot{self._token}/sendMessage"
            payload = {"chat_id": chat_id, "text": text}

            # Use sync httpx client for reliable sync calls
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

            if result.get("ok"):
                logger.debug(
                    "Sent to TG %s: %s...",
                    recipient,
                    (text[:50] + "..." if len(text) > 50 else text),
                )
                return True
            else:
                logger.error("Telegram API error: %s", result.get("description"))
                return False
        except Exception as e:
            logger.error("Telegram send_text error: %s", e)
            return False

    async def send_text_async(self, recipient: str, text: str) -> bool:
        """
        Async: Send a text message to the recipient (chat_id).

        Args:
            recipient: Telegram chat_id (str or int as string).
            text: Message body.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            # Strip markdown formatting for cleaner Telegram display
            text = (
                text.replace("**", "")
                .replace("__", "")
                .replace("*", "")
                .replace("_", "")
            )

            chat_id = int(recipient) if recipient.isdigit() else recipient
            result = await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                read_timeout=self._timeout,
                write_timeout=self._timeout,
            )
            logger.debug(
                "Sent to TG %s: %s...",
                recipient,
                (text[:50] + "..." if len(text) > 50 else text),
            )
            return result is not None
        except Exception as e:
            logger.error("Telegram send_text_async error: %s", e)
            return False

    def send_image(
        self,
        recipient: str,
        image_path: str,
        caption: Optional[str] = None,
    ) -> bool:
        """
        Send an image to the recipient using sync HTTP.

        Args:
            recipient: Telegram chat_id.
            image_path: Local path or URL.
            caption: Optional caption.

        Returns:
            True if sent successfully, False otherwise.
        """
        import httpx

        try:
            chat_id = int(recipient) if recipient.isdigit() else recipient
            url = f"https://api.telegram.org/bot{self._token}/sendPhoto"

            with httpx.Client(timeout=self._timeout) as client:
                if image_path.startswith(("http://", "https://")):
                    # URL-based photo
                    payload = {
                        "chat_id": chat_id,
                        "photo": image_path,
                        "caption": caption or "",
                    }
                    response = client.post(url, json=payload)
                else:
                    # File upload
                    with open(image_path, "rb") as f:
                        files = {"photo": f}
                        data = {"chat_id": chat_id, "caption": caption or ""}
                        response = client.post(url, data=data, files=files)

                response.raise_for_status()
                result = response.json()

            if result.get("ok"):
                logger.debug("Sent image to TG %s", recipient)
                return True
            else:
                logger.error("Telegram API error: %s", result.get("description"))
                return False
        except Exception as e:
            logger.error("Telegram send_image error: %s", e)
            return False

    def reaction(self, recipient: str, message_id: str, emoji: str) -> bool:
        """
        Send a reaction to a message using sync HTTP.

        Args:
            recipient: Telegram chat_id.
            message_id: ID of the message to react to.
            emoji: Reaction emoji (e.g. "👍", "❤️").

        Returns:
            True if reaction was sent successfully, False otherwise.
        """
        import httpx

        try:
            chat_id = int(recipient) if recipient.isdigit() else recipient
            msg_id = int(message_id)
            url = f"https://api.telegram.org/bot{self._token}/setMessageReaction"
            payload = {
                "chat_id": chat_id,
                "message_id": msg_id,
                "reaction": [{"type": "emoji", "emoji": emoji}],
            }

            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

            if result.get("ok"):
                logger.debug(
                    "Reaction sent to TG %s msg %s: %s", recipient, message_id, emoji
                )
                return True
            else:
                logger.error("Telegram API error: %s", result.get("description"))
                return False
        except Exception as e:
            logger.error("Telegram reaction error: %s", e)
            return False

    def send_typing_action(self, recipient: str) -> bool:
        """
        Send typing indicator via Telegram sendChatAction API.
        """
        import httpx

        try:
            chat_id = int(recipient) if recipient.lstrip("-").isdigit() else recipient
            url = f"https://api.telegram.org/bot{self._token}/sendChatAction"
            payload = {"chat_id": chat_id, "action": "typing"}
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                result = response.json()
            if result.get("ok"):
                return True
        except Exception as e:
            logger.debug("Telegram typing action failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Webhook handler: convert TG Update -> UnifiedMessage
# ---------------------------------------------------------------------------


def webhook_handler(
    update: "Update",
    on_message: Optional[Callable[[dict], None]] = None,
) -> Optional[UnifiedMessage]:
    """
    Convert a Telegram Update into UnifiedMessage and optionally invoke callback.

    Use this when receiving webhook POSTs from Telegram. Decode the JSON body
    to an Update, then call this function.

    Args:
        update: Telegram Update object (from Update.de_json(...)).
        on_message: Callback to invoke with the UnifiedMessage (e.g. BijouAI.process_message).

    Returns:
        UnifiedMessage if the update contained a processable message, else None.
    """
    if not update or not update.message:
        return None

    msg = update.message
    chat = msg.chat
    user = msg.from_user
    if not chat or not user:
        return None

    # Build content from text or caption
    content = msg.text or msg.caption or ""

    # Media handling
    media_type = None
    media_url = None
    filename = None

    if msg.photo:
        media_type = "image"
        # Largest photo
        photo = msg.photo[-1]
        if photo.file_id:
            media_url = f"tg://file/bot?file_id={photo.file_id}"
        filename = f"photo_{msg.message_id}.jpg"
    elif msg.document:
        media_type = "document"
        doc = msg.document
        filename = doc.file_name or f"doc_{msg.message_id}"
        if doc.file_id:
            media_url = f"tg://file/bot?file_id={doc.file_id}"
    elif msg.audio:
        media_type = "audio"
        filename = (
            getattr(msg.audio, "file_name", None) or f"audio_{msg.message_id}.ogg"
        )
        if msg.audio.file_id:
            media_url = f"tg://file/bot?file_id={msg.audio.file_id}"
    elif msg.voice:
        media_type = "ptt"
        filename = f"voice_{msg.message_id}.ogg"
        if msg.voice.file_id:
            media_url = f"tg://file/bot?file_id={msg.voice.file_id}"
    elif msg.video:
        media_type = "video"
        filename = (
            getattr(msg.video, "file_name", None) or f"video_{msg.message_id}.mp4"
        )
        if msg.video.file_id:
            media_url = f"tg://file/bot?file_id={msg.video.file_id}"
    elif msg.sticker:
        media_type = "sticker"
        if msg.sticker.file_id:
            media_url = f"tg://file/bot?file_id={msg.sticker.file_id}"

    # Timestamp
    ts = msg.date.isoformat() if msg.date else datetime.utcnow().isoformat()

    # Chat ID as string (used as chat_jid in our unified format)
    chat_id = str(chat.id)
    sender_id = str(user.id)
    sender_name = user.username or user.first_name or sender_id
    sender = f"{sender_name} ({sender_id})"

    unified = UnifiedMessage(
        id=str(msg.message_id),
        chat_jid=chat_id,
        sender=sender,
        content=content,
        timestamp=ts,
        is_from_me=False,
        media_type=media_type,
        filename=filename,
        media_url=media_url,
        channel="telegram",
    )

    if on_message:
        try:
            on_message(unified.to_dict())
        except Exception as e:
            logger.error("webhook_handler on_message callback error: %s", e)

    return unified


def create_telegram_webhook_app(
    on_message: Callable[[dict], None],
    token: Optional[str] = None,
) -> "Application":
    """
    Create a python-telegram-bot Application configured for webhook mode.
    The application will convert incoming updates to UnifiedMessage and call on_message.

    Args:
        token: Bot token. Defaults to TELEGRAM_BOT_TOKEN.
        on_message: Callback for each incoming message (e.g. BijouAI.process_message).

    Returns:
        telegram.ext.Application instance.
    """
    if not TG_AVAILABLE:
        raise ImportError("python-telegram-bot not installed")

    tok = (token or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
    if not tok:
        raise ValueError("TELEGRAM_BOT_TOKEN must be set")

    async def handle_update(update: Update, context) -> None:
        """Internal handler that converts Update -> UnifiedMessage and invokes callback."""
        # Convert to UnifiedMessage and process (sync callback)
        msg = webhook_handler(update, on_message=on_message)
        if msg:
            logger.info("Processed TG message %s from %s", msg.id, msg.chat_jid)

    app = Application.builder().token(tok).build()
    app.add_handler(
        MessageHandler(
            filters.TEXT
            | filters.PHOTO
            | filters.VIDEO
            | filters.Document.ALL
            | filters.VOICE
            | filters.AUDIO
            | filters.STICKER,
            handle_update,
        )
    )
    return app
