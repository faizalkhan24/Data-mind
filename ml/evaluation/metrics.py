"""DataMind Evaluation Metrics Module.

Computes comprehensive classification metrics for imbalanced failure prediction:
- PR-AUC (Average Precision score)
- ROC-AUC
- Precision, Recall, F1-Score
- Confusion Matrix (TN, FP, FN, TP)
- Optimal threshold tuning
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ClassificationMetrics:
    """Standardized evaluation results container."""

    model_name: str
    split_name: str
    num_samples: int
    num_positives: int
    positive_rate: float
    threshold: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    tn: int
    fp: int
    fn: int
    tp: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_metrics(
    y_true: np.ndarray | List[int],
    y_prob: np.ndarray | List[float],
    threshold: float = 0.5,
    model_name: str = "Model",
    split_name: str = "Test",
) -> ClassificationMetrics:
    """Computes full suite of classification metrics given true labels and probabilities."""
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    y_pred_arr = (y_prob_arr >= threshold).astype(int)

    n_samples = len(y_true_arr)
    n_positives = int(np.sum(y_true_arr))
    pos_rate = float(n_positives / max(1, n_samples))

    # Confusion matrix
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    # Core rates
    acc = float((tp + tn) / max(1, n_samples))
    prec = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))

    # Ranking metrics (AUC)
    # Handle single-class edge cases safely
    if len(np.unique(y_true_arr)) > 1:
        roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
        pr_auc = float(average_precision_score(y_true_arr, y_prob_arr))
    else:
        roc_auc = 0.5
        pr_auc = pos_rate

    return ClassificationMetrics(
        model_name=model_name,
        split_name=split_name,
        num_samples=n_samples,
        num_positives=n_positives,
        positive_rate=pos_rate,
        threshold=round(threshold, 4),
        accuracy=round(acc, 4),
        precision=round(prec, 4),
        recall=round(rec, 4),
        f1=round(f1, 4),
        roc_auc=round(roc_auc, 4),
        pr_auc=round(pr_auc, 4),
        tn=tn,
        fp=fp,
        fn=fn,
        tp=tp,
    )


def find_optimal_threshold(
    y_true: np.ndarray | List[int],
    y_prob: np.ndarray | List[float],
    metric: str = "f1",
) -> Tuple[float, float]:
    """Finds probability threshold maximizing the specified metric (default: F1)."""
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    precisions, recalls, thresholds = precision_recall_curve(y_true_arr, y_prob_arr)
    # precision_recall_curve returns thresholds of len n-1; last precision=1, recall=0
    f1_scores = (2 * precisions * recalls) / np.maximum(precisions + recalls, 1e-10)

    if metric == "f1":
        best_idx = int(np.argmax(f1_scores[:-1])) if len(thresholds) > 0 else 0
        best_threshold = float(thresholds[best_idx]) if len(thresholds) > 0 else 0.5
        best_score = float(f1_scores[best_idx])
        return round(best_threshold, 4), round(best_score, 4)

    raise ValueError(f"Unsupported metric for threshold optimization: {metric}")


def format_metrics_table(metrics_list: List[ClassificationMetrics]) -> str:
    """Formats comparison metrics into a structured markdown table."""
    headers = [
        "Model",
        "Split",
        "Threshold",
        "Accuracy",
        "Precision",
        "Recall",
        "F1-Score",
        "PR-AUC",
        "ROC-AUC",
        "TN / FP / FN / TP",
    ]
    rows = []
    for m in metrics_list:
        cm_str = f"{m.tn:,} / {m.fp:,} / {m.fn:,} / {m.tp:,}"
        rows.append(
            f"| **{m.model_name}** | {m.split_name} | {m.threshold:.2f} | {m.accuracy*100:.2f}% | {m.precision:.4f} | {m.recall:.4f} | {m.f1:.4f} | **{m.pr_auc:.4f}** | {m.roc_auc:.4f} | {cm_str} |"
        )

    table_header = "| " + " | ".join(headers) + " |\n"
    separator = "| " + " | ".join([":---"] + [":---:"] * (len(headers) - 1)) + " |\n"
    return table_header + separator + "\n".join(rows)


def plot_curves(
    curves_data: Dict[str, Tuple[np.ndarray, np.ndarray]],
    output_path: str | Path,
) -> Path:
    """Plots comparative ROC and Precision-Recall curves.

    curves_data: dict of model_name -> (y_true, y_prob)
    """
    fig, (ax_pr, ax_roc) = plt.subplots(1, 2, figsize=(13, 5))

    for model_name, (y_true, y_prob) in curves_data.items():
        # PR Curve
        prec, rec, _ = precision_recall_curve(y_true, y_prob)
        pr_auc = average_precision_score(y_true, y_prob)
        ax_pr.plot(rec, prec, lw=2, label=f"{model_name} (PR-AUC = {pr_auc:.3f})")

        # ROC Curve
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        roc_auc = roc_auc_score(y_true, y_prob)
        ax_roc.plot(fpr, tpr, lw=2, label=f"{model_name} (ROC-AUC = {roc_auc:.3f})")

    # Baseline references
    sample_y_true = next(iter(curves_data.values()))[0]
    base_rate = float(np.mean(sample_y_true))
    ax_pr.axhline(base_rate, color="gray", linestyle="--", label=f"Random Chance ({base_rate:.3f})")
    ax_pr.set_xlabel("Recall")
    ax_pr.set_ylabel("Precision")
    ax_pr.set_title("Precision-Recall (PR) Curves", fontweight="bold")
    ax_pr.legend(loc="lower left")

    ax_roc.plot([0, 1], [0, 1], color="gray", linestyle="--", label="Random Chance (0.500)")
    ax_roc.set_xlabel("False Positive Rate (FPR)")
    ax_roc.set_ylabel("True Positive Rate (Recall)")
    ax_roc.set_title("Receiver Operating Characteristic (ROC)", fontweight="bold")
    ax_roc.legend(loc="lower right")

    plt.suptitle("Baseline Model Discrimination & Ranking Performance", fontsize=13, fontweight="bold")
    plt.tight_layout()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(target, dpi=200)
    plt.close()
    return target


def plot_confusion_matrix_heatmap(
    cm: np.ndarray | List[List[int]],
    model_name: str,
    output_path: str | Path,
) -> Path:
    """Plots formatted confusion matrix heatmap with counts and percentages."""
    cm_arr = np.asarray(cm)
    total = np.sum(cm_arr)

    labels = [
        [f"TN\n{cm_arr[0,0]:,}\n({cm_arr[0,0]/total*100:.1f}%)", f"FP\n{cm_arr[0,1]:,}\n({cm_arr[0,1]/total*100:.1f}%)"],
        [f"FN\n{cm_arr[1,0]:,}\n({cm_arr[1,0]/total*100:.1f}%)", f"TP\n{cm_arr[1,1]:,}\n({cm_arr[1,1]/total*100:.1f}%)"],
    ]

    plt.figure(figsize=(5.5, 4.5))
    sns.heatmap(
        cm_arr,
        annot=labels,
        fmt="",
        cmap="Blues",
        cbar=False,
        xticklabels=["Pred: Normal (0)", "Pred: Failure (1)"],
        yticklabels=["Actual: Normal (0)", "Actual: Failure (1)"],
    )
    plt.title(f"Confusion Matrix: {model_name}", fontweight="bold", pad=10)
    plt.tight_layout()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(target, dpi=200)
    plt.close()
    return target
