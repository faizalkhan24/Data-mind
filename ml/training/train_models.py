"""DataMind Advanced Model Progression Pipeline.

Trains, tunes, and evaluates a progression of machine learning algorithms
for 24-hour device failure prediction:
1. Linear Baseline: Logistic Regression (from Milestone 4)
2. Bagging Ensemble: Random Forest Classifier
3. Gradient Boosting: XGBoost Classifier

Enforces rigorous ML engineering practices:
- Group-aware device partitioning (70% train, 15% validation, 15% test).
- Class imbalance mitigation (class_weight='balanced_subsample', scale_pos_weight).
- Threshold tuning optimized on Validation set, evaluated on holdout Test set.
- Latency benchmarking (inference time per observation).
- Feature importance extraction and visual comparison.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from ml.evaluation.metrics import (
    ClassificationMetrics,
    calculate_metrics,
    find_optimal_threshold,
    format_metrics_table,
    plot_confusion_matrix_heatmap,
    plot_curves,
)
from ml.training.data_split import DatasetSplits, split_by_device

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ModelProgressionTrainer:
    """Trains and compares Logistic Regression, Random Forest, and XGBoost."""

    def __init__(
        self,
        data_path: str | Path = "data/processed/featured_telemetry.parquet",
        target_col: str = "failed_within_24h",
        random_seed: int = 42,
    ) -> None:
        self.data_path = Path(data_path)
        self.target_col = target_col
        self.random_seed = random_seed
        self.splits: DatasetSplits | None = None
        self.feature_cols: List[str] = []

    def load_and_split(self) -> DatasetSplits:
        """Loads processed telemetry dataset and performs device-aware split."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Featured dataset not found at: {self.data_path.resolve()}")

        logger.info("Loading dataset from %s...", self.data_path.resolve())
        if self.data_path.suffix == ".parquet":
            df = pd.read_parquet(self.data_path)
        else:
            df = pd.read_csv(self.data_path)

        exclude_cols = {"device_id", "timestamp", self.target_col}
        self.feature_cols = [c for c in df.columns if c not in exclude_cols]

        self.splits = split_by_device(
            df=df,
            train_ratio=0.70,
            val_ratio=0.15,
            test_ratio=0.15,
            random_seed=self.random_seed,
        )
        return self.splits

    def measure_inference_latency(
        self, model: Any, X_sample: np.ndarray, num_runs: int = 500
    ) -> float:
        """Measures average inference latency in microseconds per single sample."""
        single_row = X_sample[:1]
        # Warmup
        for _ in range(20):
            _ = model.predict_proba(single_row)

        start = time.perf_counter()
        for _ in range(num_runs):
            _ = model.predict_proba(single_row)
        total_time = time.perf_counter() - start
        avg_micros = (total_time / num_runs) * 1_000_000
        return round(avg_micros, 2)

    def run_progression(
        self,
        figures_dir: str | Path = "docs/figures",
        models_dir: str | Path = "ml/models",
    ) -> Dict[str, Any]:
        """Trains, tunes, and compares Logistic Regression, Random Forest, and XGBoost."""
        if self.splits is None:
            self.load_and_split()

        assert self.splits is not None
        X_train = self.splits.train[self.feature_cols].values
        y_train = self.splits.train[self.target_col].values

        X_val = self.splits.val[self.feature_cols].values
        y_val = self.splits.val[self.target_col].values

        X_test = self.splits.test[self.feature_cols].values
        y_test = self.splits.test[self.target_col].values

        pos_count_train = int(np.sum(y_train))
        neg_count_train = len(y_train) - pos_count_train
        scale_pos = neg_count_train / max(1, pos_count_train)

        fig_dir = Path(figures_dir)
        fig_dir.mkdir(parents=True, exist_ok=True)
        mod_dir = Path(models_dir)
        mod_dir.mkdir(parents=True, exist_ok=True)

        all_test_metrics: List[ClassificationMetrics] = []
        test_curves_data: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        latencies: Dict[str, float] = {}

        # ---------------------------------------------------------------------
        # 1. Linear Baseline: Logistic Regression
        # ---------------------------------------------------------------------
        logger.info("Training Model 1: Logistic Regression...")
        lr_pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=1000, random_state=self.random_seed)),
            ]
        )
        lr_pipe.fit(X_train, y_train)
        lr_val_prob = lr_pipe.predict_proba(X_val)[:, 1]
        lr_test_prob = lr_pipe.predict_proba(X_test)[:, 1]

        lr_thresh, _ = find_optimal_threshold(y_val, lr_val_prob, metric="f1")
        m_lr = calculate_metrics(y_test, lr_test_prob, threshold=lr_thresh, model_name=f"Logistic Regression (Thresh={lr_thresh:.2f})", split_name="Test")
        all_test_metrics.append(m_lr)
        test_curves_data["Logistic Regression"] = (y_test, lr_test_prob)
        latencies["Logistic Regression"] = self.measure_inference_latency(lr_pipe, X_test)

        # ---------------------------------------------------------------------
        # 2. Bagging Ensemble: Random Forest Classifier
        # ---------------------------------------------------------------------
        logger.info("Training Model 2: Random Forest Classifier (150 trees)...")
        rf = RandomForestClassifier(
            n_estimators=150,
            max_depth=12,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=self.random_seed,
            n_jobs=-1,
        )
        rf.fit(X_train, y_train)
        rf_val_prob = rf.predict_proba(X_val)[:, 1]
        rf_test_prob = rf.predict_proba(X_test)[:, 1]

        rf_thresh, _ = find_optimal_threshold(y_val, rf_val_prob, metric="f1")
        m_rf = calculate_metrics(y_test, rf_test_prob, threshold=rf_thresh, model_name=f"Random Forest (Thresh={rf_thresh:.2f})", split_name="Test")
        all_test_metrics.append(m_rf)
        test_curves_data["Random Forest"] = (y_test, rf_test_prob)
        latencies["Random Forest"] = self.measure_inference_latency(rf, X_test)

        # ---------------------------------------------------------------------
        # 3. Gradient Boosting: XGBoost Classifier
        # ---------------------------------------------------------------------
        logger.info("Training Model 3: XGBoost Classifier (scale_pos_weight=%.2f)...", scale_pos)
        xgb = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            scale_pos_weight=scale_pos,
            eval_metric="aucpr",
            early_stopping_rounds=20,
            random_state=self.random_seed,
            n_jobs=-1,
        )
        # Fit with validation early stopping
        xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        xgb_val_prob = xgb.predict_proba(X_val)[:, 1]
        xgb_test_prob = xgb.predict_proba(X_test)[:, 1]

        xgb_thresh, _ = find_optimal_threshold(y_val, xgb_val_prob, metric="f1")
        m_xgb = calculate_metrics(y_test, xgb_test_prob, threshold=xgb_thresh, model_name=f"XGBoost (Thresh={xgb_thresh:.2f})", split_name="Test")
        all_test_metrics.append(m_xgb)
        test_curves_data["XGBoost"] = (y_test, xgb_test_prob)
        latencies["XGBoost"] = self.measure_inference_latency(xgb, X_test)

        # ---------------------------------------------------------------------
        # Visualizations & Feature Importance Comparison
        # ---------------------------------------------------------------------
        # 1. Comparative ROC and PR curves
        curves_file = fig_dir / "model_progression_curves.png"
        plot_curves(test_curves_data, curves_file)

        # 2. Confusion Matrix for Best Model (XGBoost)
        cm_best = [[m_xgb.tn, m_xgb.fp], [m_xgb.fn, m_xgb.tp]]
        cm_file = fig_dir / "xgboost_confusion_matrix.png"
        plot_confusion_matrix_heatmap(cm_best, f"XGBoost Test (Thresh={xgb_thresh:.2f})", cm_file)

        # 3. Feature Importance Extraction
        rf_importances = rf.feature_importances_
        xgb_importances = xgb.feature_importances_

        feat_imp_df = pd.DataFrame(
            {
                "feature": self.feature_cols,
                "rf_importance": rf_importances,
                "xgb_importance": xgb_importances,
            }
        ).sort_values(by="xgb_importance", ascending=False)

        # Plot Top 15 Feature Importances
        plt.figure(figsize=(10, 6.5))
        top15 = feat_imp_df.head(15).sort_values(by="xgb_importance", ascending=True)
        y_indices = np.arange(len(top15))
        height = 0.38

        plt.barh(y_indices + height / 2, top15["xgb_importance"], height=height, label="XGBoost (Gain)", color="#2b5c8f")
        plt.barh(y_indices - height / 2, top15["rf_importance"], height=height, label="Random Forest (Impurity)", color="#4a7c59")
        plt.yticks(y_indices, top15["feature"])
        plt.xlabel("Relative Importance")
        plt.title("Top 15 Feature Importances: Random Forest vs. XGBoost", fontweight="bold", pad=12)
        plt.legend(loc="lower right")
        plt.tight_layout()
        feat_imp_file = fig_dir / "feature_importance_comparison.png"
        plt.savefig(feat_imp_file, dpi=200)
        plt.close()

        # ---------------------------------------------------------------------
        # Save Trained Model Artifacts
        # ---------------------------------------------------------------------
        joblib.dump(
            {
                "model": rf,
                "feature_names": self.feature_cols,
                "threshold": rf_thresh,
                "test_metrics": m_rf.to_dict(),
                "latency_us": latencies["Random Forest"],
            },
            mod_dir / "model_random_forest.joblib",
        )

        joblib.dump(
            {
                "model": xgb,
                "feature_names": self.feature_cols,
                "threshold": xgb_thresh,
                "test_metrics": m_xgb.to_dict(),
                "latency_us": latencies["XGBoost"],
            },
            mod_dir / "best_model_xgboost.joblib",
        )
        logger.info("Saved serialized models to %s", mod_dir.resolve())

        # ---------------------------------------------------------------------
        # Metrics Reporting
        # ---------------------------------------------------------------------
        table_md = format_metrics_table(all_test_metrics)
        print("\n" + "=" * 95)
        print("                 DATAMIND MODEL PROGRESSION BENCHMARK REPORT (HOLDOUT TEST)")
        print("=" * 95)
        print(table_md)
        print("-" * 95)
        print("Single-Sample Inference Latency:")
        for m_name, lat in latencies.items():
            print(f"  {m_name:<25}: {lat:>8.2f} µs / prediction")
        print("=" * 95 + "\n")

        return {
            "metrics": [m.to_dict() for m in all_test_metrics],
            "metrics_table_md": table_md,
            "latencies": latencies,
            "feature_importance": feat_imp_df.to_dict(orient="records"),
            "best_model_path": str(mod_dir / "best_model_xgboost.joblib"),
            "figures": [str(curves_file), str(cm_file), str(feat_imp_file)],
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DataMind Model Progression Benchmark")
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/processed/featured_telemetry.parquet",
        help="Path to feature dataset (default: data/processed/featured_telemetry.parquet)",
    )
    parser.add_argument(
        "--figures-dir",
        type=str,
        default="docs/figures",
        help="Directory to save figures (default: docs/figures)",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="ml/models",
        help="Directory to save model artifacts (default: ml/models)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trainer = ModelProgressionTrainer(data_path=args.data_path)
    trainer.run_progression(figures_dir=args.figures_dir, models_dir=args.models_dir)


if __name__ == "__main__":
    main()
