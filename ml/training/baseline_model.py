"""DataMind Baseline Failure Prediction Model.

Trains and evaluates baseline models for 24-hour device failure prediction:
1. Naive Majority-Class Baseline (always predicts 0).
2. Stratified Random Dummy Baseline.
3. Standard Logistic Regression (threshold = 0.50).
4. Balanced Logistic Regression (class_weight='balanced').
5. Optimal-Threshold Logistic Regression (decision threshold tuned on Validation set).

Enforces strict leak-free practices:
- Group-aware device splitting (70% train, 15% validation, 15% test).
- Preprocessing scaler fitted strictly on training data only.
- Threshold tuned on validation partition and evaluated on test partition.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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


class BaselineModelTrainer:
    """Orchestrates baseline model training and evaluation."""

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

        # Exclude metadata and target columns from feature inputs
        exclude_cols = {"device_id", "timestamp", self.target_col}
        self.feature_cols = [c for c in df.columns if c not in exclude_cols]

        logger.info(
            "Identified %d predictor features across %d total rows.",
            len(self.feature_cols),
            len(df),
        )

        self.splits = split_by_device(
            df=df,
            train_ratio=0.70,
            val_ratio=0.15,
            test_ratio=0.15,
            random_seed=self.random_seed,
        )
        return self.splits

    def run_training_and_evaluation(
        self,
        figures_dir: str | Path = "docs/figures",
        models_dir: str | Path = "ml/models",
    ) -> Dict[str, Any]:
        """Trains all baselines and evaluates on validation and test sets."""
        if self.splits is None:
            self.load_and_split()

        assert self.splits is not None
        X_train = self.splits.train[self.feature_cols].values
        y_train = self.splits.train[self.target_col].values

        X_val = self.splits.val[self.feature_cols].values
        y_val = self.splits.val[self.target_col].values

        X_test = self.splits.test[self.feature_cols].values
        y_test = self.splits.test[self.target_col].values

        logger.info(
            "Split counts: Train=%d (%.2f%% pos), Val=%d (%.2f%% pos), Test=%d (%.2f%% pos)",
            len(y_train),
            np.mean(y_train) * 100,
            len(y_val),
            np.mean(y_val) * 100,
            len(y_test),
            np.mean(y_test) * 100,
        )

        all_metrics: List[ClassificationMetrics] = []
        test_curves_data: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

        # ---------------------------------------------------------------------
        # 1. Naive Baseline: Majority Class Dummy (always 0)
        # ---------------------------------------------------------------------
        logger.info("Training Majority Class Dummy Baseline...")
        dummy_majority = DummyClassifier(strategy="most_frequent")
        dummy_majority.fit(X_train, y_train)

        maj_val_prob = dummy_majority.predict_proba(X_val)[:, 1]
        maj_test_prob = dummy_majority.predict_proba(X_test)[:, 1]

        m_maj_val = calculate_metrics(y_val, maj_val_prob, model_name="Majority Dummy", split_name="Validation")
        m_maj_test = calculate_metrics(y_test, maj_test_prob, model_name="Majority Dummy", split_name="Test")
        all_metrics.extend([m_maj_val, m_maj_test])
        test_curves_data["Majority Dummy"] = (y_test, maj_test_prob)

        # ---------------------------------------------------------------------
        # 2. Naive Baseline: Stratified Dummy (random chance proportional to prior)
        # ---------------------------------------------------------------------
        logger.info("Training Stratified Random Dummy Baseline...")
        dummy_strat = DummyClassifier(strategy="stratified", random_state=self.random_seed)
        dummy_strat.fit(X_train, y_train)

        strat_val_prob = dummy_strat.predict_proba(X_val)[:, 1]
        strat_test_prob = dummy_strat.predict_proba(X_test)[:, 1]

        m_strat_val = calculate_metrics(y_val, strat_val_prob, model_name="Stratified Dummy", split_name="Validation")
        m_strat_test = calculate_metrics(y_test, strat_test_prob, model_name="Stratified Dummy", split_name="Test")
        all_metrics.extend([m_strat_val, m_strat_test])
        test_curves_data["Stratified Dummy"] = (y_test, strat_test_prob)

        # ---------------------------------------------------------------------
        # 3. Machine Learning Baseline: Standard Logistic Regression (Default Threshold = 0.5)
        # ---------------------------------------------------------------------
        logger.info("Training Standard Logistic Regression...")
        logreg_standard = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1000,
                        random_state=self.random_seed,
                        solver="lbfgs",
                    ),
                ),
            ]
        )
        logreg_standard.fit(X_train, y_train)

        lr_val_prob = logreg_standard.predict_proba(X_val)[:, 1]
        lr_test_prob = logreg_standard.predict_proba(X_test)[:, 1]

        m_lr_val = calculate_metrics(y_val, lr_val_prob, threshold=0.5, model_name="Logistic Regression (Default)", split_name="Validation")
        m_lr_test = calculate_metrics(y_test, lr_test_prob, threshold=0.5, model_name="Logistic Regression (Default)", split_name="Test")
        all_metrics.extend([m_lr_val, m_lr_test])
        test_curves_data["Logistic Regression"] = (y_test, lr_test_prob)

        # ---------------------------------------------------------------------
        # 4. Machine Learning Baseline: Balanced Logistic Regression
        # ---------------------------------------------------------------------
        logger.info("Training Balanced Logistic Regression (class_weight='balanced')...")
        logreg_balanced = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=self.random_seed,
                        solver="lbfgs",
                    ),
                ),
            ]
        )
        logreg_balanced.fit(X_train, y_train)

        lr_bal_val_prob = logreg_balanced.predict_proba(X_val)[:, 1]
        lr_bal_test_prob = logreg_balanced.predict_proba(X_test)[:, 1]

        m_bal_val = calculate_metrics(y_val, lr_bal_val_prob, threshold=0.5, model_name="Logistic Regression (Balanced)", split_name="Validation")
        m_bal_test = calculate_metrics(y_test, lr_bal_test_prob, threshold=0.5, model_name="Logistic Regression (Balanced)", split_name="Test")
        all_metrics.extend([m_bal_val, m_bal_test])

        # ---------------------------------------------------------------------
        # 5. Optimal Threshold Tuning on Validation Partition
        # ---------------------------------------------------------------------
        best_thresh, best_val_f1 = find_optimal_threshold(y_val, lr_val_prob, metric="f1")
        logger.info("Optimal threshold tuned on Validation set: %.4f (Val F1=%.4f)", best_thresh, best_val_f1)

        m_tuned_val = calculate_metrics(
            y_val,
            lr_val_prob,
            threshold=best_thresh,
            model_name=f"Logistic Regression (Tuned Thresh={best_thresh:.2f})",
            split_name="Validation",
        )
        m_tuned_test = calculate_metrics(
            y_test,
            lr_test_prob,
            threshold=best_thresh,
            model_name=f"Logistic Regression (Tuned Thresh={best_thresh:.2f})",
            split_name="Test",
        )
        all_metrics.extend([m_tuned_val, m_tuned_test])

        # ---------------------------------------------------------------------
        # Visualizations and Artifacts
        # ---------------------------------------------------------------------
        fig_dir = Path(figures_dir)
        fig_dir.mkdir(parents=True, exist_ok=True)
        mod_dir = Path(models_dir)
        mod_dir.mkdir(parents=True, exist_ok=True)

        # Plot curves
        curves_fig = fig_dir / "baseline_roc_pr_curves.png"
        plot_curves(test_curves_data, curves_fig)
        logger.info("Saved ROC and PR curves to %s", curves_fig.resolve())

        # Plot confusion matrix for tuned Logistic Regression on Test set
        cm_tuned = [[m_tuned_test.tn, m_tuned_test.fp], [m_tuned_test.fn, m_tuned_test.tp]]
        cm_fig = fig_dir / "baseline_confusion_matrix.png"
        plot_confusion_matrix_heatmap(cm_tuned, f"Logistic Regression (Thresh={best_thresh:.2f})", cm_fig)
        logger.info("Saved confusion matrix heatmap to %s", cm_fig.resolve())

        # Serialize model pipeline artifact
        model_artifact_path = mod_dir / "baseline_logistic_regression.joblib"
        joblib.dump(
            {
                "pipeline": logreg_standard,
                "feature_names": self.feature_cols,
                "optimal_threshold": best_thresh,
                "val_metrics": m_tuned_val.to_dict(),
                "test_metrics": m_tuned_test.to_dict(),
            },
            model_artifact_path,
        )
        logger.info("Saved serialized model artifact to %s", model_artifact_path.resolve())

        # Print metrics table
        table_md = format_metrics_table(all_metrics)
        print("\n" + "=" * 90)
        print("                   DATAMIND BASELINE MODEL EVALUATION REPORT")
        print("=" * 90)
        print(table_md)
        print("=" * 90 + "\n")

        # Feature coefficients analysis (LogReg explainability)
        coefficients = logreg_standard.named_steps["clf"].coef_[0]
        coef_df = pd.DataFrame({"feature": self.feature_cols, "coefficient": coefficients})
        coef_df["abs_coef"] = coef_df["coefficient"].abs()
        coef_df = coef_df.sort_values(by="abs_coef", ascending=False).drop(columns=["abs_coef"])

        return {
            "metrics": [m.to_dict() for m in all_metrics],
            "metrics_table_md": table_md,
            "optimal_threshold": best_thresh,
            "coefficients": coef_df.to_dict(orient="records"),
            "model_artifact": str(model_artifact_path),
            "curves_figure": str(curves_fig),
            "cm_figure": str(cm_fig),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DataMind Baseline Model Training & Evaluation")
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/processed/featured_telemetry.parquet",
        help="Path to input feature dataset (default: data/processed/featured_telemetry.parquet)",
    )
    parser.add_argument(
        "--figures-dir",
        type=str,
        default="docs/figures",
        help="Directory to save evaluation plots (default: docs/figures)",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="ml/models",
        help="Directory to save serialized model artifacts (default: ml/models)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trainer = BaselineModelTrainer(data_path=args.data_path)
    trainer.run_training_and_evaluation(
        figures_dir=args.figures_dir,
        models_dir=args.models_dir,
    )


if __name__ == "__main__":
    main()
