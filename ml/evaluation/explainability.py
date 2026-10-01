"""DataMind Model Explainability & Feature Attribution Engine.

Leverages SHAP (SHapley Additive exPlanations) TreeExplainer to deliver both:
1. Global Fleet Interpretability: Identifies overall drivers of failure across the device population.
2. Local Real-Time Explanations: Deconstructs single-device predictions into quantified,
   human-readable risk factors suitable for operations dashboards and automated alerts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure repo root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Feature category taxonomy mapping engineered signals to operational domains
FEATURE_CATEGORY_MAP: Dict[str, str] = {
    "temperature": "Thermal Stress / Chassis Heat",
    "temperature_mean_6h": "Thermal Stress / Sustained Heat",
    "temperature_mean_24h": "Thermal Stress / 24h Baseline",
    "temperature_std_6h": "Thermal Volatility / Fluctuation",
    "temperature_change_1h": "Thermal Velocity / Spike",
    "voltage": "Power Rail Sag / Instability",
    "voltage_mean_6h": "Power Rail Sag / 6h Average",
    "voltage_min_6h": "Power Rail Sag / Brownout Event",
    "voltage_std_6h": "Electrical Jitter / Regulator Noise",
    "current": "Electrical Load / Current Draw",
    "current_mean_6h": "Electrical Load / Sustained Draw",
    "battery_level": "Battery Depletion / Low Capacity",
    "battery_change_24h": "Battery Depletion / Rapid Drain",
    "error_count": "Computational Faults / Error Rate",
    "error_count_6h": "Computational Faults / Error Burst",
    "error_count_24h": "Computational Faults / 24h Errors",
    "restart_count": "Watchdog Crash Loops / Total Restarts",
    "restart_count_24h": "Watchdog Crash Loops / 24h Restarts",
    "uptime_hours": "Watchdog Crash Loops / Reset Uptime",
    "network_quality": "Wireless Connectivity / Link Quality",
    "network_quality_mean_6h": "Wireless Connectivity / Sustained Link",
    "device_age_hours": "Hardware Aging / Lifetime Wear",
    "firmware_version_1.0.0": "Firmware Version / Baseline Release",
    "firmware_version_1.1.0": "Firmware Version / Update Release",
    "firmware_version_1.2.0": "Firmware Version / Patch Release",
}


@dataclass
class RiskFactorAttribution:
    """Quantified operational risk factor attributing a portion of failure risk."""

    category: str
    feature_name: str
    feature_value: float
    attribution_score: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "featureName": self.feature_name,
            "featureValue": round(self.feature_value, 4),
            "attributionScore": round(self.attribution_score, 4),
            "description": self.description,
        }


@dataclass
class PredictionExplanation:
    """Complete prediction report with probability, risk level, and explanations."""

    device_id: Optional[str]
    timestamp: Optional[str]
    failure_probability: float
    risk_level: str
    prediction_label: int
    base_value: float
    top_risk_factors: List[RiskFactorAttribution]
    top_mitigating_factors: List[RiskFactorAttribution]
    feature_attributions: Dict[str, float]
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deviceId": self.device_id,
            "timestamp": self.timestamp,
            "failureProbability": round(self.failure_probability, 4),
            "riskLevel": self.risk_level,
            "predictionLabel": self.prediction_label,
            "baseValue": round(self.base_value, 4),
            "topRiskFactors": [f.to_dict() for f in self.top_risk_factors],
            "topMitigatingFactors": [f.to_dict() for f in self.top_mitigating_factors],
            "latencyMs": round(self.latency_ms, 3),
        }


class TelemetryExplainer:
    """Production-grade explainability engine wrapping SHAP TreeExplainer."""

    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        decision_threshold: float = 0.50,
    ) -> None:
        self.model = model
        self.feature_names = feature_names
        self.decision_threshold = float(decision_threshold)
        logger.info(
            "Initializing SHAP TreeExplainer for %d features (Threshold=%.4f)...",
            len(feature_names),
            self.decision_threshold,
        )
        self.explainer = shap.TreeExplainer(self.model)
        if np.isscalar(self.explainer.expected_value):
            self.base_value = float(self.explainer.expected_value)
        else:
            exp_arr = np.array(self.explainer.expected_value)
            if exp_arr.ndim == 1 and len(exp_arr) >= 2:
                self.base_value = float(exp_arr[1])
            else:
                self.base_value = float(exp_arr.ravel()[0])

    def _generate_factor_description(
        self, feature: str, value: float, shap_val: float
    ) -> str:
        """Constructs intuitive human-readable diagnostics for operators."""
        sign = "+" if shap_val > 0 else ""
        impact_str = f"({sign}{shap_val:.2f} log-odds)"

        if feature == "battery_change_24h":
            return f"24h battery capacity shifted by {value:+.1f}% {impact_str}"
        elif feature == "temperature":
            return f"Current chassis temperature is {value:.1f}°C {impact_str}"
        elif feature == "temperature_mean_6h":
            return f"Sustained 6h average temperature is {value:.1f}°C {impact_str}"
        elif feature == "voltage_min_6h":
            return f"Power rail dropped to minimum {value:.2f}V in past 6h {impact_str}"
        elif feature == "voltage_std_6h":
            return f"Electrical rail standard deviation reached {value:.3f}V {impact_str}"
        elif feature == "current_mean_6h":
            return f"Sustained 6h average current draw is {value:.2f}A {impact_str}"
        elif feature == "current":
            return f"Instantaneous current draw is {value:.2f}A {impact_str}"
        elif feature == "error_count_6h":
            return f"Accumulated {int(value)} system bus errors in trailing 6h {impact_str}"
        elif feature == "error_count_24h":
            return f"Recorded {int(value)} total errors across trailing 24h {impact_str}"
        elif feature == "restart_count_24h":
            return f"Underwent {int(value)} watchdog reboots in past 24h {impact_str}"
        elif feature == "uptime_hours":
            return f"Continuous uptime is {value:.1f} hours {impact_str}"
        elif feature == "network_quality_mean_6h":
            return f"6h wireless link quality averaged {value:.1f}% {impact_str}"
        elif feature == "device_age_hours":
            return f"Device total operational age is {value:.1f} hours {impact_str}"
        else:
            category = FEATURE_CATEGORY_MAP.get(feature, "Telemetry metric")
            return f"{category} ({feature}={value:.2f}) {impact_str}"

    def explain_instance(
        self,
        row_or_dict: Union[pd.Series, pd.DataFrame, Dict[str, Any]],
        device_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        top_k: int = 5,
    ) -> PredictionExplanation:
        """Generates a complete real-time prediction and diagnostic explanation."""
        start_time = time.perf_counter()

        if isinstance(row_or_dict, dict):
            device_id = device_id or row_or_dict.get("device_id")
            timestamp = timestamp or row_or_dict.get("timestamp")
            features_df = pd.DataFrame([{f: row_or_dict.get(f, 0.0) for f in self.feature_names}])
        elif isinstance(row_or_dict, pd.Series):
            device_id = device_id or row_or_dict.get("device_id")
            timestamp = timestamp or row_or_dict.get("timestamp")
            features_df = pd.DataFrame([row_or_dict[self.feature_names].to_dict()])
        elif isinstance(row_or_dict, pd.DataFrame):
            if "device_id" in row_or_dict.columns and device_id is None:
                device_id = str(row_or_dict["device_id"].iloc[0])
            if "timestamp" in row_or_dict.columns and timestamp is None:
                timestamp = str(row_or_dict["timestamp"].iloc[0])
            features_df = row_or_dict[self.feature_names].iloc[[0]]
        else:
            raise TypeError(f"Unsupported input type: {type(row_or_dict)}")

        # Ensure correct column ordering and float conversion
        X_vec = features_df[self.feature_names].astype(float)

        # 1. Model Prediction
        prob = float(self.model.predict_proba(X_vec)[0, 1])
        pred_label = 1 if prob >= self.decision_threshold else 0

        # Calibrate risk tier
        if prob >= self.decision_threshold:
            risk_level = "HIGH"
        elif prob >= self.decision_threshold * 0.45:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # 2. SHAP computation
        shap_explanation = self.explainer(X_vec)
        if shap_explanation.values.ndim == 3:
            shap_values = shap_explanation.values[0, :, 1]
        else:
            shap_values = shap_explanation.values[0]

        feature_attributions: Dict[str, float] = {}
        risk_factors: List[RiskFactorAttribution] = []
        mitigating_factors: List[RiskFactorAttribution] = []

        for f_name, s_val in zip(self.feature_names, shap_values):
            val = float(X_vec[f_name].iloc[0])
            s_float = float(s_val)
            feature_attributions[f_name] = s_float
            category = FEATURE_CATEGORY_MAP.get(f_name, "Operational Signal")
            desc = self._generate_factor_description(f_name, val, s_float)

            attribution = RiskFactorAttribution(
                category=category,
                feature_name=f_name,
                feature_value=val,
                attribution_score=s_float,
                description=desc,
            )

            if s_float > 0:
                risk_factors.append(attribution)
            else:
                mitigating_factors.append(attribution)

        # Sort risk factors descending (strongest positive drivers of failure)
        risk_factors.sort(key=lambda x: x.attribution_score, reverse=True)
        # Sort mitigating factors ascending (strongest negative push toward normal)
        mitigating_factors.sort(key=lambda x: x.attribution_score)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return PredictionExplanation(
            device_id=device_id,
            timestamp=timestamp,
            failure_probability=prob,
            risk_level=risk_level,
            prediction_label=pred_label,
            base_value=self.base_value,
            top_risk_factors=risk_factors[:top_k],
            top_mitigating_factors=mitigating_factors[:top_k],
            feature_attributions=feature_attributions,
            latency_ms=elapsed_ms,
        )

    def explain_batch(self, df: pd.DataFrame) -> shap.Explanation:
        """Computes SHAP explanations across an entire DataFrame partition."""
        X_mat = df[self.feature_names].astype(float)
        exp = self.explainer(X_mat)
        if exp.values.ndim == 3:
            return exp[:, :, 1]
        return exp

    def get_global_feature_importance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes mean absolute SHAP impact across the provided dataset."""
        logger.info("Computing global SHAP feature importance across %d rows...", len(df))
        shap_exp = self.explain_batch(df)
        mean_abs_shap = np.abs(shap_exp.values).mean(axis=0)

        importance_df = pd.DataFrame(
            {
                "feature": self.feature_names,
                "mean_abs_shap": mean_abs_shap,
                "category": [
                    FEATURE_CATEGORY_MAP.get(f, "Operational Signal")
                    for f in self.feature_names
                ],
            }
        ).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

        return importance_df

    def save_visualizations(
        self,
        df_test: pd.DataFrame,
        output_dir: Path,
        max_samples: int = 2000,
    ) -> List[Path]:
        """Generates publication-quality SHAP plots for documentation."""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: List[Path] = []

        logger.info("Generating SHAP figures using sample of %d rows...", min(len(df_test), max_samples))
        sample_df = df_test.sample(
            n=min(len(df_test), max_samples), random_state=42
        ).reset_index(drop=True)
        shap_exp = self.explain_batch(sample_df)

        # 1. Summary Beeswarm Plot
        plt.figure(figsize=(10, 8))
        shap.plots.beeswarm(shap_exp, max_display=15, show=False)
        plt.title("SHAP Beeswarm Summary: Impact on Device Failure Prediction", fontsize=13, pad=15)
        plt.tight_layout()
        beeswarm_path = output_dir / "shap_summary_beeswarm.png"
        plt.savefig(beeswarm_path, dpi=300)
        plt.close("all")
        saved_paths.append(beeswarm_path)
        logger.info("Saved beeswarm plot to %s", beeswarm_path)

        # 2. Mean Absolute SHAP Bar Plot
        plt.figure(figsize=(10, 7))
        importance_df = self.get_global_feature_importance(sample_df)
        top15 = importance_df.head(15).iloc[::-1]

        plt.barh(top15["feature"], top15["mean_abs_shap"], color="#1f77b4", edgecolor="#0d47a1")
        plt.xlabel("Mean |SHAP Value| (Average Impact on Model Log-Odds)", fontsize=11)
        plt.title("Global Feature Importance (SHAP TreeExplainer)", fontsize=13, pad=15)
        plt.grid(axis="x", linestyle="--", alpha=0.6)
        plt.tight_layout()
        bar_path = output_dir / "shap_importance_bar.png"
        plt.savefig(bar_path, dpi=300)
        plt.close("all")
        saved_paths.append(bar_path)
        logger.info("Saved feature importance bar plot to %s", bar_path)

        # 3. Local Waterfall: High-Risk Failing Device
        failing_candidates = df_test[df_test.get("failed_within_24h", 0) == 1]
        if not failing_candidates.empty:
            probs = self.model.predict_proba(failing_candidates[self.feature_names])[:, 1]
            best_idx = int(np.argmax(probs))
            failing_row = failing_candidates.iloc[[best_idx]]
            failing_exp = self.explain_batch(failing_row)[0]

            plt.figure(figsize=(10, 7))
            shap.plots.waterfall(failing_exp, max_display=10, show=False)
            dev_id = failing_row.get("device_id", pd.Series(["Unknown"])).iloc[0]
            prob_val = probs[best_idx]
            plt.title(
                f"SHAP Local Waterfall: Impending Failure ({dev_id}, P={prob_val:.1%})",
                fontsize=12,
                pad=15,
            )
            plt.tight_layout()
            failing_waterfall_path = output_dir / "shap_waterfall_failing_device.png"
            plt.savefig(failing_waterfall_path, dpi=300)
            plt.close("all")
            saved_paths.append(failing_waterfall_path)
            logger.info("Saved failing waterfall plot to %s", failing_waterfall_path)

        # 4. Local Waterfall: Nominal Healthy Device
        healthy_candidates = df_test[df_test.get("failed_within_24h", 0) == 0]
        if not healthy_candidates.empty:
            probs = self.model.predict_proba(healthy_candidates[self.feature_names])[:, 1]
            lowest_idx = int(np.argmin(probs))
            healthy_row = healthy_candidates.iloc[[lowest_idx]]
            healthy_exp = self.explain_batch(healthy_row)[0]

            plt.figure(figsize=(10, 7))
            shap.plots.waterfall(healthy_exp, max_display=10, show=False)
            dev_id = healthy_row.get("device_id", pd.Series(["Unknown"])).iloc[0]
            prob_val = probs[lowest_idx]
            plt.title(
                f"SHAP Local Waterfall: Healthy Baseline ({dev_id}, P={prob_val:.1%})",
                fontsize=12,
                pad=15,
            )
            plt.tight_layout()
            healthy_waterfall_path = output_dir / "shap_waterfall_healthy_device.png"
            plt.savefig(healthy_waterfall_path, dpi=300)
            plt.close("all")
            saved_paths.append(healthy_waterfall_path)
            logger.info("Saved healthy waterfall plot to %s", healthy_waterfall_path)

        return saved_paths


def load_explainer(
    model_path: Union[Path, str] = "ml/models/best_model_xgboost.joblib",
) -> TelemetryExplainer:
    """Loads a serialized model artifact and returns an initialized TelemetryExplainer."""
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found at {model_path}")

    artifact = joblib.load(model_path)
    model = artifact["model"]
    feature_names = artifact.get("feature_names", [])
    threshold = artifact.get("threshold", 0.50)

    return TelemetryExplainer(
        model=model,
        feature_names=feature_names,
        decision_threshold=threshold,
    )


def run_explainability_pipeline(
    data_path: Union[Path, str] = "data/processed/featured_telemetry.parquet",
    model_path: Union[Path, str] = "ml/models/best_model_xgboost.joblib",
    output_dir: Union[Path, str] = "docs/figures",
) -> Tuple[TelemetryExplainer, pd.DataFrame, List[Path]]:
    """Executes the explainability pipeline across the holdout test fleet."""
    from ml.training.data_split import split_by_device

    data_path = Path(data_path)
    model_path = Path(model_path)
    output_dir = Path(output_dir)

    logger.info("Loading dataset from %s...", data_path)
    df = pd.read_parquet(data_path)
    splits = split_by_device(df)
    test_df = splits.test

    explainer = load_explainer(model_path)
    importance_df = explainer.get_global_feature_importance(test_df)

    print("\n" + "=" * 80)
    print("           DATAMIND TOP GLOBAL RISK FACTORS (SHAP TREEEXPLAINER)")
    print("=" * 80)
    print(
        f"{'Rank':<5} | {'Feature':<26} | {'Mean |SHAP|':<12} | {'Operational Domain'}"
    )
    print("-" * 80)
    for idx, row in importance_df.head(10).iterrows():
        print(
            f"{idx+1:<5} | {row['feature']:<26} | {row['mean_abs_shap']:<12.4f} | {row['category']}"
        )
    print("=" * 80)

    # Demonstrate local explanation on a high-risk device
    failing_rows = test_df[test_df["failed_within_24h"] == 1]
    sample_failing = failing_rows.iloc[0]
    explanation = explainer.explain_instance(sample_failing)

    print("\n" + "=" * 80)
    print("         SAMPLE REAL-TIME LOCAL EXPLANATION (HIGH-RISK DEVICE)")
    print("=" * 80)
    print(f"Device ID:            {explanation.device_id}")
    print(f"Timestamp:            {explanation.timestamp}")
    print(f"Failure Probability:  {explanation.failure_probability:.2%}")
    print(f"Risk Tier:            {explanation.risk_level}")
    print(f"Prediction Label:     {explanation.prediction_label} (Impending Failure)")
    print(f"Inference Latency:    {explanation.latency_ms:.2f} ms")
    print("\nTop Contributing Risk Factors:")
    for f in explanation.top_risk_factors:
        print(f"  [+] {f.category:<30} | {f.description}")
    print("\nTop Mitigating Factors:")
    for f in explanation.top_mitigating_factors:
        print(f"  [-] {f.category:<30} | {f.description}")
    print("=" * 80 + "\n")

    saved_figures = explainer.save_visualizations(test_df, output_dir)
    return explainer, importance_df, saved_figures


if __name__ == "__main__":
    run_explainability_pipeline()
