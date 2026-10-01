# Milestone 7: Model Registry & MLflow Tracking (MLOps)

> **Milestone ID:** `M7-MODEL-REGISTRY`  
> **Status:** Completed  
> **Date:** 2026-10-01  
> **Platform:** MLflow 3.16.1 (SQLite Backend: `sqlite:///mlflow.db`)  
> **Model Registry Target:** `DataMind-Device-Failure-Predictor`  
> **Champion Model:** Version 2 (XGBoost Engine)  

---

## 1. Objective & Motivation

In production systems, machine learning models cannot remain untracked `.joblib` files on disk. Production-grade MLOps requires:
1. **Experiment Provenance:** Strict tracking of hyperparameters, feature schemas, training runs, and evaluation metrics.
2. **Schema Enforcement:** Model signatures defining exact input columns, types, and expected output predictions.
3. **Model Versioning:** Immutable version history with status flags (`READY`, `FAILED`).
4. **Lifecycle Promotion:** Alias-based model deployment (e.g., `@champion`) to decouple model training from downstream inference APIs.

In Milestone 7, we implement an enterprise MLflow tracking and registry pipeline (`ml/training/register_model.py`) backed by a local SQLite tracking database.

---

## 2. MLflow Tracking Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   DataMind MLflow Engine                     │
│               Tracking URI: sqlite:///mlflow.db             │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
    ┌───────────▼───────────┐     ┌───────────▼───────────┐
    │  Experiment Tracking  │     │     Model Registry    │
    │  - Parameters         │     │  - Named Model:       │
    │  - Test Metrics       │     │    DataMind-Predictor │
    │  - Serialized Artifact│     │  - Versions: v1, v2   │
    │  - Diagnostic Figures │     │  - Alias: @champion   │
    └───────────────────────┘     └───────────────────────┘
```

* **Local SQLite Store:** Ensures ACID compliance and complete local reproducibility without external cloud dependencies.
* **Model Signatures:** Inferred using `mlflow.models.infer_signature` across the 25 input telemetry signals.

---

## 3. Experiment Tracking Ledger

The three candidate models developed across Milestones 4 and 5 were registered and tracked under experiment `DataMind-Predictive-Intelligence`:

| Run Name | Algorithm | PR-AUC | Recall | F1-Score | Latency | Stage Tag | Registry Version |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Baseline-Logistic-Regression`** | `LogisticRegression` | 0.9625 | 0.9317 | 0.9447 | 357.4 µs | `Archived-Baseline` | — |
| **`Ensemble-Random-Forest`** | `RandomForestClassifier` | **0.9671** | **0.9501** | **0.9457** | 26,177.0 µs | `Candidate-Batch` | Version 1 |
| **`Production-XGBoost-Engine`** | `XGBClassifier` | 0.9608 | 0.9388 | 0.9417 | **400.6 µs** | **`Production`** | **Version 2 (`@champion`)** |

---

## 4. Model Registry & Champion Promotion

### 4.1 Selection Rationale
- **Random Forest (Version 1)** achieves higher recall (95.01%), but its 26.2 ms latency violates real-time SLA thresholds (< 5 ms). It is retained as `Candidate-Batch` for offline scheduled scans.
- **XGBoost (Version 2)** achieves sub-millisecond scoring (**400 µs**) with 93.88% recall and 0.9608 PR-AUC.
- **Decision:** Version 2 is assigned the production alias **`champion`** in the MLflow Model Registry (`DataMind-Device-Failure-Predictor@champion`).

### 4.2 Supplementary Artifacts Logged per Run
- Serialized `.joblib` model binary and pipeline metadata JSON.
- Evaluation curves: [`model_progression_curves.png`](../figures/model_progression_curves.png)
- Feature importance: [`feature_importance_comparison.png`](../figures/feature_importance_comparison.png)
- Confusion matrix: [`xgboost_confusion_matrix.png`](../figures/xgboost_confusion_matrix.png)
- SHAP diagnostics: [`shap_summary_beeswarm.png`](../figures/shap_summary_beeswarm.png) & [`shap_importance_bar.png`](../figures/shap_importance_bar.png)

---

## 5. Automated Unit Test Verification

- **Module:** [`tests/ml/test_model_registry.py`](../../tests/ml/test_model_registry.py)
- **Coverage:**
  1. `test_manager_initialization`: Verifies SQLite database connection and experiment setup.
  2. `test_log_and_register_production_candidate`: Validates logging of parameters, metrics, tags, and model versions.
  3. `test_get_champion_model`: Validates retrieval of model and version metadata by alias.
  4. `test_list_registered_versions`: Validates search and status verification of registry models.
  5. `test_nonexistent_artifact_raises`: Validates error handling for missing files.

**Result:** **5/5 tests passed in 15.9s**.  
**Total Repository Suite:** **47/47 tests passing** across all modules.

---

## 6. How to Reproduce

```powershell
# Run the MLflow registration pipeline
python ml/training/register_model.py

# Run registry unit tests
python -m unittest tests/ml/test_model_registry.py -v

# Run entire repository test suite
python -m unittest discover -s tests -t . -v
```
