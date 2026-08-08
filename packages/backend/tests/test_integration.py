"""
W3J Bijou AI - Integration Tests
=================================

End-to-end integration tests for production deployment.

Tests:
- Full TRACE pipeline with all components
- Health monitoring system
- Auto-recovery mechanisms
- Circuit breaker behavior
- Google Sheets integration
- Database persistence
- Message sending via bridge

Author: W3J Bijou AI
Version: 2.1.0
"""

import os
import sys
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from core.bijou import BijouAI
from core.health_monitor import HealthMonitor
from core.auto_recovery import AutoRecovery, CircuitBreaker, GracefulDegradation


class TestTRACEPipeline(unittest.TestCase):
    """Test full TRACE pipeline integration"""

    @classmethod
    def setUpClass(cls):
        """Initialize Bijou AI once for all tests"""
        cls.bijou = BijouAI(
            bridge_url="http://localhost:8080",
            db_path="data/test_bijou.db",
            bridge_db_path="../whatsapp-bridge/store/test_messages.db",
            enable_health_check=False,  # Skip for speed
        )

    def test_01_emotion_detection(self):
        """Test ASI emotion detection"""
        # Test angry message
        result = self.bijou.asi.identify_emotion(
            "Where is my package?! I ordered 2 weeks ago!", []
        )
        self.assertIn(result["emotion"], ["anger", "frustration", "neutral"])
        self.assertGreater(result["confidence"], 0.5)
        self.assertIsInstance(result["emotional_cues"], list)

    def test_02_causal_analysis(self):
        """Test CAE causal analysis"""
        result = self.bijou.cae.analyze_cause(
            message="My order hasn't arrived yet",
            emotion="concern",
            confidence=0.85,
            conversation_history=[],
        )
        self.assertIn("global_cause", result)
        self.assertIn("unmet_need", result)
        self.assertIn("urgency_level", result)
        self.assertIn(result["urgency_level"], ["low", "medium", "high", "urgent"])

    def test_03_strategy_planning(self):
        """Test SRP strategy planning"""
        result = self.bijou.srp.plan_strategy(
            message="I'm worried about my delivery",
            emotion="fear",
            confidence=0.8,
            global_cause="uncertainty",
            unmet_need="reassurance",
            urgency_level="medium",
            conversation_history=[],
        )
        self.assertIn("strategy", result)
        self.assertIn("behavioral_taxonomy", result)
        self.assertIsInstance(result["behavioral_taxonomy"], list)

    def test_04_response_synthesis(self):
        """Test ERS response synthesis"""
        result = self.bijou.ers.synthesize_response(
            message="I need help with my order",
            emotion="neutral",
            confidence=0.7,
            emotional_cues=["polite", "requesting"],
            global_cause="information_gap",
            unmet_need="information",
            urgency_level="medium",
            strategy="informational_support",
            behavioral_taxonomy=["acknowledgment", "information_provision"],
            response_guidance="Provide clear information about order status",
            knowledge_retrieved={},
            conversation_history=[],
            customer_name=None,
        )
        self.assertIn("response_text", result)
        self.assertIn("estimated_csat", result)
        self.assertGreater(len(result["response_text"]), 10)
        self.assertGreaterEqual(result["estimated_csat"], 0)
        self.assertLessEqual(result["estimated_csat"], 5.0)

    def test_05_full_pipeline(self):
        """Test complete TRACE pipeline end-to-end"""
        test_message = "Hi! I'm very happy with my purchase, thanks!"
        test_sender = "test_user@s.whatsapp.net"

        response = self.bijou.process_message(test_message, test_sender)

        # Verify response
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 10)

        # Check metrics were updated
        metrics = self.bijou.get_metrics()
        self.assertGreater(metrics["total_messages"], 0)


class TestCostOptimization(unittest.TestCase):
    """Test cost optimization features"""

    @classmethod
    def setUpClass(cls):
        cls.bijou = BijouAI(
            db_path="data/test_bijou.db",
            enable_health_check=False,
        )

    def test_01_cache_hit(self):
        """Test response caching"""
        # First call - should hit API
        test_message = "Hello there!"
        test_sender = "cache_test@s.whatsapp.net"

        response1 = self.bijou.process_message(test_message, test_sender)

        # Second call with same message - should use cache
        response2 = self.bijou.process_message(test_message, test_sender)

        # Both should have responses
        self.assertGreater(len(response1), 0)
        self.assertGreater(len(response2), 0)

    def test_02_pattern_detection(self):
        """Test common pattern detection"""
        patterns = [
            "hi",
            "hello",
            "hey",
            "thanks",
            "thank you",
            "ok",
            "okay",
        ]

        for pattern in patterns:
            should_call, trigger, _ = self.bijou.cost_optimizer.should_call_api(
                pattern, "neutral", 0.7, None
            )
            # Simple greetings should use cache
            self.assertIsNotNone(trigger)


class TestMLJudge(unittest.TestCase):
    """Test ML Judge quality assessment"""

    @classmethod
    def setUpClass(cls):
        cls.bijou = BijouAI(
            db_path="data/test_bijou.db",
            enable_health_check=False,
        )

    def test_01_quality_evaluation(self):
        """Test response quality evaluation"""
        evaluation = self.bijou.ml_judge.evaluate_response(
            user_message="Where is my package?",
            bot_response="I understand your concern. Let me check your order status right away!",
            emotion="concern",
            urgency="medium",
        )

        self.assertIn("overall_score", evaluation)
        self.assertIn("quality_level", evaluation)
        self.assertGreaterEqual(evaluation["overall_score"], 0)
        self.assertLessEqual(evaluation["overall_score"], 5.0)

    def test_02_mistake_detection(self):
        """Test mistake detection"""
        # Test with poor response
        evaluation = self.bijou.ml_judge.evaluate_response(
            user_message="I'm very angry about this!",
            bot_response="ok",  # Poor response
            emotion="anger",
            urgency="high",
        )

        # Should detect low quality
        self.assertLess(evaluation["overall_score"], 3.0)


class TestHealthMonitoring(unittest.TestCase):
    """Test health monitoring system"""

    def test_01_health_monitor_creation(self):
        """Test health monitor initialization"""
        monitor = HealthMonitor(
            bridge_url="http://localhost:8080",
            bridge_db_path="../whatsapp-bridge/store/messages.db",
            bijou_db_path="data/bijou.db",
        )
        self.assertIsNotNone(monitor)

    def test_02_component_checks(self):
        """Test individual component checks"""
        monitor = HealthMonitor(
            bridge_url="http://localhost:8080",
            bridge_db_path="../whatsapp-bridge/store/messages.db",
            bijou_db_path="data/bijou.db",
        )

        # Check bridge database (may not exist in test)
        bridge_health = monitor.check_bridge_database()
        self.assertIn("status", bridge_health)
        self.assertIn(bridge_health["status"], ["healthy", "unhealthy", "degraded"])

        # Check Bijou database
        bijou_health = monitor.check_bijou_database()
        self.assertIn("status", bijou_health)

    @patch("requests.get")
    def test_03_bridge_api_check(self, mock_get):
        """Test bridge API health check"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "ok"}

        monitor = HealthMonitor(bridge_url="http://localhost:8080")
        health = monitor.check_bridge_api()

        self.assertEqual(health["status"], "healthy")

    def test_04_full_health_check(self):
        """Test complete health check"""
        monitor = HealthMonitor(
            bridge_url="http://localhost:8080",
            bridge_db_path="../whatsapp-bridge/store/messages.db",
            bijou_db_path="data/bijou.db",
        )

        health = monitor.run_full_health_check()

        self.assertIn("overall_status", health)
        self.assertIn("components", health)
        self.assertIn("system_metrics", health)
        self.assertIn(health["overall_status"], ["healthy", "degraded", "unhealthy"])


class TestAutoRecovery(unittest.TestCase):
    """Test auto-recovery mechanisms"""

    def test_01_circuit_breaker(self):
        """Test circuit breaker pattern"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        # Simulate failures
        failed_func = Mock(side_effect=Exception("Service unavailable"))

        for i in range(3):
            with self.assertRaises(Exception):
                breaker.call(failed_func)

        # Circuit should now be OPEN
        from core.auto_recovery import CircuitState

        self.assertEqual(breaker.state, CircuitState.OPEN)

        # Should fail fast without calling function
        with self.assertRaises(Exception) as context:
            breaker.call(failed_func)
        self.assertIn("Circuit breaker OPEN", str(context.exception))

    def test_02_retry_with_backoff(self):
        """Test retry with exponential backoff"""
        recovery = AutoRecovery()

        # Create function that fails twice then succeeds
        attempt_count = {"count": 0}

        def flaky_function():
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise Exception("Temporary failure")
            return "success"

        # Wrap with retry
        retry_func = recovery.retry_with_backoff(flaky_function, max_retries=3)
        result = retry_func()

        self.assertEqual(result, "success")
        self.assertEqual(attempt_count["count"], 3)

    def test_03_graceful_degradation_emotion(self):
        """Test graceful degradation for emotion detection"""
        result = GracefulDegradation.simple_emotion_detection("I am so angry!")

        self.assertIn("emotion", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["emotion"], "anger")

    def test_04_graceful_degradation_response(self):
        """Test graceful degradation for response generation"""
        response = GracefulDegradation.simple_response_generation(
            message="I need help",
            emotion="neutral",
            customer_name="John",
        )

        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 10)
        self.assertIn("John", response)


class TestDatabasePersistence(unittest.TestCase):
    """Test database persistence"""

    @classmethod
    def setUpClass(cls):
        cls.bijou = BijouAI(
            db_path="data/test_bijou.db",
            enable_health_check=False,
        )

    def test_01_save_conversation(self):
        """Test saving conversation to database"""
        test_message = "Test message for database"
        test_sender = "db_test@s.whatsapp.net"

        # Process message (saves to DB)
        response = self.bijou.process_message(test_message, test_sender)

        # Verify it was saved
        history = self.bijou.memory.get_conversation_history(test_sender)
        self.assertGreater(len(history), 0)

        # Check last message
        last_msg = history[-1]
        self.assertEqual(last_msg["user_message"], test_message)
        self.assertEqual(last_msg["bot_response"], response)

    def test_02_retrieve_context(self):
        """Test retrieving conversation context"""
        test_sender = "context_test@s.whatsapp.net"

        # Add some messages
        self.bijou.process_message("My name is Alice", test_sender)
        self.bijou.process_message("I ordered shoes", test_sender)

        # Get context
        context = self.bijou.memory.get_context_summary(test_sender)

        self.assertIsNotNone(context)
        # Context should contain conversation info


class TestProductionIntegration(unittest.TestCase):
    """Test production features integration"""

    def test_01_bijou_with_production_features(self):
        """Test Bijou AI with all production features enabled"""
        bijou = BijouAI(
            db_path="data/test_bijou_prod.db",
            enable_health_check=True,
        )

        # Verify production features loaded
        self.assertIsNotNone(bijou.health_monitor)
        self.assertIsNotNone(bijou.recovery)

    def test_02_health_status_api(self):
        """Test health status retrieval"""
        bijou = BijouAI(
            db_path="data/test_bijou_prod.db",
            enable_health_check=False,
        )

        health = bijou.get_health_status()
        self.assertIn("overall_status", health)

    def test_03_metrics_collection(self):
        """Test metrics collection"""
        bijou = BijouAI(
            db_path="data/test_bijou_prod.db",
            enable_health_check=False,
        )

        # Process a message
        bijou.process_message("Test message", "metrics_test@s.whatsapp.net")

        # Get metrics
        metrics = bijou.get_metrics()

        self.assertIn("total_messages", metrics)
        self.assertIn("average_csat", metrics)
        self.assertIn("cost_optimization", metrics)
        self.assertGreater(metrics["total_messages"], 0)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""

    def test_01_empty_message(self):
        """Test handling empty message"""
        bijou = BijouAI(
            db_path="data/test_bijou.db",
            enable_health_check=False,
        )

        response = bijou.process_message("", "empty_test@s.whatsapp.net")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_02_very_long_message(self):
        """Test handling very long message"""
        bijou = BijouAI(
            db_path="data/test_bijou.db",
            enable_health_check=False,
        )

        long_message = "This is a test " * 500  # ~7500 chars
        response = bijou.process_message(long_message, "long_test@s.whatsapp.net")

        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_03_special_characters(self):
        """Test handling special characters"""
        bijou = BijouAI(
            db_path="data/test_bijou.db",
            enable_health_check=False,
        )

        special_message = "Hello! 🚀 こんにちは €$¥ <script>alert('xss')</script>"
        response = bijou.process_message(special_message, "special_test@s.whatsapp.net")

        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)


def run_integration_tests():
    """Run all integration tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTRACEPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestCostOptimization))
    suite.addTests(loader.loadTestsFromTestCase(TestMLJudge))
    suite.addTests(loader.loadTestsFromTestCase(TestHealthMonitoring))
    suite.addTests(loader.loadTestsFromTestCase(TestAutoRecovery))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabasePersistence))
    suite.addTests(loader.loadTestsFromTestCase(TestProductionIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
