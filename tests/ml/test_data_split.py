"""Unit tests for dataset splitting strategies."""

import unittest
import numpy as np
import pandas as pd

from ml.training.data_split import split_by_device, split_by_time


class TestDataSplit(unittest.TestCase):
    """Test suite for dataset partitioning."""

    def setUp(self):
        # 10 devices, 10 timestamps each = 100 rows
        records = []
        for d in range(10):
            dev_id = f"DEV-{d:03d}"
            for t in range(10):
                records.append(
                    {
                        "device_id": dev_id,
                        "timestamp": f"2026-01-01T{t:02d}:00:00",
                        "val": float(d * 10 + t),
                    }
                )
        self.df = pd.DataFrame(records)

    def test_split_by_device_disjoint_sets(self):
        """Verifies that devices are strictly disjoint across train, val, and test."""
        splits = split_by_device(self.df, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2, random_seed=42)

        train_devs = set(splits.train_devices)
        val_devs = set(splits.val_devices)
        test_devs = set(splits.test_devices)

        # Disjointness checks
        self.assertEqual(len(train_devs.intersection(val_devs)), 0)
        self.assertEqual(len(train_devs.intersection(test_devs)), 0)
        self.assertEqual(len(val_devs.intersection(test_devs)), 0)

        # Union check
        all_devs = train_devs.union(val_devs).union(test_devs)
        self.assertEqual(len(all_devs), 10)

        # Row counts match
        self.assertEqual(len(splits.train), 60)
        self.assertEqual(len(splits.val), 20)
        self.assertEqual(len(splits.test), 20)

    def test_split_by_device_invalid_ratios(self):
        """Verifies that invalid ratio sums raise ValueError."""
        with self.assertRaises(ValueError):
            split_by_device(self.df, train_ratio=0.5, val_ratio=0.2, test_ratio=0.1)

    def test_split_by_time(self):
        """Verifies chronological cutoff partitioning."""
        splits = split_by_time(
            self.df,
            train_end_time="2026-01-01T05:00:00",
            val_end_time="2026-01-01T07:00:00",
        )

        self.assertTrue((splits.train["timestamp"] <= "2026-01-01T05:00:00").all())
        self.assertTrue((splits.val["timestamp"] > "2026-01-01T05:00:00").all())
        self.assertTrue((splits.val["timestamp"] <= "2026-01-01T07:00:00").all())
        self.assertTrue((splits.test["timestamp"] > "2026-01-01T07:00:00").all())


if __name__ == "__main__":
    unittest.main()
