"""Unit tests for the DataMind Model Explainability & Feature Attribution Engine."""

import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ml.evaluation.explainability import (
    FEATURE_CATEGORY_MAP,
    PredictionExplanation,
    RiskFactorAttribution,
    TelemetryExplainer,
    load_explainer,
)


class TestTelemetryExplainer(unittest.TestCase):
    """Test suite for TelemetryExplainer and SHAP integration."""

    @classmethod
    def setUpClass(cls) -> None:
        """Sets up a lightweight synthetic dataset and trained model for fast testing."""
        np.random.seed(42)
        cls.n_samples = 100
        cls.feature_names = [
            "temperature",
            "voltage",
            "current",
            "battery_level",
            "battery_change_24h",
            "temperature_mean_6h",
            "voltage_min_6h",
            "error_count_6h",
        ]

        # Generate synthetic feature matrix
        data = {
            "temperature": np.random.uniform(30, 85, cls.n_samples),
            "voltage": np.random.uniform(3.0, 4.2, cls.n_samples),
            "current": np.random.uniform(0.8, 2.5, cls.n_samples),
            "battery_level": np.random.uniform(20, 100, cls.n_samples),
            "battery_change_24h": np.random.uniform(-30, 0, cls.n_samples),
            "temperature_mean_6h": np.random.uniform(30, 80, cls.n_samples),
            "voltage_min_6h": np.random.uniform(2.8, 3.8, cls.n_samples),
            "error_count_6h": np.random.poisson(2, cls.n_samples),
        }
        cls.df = pd.DataFrame(data)
        # Synthetic binary target strongly correlated with high temp and battery drop
        cls.y = (
            (cls.df["temperature"] > 65) | (cls.df["battery_change_24h"] < -20)
        ).astype(int)

        cls.model = RandomForestClassifier(n_estimators=10, max_depth=4, random_state=42)
        cls.model.fit(cls.df[cls.feature_names], cls.y)
        cls.threshold = 0.40
        cls.explainer = TelemetryExplainer(
            model=cls.model,
            feature_names=cls.feature_names,
            decision_threshold=cls.threshold,
        )

    def test_explainer_initialization(self) -> None:
        """Verifies proper initialization, threshold assignment, and base value extraction."""
        self.assertEqual(len(self.explainer.feature_names), len(self.feature_names))
        self.assertEqual(self.explainer.decision_threshold, 0.40)
        self.assertIsInstance(self.explainer.base_value, float)

    def test_explain_instance_series(self) -> None:
        """Verifies explanation output when input is a pandas Series."""
        row = self.df.iloc[0].copy()
        row["device_id"] = "DEV-00001"
        row["timestamp"] = "2026-01-01T12:00:00"

        exp = self.explainer.explain_instance(row, top_k=3)
        self.assertIsInstance(exp, PredictionExplanation)
        self.assertEqual(exp.device_id, "DEV-00001")
        self.assertEqual(exp.timestamp, "2026-01-01T12:00:00")
        self.assertGreaterEqual(exp.failure_probability, 0.0)
        self.assertLessEqual(exp.failure_probability, 1.0)
        self.assertIn(exp.risk_level, {"LOW", "MEDIUM", "HIGH"})
        self.assertIn(exp.prediction_label, {0, 1})
        self.assertGreater(exp.latency_ms, 0.0)

    def test_explain_instance_dict(self) -> None:
        """Verifies explanation output when input is a Python dictionary."""
        row_dict = self.df.iloc[1].to_dict()
        row_dict["device_id"] = "DEV-00002"

        exp = self.explainer.explain_instance(row_dict, top_k=4)
        self.assertEqual(exp.device_id, "DEV-00002")
        self.assertIsInstance(exp.top_risk_factors, list)
        self.assertLessEqual(len(exp.top_risk_factors), 4)

    def test_explain_instance_dataframe(self) -> None:
        """Verifies explanation output when input is a single-row DataFrame."""
        row_df = self.df.iloc[[2]].copy()
        row_df["device_id"] = "DEV-00003"
        row_df["timestamp"] = "2026-01-02T00:00:00"

        exp = self.explainer.explain_instance(row_df, top_k=5)
        self.assertEqual(exp.device_id, "DEV-00003")
        self.assertEqual(exp.timestamp, "2026-01-02T00:00:00")

    def test_prediction_explanation_to_dict_serialization(self) -> None:
        """Verifies JSON serializability and schema of to_dict() output."""
        row = self.df.iloc[3]
        exp = self.explainer.explain_instance(row, device_id="DEV-00042")
        exp_dict = exp.to_dict()

        self.assertIsInstance(exp_dict, dict)
        self.assertEqual(exp_dict["deviceId"], "DEV-00042")
        self.assertIn("failureProbability", exp_dict)
        self.assertIn("riskLevel", exp_dict)
        self.assertIn("topRiskFactors", exp_dict)
        self.assertIn("topMitigatingFactors", exp_dict)
        self.assertIn("latencyMs", exp_dict)

        # Ensure valid JSON encoding
        serialized = json.dumps(exp_dict)
        self.assertIsInstance(serialized, str)

    def test_risk_factors_sorting_and_signs(self) -> None:
        """Verifies risk factors are positive sorted descending and mitigating are negative sorted ascending."""
        row = self.df.iloc[4]
        exp = self.explainer.explain_instance(row)

        for rf in exp.top_risk_factors:
            self.assertIsInstance(rf, RiskFactorAttribution)
            self.assertGreater(rf.attribution_score, 0.0)

        # Check descending order of risk factors
        risk_scores = [rf.attribution_score for rf in exp.top_risk_factors]
        self.assertEqual(risk_scores, sorted(risk_scores, reverse=True))

        for mf in exp.top_mitigating_factors:
            self.assertIsInstance(mf, RiskFactorAttribution)
            self.assertLessEqual(mf.attribution_score, 0.0)

        # Check ascending order of mitigating factors
        mitigating_scores = [mf.attribution_score for mf in exp.top_mitigating_factors]
        self.assertEqual(mitigating_scores, sorted(mitigating_scores))

    def test_explain_batch(self) -> None:
        """Verifies batch explanations across multiple records."""
        shap_exp = self.explainer.explain_batch(self.df.iloc[:15])
        self.assertEqual(shap_exp.values.shape, (15, len(self.feature_names)))

    def test_global_feature_importance(self) -> None:
        """Verifies global feature importance calculation and descending sort."""
        importance_df = self.explainer.get_global_feature_importance(self.df)
        self.assertEqual(len(importance_df), len(self.feature_names))
        self.assertListEqual(
            list(importance_df.columns), ["feature", "mean_abs_shap", "category"]
        )
        # Verify monotonically non-increasing
        diffs = np.diff(importance_df["mean_abs_shap"].to_numpy())
        self.assertTrue(np.all(diffs <= 1e-6))

    def test_load_explainer_nonexistent_file(self) -> None:
        """Verifies FileNotFoundError on invalid artifact path."""
        with self.assertRaises(FileNotFoundError):
            load_explainer("ml/models/non_existent_model_123.joblib")


if __name__ == "__main__":
    unittest.main()
