"""Unit tests for evaluation metrics module."""

import unittest
import numpy as np

from ml.evaluation.metrics import (
    calculate_metrics,
    find_optimal_threshold,
    format_metrics_table,
)


class TestEvaluationMetrics(unittest.TestCase):
    """Test suite for metrics calculation."""

    def test_calculate_metrics_perfect_predictions(self):
        """Verifies metric outputs when predictions are 100% accurate."""
        y_true = [0, 0, 1, 1]
        y_prob = [0.1, 0.2, 0.8, 0.9]

        m = calculate_metrics(y_true, y_prob, threshold=0.5)

        self.assertEqual(m.accuracy, 1.0)
        self.assertEqual(m.precision, 1.0)
        self.assertEqual(m.recall, 1.0)
        self.assertEqual(m.f1, 1.0)
        self.assertEqual(m.roc_auc, 1.0)
        self.assertEqual(m.pr_auc, 1.0)
        self.assertEqual(m.tn, 2)
        self.assertEqual(m.fp, 0)
        self.assertEqual(m.fn, 0)
        self.assertEqual(m.tp, 2)

    def test_calculate_metrics_majority_class_always_zero(self):
        """Verifies majority-class predictor achieves 0 recall/f1 despite high accuracy."""
        y_true = [0] * 90 + [1] * 10
        y_prob = [0.0] * 100  # Always predicts 0

        m = calculate_metrics(y_true, y_prob, threshold=0.5)

        self.assertEqual(m.accuracy, 0.90)
        self.assertEqual(m.recall, 0.0)
        self.assertEqual(m.precision, 0.0)
        self.assertEqual(m.f1, 0.0)
        self.assertEqual(m.tn, 90)
        self.assertEqual(m.fn, 10)

    def test_find_optimal_threshold(self):
        """Verifies threshold optimization logic for F1."""
        y_true = np.array([0, 0, 0, 1, 1])
        y_prob = np.array([0.1, 0.2, 0.35, 0.4, 0.8])

        thresh, score = find_optimal_threshold(y_true, y_prob, metric="f1")
        self.assertGreater(score, 0.5)
        self.assertGreaterEqual(thresh, 0.1)
        self.assertLessEqual(thresh, 0.9)

    def test_format_metrics_table(self):
        """Verifies markdown table formatting."""
        m = calculate_metrics([0, 1], [0.1, 0.9], model_name="TestModel", split_name="Test")
        table = format_metrics_table([m])

        self.assertIn("TestModel", table)
        self.assertIn("Accuracy", table)
        self.assertIn("PR-AUC", table)


if __name__ == "__main__":
    unittest.main()
