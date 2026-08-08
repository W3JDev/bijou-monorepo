"""
MLOps Infrastructure for Bijou AI
==================================

Provides model tracking, versioning, experiment logging, and performance monitoring.

Features:
- Model version management
- Experiment tracking
- Performance metrics logging
- A/B testing support
- Model registry
- Deployment tracking
- Cost tracking per model
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import os


class ModelRegistry:
    """Centralized model registry for version control and tracking."""
    
    def __init__(self, db_path: str = "data/mlops.db"):
        """Initialize model registry."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize MLOps database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Model versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    config JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 0,
                    UNIQUE(model_name, version)
                )
            """)
            
            # Experiments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_name TEXT NOT NULL,
                    model_version_id INTEGER,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT DEFAULT 'running',
                    parameters JSON,
                    metrics JSON,
                    tags JSON,
                    notes TEXT,
                    FOREIGN KEY (model_version_id) REFERENCES model_versions(id)
                )
            """)
            
            # Predictions table (for inference tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version_id INTEGER,
                    experiment_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    input_hash TEXT,
                    input_data JSON,
                    prediction JSON,
                    confidence REAL,
                    latency_ms REAL,
                    tokens_used INTEGER,
                    cost_usd REAL,
                    feedback_score REAL,
                    metadata JSON,
                    FOREIGN KEY (model_version_id) REFERENCES model_versions(id),
                    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version_id INTEGER,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    environment TEXT DEFAULT 'production',
                    metadata JSON,
                    FOREIGN KEY (model_version_id) REFERENCES model_versions(id)
                )
            """)
            
            # Deployments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deployments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version_id INTEGER,
                    environment TEXT NOT NULL,
                    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deployed_by TEXT,
                    status TEXT DEFAULT 'active',
                    config JSON,
                    rollback_version_id INTEGER,
                    FOREIGN KEY (model_version_id) REFERENCES model_versions(id),
                    FOREIGN KEY (rollback_version_id) REFERENCES model_versions(id)
                )
            """)
            
            # A/B tests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    model_a_version_id INTEGER,
                    model_b_version_id INTEGER,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    traffic_split_a REAL DEFAULT 0.5,
                    status TEXT DEFAULT 'running',
                    winner_version_id INTEGER,
                    results JSON,
                    FOREIGN KEY (model_a_version_id) REFERENCES model_versions(id),
                    FOREIGN KEY (model_b_version_id) REFERENCES model_versions(id),
                    FOREIGN KEY (winner_version_id) REFERENCES model_versions(id)
                )
            """)
            
            conn.commit()
    
    def register_model(
        self,
        model_name: str,
        version: str,
        model_type: str,
        provider: str,
        config: Dict[str, Any],
        description: str = "",
        created_by: str = "system"
    ) -> int:
        """
        Register a new model version.
        
        Args:
            model_name: Name of the model (e.g., "emotion-detector")
            version: Version string (e.g., "v1.0.0", "gemini-2.0-flash")
            model_type: Type (e.g., "emotion_detection", "response_generation")
            provider: Provider (e.g., "gemini", "openai", "ollama")
            config: Model configuration
            description: Human-readable description
            created_by: User or system that registered the model
        
        Returns:
            Model version ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_versions 
                (model_name, version, model_type, provider, config, description, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                model_name,
                version,
                model_type,
                provider,
                json.dumps(config),
                description,
                created_by
            ))
            conn.commit()
            return cursor.lastrowid
    
    def set_active_model(self, model_name: str, version: str):
        """Set a specific model version as active."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Deactivate all versions of this model
            cursor.execute("""
                UPDATE model_versions 
                SET is_active = 0 
                WHERE model_name = ?
            """, (model_name,))
            
            # Activate the specified version
            cursor.execute("""
                UPDATE model_versions 
                SET is_active = 1 
                WHERE model_name = ? AND version = ?
            """, (model_name, version))
            
            conn.commit()
    
    def get_active_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get the currently active version of a model."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, version, model_type, provider, config
                FROM model_versions
                WHERE model_name = ? AND is_active = 1
            """, (model_name,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "version": row[1],
                    "model_type": row[2],
                    "provider": row[3],
                    "config": json.loads(row[4])
                }
            return None
    
    def log_prediction(
        self,
        model_version_id: int,
        input_data: Any,
        prediction: Any,
        confidence: Optional[float] = None,
        latency_ms: Optional[float] = None,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        experiment_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Log a prediction/inference event.
        
        Args:
            model_version_id: ID of the model version used
            input_data: Input data (will be JSON serialized)
            prediction: Prediction output (will be JSON serialized)
            confidence: Confidence score (0-1)
            latency_ms: Inference latency in milliseconds
            tokens_used: Number of tokens consumed
            cost_usd: Cost in USD
            experiment_id: Optional experiment ID
            metadata: Additional metadata
        
        Returns:
            Prediction ID
        """
        # Create hash of input for deduplication
        input_str = json.dumps(input_data, sort_keys=True)
        input_hash = hashlib.md5(input_str.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO predictions
                (model_version_id, experiment_id, input_hash, input_data, prediction,
                 confidence, latency_ms, tokens_used, cost_usd, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model_version_id,
                experiment_id,
                input_hash,
                json.dumps(input_data),
                json.dumps(prediction),
                confidence,
                latency_ms,
                tokens_used,
                cost_usd,
                json.dumps(metadata or {})
            ))
            conn.commit()
            return cursor.lastrowid
    
    def log_metric(
        self,
        model_version_id: int,
        metric_name: str,
        metric_value: float,
        environment: str = "production",
        metadata: Optional[Dict] = None
    ):
        """Log a performance metric."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO performance_metrics
                (model_version_id, metric_name, metric_value, environment, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                model_version_id,
                metric_name,
                metric_value,
                environment,
                json.dumps(metadata or {})
            ))
            conn.commit()
    
    def create_experiment(
        self,
        experiment_name: str,
        model_version_id: int,
        parameters: Dict[str, Any],
        tags: Optional[List[str]] = None,
        notes: str = ""
    ) -> int:
        """Create a new experiment."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiments
                (experiment_name, model_version_id, parameters, tags, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                experiment_name,
                model_version_id,
                json.dumps(parameters),
                json.dumps(tags or []),
                notes
            ))
            conn.commit()
            return cursor.lastrowid
    
    def complete_experiment(
        self,
        experiment_id: int,
        metrics: Dict[str, float],
        status: str = "completed"
    ):
        """Mark an experiment as complete with final metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE experiments
                SET end_time = CURRENT_TIMESTAMP,
                    status = ?,
                    metrics = ?
                WHERE id = ?
            """, (
                status,
                json.dumps(metrics),
                experiment_id
            ))
            conn.commit()
    
    def get_model_stats(self, model_version_id: int, days: int = 7) -> Dict[str, Any]:
        """Get statistics for a model version over the last N days."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Basic stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_predictions,
                    AVG(confidence) as avg_confidence,
                    AVG(latency_ms) as avg_latency,
                    SUM(tokens_used) as total_tokens,
                    SUM(cost_usd) as total_cost,
                    AVG(feedback_score) as avg_feedback
                FROM predictions
                WHERE model_version_id = ?
                AND timestamp >= datetime('now', '-' || ? || ' days')
            """, (model_version_id, days))
            
            row = cursor.fetchone()
            
            return {
                "total_predictions": row[0] or 0,
                "avg_confidence": row[1] or 0.0,
                "avg_latency_ms": row[2] or 0.0,
                "total_tokens": row[3] or 0,
                "total_cost_usd": row[4] or 0.0,
                "avg_feedback_score": row[5] or 0.0
            }
    
    def compare_models(
        self,
        model_a_id: int,
        model_b_id: int,
        metric_names: List[str],
        days: int = 7
    ) -> Dict[str, Any]:
        """Compare two model versions across specified metrics."""
        stats_a = self.get_model_stats(model_a_id, days)
        stats_b = self.get_model_stats(model_b_id, days)
        
        comparison = {
            "model_a": stats_a,
            "model_b": stats_b,
            "improvements": {}
        }
        
        for metric in metric_names:
            if metric in stats_a and metric in stats_b:
                value_a = stats_a[metric]
                value_b = stats_b[metric]
                if value_a > 0:
                    improvement = ((value_b - value_a) / value_a) * 100
                    comparison["improvements"][metric] = f"{improvement:+.2f}%"
        
        return comparison


class ExperimentTracker:
    """Track experiments and their results."""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.current_experiment_id = None
    
    def start_experiment(
        self,
        name: str,
        model_version_id: int,
        parameters: Dict[str, Any],
        tags: Optional[List[str]] = None,
        notes: str = ""
    ):
        """Start a new experiment."""
        self.current_experiment_id = self.registry.create_experiment(
            experiment_name=name,
            model_version_id=model_version_id,
            parameters=parameters,
            tags=tags,
            notes=notes
        )
        return self.current_experiment_id
    
    def log_metric(self, metric_name: str, value: float):
        """Log a metric for the current experiment."""
        if not self.current_experiment_id:
            raise ValueError("No active experiment")
        
        # This would be extended to support real-time metric logging
        pass
    
    def end_experiment(self, metrics: Dict[str, float], status: str = "completed"):
        """End the current experiment."""
        if not self.current_experiment_id:
            raise ValueError("No active experiment")
        
        self.registry.complete_experiment(
            self.current_experiment_id,
            metrics,
            status
        )
        self.current_experiment_id = None


# Example usage
if __name__ == "__main__":
    print("Bijou AI MLOps Infrastructure")
    print("=" * 60)
    
    # Initialize registry
    registry = ModelRegistry()
    
    # Register Gemini model
    gemini_id = registry.register_model(
        model_name="emotion-detector",
        version="gemini-2.0-flash",
        model_type="emotion_detection",
        provider="gemini",
        config={"temperature": 0.7, "max_tokens": 150},
        description="Primary emotion detection using Gemini 2.0 Flash"
    )
    
    registry.set_active_model("emotion-detector", "gemini-2.0-flash")
    
    # Log some predictions
    for i in range(10):
        registry.log_prediction(
            model_version_id=gemini_id,
            input_data={"message": f"Test message {i}"},
            prediction={"emotion": "joy", "confidence": 0.85 + (i * 0.01)},
            confidence=0.85 + (i * 0.01),
            latency_ms=150.0,
            tokens_used=50,
            cost_usd=0.0003
        )
    
    # Get stats
    stats = registry.get_model_stats(gemini_id, days=7)
    print("\nModel Statistics (Last 7 days):")
    print(f"  Total Predictions: {stats['total_predictions']}")
    print(f"  Avg Confidence: {stats['avg_confidence']:.2%}")
    print(f"  Avg Latency: {stats['avg_latency_ms']:.2f}ms")
    print(f"  Total Cost: ${stats['total_cost_usd']:.4f}")
    
    print("\n✓ MLOps infrastructure ready!")
