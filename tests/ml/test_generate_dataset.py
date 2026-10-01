"""Unit tests for synthetic dataset generator."""

import tempfile
from pathlib import Path
import unittest
import pandas as pd

from ml.data_pipeline.generate_dataset import (
    GeneratorConfig,
    TelemetryDatasetGenerator,
)
from ml.data_pipeline.validate_dataset import REQUIRED_COLUMNS


class TestTelemetryDatasetGenerator(unittest.TestCase):
    """Test suite for TelemetryDatasetGenerator."""

    def test_shape_and_columns(self):
        """Verifies dataset dimensions and required schema columns."""
        config = GeneratorConfig(
            num_devices=5,
            measurements_per_device=10,
            random_seed=42,
        )
        generator = TelemetryDatasetGenerator(config)
        df = generator.generate()

        self.assertEqual(df.shape, (50, 12))
        self.assertEqual(list(df.columns), REQUIRED_COLUMNS)
        self.assertEqual(df["device_id"].nunique(), 5)

    def test_deterministic_reproducibility(self):
        """Verifies that the same seed produces identical datasets."""
        config = GeneratorConfig(
            num_devices=10,
            measurements_per_device=20,
            random_seed=42,
        )
        gen1 = TelemetryDatasetGenerator(config)
        df1 = gen1.generate()

        gen2 = TelemetryDatasetGenerator(config)
        df2 = gen2.generate()

        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_produce_different_data(self):
        """Verifies that different seeds produce distinct datasets."""
        cfg1 = GeneratorConfig(num_devices=5, measurements_per_device=10, random_seed=42)
        cfg2 = GeneratorConfig(num_devices=5, measurements_per_device=10, random_seed=99)

        df1 = TelemetryDatasetGenerator(cfg1).generate()
        df2 = TelemetryDatasetGenerator(cfg2).generate()

        self.assertFalse(df1["temperature"].equals(df2["temperature"]))

    def test_save_dataset(self):
        """Verifies file saving to disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_measurements.csv"
            config = GeneratorConfig(
                num_devices=2,
                measurements_per_device=5,
                output_path=str(out_file),
            )
            generator = TelemetryDatasetGenerator(config)
            df = generator.generate()
            saved_path = generator.save_dataset(df, out_file)

            self.assertTrue(saved_path.exists())
            loaded = pd.read_csv(saved_path)
            self.assertEqual(len(loaded), 10)


if __name__ == "__main__":
    unittest.main()
