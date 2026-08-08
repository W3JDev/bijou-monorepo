#!/usr/bin/env python3
"""
LLM Gateway - Key Rotator (Brain)
=================================

Loads GEMINI_API_KEYS from environment (comma-separated), provides round-robin
rotation with automatic cooldown on 429 (rate limit) so the next key is used.

Author: W3J Bijou Enterprise
Architecture: docs/SAAS_ARCHITECTURE.md
"""

import logging
import os
import time
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Default cooldown seconds when a key returns 429
DEFAULT_COOLDOWN_SECONDS = 60


class RoundRobinRotator:
    """
    Rotates over a list of API keys. On 429 (rate limit), marks the current key
    as in cooldown and uses the next key until cooldown expires.
    """

    def __init__(
        self,
        keys: Optional[List[str]] = None,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        """
        Initialize the rotator.

        Args:
            keys: List of API keys. If None, loads from env GEMINI_API_KEYS (comma-separated).
            cooldown_seconds: How long to skip a key after it returns 429.
        """
        if keys is None:
            raw = os.getenv("GEMINI_API_KEYS", "").strip()
            keys = [k.strip() for k in raw.split(",") if k.strip()]
            # Fallback to GEMINI_API_KEY for backward compatibility
            if not keys:
                single = os.getenv("GEMINI_API_KEY", "").strip()
                if single:
                    keys = [single]
        self._keys: List[str] = keys
        self._cooldown_seconds = cooldown_seconds
        self._index = 0
        # key -> (cooldown_until_timestamp,)
        self._cooldown_until: dict[str, float] = {}

        if not self._keys:
            logger.warning("RoundRobinRotator: no API keys provided (GEMINI_API_KEYS empty or missing)")

    def get_next_key(self) -> Optional[str]:
        """
        Return the next available key (round-robin). Keys in cooldown are skipped.

        Returns:
            An API key string, or None if no keys or all are in cooldown.
        """
        if not self._keys:
            return None

        now = time.monotonic()
        # Clear expired cooldowns
        for k in list(self._cooldown_until):
            if self._cooldown_until[k] <= now:
                del self._cooldown_until[k]

        start = self._index
        while True:
            key = self._keys[self._index]
            self._index = (self._index + 1) % len(self._keys)
            if key not in self._cooldown_until or self._cooldown_until[key] <= now:
                return key
            if self._index == start:
                # All keys in cooldown; return the one that expires soonest
                soonest = min(self._cooldown_until.values())
                if soonest > now:
                    logger.warning(
                        "All keys in cooldown until %.0fs from now", soonest - now
                    )
                return key
        return None

    def mark_rate_limited(self, key: str) -> None:
        """
        Mark a key as rate-limited (429). It will be skipped until cooldown expires.

        Args:
            key: The API key that returned 429.
        """
        self._cooldown_until[key] = time.monotonic() + self._cooldown_seconds
        logger.info(
            "Key marked rate-limited (429); cooldown %.0fs", self._cooldown_seconds
        )

    def is_rate_limit_response(self, status_code: int) -> bool:
        """Return True if status_code indicates rate limit (429)."""
        return status_code == 429
