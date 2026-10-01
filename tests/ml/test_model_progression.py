"""Unit tests for model progression pipeline (Random Forest & XGBoost)."""

import tempfile
from pathlib import Path
import unittest
import numpy as np

from ml.data_pipeline.generate_dataset import GeneratorConfig, TelemetryDatasetGenerator
from ml.feature_engineering.pipeline import FeatureEngineeringPipeline
from ml.training.train_models import ModelProgressionTrainer


class TestModelProgression(unittest.TestCase):
    """Test suite for ModelProgressionTrainer."""

    @classmethod
    def setUpClass(cls):
        """Generate small featured dataset for unit tests."""
        cls.temp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(cls.temp_dir.name)

        gen_cfg = GeneratorConfig(num_devices=20, measurements_per_device=20, random_seed=42)
        raw_df = TelemetryDatasetGenerator(gen_cfg).generate()

        pipe = FeatureEngineeringPipeline()
        featured_df = pipe.fit_transform(raw_df)

        cls.parquet_path = tmp_path / "featured.parquet"
        featured_df.to_parquet(cls.parquet_path, index=False)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_model_progression_execution(self):
        """Verifies full training, evaluation, latency measurement, and artifact persistence."""
        with tempfile.TemporaryDirectory() as out_tmp:
            out_dir = Path(out_tmp)
            fig_dir = out_dir / "figures"
            mod_dir = out_dir / "models"

            trainer = ModelProgressionTrainer(data_path=self.parquet_path, random_seed=42)
            results = trainer.run_progression(figures_dir=fig_dir, models_dir=mod_dir)

            self.assertIn("metrics", results)
            self.assertIn("latencies", results)
            self.assertIn("feature_importance", results)

            # Check that all three model types are present
            model_names = [m["model_name"] for m in results["metrics"]]
            self.assertTrue(any("Logistic Regression" in name for name in model_names))
            self.assertTrue(any("Random Forest" in name for name in model_names))
            self.assertTrue(any("XGBoost" in name for name in model_names))

            # Verify latency outputs
            self.assertIn("Logistic Regression", results["latencies"])
            self.assertIn("Random Forest", results["latencies"])
            self.assertIn("XGBoost", results["latencies"])
            for model_name, lat in results["latencies"].items():
                self.assertGreater(lat, 0.0)

            # Check artifact existence
            self.assertTrue(Path(results["best_model_path"]).exists())
            for fig in results["figures"]:
                self.assertTrue(Path(fig).exists())


if __name__ == "__main__":
    unittest.main()
