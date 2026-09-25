"""
W3J Bijou AI - Integration Tests
=================================

End-to-end integration tests for production deployment.

Tests:
- Full TRACE pipeline with all components
- Health monitoring system
- Auto-recovery mechanisms
- Circuit breaker behavior
- Cost optimisation and response quality scoring
- Database persistence
- Runtime wiring of the BijouAI agent

Author: W3J Bijou AI
Version: 2.1.0
"""

import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))


def _install_generativeai_stub():
    """Make ``google.generativeai`` importable so the TRACE agents can be tested.

    ``google-generativeai`` was dropped from requirements.txt when the project
    moved to ``google-genai`` (see requirements.txt:43), but src/agents/{asi,cae,
    srp,ers}.py still import it at module scope. The package is therefore absent
    both here and in the deployed backend image, which makes the whole TRACE
    pipeline unimportable at runtime. That is a product bug, tracked separately;
    stubbing the SDK here keeps the agents' own logic — prompt assembly, JSON
    parsing, emotion validation, humanising, fallbacks — under test instead of
    leaving it uncovered until the dependency is migrated.

    The stub deliberately raises if anything actually calls it: every test below
    replaces ``agent.model`` with its own double, so a real call means the test
    lost its stub rather than silently reaching the network.
    """
    try:
        import google.generativeai  # noqa: F401

        return
    except ImportError:
        pass

    import google as _google_namespace

    stub = types.ModuleType("google.generativeai")
    stub.configure = lambda **kwargs: None

    class _StubGenerativeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, *args, **kwargs):
            raise RuntimeError(
                "google.generativeai is stubbed in tests; patch agent.model instead"
            )

    stub.GenerativeModel = _StubGenerativeModel
    sys.modules["google.generativeai"] = stub
    # google is a namespace package, so attribute access needs wiring too.
    setattr(_google_namespace, "generativeai", stub)


_install_generativeai_stub()

from agents.asi import AffectiveStateIdentifier
from agents.cae import CausalAnalysisEngine
from agents.srp import StrategicResponsePlanner
from agents.ers import EmpatheticResponseSynthesizer
from core.bijou import BijouAI
from core.cost_optimizer import CostOptimizer, ResponseTriggerType
from core.health_monitor import HealthMonitor
from core.ml_judge import MLJudge
from core.auto_recovery import AutoRecovery, CircuitBreaker, GracefulDegradation


def stub_llm(agent, payload):
    """Pin a TRACE agent's LLM boundary to a fixed reply.

    The agents all call ``self.model.generate_content(prompt).text``. Replacing
    that one seam keeps every other line of the agent — validation, parsing,
    metadata stamping, humanising — running for real, while making the test
    deterministic and offline.
    """
    agent.model = MagicMock()
    text = payload if isinstance(payload, str) else json.dumps(payload)
    agent.model.generate_content.return_value = MagicMock(text=text)
    return agent


_BIJOU_SINGLETON = None


def get_bijou():
    """One shared BijouAI for the whole module.

    Constructing it wires ~30 subsystems and takes several seconds, so the
    instance is built once. DB_TYPE is forced to sqlite (conftest sets "mock",
    under which BijouAI._save_conversation writes nothing) and pointed at a
    throwaway file so persistence tests exercise the real SQL path without
    touching the developer's database.
    """
    global _BIJOU_SINGLETON
    if _BIJOU_SINGLETON is None:
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["BIJOU_DB_PATH"] = os.path.join(
            tempfile.mkdtemp(prefix="bijou-itest-"), "bijou.db"
        )
        _BIJOU_SINGLETON = BijouAI()
    return _BIJOU_SINGLETON


class TestTRACEPipeline(unittest.TestCase):
    """Test full TRACE pipeline integration"""

    @classmethod
    def setUpClass(cls):
        """Build the four TRACE agents once for all tests.

        BijouAI no longer owns them: since the agent refactor they live in
        src/agents/ and are lazily constructed by bijou._get_trace_agents()
        behind the TRACE_ENABLED flag, so the pipeline is exercised directly.
        """
        cls.asi = AffectiveStateIdentifier()
        cls.cae = CausalAnalysisEngine()
        cls.srp = StrategicResponsePlanner()
        cls.ers = EmpatheticResponseSynthesizer()

    def test_01_emotion_detection(self):
        """Test ASI emotion detection"""
        # Test angry message. Emotion comes back title-cased to prove ASI
        # normalises it against EKMAN_EMOTIONS rather than passing it through.
        stub_llm(
            self.asi,
            {
                "emotion": "Anger",
                "confidence": 0.9,
                "emotional_cues": ["?!", "2 weeks"],
                "reasoning": "Customer is chasing a long-overdue order",
                "intensity": "high",
            },
        )
        result = self.asi.identify_emotion(
            "Where is my package?! I ordered 2 weeks ago!", []
        )
        self.assertIn(result["emotion"], ["anger", "frustration", "neutral"])
        self.assertGreater(result["confidence"], 0.5)
        self.assertIsInstance(result["emotional_cues"], list)

    def test_02_causal_analysis(self):
        """Test CAE causal analysis"""
        stub_llm(
            self.cae,
            {
                "global_cause": "delayed_shipment",
                "local_triggers": ["hasn't arrived"],
                "unmet_need": "information",
                "situation_type": "shipping",
                "urgency_level": "high",
            },
        )
        result = self.cae.analyze_cause(
            message="My order hasn't arrived yet",
            emotion="concern",
            emotion_confidence=0.85,
            conversation_history=[],
        )
        self.assertIn("global_cause", result)
        self.assertIn("unmet_need", result)
        self.assertIn("urgency_level", result)
        self.assertIn(result["urgency_level"], ["low", "medium", "high", "urgent"])

    def test_03_strategy_planning(self):
        """Test SRP strategy planning"""
        stub_llm(
            self.srp,
            {
                "strategy": "emotional_reaction",
                "rationale": "Customer is anxious and needs validation first",
                "behavioral_taxonomy": ["Mirroring", "Empathic Concern"],
                "response_guidance": ["Acknowledge the worry", "Give a tracking ETA"],
                "confidence": 0.9,
            },
        )
        result = self.srp.plan_strategy(
            message="I'm worried about my delivery",
            emotion="fear",
            emotion_confidence=0.8,
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
        stub_llm(
            self.ers,
            "I can definitely help with that. Let me pull up your order and "
            "confirm exactly where it is and when it lands.",
        )
        result = self.ers.synthesize_response(
            message="I need help with my order",
            emotion="neutral",
            emotion_confidence=0.7,
            emotional_cues=["polite", "requesting"],
            global_cause="information_gap",
            unmet_need="information",
            urgency_level="medium",
            strategy="informational_support",
            behavioral_taxonomy=["acknowledgment", "information_provision"],
            response_guidance=["Provide clear information about order status"],
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

        stub_llm(
            self.asi,
            {
                "emotion": "joy",
                "confidence": 0.92,
                "emotional_cues": ["very happy", "thanks"],
                "reasoning": "Explicit praise",
                "intensity": "medium",
            },
        )
        emotion = self.asi.identify_emotion(test_message, [])

        stub_llm(
            self.cae,
            {
                "global_cause": "successful_purchase",
                "local_triggers": ["happy"],
                "unmet_need": "acknowledgment",
                "situation_type": "general",
                "urgency_level": "low",
            },
        )
        cause = self.cae.analyze_cause(
            message=test_message,
            emotion=emotion["emotion"],
            emotion_confidence=emotion["confidence"],
            conversation_history=[],
        )

        stub_llm(
            self.srp,
            {
                "strategy": "interpretation",
                "rationale": "Positive sentiment, reinforce it",
                "behavioral_taxonomy": ["Altruistic Helping"],
                "response_guidance": ["Thank the customer", "Invite them back"],
                "confidence": 0.88,
            },
        )
        strategy = self.srp.plan_strategy(
            message=test_message,
            emotion=emotion["emotion"],
            emotion_confidence=emotion["confidence"],
            global_cause=cause["global_cause"],
            unmet_need=cause["unmet_need"],
            urgency_level=cause["urgency_level"],
            conversation_history=[],
        )

        stub_llm(
            self.ers,
            "Wah, so glad to hear that! Thank you for the kind words — shout if "
            "you need anything else.",
        )
        synthesis = self.ers.synthesize_response(
            message=test_message,
            emotion=emotion["emotion"],
            emotion_confidence=emotion["confidence"],
            emotional_cues=emotion["emotional_cues"],
            global_cause=cause["global_cause"],
            unmet_need=cause["unmet_need"],
            urgency_level=cause["urgency_level"],
            strategy=strategy["strategy"],
            behavioral_taxonomy=strategy["behavioral_taxonomy"],
            response_guidance=strategy["response_guidance"],
            knowledge_retrieved=strategy.get("knowledge_retrieved", {}),
            conversation_history=[],
            customer_name=None,
        )
        response = synthesis["response_text"]

        # Verify response
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 10)

        # Every stage's decision must reach the next one; ERS echoes back the
        # strategy it was handed, which is what proves the chain is connected.
        self.assertEqual(synthesis["strategy_used"], strategy["strategy"])


class TestCostOptimization(unittest.TestCase):
    """Test cost optimization features"""

    @classmethod
    def setUpClass(cls):
        cls.optimizer = CostOptimizer()

    def test_01_cache_hit(self):
        """Test response caching"""
        # First call - should hit API
        test_message = "Hello there!"

        should_call_1, trigger_1, cached_1 = self.optimizer.should_call_api(
            test_message, "neutral", 0.7, None
        )
        self.assertTrue(should_call_1)

        # Cache the answer, then repeat the same message - should use cache
        self.optimizer.cache_response(test_message, "Hi boss! How can I help?")
        should_call_2, trigger_2, cached_2 = self.optimizer.should_call_api(
            test_message, "neutral", 0.7, None
        )

        self.assertFalse(should_call_2)
        self.assertEqual(trigger_2, ResponseTriggerType.CACHE_HIT)
        self.assertEqual(cached_2, "Hi boss! How can I help?")

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
            should_call, trigger, _ = self.optimizer.should_call_api(
                pattern, "neutral", 0.7, None
            )
            # Simple greetings should use cache
            self.assertIsNotNone(trigger)
            self.assertIsInstance(trigger, ResponseTriggerType)


class TestMLJudge(unittest.TestCase):
    """Test ML Judge quality assessment"""

    @classmethod
    def setUpClass(cls):
        cls.ml_judge = MLJudge()

    def test_01_quality_evaluation(self):
        """Test response quality evaluation"""
        evaluation = self.ml_judge.evaluate_response(
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
        evaluation = self.ml_judge.evaluate_response(
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
        health = monitor.check_bridge_connectivity()

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
        cls.bijou = get_bijou()

    def _turn(self, chat_jid, content, message_id):
        """Build the message dict shape BijouAI._save_conversation expects."""
        return {
            "chat_jid": chat_jid,
            "message_id": message_id,
            "content": content,
            "sender": chat_jid,
        }

    def test_01_save_conversation(self):
        """Test saving conversation to database"""
        test_message = "Test message for database"
        test_sender = "db_test@s.whatsapp.net"
        response = "Sure boss, checking that for you now!"

        lang_context = self.bijou.ml_processor.detect_language(test_message)
        self.bijou._save_conversation(
            self._turn(test_sender, test_message, "db-test-1"), lang_context, response
        )

        # Verify it was saved
        history = self.bijou._get_conversation_history(test_sender)
        self.assertGreater(len(history), 0)

        # _get_conversation_history returns Gemini-style turns: the customer
        # message as "user" and the agent reply as "model", oldest first.
        self.assertEqual(history[0]["parts"][0]["text"], test_message)
        self.assertEqual(history[-1]["parts"][0]["text"], response)

    def test_02_retrieve_context(self):
        """Test retrieving conversation context"""
        test_sender = "context_test@s.whatsapp.net"

        # Add some messages
        for idx, (msg, reply) in enumerate(
            [
                ("My name is Alice", "Nice to meet you, Alice!"),
                ("I ordered shoes", "Got it — let me look up that shoe order."),
            ]
        ):
            lang_context = self.bijou.ml_processor.detect_language(msg)
            self.bijou._save_conversation(
                self._turn(test_sender, msg, f"ctx-test-{idx}"), lang_context, reply
            )

        # Get context
        context = self.bijou._get_conversation_history(test_sender)

        self.assertIsNotNone(context)
        # Context should contain conversation info
        self.assertIn(
            "My name is Alice", [turn["parts"][0]["text"] for turn in context]
        )


class TestProductionIntegration(unittest.TestCase):
    """Test production features integration"""

    @classmethod
    def setUpClass(cls):
        cls.bijou = get_bijou()

    def test_01_bijou_with_production_features(self):
        """Test Bijou AI with all production features enabled"""
        bijou = self.bijou

        # Verify production features loaded. HealthMonitor/AutoRecovery are no
        # longer attached to BijouAI (see get_metrics' own docstring), so the
        # subsystems the runtime does wire are what get asserted here.
        self.assertIsNotNone(bijou.db_conn)
        self.assertIsNotNone(bijou.response_coordinator)

    def test_02_health_status_api(self):
        """Test health status retrieval"""
        bijou = self.bijou

        health = bijou.get_health_status()
        self.assertIn(health["status"], ["healthy", "degraded", "unhealthy"])

    def test_03_metrics_collection(self):
        """Test metrics collection"""
        bijou = self.bijou

        # Get metrics
        metrics = bijou.get_metrics()

        self.assertIn("poll_count", metrics)
        self.assertIn("bridge_url", metrics)
        self.assertIn("database", metrics)
        self.assertEqual(metrics["database"], bijou.db_type)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""

    @classmethod
    def setUpClass(cls):
        """Drive ERS with a dead LLM so every case takes the fallback path.

        The customer must still get a reply when Gemini is down — that is the
        behaviour these edge cases are guarding, so the model is wired to raise
        rather than to answer.
        """
        cls.ers = EmpatheticResponseSynthesizer()
        cls.ers.model = MagicMock()
        cls.ers.model.generate_content.side_effect = RuntimeError("gemini unavailable")

    def _respond(self, message):
        return self.ers.synthesize_response(
            message=message,
            emotion="neutral",
            emotion_confidence=0.7,
            emotional_cues=[],
            global_cause="information_gap",
            unmet_need="information",
            urgency_level="medium",
            strategy="interpretation",
            behavioral_taxonomy=["acknowledgment"],
            response_guidance=["Acknowledge and offer help"],
            knowledge_retrieved={},
            conversation_history=[],
            customer_name=None,
        )

    def test_01_empty_message(self):
        """Test handling empty message"""
        result = self._respond("")

        response = result["response_text"]
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_02_very_long_message(self):
        """Test handling very long message"""
        long_message = "This is a test " * 500  # ~7500 chars
        result = self._respond(long_message)

        response = result["response_text"]
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_03_special_characters(self):
        """Test handling special characters"""
        special_message = "Hello! 🚀 こんにちは €$¥ <script>alert('xss')</script>"
        result = self._respond(special_message)

        response = result["response_text"]
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
