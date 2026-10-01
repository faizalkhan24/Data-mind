"""Unit tests for DataMind Model Registry & MLflow Tracking."""

import gc
from pathlib import Path
import tempfile
import unittest

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from ml.training.register_model import (
    MODEL_REGISTRY_NAME,
    ModelRegistryManager,
    RegisteredModelRecord,
)


class TestModelRegistry(unittest.TestCase):
    """Test suite for MLflow tracking, model signatures, and registry operations."""

    @classmethod
    def setUpClass(cls) -> None:
        """Sets up a temporary SQLite database and synthetic artifacts for isolated testing."""
        cls.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.temp_path = Path(cls.temp_dir.name)
        cls.tracking_db = cls.temp_path / "test_mlflow.db"
        cls.tracking_uri = f"sqlite:///{cls.tracking_db.as_posix()}"

        # Initialize manager with isolated test URI
        cls.manager = ModelRegistryManager(
            experiment_name="Test-DataMind-Experiment",
            tracking_uri=cls.tracking_uri,
        )

        # Create lightweight synthetic dataset
        cls.feature_names = ["temp", "voltage", "current"]
        cls.df = pd.DataFrame(
            {
                "temp": np.random.uniform(30, 80, 50),
                "voltage": np.random.uniform(3.0, 4.0, 50),
                "current": np.random.uniform(1.0, 2.0, 50),
            }
        )
        cls.y = (cls.df["temp"] > 60).astype(int)

        # Train and save a test model
        cls.model = LogisticRegression()
        cls.model.fit(cls.df[cls.feature_names], cls.y)
        cls.artifact_path = cls.temp_path / "test_model.joblib"
        joblib.dump(
            {
                "model": cls.model,
                "feature_names": cls.feature_names,
                "threshold": 0.45,
                "test_metrics": {
                    "pr_auc": 0.92,
                    "roc_auc": 0.95,
                    "recall": 0.90,
                    "precision": 0.88,
                    "f1": 0.89,
                    "accuracy": 0.91,
                },
                "latency_us": 320.5,
            },
            cls.artifact_path,
        )

        # Pre-register a champion model for inspection tests
        cls.champion_record = cls.manager.log_and_register_candidate(
            run_name="Setup-Champion-Run",
            artifact_path=cls.artifact_path,
            model_type="LogisticRegression",
            stage="Production",
            sample_features_df=cls.df,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        gc.collect()
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_manager_initialization(self) -> None:
        """Verifies tracking initialization and experiment attributes."""
        self.assertEqual(self.manager.experiment.name, "Test-DataMind-Experiment")
        self.assertIsNotNone(self.manager.client)

    def test_log_and_register_production_candidate(self) -> None:
        """Verifies full logging and promotion of a candidate model."""
        record = self.manager.log_and_register_candidate(
            run_name="Test-Candidate-Run",
            artifact_path=self.artifact_path,
            model_type="LogisticRegression",
            stage="Candidate-Batch",
            sample_features_df=self.df,
        )
        self.assertIsInstance(record, RegisteredModelRecord)
        self.assertIsNotNone(record.run_id)
        self.assertEqual(record.stage, "Candidate-Batch")
        self.assertEqual(record.model_name, MODEL_REGISTRY_NAME)
        self.assertIsNotNone(record.version)
        self.assertAlmostEqual(record.metrics["test_pr_auc"], 0.92, places=2)

    def test_get_champion_model(self) -> None:
        """Verifies retrieval of the production champion model by alias."""
        model, version_meta = self.manager.get_champion_model()
        self.assertIsNotNone(model)
        self.assertIsNotNone(version_meta)
        self.assertIn("champion", version_meta.aliases)

    def test_list_registered_versions(self) -> None:
        """Verifies listing versions in the registry."""
        versions = self.manager.list_registered_versions()
        self.assertIsInstance(versions, list)
        self.assertGreaterEqual(len(versions), 1)
        self.assertEqual(versions[0]["status"], "READY")

    def test_nonexistent_artifact_raises(self) -> None:
        """Verifies FileNotFoundError on invalid artifact path."""
        with self.assertRaises(FileNotFoundError):
            self.manager.log_and_register_candidate(
                run_name="Invalid-Run",
                artifact_path=self.temp_path / "nonexistent.joblib",
                model_type="None",
                stage="Baseline",
                sample_features_df=self.df,
            )


if __name__ == "__main__":
    unittest.main()
