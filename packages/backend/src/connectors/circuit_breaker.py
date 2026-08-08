"""Per-backend circuit breaker with injectable clock."""
from __future__ import annotations
import time
from typing import Callable


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0,
                 now: Callable[[], float] = time.monotonic):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._now = now
        self._failures = 0
        self._state = "closed"
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        if self._state == "open" and self._now() - self._opened_at >= self.cooldown_seconds:
            self._state = "half_open"
        return self._state

    def is_open(self) -> bool:
        return self.state == "open"

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = "open"
            self._opened_at = self._now()
