"""Unit tests for baseline model training."""

import tempfile
from pathlib import Path
import unittest

from ml.data_pipeline.generate_dataset import GeneratorConfig, TelemetryDatasetGenerator
from ml.feature_engineering.pipeline import FeatureEngineeringPipeline
from ml.training.baseline_model import BaselineModelTrainer


class TestBaselineModelTraining(unittest.TestCase):
    """Test suite for BaselineModelTrainer."""

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

    def test_baseline_trainer_execution(self):
        """Verifies full baseline training pipeline run and artifact generation."""
        with tempfile.TemporaryDirectory() as out_tmp:
            out_dir = Path(out_tmp)
            fig_dir = out_dir / "figures"
            mod_dir = out_dir / "models"

            trainer = BaselineModelTrainer(data_path=self.parquet_path, random_seed=42)
            results = trainer.run_training_and_evaluation(figures_dir=fig_dir, models_dir=mod_dir)

            self.assertIn("metrics", results)
            self.assertIn("optimal_threshold", results)
            self.assertIn("coefficients", results)
            self.assertTrue(Path(results["model_artifact"]).exists())
            self.assertTrue(Path(results["curves_figure"]).exists())
            self.assertTrue(Path(results["cm_figure"]).exists())

            # Check that metrics contains both majority dummy and logistic regression
            model_names = {m["model_name"] for m in results["metrics"]}
            self.assertIn("Majority Dummy", model_names)
            self.assertIn("Logistic Regression (Default)", model_names)


if __name__ == "__main__":
    unittest.main()
