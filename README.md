# DataMind: Predictive Intelligence & Failure Prevention Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11.9-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: 47 Passing](https://img.shields.io/badge/tests-47%20passed-brightgreen.svg)]()
[![Status: Phase 2 In Progress](https://img.shields.io/badge/status-7%2F14%20Milestones%20Complete-orange.svg)]()

**DataMind** is an enterprise-grade predictive intelligence platform designed to demonstrate deep Software Engineering, Data Engineering, and Machine Learning capabilities (Google Software Engineer standard). 

This is **not** a toy machine learning script, a static Jupyter notebook, or a simple CRUD application. It is a production-oriented distributed system engineered to ingest real-time IoT device telemetry, engineer temporal signals with zero leakage, score failure risk under strict latency SLAs (< 5 ms), explain predictions with game-theoretic attribution (SHAP), and serve actionable insights to operations teams.

---

## 1. Problem Statement: Predictive Maintenance

Given streaming hardware telemetry across an IoT fleet, **predict whether a device will experience an operational failure within the next 24 hours (`failed_within_24h`)**.

```json
{
  "deviceId": "DEV-00042",
  "predictionWindowHours": 24,
  "failureProbability": 0.884,
  "riskLevel": "HIGH",
  "latencyMs": 0.40,
  "topRiskFactors": [
    { "factor": "Rapid Battery Depletion", "feature": "battery_change_24h", "impact": "+0.34" },
    { "factor": "Thermal Runaway", "feature": "temperature_mean_6h", "impact": "+0.28" },
    { "factor": "Power Rail Sag", "feature": "voltage_min_6h", "impact": "+0.19" }
  ]
}
```

* **Dataset Scale:** 100,000 telemetry observations across 1,000 devices.
* **Class Imbalance:** **7.35%** failure rate (~12.6:1 imbalance). Accuracy is misleading; evaluation centers on **PR-AUC (Average Precision)** and **Failure Recall**.
* **Primary Predictors:** Coupled thermodynamic and electrical degradation (Joule heating, current spikes, power rail droop, and error cascades).

---

## 2. End-to-End System Architecture

```
                  Telemetry Stream (IoT Devices)
                                │
                                ▼
                   ┌──────────────────────────┐
                   │    Data Ingestion API    │
                   └────────────┬─────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │   Kafka / Redis Streams  │
                   └────────────┬─────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │  Stream Processing Worker │ (Sliding Window Features)
                   └───────┬───────────┬──────┘
                           │           │
            ┌──────────────┘           └──────────────┐
            ▼                                         ▼
┌───────────────────────┐                 ┌───────────────────────┐
│  PostgreSQL Storage   │                 │  Real-Time Predictor  │
│ (Fleet & Alert Store) │                 │  (XGBoost / < 1 ms)   │
└───────────────────────┘                 └───────────┬───────────┘
                                                      │
                                                      ▼
                                          ┌───────────────────────┐
                                          │   Explainability Engine│
                                          │   (SHAP Attribution)  │
                                          └───────────┬───────────┘
                                                      │
                                                      ▼
                                          ┌───────────────────────┐
                                          │ React Fleet Dashboard │
                                          └───────────────────────┘
```

---

## 3. 14-Milestone Engineering Roadmap

The project is structured into **4 distinct phases** spanning 14 modular milestones:

```
Phase 1: ML Foundations & Ensembles      ──► [COMPLETED (M1 – M5)]
Phase 2: Explainability & Serving API    ──► [IN PROGRESS (M6 – M8)]  ──► (Working MVP API)
Phase 3: Data Systems & Fleet UI         ──► [PLANNED (M9 – M11)]     ──► (Full Data Platform)
Phase 4: Cloud, Observability & CI/CD    ──► [PLANNED (M12 – M14)]    ──► (Enterprise Production)
```

### Roadmap Breakdown:

| # | Milestone | Domain | Deliverables & Scope | Status | Git Commit / Doc |
| :-: | :--- | :--- | :--- | :-: | :--- |
| **M1** | **Data Generation & Validation** | Data Eng | Physics-grounded simulator (100k rows, seed 42), 13-rule pre-ML validator | **Completed** | [`8ad82d2`](https://github.com/faizalkhan24/Data-mind/commit/8ad82d2) &bull; [Doc](docs/milestones/MILESTONE_1_DATA_GENERATION_AND_VALIDATION.md) |
| **M2** | **Exploratory Data Analysis** | Data Science | 10 core questions, Tukey IQR outlier preservation, leakage audit, 6 figures | **Completed** | [`851c998`](https://github.com/faizalkhan24/Data-mind/commit/851c998) &bull; [Doc](docs/milestones/MILESTONE_2_EXPLORATORY_DATA_ANALYSIS.md) |
| **M3** | **Feature Engineering Pipeline** | Feature Eng | 25 temporal signals (1h, 6h, 24h rolling, rate-of-change, power sag), zero leakage | **Completed** | [`f7002d6`](https://github.com/faizalkhan24/Data-mind/commit/f7002d6) &bull; [Doc](docs/milestones/MILESTONE_3_FEATURE_ENGINEERING.md) |
| **M4** | **Baseline Failure Models** | ML | Group-aware split (70/15/15), Dummy baselines, Logistic Regression, PR-AUC | **Completed** | [`c34f1aa`](https://github.com/faizalkhan24/Data-mind/commit/c34f1aa) &bull; [Doc](docs/milestones/MILESTONE_4_BASELINE_MODEL_AND_EVALUATION.md) |
| **M5** | **Advanced Model Progression** | ML | Random Forest vs. XGBoost benchmark, threshold tuning, latency profiling | **Completed** | [`7b1fb6d`](https://github.com/faizalkhan24/Data-mind/commit/7b1fb6d) &bull; [Doc](docs/milestones/MILESTONE_5_MODEL_PROGRESSION.md) |
| **M6** | **Model Explainability (SHAP)** | ML / XAI | `TreeExplainer`, top-k human risk factor attribution, beeswarm & waterfall plots | **Completed** | [Doc](docs/milestones/MILESTONE_6_MODEL_EXPLAINABILITY.md) |
| **M7** | **Model Registry & Tracking** | MLOps | MLflow tracking, parameter/metric logging, artifact staging & model promotion | **Completed** | [Doc](docs/milestones/MILESTONE_7_MODEL_REGISTRY.md) |
| **M8** | **Real-Time Prediction API** | Backend / SWE | FastAPI inference server, in-memory model cache, sub-5ms SLA, Pydantic DTOs | **Next** | `services/DataMind.Prediction/` |
| **M9** | **Database & Persistence Layer** | Backend / Data | PostgreSQL schema (devices, telemetry, predictions, alerts), async repository | *Planned* | `services/DataMind.Api/` |
| **M10** | **Streaming Ingestion & Queue** | Data Eng | Kafka / Redis Streams buffer, real-time sliding window aggregation worker | *Planned* | `services/DataMind.Ingestion/` |
| **M11** | **Fleet Health Dashboard** | Frontend | React + TypeScript web console, live risk grid, telemetry graphs, SHAP drawer | *Planned* | `services/DataMind.Dashboard/` |
| **M12** | **Containerization & Compose** | DevOps | Multi-stage Dockerfiles, 1-command local orchestration (`docker compose up`) | *Planned* | `infrastructure/docker/` |
| **M13** | **Observability & Monitoring** | SRE / DevOps | OpenTelemetry tracing, Prometheus metrics (latency, RPS, drift), Grafana | *Planned* | `infrastructure/observability/` |
| **M14** | **Kubernetes & CI/CD Pipelines** | Cloud / SRE | K8s manifests (Deployments, HPA), GitHub Actions automated CI/CD pipeline | *Planned* | `.github/workflows/` |

---

## 4. Model Benchmark Results (Holdout Test Fleet)

All models evaluated on the **exact same unseen test fleet** (150 devices, 15,000 observations):

| Model | Optimal Thresh ($\tau$) | Accuracy | Precision | Recall | F1-Score | PR-AUC | ROC-AUC | Single-Sample Latency | Best Deployment Scenario |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Majority Dummy** | 0.50 | 93.46% | 0.0000 | 0.0000 | 0.0000 | 0.0654 | 0.5000 | < 1 µs | Naive baseline |
| **Logistic Regression** | 0.24 | 99.29% | **0.9581** | 0.9317 | 0.9447 | 0.9625 | 0.9841 | **357.39 µs** (~0.36 ms) | Ultra-light linear baseline |
| **Random Forest** (150 trees) | 0.39 | 99.29% | 0.9414 | **0.9501** | **0.9457** | **0.9671** | **0.9868** | 26,176.95 µs (~26.18 ms) | **Batch fleet audits** (highest recall) |
| **XGBoost** (`scale_pos_weight=12.4`) | 0.72 | 99.24% | 0.9446 | 0.9388 | 0.9417 | 0.9608 | 0.9841 | **400.61 µs** (~0.40 ms) | **Real-time API inference** (65x faster than RF) |

---

## 5. Quickstart & Verification

Run within the Python 3.11 virtual environment (`.venv`):

```powershell
# 1. Activate the environment
.venv\Scripts\activate

# 2. Generate deterministic synthetic dataset (100k rows, seed 42)
python ml/data_pipeline/generate_dataset.py

# 3. Run automated 13-rule data validation suite
python ml/data_pipeline/validate_dataset.py --strict

# 4. Generate exploratory data analysis report and 6 visual figures
python ml/data_pipeline/eda.py

# 5. Execute zero-leakage feature engineering pipeline (25 predictor features)
python ml/feature_engineering/pipeline.py

# 6. Train and evaluate baseline models
python ml/training/baseline_model.py

# 7. Train and benchmark advanced ensemble models (Random Forest & XGBoost)
python ml/training/train_models.py

# 8. Run explainability pipeline and generate SHAP diagnostic figures
python ml/evaluation/explainability.py

# 9. Register models with MLflow and promote production champion
python ml/training/register_model.py

# 10. Run repository automated test suite (47 tests)
python -m unittest discover -s tests -t . -v
```

---

## 6. Repository Layout

```
D:\DataMind
│
├── README.md                                       # Platform overview and 14-milestone roadmap
├── requirements.txt                                # Locked dependency specifications
├── .gitignore                                      # Excludes large CSVs, Parquet, and model binaries
│
├── data/
│   ├── sample/device_measurements.csv              # Synthetic raw telemetry (100k rows, 6.6 MB)
│   └── processed/featured_telemetry.parquet        # Engineered feature matrix (28 cols, 2.1 MB)
│
├── docs/
│   ├── MILESTONE_PROGRESS.md                       # Comprehensive milestone engineering log
│   ├── eda/                                        # EDA reports and 6 visual figures
│   ├── figures/                                    # Model curves, importance charts, confusion matrix
│   └── milestones/                                 # Standalone documentation for each milestone
│       ├── README.md                               # Milestone documentation index
│       ├── MILESTONE_1_DATA_GENERATION_AND_VALIDATION.md
│       ├── MILESTONE_2_EXPLORATORY_DATA_ANALYSIS.md
│       ├── MILESTONE_3_FEATURE_ENGINEERING.md
│       ├── MILESTONE_4_BASELINE_MODEL_AND_EVALUATION.md
│       └── MILESTONE_5_MODEL_PROGRESSION.md
│
├── ml/
│   ├── data_pipeline/                              # Generation, validation, and EDA modules
│   ├── feature_engineering/                        # Zero-leakage temporal feature transformer
│   ├── training/                                   # Split logic, baseline & ensemble trainers
│   ├── evaluation/                                 # Metric engine (PR-AUC, ROC, confusion matrix)
│   └── models/                                     # Model registry (.joblib binaries)
│
├── services/                                       # Microservices (Prediction, API, Ingestion)
├── infrastructure/                                 # Docker, Kubernetes, and Observability configs
│
└── tests/
    └── ml/                                         # 33 comprehensive unit tests
```

---

## 7. Technology Stack

* **Machine Learning & Data:** Python 3.11, pandas, NumPy, scikit-learn, XGBoost, SHAP, MLflow.
* **Serving & Backend:** FastAPI, C# / .NET 10, ASP.NET Core, Pydantic.
* **Storage & Messaging:** PostgreSQL, Redis, Apache Kafka.
* **Frontend:** React, TypeScript, Vite, TailwindCSS.
* **DevOps & Cloud:** Docker, Docker Compose, Kubernetes, Prometheus, Grafana, OpenTelemetry, GitHub Actions.
