"""
Circuit Breaker for Gemini API Calls
=====================================

Prevents cascading failures when Gemini API is slow or down.

Features:
- Auto-opens circuit after 5 consecutive failures
- Auto-closes circuit after 60 seconds (recovery timeout)
- Timeout protection (5 seconds max per call)
- Fallback responses when circuit is open
- Thread-safe implementation

Usage:
    from src.utils.circuit_breaker import gemini_with_fallback
    
    response = await gemini_with_fallback(
        client=genai_client,
        model_name="gemini-2.0-flash-exp",
        prompt="Hello",
        fallback_fn=lambda: "I'm experiencing technical difficulties..."
    )

Author: W3J Bijou AI
Version: 1.0.0
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, reject all calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for Gemini API calls.
    
    Protects against cascading failures by:
    1. Tracking consecutive failures
    2. Opening circuit after threshold (default: 5 failures)
    3. Rejecting calls immediately when circuit is open
    4. Auto-recovery after timeout (default: 60 seconds)
    """
    
    def __init__(
        self,
        name: str = "gemini",
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        call_timeout: int = 5,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.call_timeout = call_timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.state != CircuitState.OPEN:
            return False
        
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            # Recovery successful
            logger.info(f"🔓 [{self.name}] Circuit breaker CLOSED - service recovered")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.debug(f"✅ [{self.name}] Call succeeded, resetting failure count")
                self.failure_count = 0
    
    def _on_failure(self, error: Exception):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(
            f"⚠️ [{self.name}] Call failed ({self.failure_count}/{self.failure_threshold}): {error}"
        )
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(
                    f"🔒 [{self.name}] Circuit breaker OPENED after {self.failure_count} failures"
                )
                self.state = CircuitState.OPEN
    
    async def call(
        self, 
        func: Callable, 
        fallback: Optional[Callable] = None,
        *args, 
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call (should be async)
            fallback: Optional fallback function if circuit is open
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Result from func or fallback
            
        Raises:
            Exception: If circuit is open and no fallback provided
        """
        # Check if we should attempt recovery
        if self._should_attempt_reset():
            logger.info(f"🔄 [{self.name}] Circuit breaker entering HALF_OPEN state")
            self.state = CircuitState.HALF_OPEN
        
        # If circuit is open, use fallback immediately
        if self.state == CircuitState.OPEN:
            logger.warning(
                f"⚡ [{self.name}] Circuit is OPEN - using fallback "
                f"(recovery in {self.recovery_timeout - (datetime.now() - self.last_failure_time).total_seconds():.0f}s)"
            )
            if fallback:
                return fallback() if not asyncio.iscoroutinefunction(fallback) else await fallback()
            raise Exception(f"Circuit breaker is OPEN for {self.name}")
        
        # Attempt call with timeout
        try:
            logger.debug(f"🔵 [{self.name}] Attempting call (timeout: {self.call_timeout}s)")
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.call_timeout)
            self._on_success()
            return result
            
        except asyncio.TimeoutError as e:
            logger.error(f"⏱️ [{self.name}] Call timed out after {self.call_timeout}s")
            self._on_failure(e)
            if fallback:
                return fallback() if not asyncio.iscoroutinefunction(fallback) else await fallback()
            raise
            
        except Exception as e:
            logger.error(f"❌ [{self.name}] Call failed: {e}")
            self._on_failure(e)
            if fallback:
                return fallback() if not asyncio.iscoroutinefunction(fallback) else await fallback()
            raise


# Global circuit breakers for different services
_gemini_breaker = CircuitBreaker(
    name="gemini-api",
    failure_threshold=5,
    recovery_timeout=60,
    call_timeout=5,
)

_lead_analysis_breaker = CircuitBreaker(
    name="lead-analysis",
    failure_threshold=3,
    recovery_timeout=30,
    call_timeout=3,
)

_handover_detection_breaker = CircuitBreaker(
    name="handover-detection",
    failure_threshold=3,
    recovery_timeout=30,
    call_timeout=3,
)


async def gemini_with_fallback(
    client: Any,
    model_name: str,
    prompt: str,
    fallback_fn: Optional[Callable] = None,
    use_json: bool = False,
) -> Any:
    """
    Call Gemini API with circuit breaker protection and fallback.
    
    Args:
        client: Gemini client instance
        model_name: Model to use (e.g., "gemini-2.0-flash-exp")
        prompt: Prompt to send
        fallback_fn: Optional fallback function (returns response or dict)
        use_json: Whether to expect JSON response
        
    Returns:
        Gemini response or fallback response
        
    Example:
        response = await gemini_with_fallback(
            client=genai_client,
            model_name="gemini-2.0-flash-exp",
            prompt="Analyze this message...",
            fallback_fn=lambda: {"wants_human": False, "reason": "AI unavailable"}
        )
    """
    async def call_gemini():
        """Wrapper to make Gemini call async-compatible"""
        # Gemini SDK is sync, but we can await it
        if use_json:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
        else:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
        return response
    
    return await _gemini_breaker.call(
        call_gemini,
        fallback=fallback_fn
    )


async def lead_analysis_with_fallback(
    client: Any,
    model_name: str,
    prompt: str,
    fallback_fn: Optional[Callable] = None,
) -> Any:
    """
    Call Gemini for lead analysis with circuit breaker.
    
    Separate breaker from main Gemini calls to avoid false positives
    from lead analysis affecting critical message responses.
    """
    async def call_gemini():
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return response
    
    return await _lead_analysis_breaker.call(
        call_gemini,
        fallback=fallback_fn
    )


async def handover_detection_with_fallback(
    client: Any,
    model_name: str,
    prompt: str,
    fallback_fn: Optional[Callable] = None,
) -> Any:
    """
    Call Gemini for handover detection with circuit breaker.
    
    Separate breaker to protect critical escalation detection.
    """
    async def call_gemini():
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return response
    
    return await _handover_detection_breaker.call(
        call_gemini,
        fallback=fallback_fn
    )


# Fallback response generators
def escalation_fallback(message: str) -> tuple:
    """
    Fallback for handover detection when AI is down.
    Uses keyword-based detection as last resort.
    """
    message_lower = message.lower()
    
    # Critical escalation keywords that always trigger
    urgent_keywords = [
        "speak to owner",
        "talk to manager",
        "connect me to",
        "real person now",
        "human agent",
        "not helping",
        "useless bot",
    ]
    
    for keyword in urgent_keywords:
        if keyword in message_lower:
            logger.info(f"🔴 Fallback: Escalation triggered by keyword: '{keyword}'")
            return (True, f"Fallback keyword detection: {keyword}", "urgent")
    
    # Default: no escalation
    logger.info("🟢 Fallback: No escalation keywords found")
    return (False, "AI unavailable, using fallback detection", "none")


def lead_scoring_fallback() -> dict:
    """
    Fallback for lead analysis when AI is down.
    Returns COLD status to avoid false hot leads.
    """
    logger.info("❄️ Fallback: Marking lead as COLD (AI unavailable)")
    return {
        "status": "COLD",
        "confidence": 0,
        "reason": "AI lead analysis unavailable",
        "qualification_data": {},
    }


def response_generation_fallback() -> str:
    """
    Fallback response when AI is down.
    Human-like message indicating temporary issues.
    """
    return (
        "Hi! I'm experiencing some technical difficulties at the moment. "
        "Let me connect you with our team who can help you right away."
    )


async def safe_gemini_call(
    func: Callable,
    *args,
    timeout: int = 5,
    fallback: Optional[Callable] = None,
    **kwargs,
) -> Any:
    """
    Call any Gemini-related function with a hard timeout and optional fallback.

    Enforces a timeout (default: 5 seconds) via asyncio.wait_for to prevent
    indefinite hangs when the Gemini API is slow or unresponsive.

    Args:
        func: Async callable to execute
        *args: Positional arguments forwarded to func
        timeout: Max seconds before TimeoutError (default 5)
        fallback: Optional callable returning a default value on failure
        **kwargs: Keyword arguments forwarded to func

    Returns:
        Result of func(*args, **kwargs) or fallback() on error
    """
    try:
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ safe_gemini_call: timed out after {timeout}s")
        if fallback:
            return fallback()
        raise
    except Exception as e:
        logger.error(f"❌ safe_gemini_call: failed: {e}")
        if fallback:
            return fallback()
        raise
