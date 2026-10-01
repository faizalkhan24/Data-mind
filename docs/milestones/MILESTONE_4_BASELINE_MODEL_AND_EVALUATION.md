# Milestone 4: Baseline Failure Prediction Model & Evaluation Framework

> **Milestone ID:** `M4-BASELINE-MODEL-EVALUATION`  
> **Status:** Completed  
> **Date:** 2026-10-01  
> **Target Metric:** PR-AUC, F1-Score, Recall, Precision, ROC-AUC  

---

## 1. Objective & Motivation

Milestone 4 establishes the predictive modeling baseline and evaluation framework for DataMind, following Sections 14 and 15 of the project specification:
1. **Never jump directly to complex black-box models:** Build naive and linear baselines first to establish rigorous performance floors.
2. **Prevent cross-device autocorrelation leakage:** Use group-aware device partitioning so the model is evaluated on completely unseen hardware fleets.
3. **Prove why accuracy is deceptive:** Demonstrate empirically that a 93.46% accurate naive predictor achieves 0.00% recall on actual failures.
4. **Tune decision thresholds based on operational costs:** Optimize probability thresholds on the Validation set and measure generalization on the holdout Test set.

---

## 2. Dataset Splitting Strategy & Leakage Prevention

Because device telemetry forms an autocorrelated time series per hardware unit, randomly splitting rows across time steps would leak past and future states of the same device into training.

### Group-Aware Device Split Configuration:
* **Train Set (70%):** 700 devices (70,000 rows, 7.46% positive failure rate).
* **Validation Set (15%):** 150 devices (15,000 rows, 7.65% positive failure rate).
* **Test Set (15%):** 150 devices (15,000 rows, 6.54% positive failure rate).
* **Leakage Guarantee:** Every device's entire 100-hour operational history resides exclusively in one partition. Preprocessing scalers (`StandardScaler`) are fitted **strictly on the Train partition**.

---

## 3. Empirical Model Comparison Results

All models evaluated across identical, fixed partitions:

| Model | Partition | Decision Thresh | Accuracy | Precision | Recall | F1-Score | PR-AUC | ROC-AUC | Confusion Matrix (TN / FP / FN / TP) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Dummy** | Validation | 0.50 | 92.35% | 0.0000 | 0.0000 | 0.0000 | **0.0765** | 0.5000 | 13,852 / 0 / 1,148 / 0 |
| **Majority Dummy** | Test | 0.50 | 93.46% | 0.0000 | 0.0000 | 0.0000 | **0.0654** | 0.5000 | 14,019 / 0 / 981 / 0 |
| **Stratified Dummy** | Validation | 0.50 | 85.93% | 0.0780 | 0.0775 | 0.0778 | **0.0766** | 0.5008 | 12,800 / 1,052 / 1,059 / 89 |
| **Stratified Dummy** | Test | 0.50 | 86.87% | 0.0666 | 0.0775 | 0.0716 | **0.0655** | 0.5008 | 12,954 / 1,065 / 905 / 76 |
| **Logistic Regression (Default)** | Validation | 0.50 | 99.16% | 0.9821 | 0.9068 | 0.9429 | **0.9691** | 0.9871 | 13,833 / 19 / 107 / 1,041 |
| **Logistic Regression (Default)** | **Test** | **0.50** | **99.29%** | **0.9720** | **0.9185** | **0.9444** | **0.9625** | **0.9841** | **13,993 / 26 / 80 / 901** |
| **Logistic Regression (Balanced)** | Validation | 0.50 | 99.03% | 0.9246 | 0.9503 | 0.9373 | **0.9691** | 0.9869 | 13,763 / 89 / 57 / 1,091 |
| **Logistic Regression (Balanced)** | **Test** | **0.50** | **99.06%** | **0.9150** | **0.9439** | **0.9293** | **0.9618** | **0.9832** | **13,933 / 86 / 55 / 926** |
| **Logistic Regression (Tuned)** | Validation | 0.24 | 99.29% | 0.9736 | 0.9329 | 0.9528 | **0.9691** | 0.9871 | 13,823 / 29 / 77 / 1,071 |
| **Logistic Regression (Tuned)** | **Test** | **0.24** | **99.29%** | **0.9581** | **0.9317** | **0.9447** | **0.9625** | **0.9841** | **13,979 / 40 / 67 / 914** |

---

## 4. Engineering & ML Insights

### 4.1 The Accuracy Paradox in Predictive Maintenance
The Majority Class Dummy achieves an impressive **93.46% accuracy** on the holdout test set by simply predicting that no device ever fails.
* **Failure Miss Rate:** It produces **0 True Positives** and **981 False Negatives** (Recall = 0.00%, F1 = 0.00%).
* **Takeaway:** In imbalanced failure prediction (~7.35% positive rate), accuracy is an uninformative metric. **PR-AUC (0.9625)**, **Recall (93.17%)**, and **Precision (95.81%)** are the true north-star metrics.

### 4.2 Linear Model Explainability: Feature Weights
Because Logistic Regression is fitted on standardized features ($\mu=0, \sigma=1$), feature coefficients directly reveal the log-odds impact of each physical signal:

#### Top Risk Factors (Positive Weights):
1. `temperature`: **$+2.42$** (die overheating directly drives failure odds)
2. `current`: **$+2.41$** (high electrical draw from short circuits / runaway)
3. `network_quality_mean_6h`: **$+1.47$**
4. `voltage_mean_6h`: **$+1.47$**
5. `error_count`: **$+1.25$** (bursts of computational faults)

#### Top Protective / Negative Factors (Negative Weights):
1. `battery_change_24h`: **$-3.27$** (rapid battery drainage over 24h is the strongest early warning sign)
2. `voltage`: **$-2.88$** (dropping rail voltage heavily signals power system collapse)
3. `network_quality`: **$-1.80$** (packet loss under stress)
4. `restart_count`: **$-1.36$**

This empirical attribution directly validates the initial problem domain:
$$\text{High Temp} + \text{Voltage Collapse} + \text{Battery Drain} + \text{Error Bursts} \implies \text{High Failure Probability}$$

---

## 5. Threshold Tuning & Operational Trade-offs

In industrial predictive maintenance, the business cost of a **False Negative** (an undetected catastrophic device failure causing downtime and customer outage) is typically $5\times$ to $20\times$ higher than a **False Positive** (a technician running a non-invasive diagnostic check on a healthy device).

* **Default Threshold ($\tau = 0.50$):**
  * Recall: 91.85% (80 failures missed out of 981).
  * False Positives: 26.
* **Tuned Threshold ($\tau = 0.24$, optimized for F1 on Validation):**
  * Recall increases to **93.17%** (only 67 failures missed out of 981, catching 13 additional impending failures).
  * Precision remains high at **95.81%** (only 40 false alarms out of 14,019 healthy observations).
* **Balanced Weights ($\text{class\_weight}=\text{'balanced'}$):**
  * Maximizes Recall to **94.39%** (only 55 failures missed), while maintaining 91.50% Precision.

---

## 6. Generated Visual Artifacts

Evaluation figures are saved in [`docs/figures/`](file:///d:/DataMind/docs/figures/):
* [`baseline_roc_pr_curves.png`](file:///d:/DataMind/docs/figures/baseline_roc_pr_curves.png): Comparative Precision-Recall and ROC curves demonstrating clear separation of Logistic Regression (PR-AUC 0.962) over naive random baselines (PR-AUC 0.065).
* [`baseline_confusion_matrix.png`](file:///d:/DataMind/docs/figures/baseline_confusion_matrix.png): Heatmap of test set predictions under the tuned threshold ($\tau=0.24$) showing 13,979 TN, 40 FP, 67 FN, 914 TP.

---

## 7. Model Serialization & Registry

* **Model Artifact:** [`ml/models/baseline_logistic_regression.joblib`](file:///d:/DataMind/ml/models/baseline_logistic_regression.joblib) (serialized Scikit-Learn Pipeline combining `StandardScaler` and `LogisticRegression`, plus threshold metadata and feature schema).
* The artifact is kept out of Git via `.gitignore` (`ml/models/*`), adhering to Rule 14.

---

## 8. Automated Unit Test Verification

* **New Test Suites:**
  * [`tests/ml/test_data_split.py`](file:///d:/DataMind/tests/ml/test_data_split.py): 3 tests verifying disjoint device partitions, ratio enforcement, and chronological cutoff.
  * [`tests/ml/test_evaluation.py`](file:///d:/DataMind/tests/ml/test_evaluation.py): 4 tests verifying metric calculation, dummy baseline behavior, threshold optimization, and markdown table formatting.
  * [`tests/ml/test_training.py`](file:///d:/DataMind/tests/ml/test_training.py): 1 end-to-end integration test verifying training orchestration and artifact persistence.
* **Total Automated Tests:** **32/32 tests passing** in 7.48s.

---

## 9. How to Reproduce

```powershell
# 1. Run baseline model training and evaluation
python ml/training/baseline_model.py

# 2. Run automated test suite
python -m unittest discover -s tests -t . -v
```
