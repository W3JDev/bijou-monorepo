#!/usr/bin/env python3
"""
Channel base - abstract interface for messaging channels.
=========================================================

Defines the contract all channel adapters must implement (send_text, send_image, reaction).
UnifiedMessage: channel-agnostic message format for incoming webhooks.

Author: W3J Bijou Enterprise
Architecture: docs/SAAS_ARCHITECTURE.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class UnifiedMessage:
    """
    Channel-agnostic message format for incoming webhooks (WhatsApp, Telegram, etc.).
    Maps to our internal processing format.
    """

    id: str
    chat_jid: str  # Channel-specific chat ID (e.g. 60123456789@s.whatsapp.net or TG chat_id)
    sender: str
    content: str
    timestamp: str
    is_from_me: bool = False
    media_type: Optional[str] = None
    filename: Optional[str] = None
    media_url: Optional[str] = None
    channel: str = "whatsapp"  # "whatsapp" | "telegram"

    def to_dict(self) -> dict:
        """Convert to dict for process_message compatibility."""
        return {
            "id": self.id,
            "message_id": self.id,
            "chat_jid": self.chat_jid,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
            "is_from_me": self.is_from_me,
            "media_type": self.media_type,
            "filename": self.filename,
            "media_url": self.media_url,
            "channel": self.channel,
        }


class BaseChannel(ABC):
    """
    Abstract base for channel adapters (WhatsApp bridge, future Telegram, etc.).
    """

    @abstractmethod
    def send_text(self, recipient: str, text: str) -> bool:
        """
        Send a text message to the recipient.

        Args:
            recipient: Channel-specific recipient ID (e.g. chat_jid for WhatsApp).
            text: Plain text message body.

        Returns:
            True if sent successfully, False otherwise.
        """
        ...

    @abstractmethod
    def send_image(
        self,
        recipient: str,
        image_path: str,
        caption: Optional[str] = None,
    ) -> bool:
        """
        Send an image to the recipient.

        Args:
            recipient: Channel-specific recipient ID.
            image_path: Local file path or URL the bridge can use to send the image.
            caption: Optional caption.

        Returns:
            True if sent successfully, False otherwise.
        """
        ...

    @abstractmethod
    def reaction(self, recipient: str, message_id: str, emoji: str) -> bool:
        """
        Send a reaction (e.g. thumbs up) to a message.

        Args:
            recipient: Channel-specific recipient/chat ID.
            message_id: ID of the message to react to.
            emoji: Reaction emoji (e.g. "👍", "❤️").

        Returns:
            True if reaction was sent successfully, False otherwise.
        """
        ...

    def send_typing_action(self, recipient: str) -> bool:
        """
        Send typing indicator to recipient (e.g. "typing..." in chat).

        Optional - default is no-op. Override in adapters that support it.

        Args:
            recipient: Channel-specific recipient/chat ID.

        Returns:
            True if typing was sent successfully, False otherwise.
        """
        return False
