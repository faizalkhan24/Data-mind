"""Unit tests for dataset validator."""

import unittest
import numpy as np
import pandas as pd

from ml.data_pipeline.generate_dataset import (
    GeneratorConfig,
    TelemetryDatasetGenerator,
)
from ml.data_pipeline.validate_dataset import (
    DatasetValidator,
)


class TestDatasetValidator(unittest.TestCase):
    """Test suite for DatasetValidator."""

    def setUp(self):
        """Create a valid baseline DataFrame."""
        config = GeneratorConfig(
            num_devices=10,
            measurements_per_device=20,
            random_seed=42,
        )
        self.valid_df = TelemetryDatasetGenerator(config).generate()

    def test_valid_dataset_passes(self):
        """Verifies that a valid generated dataset passes all checks."""
        validator = DatasetValidator(self.valid_df)
        summary = validator.run_all()
        self.assertTrue(summary.passed_all_critical)
        self.assertEqual(summary.total_errors, 0)

    def test_missing_column_fails(self):
        """Verifies failure when a required column is dropped."""
        df = self.valid_df.drop(columns=["voltage"])
        validator = DatasetValidator(df)
        summary = validator.run_all()
        self.assertFalse(summary.passed_all_critical)
        failed_checks = [c for c in summary.checks if not c.passed]
        self.assertTrue(any("Required Columns Present" in c.check_name for c in failed_checks))

    def test_null_value_fails(self):
        """Verifies failure when null/NaN is introduced."""
        df = self.valid_df.copy()
        df.loc[0, "temperature"] = np.nan
        validator = DatasetValidator(df)
        summary = validator.run_all()
        self.assertFalse(summary.passed_all_critical)
        failed_checks = [c for c in summary.checks if not c.passed]
        self.assertTrue(any("Missing Values" in c.check_name for c in failed_checks))

    def test_empty_string_fails(self):
        """Verifies failure when empty string is introduced."""
        df = self.valid_df.copy()
        df.loc[0, "firmware_version"] = "   "
        validator = DatasetValidator(df)
        summary = validator.run_all()
        self.assertFalse(summary.passed_all_critical)
        failed_checks = [c for c in summary.checks if not c.passed]
        self.assertTrue(any("Missing Values" in c.check_name for c in failed_checks))

    def test_out_of_range_temperature_fails(self):
        """Verifies failure when temperature is physically unrealistic."""
        df = self.valid_df.copy()
        df.loc[0, "temperature"] = 250.0
        validator = DatasetValidator(df)
        summary = validator.run_all()
        self.assertFalse(summary.passed_all_critical)
        failed_checks = [c for c in summary.checks if not c.passed]
        self.assertTrue(any("Range Check: temperature" in c.check_name for c in failed_checks))

    def test_out_of_range_battery_fails(self):
        """Verifies failure when battery level exceeds 100%."""
        df = self.valid_df.copy()
        df.loc[0, "battery_level"] = 105
        validator = DatasetValidator(df)
        summary = validator.run_all()
        self.assertFalse(summary.passed_all_critical)
        failed_checks = [c for c in summary.checks if not c.passed]
        self.assertTrue(any("Range Check: battery_level" in c.check_name for c in failed_checks))

    def test_duplicate_primary_keys_fail(self):
        """Verifies failure when duplicate (device_id, timestamp) rows exist."""
        df = self.valid_df.copy()
        duplicate_row = df.iloc[[0]].copy()
        df = pd.concat([df, duplicate_row], ignore_index=True)
        validator = DatasetValidator(df)
        summary = validator.run_all()
        self.assertFalse(summary.passed_all_critical)
        failed_checks = [c for c in summary.checks if not c.passed]
        self.assertTrue(any("Primary Key Uniqueness" in c.check_name for c in failed_checks))

    def test_non_binary_target_fails(self):
        """Verifies failure when target contains non-binary values."""
        df = self.valid_df.copy()
        df.loc[0, "failed_within_24h"] = 2
        validator = DatasetValidator(df)
        summary = validator.run_all()
        self.assertFalse(summary.passed_all_critical)
        failed_checks = [c for c in summary.checks if not c.passed]
        self.assertTrue(any("Target Binary Values" in c.check_name for c in failed_checks))

    def test_non_monotonic_timestamps_fail(self):
        """Verifies failure when timestamps are out of order for a device."""
        df = self.valid_df.copy()
        # Swap timestamps for rows 0 and 1
        t0 = df.loc[0, "timestamp"]
        t1 = df.loc[1, "timestamp"]
        df.loc[0, "timestamp"] = t1
        df.loc[1, "timestamp"] = t0
        validator = DatasetValidator(df)
        summary = validator.run_all()
        self.assertFalse(summary.passed_all_critical)
        failed_checks = [c for c in summary.checks if not c.passed]
        self.assertTrue(any("Chronological Monotonicity" in c.check_name for c in failed_checks))


if __name__ == "__main__":
    unittest.main()
