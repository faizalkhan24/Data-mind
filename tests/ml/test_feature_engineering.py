"""Unit tests for Feature Engineering Pipeline."""

import tempfile
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

from ml.data_pipeline.generate_dataset import GeneratorConfig, TelemetryDatasetGenerator
from ml.feature_engineering.pipeline import (
    PREDICTOR_FEATURE_NAMES,
    FeatureEngineeringPipeline,
    process_dataset_file,
)


class TestFeatureEngineeringPipeline(unittest.TestCase):
    """Test suite for FeatureEngineeringPipeline."""

    @classmethod
    def setUpClass(cls):
        """Generate a deterministic small telemetry dataset for testing."""
        config = GeneratorConfig(
            num_devices=5,
            measurements_per_device=30,
            random_seed=42,
        )
        cls.raw_df = TelemetryDatasetGenerator(config).generate()

    def test_feature_names_list(self):
        """Verifies feature names list matches specification."""
        pipeline = FeatureEngineeringPipeline()
        pipeline.fit(self.raw_df)
        feature_names = pipeline.get_feature_names()

        self.assertEqual(len(feature_names), 25)
        for expected in PREDICTOR_FEATURE_NAMES:
            self.assertIn(expected, feature_names)

    def test_no_null_values_produced(self):
        """Verifies that transformation produces zero NaN or infinite values."""
        pipeline = FeatureEngineeringPipeline()
        featured_df = pipeline.fit_transform(self.raw_df)

        self.assertEqual(len(featured_df), len(self.raw_df))
        self.assertEqual(featured_df.isna().sum().sum(), 0)
        # Check no inf
        numeric_cols = [c for c in pipeline.get_feature_names()]
        self.assertFalse(np.isinf(featured_df[numeric_cols].values).any())

    def test_device_group_isolation_no_cross_leakage(self):
        """Verifies that rolling windows and diffs are strictly isolated between devices."""
        df_custom = pd.DataFrame(
            {
                "device_id": ["DEV-A", "DEV-A", "DEV-B", "DEV-B"],
                "timestamp": [
                    "2026-01-01T00:00:00",
                    "2026-01-01T01:00:00",
                    "2026-01-01T00:00:00",
                    "2026-01-01T01:00:00",
                ],
                "temperature": [40.0, 50.0, 90.0, 95.0],
                "voltage": [3.8, 3.7, 3.1, 3.0],
                "current": [1.2, 1.3, 2.5, 2.6],
                "battery_level": [90, 89, 40, 38],
                "network_quality": [95, 94, 60, 59],
                "error_count": [0, 1, 15, 18],
                "restart_count": [0, 0, 3, 4],
                "uptime_hours": [100.0, 101.0, 5.0, 6.0],
                "firmware_version": ["1.0.0", "1.0.0", "1.2.0", "1.2.0"],
                "failed_within_24h": [0, 0, 1, 1],
            }
        )
        pipeline = FeatureEngineeringPipeline()
        out = pipeline.fit_transform(df_custom)

        # DEV-B row 0 (index 2) should NOT use DEV-A row 1 (index 1) for temperature_change_1h
        # Its change should be 0.0 because it is the first observation of DEV-B
        dev_b_row0 = out[(out["device_id"] == "DEV-B") & (out["timestamp"] == "2026-01-01T00:00:00")].iloc[0]
        self.assertEqual(dev_b_row0["temperature_change_1h"], 0.0)

        # DEV-A row 1 should have delta = 50.0 - 40.0 = 10.0
        dev_a_row1 = out[(out["device_id"] == "DEV-A") & (out["timestamp"] == "2026-01-01T01:00:00")].iloc[0]
        self.assertEqual(dev_a_row1["temperature_change_1h"], 10.0)

        # DEV-B row 1 should have delta = 95.0 - 90.0 = 5.0
        dev_b_row1 = out[(out["device_id"] == "DEV-B") & (out["timestamp"] == "2026-01-01T01:00:00")].iloc[0]
        self.assertEqual(dev_b_row1["temperature_change_1h"], 5.0)

    def test_rolling_aggregations_mathematical_correctness(self):
        """Verifies rolling mean and min calculations on a simple time series."""
        df_dev = pd.DataFrame(
            {
                "device_id": ["DEV-X"] * 4,
                "timestamp": [f"2026-01-01T0{i}:00:00" for i in range(4)],
                "temperature": [10.0, 20.0, 30.0, 40.0],
                "voltage": [4.0, 3.8, 3.6, 3.4],
                "current": [1.0, 1.1, 1.2, 1.3],
                "battery_level": [100, 95, 90, 85],
                "network_quality": [90, 90, 90, 90],
                "error_count": [1, 2, 3, 4],
                "restart_count": [0, 0, 0, 1],
                "uptime_hours": [10.0, 11.0, 12.0, 0.5],
                "firmware_version": ["1.1.0"] * 4,
                "failed_within_24h": [0, 0, 0, 1],
            }
        )
        pipeline = FeatureEngineeringPipeline()
        out = pipeline.fit_transform(df_dev)

        # Row 0: mean over 1 obs = 10.0
        self.assertAlmostEqual(out.loc[0, "temperature_mean_6h"], 10.0)
        # Row 1: mean over 2 obs = (10+20)/2 = 15.0
        self.assertAlmostEqual(out.loc[1, "temperature_mean_6h"], 15.0)
        # Row 2: mean over 3 obs = (10+20+30)/3 = 20.0
        self.assertAlmostEqual(out.loc[2, "temperature_mean_6h"], 20.0)
        # Row 3: mean over 4 obs = (10+20+30+40)/4 = 25.0
        self.assertAlmostEqual(out.loc[3, "temperature_mean_6h"], 25.0)

        # voltage_min_6h for Row 3: min(4.0, 3.8, 3.6, 3.4) = 3.4
        self.assertAlmostEqual(out.loc[3, "voltage_min_6h"], 3.4)

        # error_count_6h for Row 3: sum(1, 2, 3, 4) = 10
        self.assertEqual(out.loc[3, "error_count_6h"], 10)

    def test_firmware_one_hot_encoding(self):
        """Verifies that firmware categories are strictly binary one-hot encoded."""
        pipeline = FeatureEngineeringPipeline()
        featured_df = pipeline.fit_transform(self.raw_df)

        fw_cols = [c for c in featured_df.columns if c.startswith("firmware_version_")]
        self.assertGreaterEqual(len(fw_cols), 3)

        # Each row must have exactly one firmware version active (sum = 1)
        row_sums = featured_df[fw_cols].sum(axis=1)
        self.assertTrue((row_sums == 1).all())

    def test_metadata_save_and_load(self):
        """Verifies pipeline configuration serialization and deserialization."""
        pipeline = FeatureEngineeringPipeline()
        pipeline.fit(self.raw_df)

        with tempfile.TemporaryDirectory() as tmp_dir:
            meta_file = Path(tmp_dir) / "pipeline_meta.json"
            pipeline.save_metadata(meta_file)

            self.assertTrue(meta_file.exists())
            loaded = FeatureEngineeringPipeline.load_metadata(meta_file)
            self.assertEqual(loaded.known_firmware_versions, pipeline.known_firmware_versions)
            self.assertEqual(loaded.get_feature_names(), pipeline.get_feature_names())

    def test_process_dataset_file(self):
        """Verifies batch file processing and disk export."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            in_csv = Path(tmp_dir) / "raw.csv"
            out_parquet = Path(tmp_dir) / "featured.parquet"
            out_csv = Path(tmp_dir) / "featured.csv"

            self.raw_df.to_csv(in_csv, index=False)
            res = process_dataset_file(in_csv, out_parquet, out_csv)

            self.assertTrue(out_parquet.exists())
            self.assertTrue(out_csv.exists())
            self.assertEqual(len(res), len(self.raw_df))


if __name__ == "__main__":
    unittest.main()
