# DataMind: Enterprise Predictive Intelligence & Hardware Failure Prevention Platform

[![Version: 1.0.0.1](https://img.shields.io/badge/version-1.0.0.1-blue.svg)](VERSION)
[![Python 3.11](https://img.shields.io/badge/python-3.11.9-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: 100% Passing](https://img.shields.io/badge/tests-100%25%20passing-brightgreen.svg)]()
[![Status: Production Ready](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)]()
[![User Manual](https://img.shields.io/badge/docs-User%20Manual-orange.svg)](docs/USER_MANUAL.md)
[![Contributing](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**DataMind** is an enterprise-grade hardware intelligence, failure prevention, and real-time predictive analytics platform engineered to Google Software Engineering and Site Reliability Engineering (SRE) standards.

> 📖 **Comprehensive Documentation:**
> * **[User & Operator Manual](docs/USER_MANUAL.md):** Complete operational guide for ML pipelines, local microservices, Docker Compose, Kubernetes, and the Web Console.
> * **[Security & Validation Traceability](docs/SECURITY_VALIDATION_TRACEABILITY.md):** Formal audit matrix of all 10 security and validation controls (`[SECURITY-1..6]`, `[VALIDATION-1..4]`).
> * **[PowerPoint Presentation Script](docs/POWERPOINT_PRESENTATION_SCRIPT.md):** 12-slide executive presentation and technical deep-dive.

---

## 1. Executive Summary & Problem Statement

In distributed IoT fleets, edge computing nodes, and mission-critical hardware, unplanned hardware failures cause catastrophic operational downtime. 

DataMind solves this by answering the core operational question: **Given streaming multi-sensor telemetry across a connected hardware fleet, predict whether a device will experience an operational failure within the next 24 hours (`failed_within_24h`) with sub-millisecond scoring and explainable causal factors.**

```json
{
  "deviceId": "DEV-00042",
  "predictionWindowHours": 24,
  "failureProbability": 0.884,
  "riskLevel": "HIGH",
  "latencyMs": 0.38,
  "topRiskFactors": [
    { "factor": "Rapid Battery Depletion", "feature": "battery_change_24h", "impact": "+0.34", "impactValue": 0.342 },
    { "factor": "Thermal Runaway", "feature": "temperature_mean_6h", "impact": "+0.28", "impactValue": 0.281 },
    { "factor": "Power Rail Droop", "feature": "voltage_min_6h", "impact": "+0.19", "impactValue": 0.194 }
  ]
}
```

* **Dataset Scale:** 100,000 telemetry observations across 1,000 distinct physical devices.
* **Class Imbalance:** Realistic **7.35%** failure rate (~12.6:1 ratio). Optimization prioritizes **PR-AUC (0.841)**, Failure Recall, and F1-Score over raw accuracy.
* **Inference SLA:** Sub-millisecond single-sample scoring (**0.40 ms** on CPU).

---

## 2. Distributed Microservice Cluster Architecture

```
                               ┌──────────────────────────────────────────────┐
                               │       IoT Fleet & Edge Hardware Nodes        │
                               └──────────────────────┬───────────────────────┘
                                                      │ Telemetry Stream (HTTP/JSON)
                                                      ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                           DataMind Cluster (Service Mesh)                                         │
 │                                                                                                                  │
 │  ┌────────────────────────────────────┐                   ┌───────────────────────────────────────────────────┐  │
 │  │        DataMind.Ingestion          │                   │                DataMind.Prediction                │  │
 │  │             (Port 8002)            │                   │                    (Port 8000)                    │  │
 │  ├────────────────────────────────────┤                   ├───────────────────────────────────────────────────┤  │
 │  │ • Sliding-Window Ring Buffer       │                   │ • XGBoost Champion Classifier (PR-AUC = 0.841)    │  │
 │  │ • Zero-Leakage Feature Extraction  │                   │ • SHAP TreeExplainer Attribution Engine           │  │
 │  │ • Background Queue Dispatcher      │                   │ • SHA-256 Model Checksum Verification Sidecar     │  │
 │  └─────────────────┬──────────────────┘                   └─────────────────────────┬─────────────────────────┘  │
 │                    │                                                                │                            │
 │                    ▼                                                                ▼                            │
 │  ┌────────────────────────────────────┐                   ┌───────────────────────────────────────────────────┐  │
 │  │            DataMind.Api            │                   │                DataMind.Dashboard                 │  │
 │  │             (Port 8001)            │◄──────────────────┤                    (Port 8003)                    │  │
 │  ├────────────────────────────────────┤  Internal REST    ├───────────────────────────────────────────────────┤  │
 │  │ • Fleet Hardware Entity Store      │     Service       │ • Enterprise 6-View Operations Console            │  │
 │  │ • Incident Alert Lifecycle Ledger  │      Mesh         │ • Responsive Multi-Tier Fluid UI (Mobile to 4K)   │  │
 │  │ • SQLAlchemy Async / aiosqlite / PG│                   │ • What-If Studio, Stream Sim & Cluster Mesh       │  │
 │  └────────────────────────────────────┘                   └───────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Enterprise Operations Console & Responsive Multi-Tier UI

The DataMind Web Operations Console (`http://localhost:8003`) is engineered with a dark aerospace theme and an enterprise multi-tier responsive architecture:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DataMind Enterprise Operations Suite                            │
├─────────────────┬──────────────────┬─────────────────┬────────────────┬────────────────┤
│ Mission Control │ Fleet Explorer   │ AI What-If      │ Stream Sim     │ Incident Desk  │
│  (Executive)    │  (Device Ops)    │  (SHAP Engine)  │  (Live Stream) │  (Triage Desk) │
├─────────────────┴──────────────────┴─────────────────┴────────────────┴────────────────┤
│                     Cluster Service Mesh & Security Compliance                         │
│       [SECURITY-1..6] Cryptographic Checksums, Auth Tokens, Strict Origin Whitelists   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1. The 6 Specialized Operations Views
1. **Mission Control (`#pane-overview`):**
   - **Executive KPI Bar:** Real-time counters for Managed Endpoints, Nominal Devices, Critical Risk Count ($P > 0.70$), Open Incidents, and Average Inference SLA.
   - **Risk Distribution Donut Chart:** Interactive Chart.js donut categorizing the fleet into Nominal, Elevated (Watch), and Critical risk.
   - **Fleet Telemetry Vitals:** Trailing fleet-wide averages for chassis temperature, supply voltage, battery charge, and temporal window coverage.
   - **Priority Incident Queue:** Live triage table for high-severity failure warnings.
2. **Fleet Explorer (`#pane-devices`):**
   - **Inventory Management:** Search by device ID, filter by risk level (`ALL`, `HIGH`, `NOMINAL`) or operational state (`ACTIVE`, `MAINTENANCE`).
   - **Device Inspection:** Detailed hardware specs, estimated Remaining Useful Life (RUL), and a 10-point telemetry trend chart.
   - **Device Provisioning & Lifecycle:** Register new devices, update firmware releases, or decommission aging hardware.
   - **CSV Export:** One-click fleet inventory report download (`/api/dashboard/export/fleet`).
3. **AI What-If Scenario Studio (`#pane-whatif`):**
   - **Scenario Presets:** Instant simulation of *Healthy Baseline*, *Thermal Spike*, *Discharge Drop*, or *Power Rail Sag*.
   - **Sub-Millisecond Inference:** Evaluates parameters using the champion XGBoost model.
   - **Visual SHAP Attribution:** Waterfall contribution bars showing game-theoretic positive and negative risk factors.
   - **Global Feature Gain Leaderboard:** Ranked feature importance table based on 100,000 historical telemetry observations.
4. **Stream & Fault Simulator (`#pane-simulator`):**
   - **Continuous Stream Daemon:** Generates live synthetic physical telemetry for 25 concurrent background endpoints.
   - **Synthetic Fault Injection:** One-click triggers for Thermal Runaway ($88^\circ\text{C}$), Power Rail Sag ($2.90\text{V}$), or Watchdog Reset Cascades.
   - **Buffer Diagnostics:** Live health tracking of sliding-window feature transformers.
5. **Incident Command Desk (`#pane-incidents`):**
   - **Operational Ledger:** Centralized queue for all automated hardware failure alerts.
   - **Incident Triage:** One-click actions to acknowledge (`ACKNOWLEDGED`) or resolve (`RESOLVED`) active alerts.
   - **Incident Audit Export:** Downloadable CSV report of all incident tickets (`/api/dashboard/export/alerts`).
6. **Cluster Service Mesh & Security (`#pane-topology`):**
   - **Distributed Node Grid:** Real-time round-trip latency pings across all microservices (Ports 8000–8003).
   - **Security Ledger:** Live verification matrix for all 10 security and validation controls.

### 3.2. Responsive Multi-Tier Form-Factor Support
* **Desktop & Ultra-Wide ($\ge 1280\text{px}$):** 3-cluster navbar, 5-column balanced KPI grid, 2-column split workspaces.
* **Laptop / Small Desktop ($1025\text{px} - 1279\text{px}$):** Auto-fit adaptive KPI grid, fluid padding, optimized chart heights.
* **Tablet Landscape & Portrait ($768\text{px} - 1024\text{px}$):** 2-row navbar with smooth horizontal touch-scrolling tabs, 3-column KPI grid, 1-column workspace stacking.
* **Mobile Landscape & Large Phones ($481\text{px} - 767\text{px}$):** 2-column compact metric cards, sticky first column (`Device ID`) on wide tables, touch-friendly $\ge 44\text{px}$ action targets, bottom-centered toast notifications.
* **Mobile Portrait & Compact Phones ($\le 480\text{px}$):** Fluid typography with CSS `clamp()`, full-width modal sheets, touch scroll-snap tab navigation, responsive input rows.

---

## 4. Formal Security & Validation Controls Ledger

All security and input validation requirements are enforced in code and backed by automated regression tests in [`tests/test_security_and_validation.py`](tests/test_security_and_validation.py):

| Code Identifier | Category | Implementation & Defense Mechanism |
| :--- | :---: | :--- |
| **`[SECURITY-1]`** | Network Security | **Strict Origin CORS Whitelist:** Rejects arbitrary wildcard (`*`) cross-site requests across all microservices. |
| **`[SECURITY-2]`** | Model Security | **Cryptographic SHA-256 Model Verification:** Sidecar checksum verification prevents arbitrary code execution on model load. |
| **`[SECURITY-3]`** | Auth & Access | **API Key & Bearer Token Authentication:** Unified credentials scheme protecting telemetry, write, and administrative routes. |
| **`[SECURITY-4]`** | Cryptography | **Timing-Attack Resistant Validation:** `secrets.compare_digest` prevents side-channel timing attacks on secret token verification. |
| **`[SECURITY-5]`** | Path Security | **Path Traversal Sanitization:** Strict path canonicalization prevents malicious directory traversal attacks during model artifact loading. |
| **`[SECURITY-6]`** | Network Binding | **Safe Host & Port Configuration:** Environment-variable controlled host binding preventing accidental exposure on public interfaces. |
| **`[VALIDATION-1]`**| Input Sanitization | **Alphanumeric Device ID Guard:** Strict regex pattern `^[A-Za-z0-9_-]+$` rejects SQL injection, command injection, and traversal tokens. |
| **`[VALIDATION-2]`**| Temporal Integrity | **ISO-8601 UTC Timestamp Validation:** Rejects malformed date strings and non-UTC timestamps. |
| **`[VALIDATION-3]`**| Numerical Safety | **Finite Float Boundary Guardrails:** Bounded range checks reject `NaN` and `Infinite` floating-point denial-of-service payloads. |
| **`[VALIDATION-4]`**| Schema Guard | **Strict Pydantic Field Validation:** Strongly typed DTO models enforce valid operational ranges on temperature, voltage, and battery metrics. |

---

## 5. Machine Learning Benchmark Results

All models evaluated on the **exact same unseen test fleet** (150 devices, 15,000 observations):

| Model | Optimal Thresh ($\tau$) | Accuracy | Precision | Recall | F1-Score | PR-AUC | ROC-AUC | Single-Sample Latency | Best Deployment Scenario |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Majority Dummy** | 0.50 | 93.46% | 0.0000 | 0.0000 | 0.0000 | 0.0654 | 0.5000 | < 1 µs | Naive baseline |
| **Logistic Regression** | 0.24 | 99.29% | **0.9581** | 0.9317 | 0.9447 | 0.9625 | 0.9841 | **357.39 µs** (~0.36 ms) | Ultra-light linear baseline |
| **Random Forest** (150 trees) | 0.39 | 99.29% | 0.9414 | **0.9501** | **0.9457** | **0.9671** | **0.9868** | 26,176.95 µs (~26.18 ms) | Batch fleet audits (highest recall) |
| **XGBoost** (`scale_pos_weight=12.4`) | 0.72 | 99.24% | 0.9446 | 0.9388 | 0.9417 | 0.9608 | 0.9841 | **400.61 µs** (~0.40 ms) | **Production Champion API** (65x faster than RF) |

---

## 6. One-Click Startup & Quickstart Guide

DataMind provides multiple zero-configuration startup scripts that launch all 4 microservices simultaneously and open the web browser:

### 6.1. One-Click Launchers
* **Windows (Double-Click):** Double-click [`run.cmd`](run.cmd) or [`start_datamind.bat`](start_datamind.bat).
* **PowerShell:** `.\start_datamind.ps1`
* **Linux / macOS / WSL:** `./start_datamind.sh`
* **Unified CLI:** `python datamind.py start --all --browser`

### 6.2. Unified CLI Orchestrator (`datamind.py`)
```bash
# Check platform version and build metadata
python datamind.py version

# Check readiness and health probe across all 4 microservices
python datamind.py status

# Run complete automated test suite (7 suites, 100% green pass)
python datamind.py test

# Launch autonomous real-time IoT fleet telemetry simulator (25 devices)
python datamind.py simulate --devices 25 --interval 2.0

# Stop all running microservices
python datamind.py stop --all
```

### 6.3. Step-by-Step Pipeline Execution (From Scratch)
```powershell
# 1. Activate the Python 3.11 virtual environment
.venv\Scripts\activate

# 2. Generate deterministic synthetic dataset (100k rows, seed 42)
python ml/data_pipeline/generate_dataset.py

# 3. Run automated 13-rule data validation suite
python ml/data_pipeline/validate_dataset.py --strict

# 4. Generate exploratory data analysis report and 6 visual figures
python ml/data_pipeline/eda.py

# 5. Execute zero-leakage feature engineering pipeline (25 predictor features)
python ml/feature_engineering/pipeline.py

# 6. Train baseline and advanced ensemble models (Random Forest & XGBoost)
python ml/training/baseline_model.py
python ml/training/train_models.py

# 7. Run explainability pipeline and generate SHAP diagnostic figures
python ml/evaluation/explainability.py

# 8. Launch complete distributed stack via Docker Compose
docker compose up --build -d
```

---

## 7. Complete Project Repository Layout

```
D:\DataMind
│
├── README.md                                       # Comprehensive platform guide and architectural docs
├── run.cmd                                         # One-click Windows CMD launcher (auto browser open)
├── start_datamind.bat                              # Batch cluster launcher
├── start_datamind.ps1                              # PowerShell cluster launcher
├── start_datamind.sh                               # Linux/macOS shell launcher
├── datamind.py                                     # Unified CLI orchestrator (start, stop, test, status)
├── requirements.txt                                # Locked dependency specifications
├── VERSION                                         # Semantic release version (v1.0.0.1)
├── LICENSE                                         # MIT License
├── CONTRIBUTING.md                                 # Open-source contribution guidelines
│
├── data/
│   ├── sample/device_measurements.csv              # Synthetic raw telemetry (100k rows, 6.6 MB)
│   └── processed/featured_telemetry.parquet        # Engineered feature matrix (28 cols, 2.1 MB)
│
├── docs/
│   ├── USER_MANUAL.md                              # Complete end-to-end operator and user manual
│   ├── SECURITY_VALIDATION_TRACEABILITY.md         # Traceability matrix for [SECURITY-1..6] & [VALIDATION-1..4]
│   ├── POWERPOINT_PRESENTATION_SCRIPT.md           # 12-slide executive presentation script
│   ├── MILESTONE_PROGRESS.md                       # Comprehensive 14-milestone engineering log
│   ├── eda/                                        # EDA reports and 6 visual figures
│   ├── figures/                                    # Model curves, importance charts, confusion matrix
│   └── milestones/                                 # Milestone documentation (M1 through M14)
│
├── ml/
│   ├── data_pipeline/                              # Generation, validation, and EDA modules
│   ├── feature_engineering/                        # Zero-leakage temporal feature transformer
│   ├── training/                                   # Split logic, baseline & ensemble trainers
│   ├── evaluation/                                 # Metric engine (PR-AUC, ROC, SHAP explainability)
│   └── models/                                     # Model registry (.joblib binaries & .sha256 sidecars)
│
├── services/
│   ├── DataMind.Prediction/                        # Port 8000: Real-time XGBoost & SHAP inference API
│   │   ├── main.py                                 # FastAPI application with security middleware
│   │   ├── prediction_engine.py                    # In-memory model cache & telemetry explainer
│   │   └── prediction_config.py                    # Prediction service configuration
│   │
│   ├── DataMind.Api/                               # Port 8001: Fleet persistence & incident store
│   │   ├── main.py                                 # FastAPI fleet management & alerts API
│   │   ├── database.py                             # SQLAlchemy 2.0 async engine & session maker
│   │   ├── models.py                               # Hardware devices & alerts ORM schema
│   │   └── schemas.py                              # Pydantic request/response validation schemas
│   │
│   ├── DataMind.Ingestion/                         # Port 8002: Sliding-window stream buffer
│   │   ├── main.py                                 # Streaming telemetry ingestion REST API
│   │   ├── stream_buffer.py                        # Per-device sliding window ring buffers
│   │   └── queue_worker.py                         # Async stream ingestion worker
│   │
│   ├── DataMind.Dashboard/                         # Port 8003: Multi-view operations web console
│   │   ├── main.py                                 # FastAPI web server, proxy, and diagnostic endpoints
│   │   ├── dashboard_config.py                     # Dashboard service configuration
│   │   └── static/                                 # Single Page Application assets
│   │       ├── index.html                          # 6-view semantic operations HTML layout
│   │       ├── style.css                           # Multi-tier responsive CSS design system
│   │       └── app.js                              # Client application logic & real-time charts
│   │
│   ├── simulator/                                  # Continuous autonomous IoT fleet simulator
│   │   ├── fleet_simulator.py                      # Background telemetry generation daemon
│   │   └── synthetic_faults.py                     # Fault injection generators (thermal, sag, watchdog)
│   │
│   └── observability/                              # Prometheus metrics exporter & SLA monitoring
│
├── infrastructure/
│   ├── docker/                                     # Multi-stage Dockerfiles for all microservices
│   ├── docker-compose.yml                          # 1-command local cluster composition
│   ├── kubernetes/                                 # Production manifests (Deployments, HPA, Ingress)
│   ├── prometheus/                                 # Prometheus scraping configs & SLA alert rules
│   └── grafana/                                    # Pre-configured Grafana fleet monitoring dashboards
│
└── tests/
    ├── ml/                                         # ML pipeline, feature transformer, & model unit tests
    ├── services/                                   # Microservice unit & integration tests
    │   ├── test_fleet_api.py                       # DataMind.Api test suite
    │   ├── test_prediction_api.py                  # DataMind.Prediction test suite
    │   ├── test_ingestion_stream.py                # DataMind.Ingestion test suite
    │   ├── test_dashboard.py                       # DataMind.Dashboard & responsive UI test suite
    │   └── test_simulator.py                       # Continuous fleet simulator test suite
    ├── test_security_and_validation.py             # Security [SECURITY-1..6] & [VALIDATION-1..4] tests
    └── test_end_to_end_integration.py              # End-to-end 4-service cluster integration tests
```

---

## 8. Technology Stack

* **Machine Learning & Data:** Python 3.11, pandas, NumPy, scikit-learn, XGBoost, SHAP, MLflow.
* **Backend & Microservices:** FastAPI, Uvicorn, SQLAlchemy 2.0, asyncpg, aiosqlite, Pydantic, httpx.
* **Frontend Web Console:** Modern HTML5, Multi-Tier Responsive CSS3 (CSS Variables, Flexbox, Grid, `clamp()`), JavaScript (ES2022), Chart.js.
* **DevOps & Cloud:** Docker Compose, Kubernetes (Kustomize, HPA, Ingress), Prometheus, Grafana, GitHub Actions CI/CD.

---

## 9. Open-Source Contributions & Protected Main Branch

We welcome contributions from the engineering community! To ensure high reliability:
* **Fork & Pull Request Workflow:** External contributors work on their own fork in a dedicated feature branch (`feat/my-feature`) and submit a Pull Request. Direct push access to `main` is restricted to maintainers.
* **Automated CI Gates:** Every Pull Request must pass all 7 automated test suites and code linters via GitHub Actions before review.
* **Contribution Guide:** Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) for full instructions on setup, testing, and PR submission.

---

## 10. License

This project is licensed under the MIT License — see the [`LICENSE`](LICENSE) file for details.  
Copyright (c) 2026 Faizal Khan.
