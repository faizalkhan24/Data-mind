"""Unit tests for EDA pipeline."""

import tempfile
from pathlib import Path
import unittest

from ml.data_pipeline.generate_dataset import GeneratorConfig, TelemetryDatasetGenerator
from ml.data_pipeline.eda import TelemetryEDA


class TestTelemetryEDA(unittest.TestCase):
    """Test suite for TelemetryEDA."""

    @classmethod
    def setUpClass(cls):
        """Generate a small deterministic dataset for testing."""
        config = GeneratorConfig(
            num_devices=10,
            measurements_per_device=20,
            random_seed=42,
        )
        cls.df = TelemetryDatasetGenerator(config).generate()

    def test_compute_overview(self):
        """Verifies calculation of dataset overview metrics."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            eda = TelemetryEDA(self.df, output_dir=tmp_dir)
            overview = eda.compute_overview()

            self.assertEqual(overview["total_records"], 200)
            self.assertEqual(overview["total_devices"], 10)
            self.assertEqual(overview["total_nulls"], 0)
            self.assertEqual(overview["duplicate_records"], 0)
            self.assertIn("class_0_count", overview)
            self.assertIn("class_1_count", overview)

    def test_compute_correlations(self):
        """Verifies calculation of Pearson and Spearman correlations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            eda = TelemetryEDA(self.df, output_dir=tmp_dir)
            corrs = eda.compute_correlations()

            self.assertIn("pearson", corrs.columns)
            self.assertIn("spearman", corrs.columns)
            self.assertIn("temperature", corrs.index)

    def test_compute_outliers(self):
        """Verifies calculation of IQR outlier statistics."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            eda = TelemetryEDA(self.df, output_dir=tmp_dir)
            outliers = eda.compute_outliers()

            self.assertIn("temperature", outliers)
            stats = outliers["temperature"]
            self.assertIn("q1", stats)
            self.assertIn("q3", stats)
            self.assertIn("iqr", stats)
            self.assertIn("outliers_count", stats)

    def test_full_pipeline_artifacts(self):
        """Verifies that running run_all creates all plots and markdown report."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            eda = TelemetryEDA(self.df, output_dir=tmp_dir)
            results = eda.run_all()

            report_file = Path(results["report_path"])
            self.assertTrue(report_file.exists())
            self.assertGreater(report_file.stat().st_size, 500)

            for fig_path_str in results["figures"]:
                fig_path = Path(fig_path_str)
                self.assertTrue(fig_path.exists())
                self.assertGreater(fig_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
