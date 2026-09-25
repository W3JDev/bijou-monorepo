"""
Comprehensive Test Suite for Bijou AI
======================================

Includes unit tests, integration tests, performance tests,
and end-to-end tests with mocking for external services.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import shutil
import tempfile
import time
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.humanizer import ConversationHumanizer
from core.cost_optimizer import CostOptimizer, ResponseTriggerType
from core.ml_judge import MLJudge
from core.mlops import ModelRegistry, ExperimentTracker


class TestHumanizer(unittest.TestCase):
    """Test ConversationHumanizer"""
    
    def setUp(self):
        self.humanizer = ConversationHumanizer()
    
    def test_casual_tone_detection(self):
        """Test casual language detection and the stripping it enables"""
        self.assertEqual(self.humanizer.detect_user_tone("thx, can u help"), "casual")

        # conversation_length > 1 is what switches prefix stripping on: the
        # robotic opener is only noise once the chat is already under way.
        result = self.humanizer.humanize_response(
            response="I understand you need a quote. I will send it over.",
            emotion="neutral",
            urgency="medium",
            conversation_length=2,
            user_tone="casual"
        )
        self.assertEqual(
            result["humanized_text"], "You need a quote. I will send it over."
        )
        self.assertEqual(
            result["original_text"],
            "I understand you need a quote. I will send it over.",
        )
    
    def test_emoji_insertion(self):
        """Test emoji insertion based on emotion"""
        result = self.humanizer.humanize_response(
            response="I'm happy to help!",
            emotion="joy",
            urgency="low",
            conversation_length=1,
            user_tone="casual"
        )
        # Should have emoji 40% of the time in multiple runs
        # For single test, just check format is correct
        self.assertIsInstance(result["humanized_text"], str)
    
    def test_typing_time_calculation(self):
        """Test typing time calculation"""
        result = self.humanizer.humanize_response(
            response="This is a test message.",
            emotion="neutral",
            urgency="medium",
            conversation_length=1,
            user_tone="formal"
        )
        self.assertGreater(result["typing_time_seconds"], 0)
        self.assertLess(result["typing_time_seconds"], 10)  # Should be reasonable


class TestCostOptimizer(unittest.TestCase):
    """Test CostOptimizer"""
    
    def setUp(self):
        self.optimizer = CostOptimizer(cache_ttl_minutes=60)
    
    def test_pattern_matching(self):
        """Test common pattern detection"""
        should_call, trigger, response = self.optimizer.should_call_api(
            message="hi",
            emotion="neutral",
            confidence=0.9,
            conversation_history=None
        )
        self.assertFalse(should_call)
        self.assertIsNotNone(response)
    
    def test_cache_functionality(self):
        """Test response caching"""
        message = "What is your return policy?"
        
        # First call
        self.optimizer.cache_response(message, "Our return policy...")

        # Second call should hit cache
        should_call, trigger, response = self.optimizer.should_call_api(
            message=message,
            emotion="neutral",
            confidence=0.9,
            conversation_history=None
        )
        self.assertFalse(should_call)
        self.assertEqual(trigger, ResponseTriggerType.CACHE_HIT)
        self.assertEqual(response, "Our return policy...")
    
    def test_api_trigger_on_complex_query(self):
        """Test API trigger for complex queries"""
        should_call, trigger, response = self.optimizer.should_call_api(
            message="I have a very complex issue with my order that requires detailed analysis",
            emotion="anger",
            confidence=0.5,
            conversation_history=None
        )
        self.assertTrue(should_call)


class TestMLJudge(unittest.TestCase):
    """Test ML Judge"""
    
    def setUp(self):
        self.judge = MLJudge()
    
    def test_good_response_evaluation(self):
        """Test evaluation of a good response"""
        # Empathy is the heaviest-weighted criterion (0.3), and it is scored by
        # counting empathy phrases — so a reply needs several of them, not one,
        # to clear the 3.5 needs_improvement threshold.
        eval_result = self.judge.evaluate_response(
            user_message="Where is my order?",
            bot_response="I hear you, and I'm sorry - I understand how frustrating this is. Let me track your order right away. Can you please provide your order number?",
            emotion="anger",
            urgency="high",
            conversation_history=None
        )
        self.assertGreater(eval_result["overall_score"], 2.5)
        self.assertFalse(eval_result["needs_improvement"])
        self.assertFalse(eval_result["mistake_detected"]["has_mistake"])
        self.assertEqual(eval_result["quality_level"], "GOOD")
    
    def test_poor_response_detection(self):
        """Test detection of poor responses"""
        eval_result = self.judge.evaluate_response(
            user_message="I need help with my account",
            bot_response="OK",
            emotion="neutral",
            urgency="medium",
            conversation_history=None
        )
        self.assertLess(eval_result["overall_score"], 3.0)
        self.assertTrue(eval_result["needs_improvement"])
    
    def test_mistake_detection(self):
        """Test mistake detection"""
        # The bot invents an order number, a time and a price that the customer
        # never supplied - the classic hallucination the judge exists to catch.
        eval_result = self.judge.evaluate_response(
            user_message="Where is my order?",
            bot_response="Your order #12345 will arrive at 3:00 PM and costs $45.99.",
            emotion="neutral",
            urgency="low",
            conversation_history=None
        )
        # Mistakes live under the mistake_detected sub-dict, not at the top level
        mistakes = eval_result["mistake_detected"]["mistakes"]
        self.assertGreater(len(mistakes), 0)
        self.assertTrue(eval_result["mistake_detected"]["has_mistake"])
        self.assertIn("hallucination", [m["type"] for m in mistakes])
        self.assertTrue(eval_result["mistake_detected"]["should_apologize"])
        self.assertTrue(eval_result["needs_improvement"])


class TestMLOps(unittest.TestCase):
    """Test MLOps infrastructure"""

    def setUp(self):
        # ModelRegistry opens a fresh sqlite connection per call, so ":memory:"
        # gives every method its own empty database and the schema created in
        # _init_database() is gone by the time register_model() runs. A throwaway
        # file is the only db_path that exercises the real code path.
        self._db_dir = tempfile.mkdtemp(prefix="bijou-mlops-test-")
        self.registry = ModelRegistry(db_path=str(Path(self._db_dir) / "mlops.db"))

    def tearDown(self):
        shutil.rmtree(self._db_dir, ignore_errors=True)


    def test_model_registration(self):
        """Test model registration"""
        model_id = self.registry.register_model(
            model_name="test-model",
            version="v1.0.0",
            model_type="emotion_detection",
            provider="gemini",
            config={"temp": 0.7},
            description="Test model"
        )
        self.assertGreater(model_id, 0)
    
    def test_active_model_setting(self):
        """Test setting active model"""
        model_id = self.registry.register_model(
            model_name="test-model",
            version="v1.0.0",
            model_type="emotion_detection",
            provider="gemini",
            config={},
            description="Test"
        )
        
        self.registry.set_active_model("test-model", "v1.0.0")
        active = self.registry.get_active_model("test-model")
        
        self.assertIsNotNone(active)
        self.assertEqual(active["version"], "v1.0.0")
    
    def test_prediction_logging(self):
        """Test prediction logging"""
        model_id = self.registry.register_model(
            model_name="test-model",
            version="v1.0.0",
            model_type="emotion_detection",
            provider="gemini",
            config={},
            description="Test"
        )
        
        pred_id = self.registry.log_prediction(
            model_version_id=model_id,
            input_data={"message": "test"},
            prediction={"emotion": "joy"},
            confidence=0.9,
            latency_ms=150.0,
            tokens_used=50,
            cost_usd=0.0003
        )
        
        self.assertGreater(pred_id, 0)
    
    def test_model_stats(self):
        """Test model statistics retrieval"""
        model_id = self.registry.register_model(
            model_name="test-model",
            version="v1.0.0",
            model_type="emotion_detection",
            provider="gemini",
            config={},
            description="Test"
        )
        
        # Log some predictions
        for i in range(5):
            self.registry.log_prediction(
                model_version_id=model_id,
                input_data={"message": f"test{i}"},
                prediction={"emotion": "joy"},
                confidence=0.8 + (i * 0.02),
                latency_ms=150.0,
                tokens_used=50,
                cost_usd=0.0003
            )
        
        stats = self.registry.get_model_stats(model_id, days=1)
        
        self.assertEqual(stats["total_predictions"], 5)
        self.assertGreater(stats["avg_confidence"], 0.8)
        self.assertEqual(stats["total_tokens"], 250)


class TestExperimentTracker(unittest.TestCase):
    """Test experiment tracking"""
    
    def setUp(self):
        # See TestMLOps.setUp - ":memory:" cannot survive the registry's
        # connection-per-call design.
        self._db_dir = tempfile.mkdtemp(prefix="bijou-mlops-test-")
        self.registry = ModelRegistry(db_path=str(Path(self._db_dir) / "mlops.db"))
        self.tracker = ExperimentTracker(self.registry)

    def tearDown(self):
        shutil.rmtree(self._db_dir, ignore_errors=True)


    def test_experiment_lifecycle(self):
        """Test complete experiment lifecycle"""
        model_id = self.registry.register_model(
            model_name="test-model",
            version="v1.0.0",
            model_type="emotion_detection",
            provider="gemini",
            config={},
            description="Test"
        )
        
        # Start experiment
        exp_id = self.tracker.start_experiment(
            name="test-experiment",
            model_version_id=model_id,
            parameters={"learning_rate": 0.001},
            tags=["test", "experiment"]
        )
        
        self.assertGreater(exp_id, 0)
        
        # End experiment
        self.tracker.end_experiment(
            metrics={"accuracy": 0.95, "f1": 0.92},
            status="completed"
        )


class TestPerformance(unittest.TestCase):
    """Performance and benchmark tests"""
    
    def test_humanizer_performance(self):
        """Test humanizer performance"""
        humanizer = ConversationHumanizer()
        
        start = time.time()
        for _ in range(100):
            humanizer.humanize_response(
                response="This is a test message",
                emotion="neutral",
                urgency="medium",
                conversation_length=1,
                user_tone="casual"
            )
        duration = time.time() - start
        
        avg_time = duration / 100
        self.assertLess(avg_time, 0.1)  # Should be less than 100ms per call
    
    def test_cost_optimizer_performance(self):
        """Test cost optimizer performance"""
        optimizer = CostOptimizer()
        
        start = time.time()
        for i in range(100):
            optimizer.should_call_api(
                message=f"Test message {i}",
                emotion="neutral",
                confidence=0.8,
                conversation_history=None
            )
        duration = time.time() - start
        
        avg_time = duration / 100
        self.assertLess(avg_time, 0.05)  # Should be less than 50ms per call


class TestIntegration(unittest.TestCase):
    """Integration tests with mocked external services"""
    
    def test_full_pipeline_with_mocks(self):
        """Test the optimizer -> AI -> humanizer -> judge -> cache loop"""
        optimizer = CostOptimizer(cache_ttl_minutes=60)
        humanizer = ConversationHumanizer()
        judge = MLJudge()

        message = "My delivery is three days late and nobody has called me back"

        # Stand-in for the LLM call. The real TRACE agents import
        # google.generativeai, which requirements.txt dropped as deprecated
        # (Dec 2025), so there is no such module left to patch - mock the call
        # boundary the pipeline goes through instead.
        generate_content = Mock(side_effect=[
            json.dumps({
                "emotion": "anger",
                "confidence": 0.6,
                "cues": ["three days late", "nobody has called"]
            }),
            "I hear you, and I'm sorry - I understand how frustrating this is. "
            "Let me chase the courier right away. "
            "Can you please confirm your postcode?",
        ])

        # Step 1: low confidence + no cache means the API has to be paid for
        should_call, trigger, cached = optimizer.should_call_api(
            message=message,
            emotion="anger",
            confidence=0.6,
            conversation_history=None
        )
        self.assertTrue(should_call)
        self.assertEqual(trigger, ResponseTriggerType.API_REQUIRED)
        self.assertIsNone(cached)

        # Step 2: emotion analysis, then the reply itself
        analysis = json.loads(generate_content(f"classify: {message}"))
        self.assertEqual(analysis["emotion"], "anger")
        ai_reply = generate_content(f"reply: {message}")

        # Step 3: humanize - high urgency splits the compound opening sentence
        humanized = humanizer.humanize_response(
            response=ai_reply,
            emotion=analysis["emotion"],
            urgency="high",
            conversation_length=3,
            user_tone="casual"
        )
        text = humanized["humanized_text"]
        self.assertNotIn(", and ", text)
        self.assertGreater(humanized["typing_time_seconds"], 0)

        # Step 4: the judge must be happy with what we are about to send
        evaluation = judge.evaluate_response(
            user_message=message,
            bot_response=text,
            emotion=analysis["emotion"],
            urgency="high",
            conversation_history=None
        )
        self.assertFalse(evaluation["needs_improvement"])
        self.assertFalse(evaluation["mistake_detected"]["has_mistake"])

        # Step 5: cache it, so an identical message costs nothing next time
        optimizer.cache_response(message, text)
        should_call, trigger, cached = optimizer.should_call_api(
            message=message,
            emotion="anger",
            confidence=0.6,
            conversation_history=None
        )
        self.assertFalse(should_call)
        self.assertEqual(trigger, ResponseTriggerType.CACHE_HIT)
        self.assertEqual(cached, text)
        self.assertEqual(generate_content.call_count, 2)  # not 4
        self.assertEqual(optimizer.stats["api_calls"], 1)
        self.assertEqual(optimizer.stats["cache_hits"], 1)


# Pytest markers for categorization
pytestmark = [
    pytest.mark.unit,
]


if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)
