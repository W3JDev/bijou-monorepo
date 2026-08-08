#!/usr/bin/env python3
"""
Bridge Adapter - WhatsApp bridge (whatsapp-bridge) channel.
=============================================================

Sends messages via HTTP POST to the local WhatsApp bridge (default localhost:8080),
matching existing whatsapp-bridge logic: POST /api/send with recipient, message, optional media_path.

Author: W3J Bijou Enterprise
Architecture: docs/SAAS_ARCHITECTURE.md
"""

import logging
import os
import re
from typing import Optional

import requests
from dotenv import load_dotenv

from .base import BaseChannel

load_dotenv()

logger = logging.getLogger(__name__)


class BridgeAdapter(BaseChannel):
    """
    Channel adapter that talks to the WhatsApp bridge (Go whatsmeow) over HTTP.
    Bridge base URL is read from BRIDGE_URL (default http://localhost:8080).
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0, api_key: Optional[str] = None) -> None:
        """
        Initialize the bridge adapter.

        Args:
            base_url: Bridge base URL (e.g. http://localhost:8080). Defaults to BRIDGE_URL env.
            timeout: Request timeout in seconds.
            api_key: Bridge API key for authentication. Defaults to BRIDGE_API_KEY env.
        """
        self._base_url = (
            base_url or os.getenv("BRIDGE_URL", "http://localhost:8080")
        ).rstrip("/")
        self._timeout = timeout
        self._api_key = api_key or os.getenv("BRIDGE_API_KEY", "")
    
    def _get_headers(self) -> dict:
        """Get common headers including API key authentication."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def send_text(self, recipient: str, text: str) -> bool:
        """
        Send a text message via bridge POST /api/send.

        Args:
            recipient: chat_jid (e.g. 60123456789@s.whatsapp.net).
            text: Message body.

        Returns:
            True if bridge returned success, False otherwise.
        """
        # FORCE CLEAN: Strip all Markdown formatting for WhatsApp
        clean_text = self._strip_markdown(text)

        url = f"{self._base_url}/api/send"
        payload = {"recipient": recipient, "message": clean_text}
        try:
            resp = requests.post(url, json=payload, headers=self._get_headers(), timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success", False):
                    logger.debug(
                        "Sent to %s: %s...",
                        recipient,
                        (text[:50] + "..." if len(text) > 50 else text),
                    )
                    return True
                logger.warning("Bridge send failed: %s", data)
                return False
            logger.error("Bridge send HTTP %s", resp.status_code)
            return False
        except requests.RequestException as e:
            logger.error("Bridge send error: %s", e)
            return False

    def send_image(
        self,
        recipient: str,
        image_path: str,
        caption: Optional[str] = None,
    ) -> bool:
        """
        Send an image via bridge POST /api/send with media_path.
        Caption is sent as message when media_path is set (bridge accepts both).

        Args:
            recipient: chat_jid.
            image_path: Local path the bridge can read (e.g. store/.../image.jpg).
            caption: Optional caption; sent as message field along with media_path.

        Returns:
            True if bridge returned success, False otherwise.
        """
        url = f"{self._base_url}/api/send"
        # Strip markdown from caption too
        clean_caption = self._strip_markdown(caption) if caption else ""

        payload: dict = {
            "recipient": recipient,
            "media_path": image_path,
        }
        if clean_caption:
            payload["message"] = clean_caption
        else:
            payload["message"] = ""
        try:
            resp = requests.post(url, json=payload, headers=self._get_headers(), timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success", False):
                    logger.debug("Sent image to %s", recipient)
                    return True
                logger.warning("Bridge send image failed: %s", data)
                return False
            logger.error("Bridge send image HTTP %s", resp.status_code)
            return False
        except requests.RequestException as e:
            logger.error("Bridge send image error: %s", e)
            return False

    def reaction(self, recipient: str, message_id: str, emoji: str) -> bool:
        """
        Send a reaction to a message. The current whatsapp-bridge may not expose
        a reaction endpoint; this is a stub for future bridge support.

        Args:
            recipient: chat_jid.
            message_id: ID of the message to react to.
            emoji: Reaction emoji (e.g. "👍").

        Returns:
            True if supported and successful; False if not supported or error.
        """
        # Bridge does not yet expose POST /api/reaction; log and return False
        logger.debug(
            "Reaction not implemented by bridge: recipient=%s message_id=%s emoji=%s",
            recipient,
            message_id,
            emoji,
        )
        return False

    def send_document(
        self,
        recipient: str,
        document_path: str,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> bool:
        """
        Send a document/PDF via bridge POST /api/send with media_path.
        
        Args:
            recipient: chat_jid.
            document_path: Local path to document (PDF, DOCX, TXT, etc.).
            filename: Original filename to display (optional).
            caption: Optional caption.
            
        Returns:
            True if bridge returned success, False otherwise.
        """
        url = f"{self._base_url}/api/send"
        clean_caption = self._strip_markdown(caption) if caption else ""
        
        payload: dict = {
            "recipient": recipient,
            "media_path": document_path,
        }
        if clean_caption:
            payload["message"] = clean_caption
        else:
            payload["message"] = ""
            
        try:
            resp = requests.post(url, json=payload, headers=self._get_headers(), timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success", False):
                    logger.debug("Sent document to %s: %s", recipient, filename or document_path)
                    return True
                logger.warning("Bridge send document failed: %s", data)
                return False
            logger.error("Bridge send document HTTP %s", resp.status_code)
            return False
        except requests.RequestException as e:
            logger.error("Bridge send document error: %s", e)
            return False

    def send_media(
        self,
        recipient: str,
        media_path: str,
        media_type: str = "auto",
        caption: Optional[str] = None,
    ) -> bool:
        """
        Send any media file (image, video, audio, document) via bridge.
        Auto-detects media type from file extension.
        
        Args:
            recipient: chat_jid.
            media_path: Local path to media file.
            media_type: Type hint ("image", "video", "audio", "document", or "auto").
            caption: Optional caption with support for links.
            
        Returns:
            True if bridge returned success, False otherwise.
            
        Note:
            WhatsApp automatically renders URLs as clickable links in captions.
            Example caption: "Check out https://example.com for more info!"
        """
        url = f"{self._base_url}/api/send"
        
        # Caption can include URLs - WhatsApp will make them clickable
        clean_caption = self._strip_markdown(caption) if caption else ""
        
        payload: dict = {
            "recipient": recipient,
            "media_path": media_path,
            "message": clean_caption,
        }
        
        try:
            resp = requests.post(url, json=payload, headers=self._get_headers(), timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success", False):
                    logger.debug("Sent media to %s: %s", recipient, media_path)
                    return True
                logger.warning("Bridge send media failed: %s", data)
                return False
            logger.error("Bridge send media HTTP %s", resp.status_code)
            return False
        except requests.RequestException as e:
            logger.error("Bridge send media error: %s", e)
            return False

    def send_audio(
        self,
        recipient: str,
        audio_path: str,
        ptt: bool = True,
    ) -> bool:
        """
        Send an audio file (voice note) via bridge POST /api/send with media_path.
        
        Args:
            recipient: chat_jid.
            audio_path: Local path to audio file (OGG/Opus preferred for WhatsApp).
            ptt: If True, sends as Push-To-Talk voice note (default for voice replies).
            
        Returns:
            True if bridge returned success, False otherwise.
        """
        url = f"{self._base_url}/api/send"
        
        payload: dict = {
            "recipient": recipient,
            "media_path": audio_path,
            "message": "",  # No caption for voice messages
        }
        
        # Some bridges support a `ptt` flag to send as voice note instead of audio file
        if ptt:
            payload["ptt"] = True
        
        try:
            resp = requests.post(url, json=payload, headers=self._get_headers(), timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success", False):
                    logger.info("🎤 Sent voice note to %s", recipient)
                    return True
                logger.warning("Bridge send audio failed: %s", data)
                return False
            logger.error("Bridge send audio HTTP %s", resp.status_code)
            return False
        except requests.RequestException as e:
            logger.error("Bridge send audio error: %s", e)
            return False

    def send_typing_action(self, recipient: str) -> bool:
        """
        Send typing indicator via bridge. Tries POST /api/typing if bridge supports it.

        WhatsApp bridge may expose typing/presence in future; no-op if not available.
        """
        url = f"{self._base_url}/api/typing"
        try:
            resp = requests.post(
                url,
                json={"recipient": recipient, "action": "composing"},
                timeout=2.0, # FAST timeout so we don't block main thread
            )
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            # Silently fail - typing indicators are optional polish
            pass
        # logger.debug("Typing indicator not supported or failed (no-op)")
        return False

    def _strip_markdown(self, text: str) -> str:
        """
        Remove ALL markdown formatting from text for WhatsApp.

        Removes:
        - Bold: ** __
        - Italic: * _
        - Headers: ## ### ####
        - Code blocks: ``` `
        - Strikethrough: ~~

        Args:
            text: Text with potential markdown

        Returns:
            Clean plain text
        """
        if not text:
            return text

        # Remove bold (**text** or __text__)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)

        # Remove italic (*text* or _text_)
        # Be careful not to remove single * used as bullet points at start of line
        text = re.sub(r"(?<!\s)\*(.+?)\*(?!\s)", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)

        # Remove headers (### Header or ## Header)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove inline code (`code`)
        text = re.sub(r"`(.+?)`", r"\1", text)

        # Remove code blocks (```code```)
        text = re.sub(r"```[\s\S]*?```", "", text)

        # Remove strikethrough (~~text~~)
        text = re.sub(r"~~(.+?)~~", r"\1", text)

        # Clean up any remaining ** or __ that might have been missed
        text = text.replace("**", "").replace("__", "")

        return text.strip()
