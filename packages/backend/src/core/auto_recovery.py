"""
W3J Bijou AI - Self-Healing & Auto-Recovery System
===================================================

Automatic failure detection and recovery mechanisms for production reliability.

Features:
- Automatic retry with exponential backoff
- Fallback mechanisms for each component
- Circuit breaker pattern
- Graceful degradation
- Error logging and alerting

Author: W3J Bijou AI
Version: 2.1.0
"""

import time
import logging
from typing import Callable, Any, Optional, Dict
from functools import wraps
from enum import Enum


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, using fallback
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping calls to failing services
    and providing fallback mechanisms.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker.

        Args:
            func: Function to call
            *args, **kwargs: Function arguments

        Returns:
            Function result or raises exception
        """
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker HALF_OPEN: Testing recovery")
            else:
                raise Exception(f"Circuit breaker OPEN: Service unavailable")

        try:
            result = func(*args, **kwargs)

            # Success! Close circuit if it was half-open
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker CLOSED: Service recovered")

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(
                    f"Circuit breaker OPEN: Too many failures ({self.failure_count})"
                )

            raise


class AutoRecovery:
    """
    Automatic recovery mechanisms for Bijou AI components.
    """

    def __init__(self):
        # Circuit breakers for each component
        self.bridge_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.gemini_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self.sheets_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120)

        # Fallback providers
        self.fallback_enabled = True

    @staticmethod
    def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        exceptions: tuple = (Exception,),
    ) -> Callable:
        """
        Decorator for automatic retry with exponential backoff.

        Args:
            func: Function to wrap
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            exceptions: Tuple of exceptions to catch

        Returns:
            Wrapped function with retry logic
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = base_delay

            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    retries += 1

                    if retries > max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    wait_time = min(delay, max_delay)
                    logger.warning(
                        f"{func.__name__} failed (attempt {retries}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )

                    time.sleep(wait_time)
                    delay *= exponential_base

            raise Exception(f"{func.__name__} failed after all retries")

        return wrapper

    def send_message_with_recovery(
        self, bridge_send_func: Callable, recipient: str, message: str
    ) -> bool:
        """
        Send message with automatic retry and fallback.

        Args:
            bridge_send_func: Function to send message via bridge
            recipient: Recipient JID
            message: Message text

        Returns:
            True if sent successfully
        """
        try:
            # Try primary method with circuit breaker
            return self.bridge_breaker.call(
                self._send_with_retry, bridge_send_func, recipient, message
            )

        except Exception as e:
            logger.error(f"Bridge send failed with recovery: {e}")

            # Fallback: Queue message for later
            if self.fallback_enabled:
                self._queue_failed_message(recipient, message)
                return False

            raise

    @staticmethod
    def _send_with_retry(send_func: Callable, recipient: str, message: str) -> bool:
        """Internal method with retry logic"""

        @AutoRecovery.retry_with_backoff
        def send():
            return send_func(recipient, message)

        return send()

    def _queue_failed_message(self, recipient: str, message: str):
        """Queue message for retry later"""
        # TODO: Implement message queue (Redis or local file)
        logger.warning(f"Queued message for retry: {recipient}")
        pass

    def generate_response_with_fallback(
        self, primary_func: Callable, fallback_func: Callable, *args, **kwargs
    ) -> Any:
        """
        Try primary AI generation with automatic fallback.

        Args:
            primary_func: Primary AI function (Gemini)
            fallback_func: Fallback function (simple rules)
            *args, **kwargs: Function arguments

        Returns:
            Generated response
        """
        try:
            # Try primary with circuit breaker
            return self.gemini_breaker.call(primary_func, *args, **kwargs)

        except Exception as e:
            logger.warning(f"Primary AI failed, using fallback: {e}")

            # Use fallback
            if self.fallback_enabled and fallback_func:
                return fallback_func(*args, **kwargs)

            raise

    def load_knowledge_with_fallback(
        self, sheets_func: Callable, local_cache_func: Callable
    ) -> Dict[str, Any]:
        """
        Load knowledge from Sheets with local cache fallback.

        Args:
            sheets_func: Function to load from Google Sheets
            local_cache_func: Function to load from local cache

        Returns:
            Knowledge base dict
        """
        try:
            # Try Sheets with circuit breaker
            return self.sheets_breaker.call(sheets_func)

        except Exception as e:
            logger.warning(f"Sheets unavailable, using local cache: {e}")

            # Fallback to local cache
            if local_cache_func:
                return local_cache_func()

            return {}


class GracefulDegradation:
    """
    Provides graceful degradation strategies when components fail.
    """

    @staticmethod
    def simple_emotion_detection(message: str) -> Dict[str, Any]:
        """
        Rule-based emotion detection fallback.

        Args:
            message: User message text

        Returns:
            Emotion detection dict
        """
        message_lower = message.lower()

        # Simple keyword-based detection
        anger_keywords = ["angry", "frustrated", "furious", "mad", "annoyed"]
        sadness_keywords = ["sad", "disappointed", "unhappy", "upset", "hurt"]
        joy_keywords = ["happy", "great", "awesome", "thanks", "perfect"]
        fear_keywords = ["worried", "scared", "afraid", "concerned", "nervous"]

        if any(word in message_lower for word in anger_keywords):
            return {"emotion": "anger", "confidence": 0.7}
        elif any(word in message_lower for word in sadness_keywords):
            return {"emotion": "sadness", "confidence": 0.7}
        elif any(word in message_lower for word in joy_keywords):
            return {"emotion": "joy", "confidence": 0.7}
        elif any(word in message_lower for word in fear_keywords):
            return {"emotion": "fear", "confidence": 0.7}
        else:
            return {"emotion": "neutral", "confidence": 0.5}

    @staticmethod
    def simple_response_generation(
        message: str, emotion: str, customer_name: Optional[str] = None
    ) -> str:
        """
        Rule-based response generation fallback.

        Args:
            message: User message
            emotion: Detected emotion
            customer_name: Customer's name if known

        Returns:
            Simple empathetic response
        """
        greeting = f"Hi {customer_name}, " if customer_name else "Hi there, "

        if emotion == "anger":
            return (
                f"{greeting}I understand you're frustrated, and I'm really sorry "
                f"about this. Let me help you resolve this right away. Can you "
                f"give me a moment to look into your situation?"
            )
        elif emotion == "sadness":
            return (
                f"{greeting}I'm sorry you're experiencing this. I want to help "
                f"make things right for you. Let me check what I can do to assist."
            )
        elif emotion == "joy":
            return (
                f"{greeting}That's wonderful! I'm glad to hear it. How else can "
                f"I help you today?"
            )
        else:
            return (
                f"{greeting}Thank you for your message. I'm here to help! "
                f"Let me look into this for you right away."
            )

    @staticmethod
    def get_local_knowledge(query: str) -> Dict[str, Any]:
        """
        Simple local knowledge base fallback.

        Args:
            query: User query

        Returns:
            Knowledge dict
        """
        query_lower = query.lower()

        # Basic FAQ patterns
        if "order" in query_lower and (
            "where" in query_lower or "status" in query_lower
        ):
            return {
                "category": "orders",
                "answer": "You can track your order status in your account dashboard. "
                "If you need help finding it, please share your order number.",
            }
        elif "refund" in query_lower or "return" in query_lower:
            return {
                "category": "returns",
                "answer": "We offer hassle-free returns within 30 days. "
                "You can initiate a return from your account page.",
            }
        elif (
            "contact" in query_lower or "email" in query_lower or "phone" in query_lower
        ):
            return {
                "category": "contact",
                "answer": "You can reach our team at support@company.com or call "
                "us at 1-800-XXX-XXXX during business hours.",
            }
        else:
            return {
                "category": "general",
                "answer": "I'm here to help! Could you provide more details about "
                "what you need assistance with?",
            }


# Utility functions for common recovery patterns
def safe_execute(func: Callable, fallback: Any = None, *args, **kwargs) -> Any:
    """
    Safely execute function with fallback on error.

    Args:
        func: Function to execute
        fallback: Value to return on error
        *args, **kwargs: Function arguments

    Returns:
        Function result or fallback value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Function {func.__name__} failed: {e}")
        return fallback


def with_timeout(func: Callable, timeout_seconds: float, fallback: Any = None):
    """
    Execute function with timeout.

    Args:
        func: Function to execute
        timeout_seconds: Timeout in seconds
        fallback: Value to return on timeout

    Returns:
        Function result or fallback on timeout
    """
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Function timed out after {timeout_seconds}s")

    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(timeout_seconds))

    try:
        result = func()
        signal.alarm(0)  # Cancel alarm
        return result
    except TimeoutError:
        logger.error(f"Function {func.__name__} timed out")
        return fallback
    finally:
        signal.alarm(0)  # Ensure alarm is cancelled


# Example usage
if __name__ == "__main__":
    # Test retry with backoff
    @AutoRecovery.retry_with_backoff(max_retries=3, base_delay=1.0)
    def flaky_function():
        import random

        if random.random() < 0.7:  # 70% failure rate
            raise Exception("Random failure")
        return "Success!"

    try:
        result = flaky_function()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")

    # Test graceful degradation
    degradation = GracefulDegradation()

    # Test emotion detection fallback
    emotion = degradation.simple_emotion_detection(
        "I'm really frustrated with this service!"
    )
    print(f"Emotion detected: {emotion}")

    # Test response generation fallback
    response = degradation.simple_response_generation(
        "This is not working!", "anger", "John"
    )
    print(f"Fallback response: {response}")

    # Test knowledge fallback
    knowledge = degradation.get_local_knowledge("Where is my order?")
    print(f"Knowledge: {knowledge}")
