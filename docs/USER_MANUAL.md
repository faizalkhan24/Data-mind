# DataMind Platform: User & Operator Manual

> **Document:** Comprehensive User & Operator Guide  
> **Target Audience:** Developers, Data Scientists, MLOps Engineers, and Fleet Operators  
> **Repository:** [`https://github.com/faizalkhan24/Data-mind.git`](https://github.com/faizalkhan24/Data-mind.git)  
> **Current Version:** v1.0.0 (Production Ready — 14/14 Milestones Completed)  

---

## Table of Contents
1. [Introduction & System Overview](#1-introduction--system-overview)
2. [Prerequisites & System Requirements](#2-prerequisites--system-requirements)
3. [Quick Setup & Installation](#3-quick-setup--installation)
4. [Running the Machine Learning Pipelines](#4-running-the-machine-learning-pipelines)
5. [Mode 1: Running Microservices Locally (Python)](#5-mode-1-running-microservices-locally-python)
6. [Mode 2: Running via Docker Compose (Recommended)](#6-mode-2-running-via-docker-compose-recommended)
7. [Mode 3: Production Kubernetes Deployment](#7-mode-3-production-kubernetes-deployment)
8. [Using the Fleet Health Operations Console (Web UI)](#8-using-the-fleet-health-operations-console-web-ui)
9. [REST API Reference & Usage Examples](#9-rest-api-reference--usage-examples)
10. [Observability & Monitoring (Prometheus & Grafana)](#10-observability--monitoring-prometheus--grafana)
11. [Running the Automated Test Suite](#11-running-the-automated-test-suite)
12. [Troubleshooting & Frequently Asked Questions](#12-troubleshooting--frequently-asked-questions)

---

## 1. Introduction & System Overview

**DataMind** is an enterprise-grade predictive intelligence and IoT failure prevention platform designed to predict whether a hardware device in an operational fleet will suffer a critical failure within the next 24 hours (`failed_within_24h`).

### 1.1 Architecture & Services Matrix
The platform consists of four loosely-coupled, high-performance microservices, two backing data stores, and an observability stack:

| Service Name | Port | Directory | Tech Stack | Primary Responsibility |
| :--- | :---: | :--- | :--- | :--- |
| **`DataMind.Prediction`** | `8000` | [`services/DataMind.Prediction/`](../services/DataMind.Prediction/) | FastAPI, XGBoost, SHAP | Real-time inference engine (< 5 ms SLA) with in-memory model cache & game-theoretic risk attribution. |
| **`DataMind.Api`** | `8001` | [`services/DataMind.Api/`](../services/DataMind.Api/) | FastAPI, SQLAlchemy 2.0, Asyncpg / SQLite | Fleet metadata CRUD, historical observations, alert lifecycle, and fleet aggregation statistics. |
| **`DataMind.Ingestion`** | `8002` | [`services/DataMind.Ingestion/`](../services/DataMind.Ingestion/) | FastAPI, Asyncio Queue, Sliding Window | High-throughput telemetry ingestion, 24-hour temporal sliding window buffering, feature computation. |
| **`DataMind.Dashboard`** | `8003` | [`services/DataMind.Dashboard/`](../services/DataMind.Dashboard/) | FastAPI, Vanilla JS, CSS3, HTML5 | Live operations console, interactive fleet risk grid, real-time diagnostic simulator, and telemetry drawer. |
| **`PostgreSQL`** | `5432` | `infrastructure/docker/` | PostgreSQL 16 Alpine | Primary transactional relational persistence store for devices, telemetry, predictions, and alerts. |
| **`Redis`** | `6379` | `infrastructure/docker/` | Redis 7 Alpine | High-throughput memory cache and streaming buffer. |
| **`Prometheus`** | `9090` | [`infrastructure/observability/prometheus/`](../infrastructure/observability/prometheus/) | Prometheus v2.54 | Continuous metric scraping, SLA latency histograms, and rule-based alerting (`alerts.yml`). |
| **`Grafana`** | `3000` | [`infrastructure/observability/grafana/`](../infrastructure/observability/grafana/) | Grafana v11.2 | Provisioned executive monitoring dashboards, SLA threshold gauges, and fleet risk visualization. |

---

## 2. Prerequisites & System Requirements

Before running the project, verify that your machine has the following installed:

* **Operating System:** Windows 10/11, macOS (12+), or Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+).
* **Python Runtime:** **Python 3.11.x** (64-bit).  
  > [!IMPORTANT]
  > Python 3.11 is strictly required because key numerical and ML libraries (`xgboost`, `scipy`, `scikit-learn`, `shap`, `mlflow`) require pre-compiled CPython 3.11 ABI (`cp311`) wheels. Python 3.13 or 3.15 does not have binary wheels for several ML dependencies yet.
* **Git:** Version 2.30 or higher.
* **Docker & Docker Compose:** Docker Desktop (Windows/macOS) or Docker Engine 24.0+ with Compose plugin (Linux).
* **Kubernetes (Optional for Mode 3):** `kubectl` v1.28+, and Minikube, Kind, or a remote cloud cluster (EKS/GKE/AKS).

---

## 3. Quick Setup & Installation

### Step 3.1: Clone the Repository
```bash
git clone https://github.com/faizalkhan24/Data-mind.git
cd Data-mind
```

### Step 3.2: Create and Activate Python 3.11 Virtual Environment

**On Windows (PowerShell):**
```powershell
# Create virtual environment using Python 3.11
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1
```

**On Linux / macOS (Bash / Zsh):**
```bash
# Create virtual environment using Python 3.11
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### Step 3.3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.4: Configure Environment Variables
Copy the default environment template:
```bash
# Windows
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

---

## 4. Running the Machine Learning Pipelines

DataMind includes a deterministic, physics-grounded ML training and evaluation lifecycle. You can execute each pipeline sequentially from the terminal:

### Step 4.1: Generate Deterministic Synthetic Telemetry (100k Rows)
Generates 100,000 realistic IoT telemetry records across 1,000 devices exhibiting coupled thermal and electrical degradation physics:
```bash
python ml/data_pipeline/generate_dataset.py
```
*Output File:* `data/synthetic_iot_telemetry.parquet` (and `.csv`)

### Step 4.2: Run 13-Rule Pre-ML Data Quality Validator
Audits the raw dataset against schema rules, missingness, physical boundary checks, and temporal consistency:
```bash
python ml/data_pipeline/validate_dataset.py --strict
```
*Output:* Validated audit table with 100% pass rate.

### Step 4.3: Run Exploratory Data Analysis (EDA) & Profiling
Analyzes distributions, performs Tukey IQR outlier audits, and renders 6 high-resolution visual plots:
```bash
python ml/data_pipeline/eda.py
```
*Output Directory:* [`docs/figures/`](../docs/figures/) (correlation heatmaps, degradation curves, pairplots).

### Step 4.4: Execute Zero-Leakage Feature Engineering Pipeline
Computes 25 rolling temporal signals (1h, 6h, 24h rolling means, standard deviations, power sags, error cascades) with zero future information leakage:
```bash
python ml/feature_engineering/pipeline.py
```
*Output File:* `data/feature_engineered_dataset.parquet`

### Step 4.5: Train Baseline Models
Evaluates Majority Dummy, Stratified Dummy, and Logistic Regression with group-aware cross-device splitting:
```bash
python ml/training/baseline_model.py
```

### Step 4.6: Train & Benchmark Advanced Models (Random Forest vs XGBoost)
Trains 150-tree Random Forest and gradient-boosted XGBoost classifiers, tunes decision thresholds for PR-AUC / F1-Score, and measures latency:
```bash
python ml/training/train_models.py
```
*Output Artifact:* `ml/models/best_model_xgboost.joblib`

### Step 4.7: Generate SHAP Explainability Attributions
Computes game-theoretic Shapley values and produces beeswarm and waterfall attribution plots:
```bash
python ml/evaluation/explainability.py
```
*Output Directory:* `docs/figures/shap_beeswarm.png`, `docs/figures/shap_waterfall_high_risk.png`

### Step 4.8: Register Model with MLflow
Stages models in the local MLflow registry and promotes the champion XGBoost model:
```bash
python ml/training/register_model.py
```

---

## 5. Mode 1: Running Microservices Locally (Python)

To run the platform natively on your host machine without Docker:

### Terminal 1: Real-Time Prediction API (Port 8000)
```powershell
$env:PYTHONPATH = "."
python -m uvicorn services.DataMind.Prediction.main:app --host 0.0.0.0 --port 8000 --reload
```
* Interactive Swagger Docs: `http://localhost:8000/docs`
* Health Endpoint: `http://localhost:8000/health`
* Prometheus Metrics: `http://localhost:8000/metrics`

### Terminal 2: Fleet Management API (Port 8001)
```powershell
$env:PYTHONPATH = "."
python -m uvicorn services.DataMind.Api.main:app --host 0.0.0.0 --port 8001 --reload
```
* Interactive Swagger Docs: `http://localhost:8001/docs`
* Health Endpoint: `http://localhost:8001/health`

### Terminal 3: Streaming Ingestion Service (Port 8002)
```powershell
$env:PYTHONPATH = "."
python -m uvicorn services.DataMind.Ingestion.main:app --host 0.0.0.0 --port 8002 --reload
```
* Interactive Swagger Docs: `http://localhost:8002/docs`
* Health Endpoint: `http://localhost:8002/health`

### Terminal 4: Fleet Health Operations Console (Port 8003)
```powershell
$env:PYTHONPATH = "."
python -m uvicorn services.DataMind.Dashboard.main:app --host 0.0.0.0 --port 8003 --reload
```
* **Operations Web Console:** **`http://localhost:8003/`**
* Health Endpoint: `http://localhost:8003/health`

---

## 6. Mode 2: Running via Docker Compose (Recommended)

Running via Docker Compose launches all 4 microservices, PostgreSQL, Redis, Prometheus, and Grafana with one command.

### Step 6.1: Start All Services
```bash
docker compose up -d --build
```

### Step 6.2: Verify Service Status
```bash
docker compose ps
```
You should see all 8 containers in a healthy state:
* `postgres` (Port 5432)
* `redis` (Port 6379)
* `prediction` (Port 8000)
* `api` (Port 8001)
* `ingestion` (Port 8002)
* `dashboard` (Port 8003)
* `prometheus` (Port 9090)
* `grafana` (Port 3000)

### Step 6.3: View Real-Time Service Logs
```bash
# Tail logs for all containers
docker compose logs -f

# Tail logs for a specific service
docker compose logs -f prediction
```

### Step 6.4: Stop and Tear Down
```bash
# Stop all containers
docker compose down

# Stop all containers and remove persistent database volumes
docker compose down -v
```

---

## 7. Mode 3: Production Kubernetes Deployment

The DataMind Kubernetes infrastructure is bundled using **Kustomize** located in [`infrastructure/k8s/`](../infrastructure/k8s/).

### Step 7.1: Deploy Full Manifest Stack
```bash
kubectl apply -k infrastructure/k8s/
```

### Step 7.2: Monitor Cluster Deployment
```bash
# Check Pods in the datamind namespace
kubectl get pods -n datamind -w

# Check Services and Endpoints
kubectl get svc -n datamind

# Check Horizontal Pod Autoscalers (HPA)
kubectl get hpa -n datamind

# Check Ingress Routing
kubectl get ingress -n datamind
```

### Step 7.3: Accessing Services Locally via Port Forwarding
If you are running in a local cluster without external LoadBalancers:
```bash
# Forward Fleet Health Console
kubectl port-forward svc/datamind-dashboard 8003:8003 -n datamind

# Forward Prediction API
kubectl port-forward svc/datamind-prediction 8000:8000 -n datamind
```
Then browse to `http://localhost:8003/`.

### Step 7.4: Zero-Downtime Rolling Update & Rollback
```bash
# Update to a new container version
kubectl set image deployment/datamind-prediction prediction=ghcr.io/faizalkhan24/datamind-prediction:v1.1.0 -n datamind

# Monitor rollout status
kubectl rollout status deployment/datamind-prediction -n datamind

# Roll back immediately in case of issues
kubectl rollout undo deployment/datamind-prediction -n datamind
```

---

## 8. Using the Fleet Health Operations Console (Web UI)

Open **`http://localhost:8003/`** in your browser to access the live operations dashboard.

```
┌────────────────────────────────────────────────────────────────────────┐
│  DATAMIND FLEET HEALTH OPERATIONS CONSOLE           [Status: OPERATIONAL]│
├──────────────────┬──────────────────┬────────────────┬─────────────────┤
│ TOTAL DEVICES    │ ACTIVE MONITORED │ HIGH RISK (24h)│ OPEN ALERTS     │
│      1,000       │       984        │       74       │        12       │
├──────────────────┴──────────────────┴────────────────┴─────────────────┤
│ FLEET RISK GRID (Filter: [All] [High Risk] [Nominal]   Sort: [Risk ↓]) │
│ ┌──────────────┬──────────────────┬──────────┬───────────┬───────────┐ │
│ │ Device ID    │ Status           │ Risk (%) │ Temp (°C) │ Action    │ │
│ ├──────────────┼──────────────────┼──────────┼───────────┼───────────┤ │
│ │ DEV-00042    │ HIGH RISK        │  88.4%   │   84.2°C  │ [Diagnose]│ │
│ │ DEV-00109    │ HIGH RISK        │  79.1%   │   78.6°C  │ [Diagnose]│ │
│ │ DEV-00003    │ NOMINAL          │   4.2%   │   41.0°C  │ [Diagnose]│ │
│ └──────────────┴──────────────────┴──────────┴───────────┴───────────┘ │
├────────────────────────────────────────────────────────────────────────┤
│ DIAGNOSTIC TELEMETRY SIMULATOR                                         │
│ Device: [DEV-00042]   Temperature: [85.0°C]   Voltage: [3.10V]         │
│ Current: [2.65A]      Battery: [32%]         Errors: [14/hr]           │
│ [► Run Real-Time Prediction & SHAP Analysis]                           │
└────────────────────────────────────────────────────────────────────────┘
```

### Key UI Features:
1. **Executive Fleet KPI Cards:** Real-time visibility into fleet scale, active nodes, elevated failure risks, and open incident tickets.
2. **Interactive Fleet Risk Grid:** Lists monitored devices with color-coded risk status badges (`HIGH RISK` in red, `NOMINAL` in green). Supports filtering and sorting by risk percentage.
3. **Diagnostic Drawer:** Click **[Diagnose]** on any device to expand the historical telemetry drawer showing voltage droop, temperature trends, and top human-readable SHAP risk factor attributions.
4. **Real-Time Diagnostic Simulator:** Test the machine learning model live directly in the browser by adjusting temperature, voltage sag, and error spikes to observe how the failure probability and risk attributions respond instantaneously.

---

## 9. REST API Reference & Usage Examples

### 9.1 Real-Time Prediction API (`:8000`)

#### Predict Device Failure Risk & Request SHAP Attribution
```bash
curl -X POST "http://localhost:8000/api/v1/predict?include_explanations=true&top_k=3" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV-00042",
    "timestamp": "2026-01-05T03:00:00",
    "temperature": 82.5,
    "voltage": 3.12,
    "current": 2.55,
    "battery_level": 35,
    "network_quality": 85,
    "error_count": 12,
    "restart_count": 3,
    "uptime_hours": 12.5,
    "firmware_version": "1.2.0"
  }'
```

**Response (Sub-5ms SLA):**
```json
{
  "device_id": "DEV-00042",
  "prediction_timestamp": "2026-10-11T08:00:00.123456",
  "failure_probability": 0.8841,
  "risk_severity": "HIGH",
  "predicted_failure_within_24h": true,
  "threshold_applied": 0.7173,
  "inference_latency_ms": 0.38,
  "explanations": [
    {
      "rank": 1,
      "feature_name": "battery_change_24h",
      "human_label": "Rapid Battery Depletion",
      "shap_value": 0.3421,
      "feature_value": -42.0,
      "direction": "INCREASES_RISK"
    },
    {
      "rank": 2,
      "feature_name": "temperature_mean_6h",
      "human_label": "Thermal Runaway",
      "shap_value": 0.2814,
      "feature_value": 81.3,
      "direction": "INCREASES_RISK"
    },
    {
      "rank": 3,
      "feature_name": "voltage_min_6h",
      "human_label": "Power Rail Sag",
      "shap_value": 0.1942,
      "feature_value": 3.08,
      "direction": "INCREASES_RISK"
    }
  ]
}
```

---

### 9.2 Fleet Management API (`:8001`)

#### Register a Hardware Device
```bash
curl -X POST "http://localhost:8001/api/v1/devices" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV-01001",
    "model_type": "IoT-Industrial-Sensor-X1",
    "firmware_version": "1.2.0",
    "installation_date": "2026-01-01"
  }'
```

#### Fetch Fleet Health Summary
```bash
curl -X GET "http://localhost:8001/api/v1/fleet/summary"
```

#### Query Open Alerts
```bash
curl -X GET "http://localhost:8001/api/v1/alerts?status=OPEN"
```

---

### 9.3 Streaming Ingestion API (`:8002`)

#### Post High-Frequency Telemetry Observation
```bash
curl -X POST "http://localhost:8002/api/v1/stream/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV-00042",
    "timestamp": "2026-01-05T04:00:00",
    "temperature": 83.1,
    "voltage": 3.10,
    "current": 2.58,
    "battery_level": 33,
    "network_quality": 88,
    "error_count": 14,
    "restart_count": 3,
    "uptime_hours": 13.5,
    "firmware_version": "1.2.0"
  }'
```

#### Retrieve Computed 24-Hour Sliding Window
```bash
curl -X GET "http://localhost:8002/api/v1/stream/devices/DEV-00042/window"
```

---

## 10. Observability & Monitoring (Prometheus & Grafana)

DataMind is equipped with production telemetry and SLA tracking out-of-the-box.

### 10.1 Accessing Observability Consoles
* **Prometheus Server:** `http://localhost:9090`
  * Status -> Targets: Verifies health of all four `/metrics` endpoints.
  * Alerts: Displays status of the 5 automated alert rules.
* **Grafana Dashboards:** `http://localhost:3000`
  * Default Credentials: User: `admin`, Password: `admin` (or configured in `.env`).
  * Dashboards -> Browse -> **DataMind Fleet Overview**:
    * **P99 Inference Latency Gauge** (Threshold alert at 5.0 ms).
    * **Fleet Risk Distribution Donut** (High vs. Nominal).
    * **HTTP Request Throughput & Error Rate Timeseries**.
    * **Buffer Backpressure & Queue Depth Gauge**.

### 10.2 Key Prometheus Metrics
* `datamind_prediction_latency_seconds_bucket`: Latency histogram for ML inference.
* `datamind_predictions_total{risk_severity="HIGH"}`: Counter of high-risk failure predictions.
* `datamind_stream_buffer_depth`: Current depth of the ingestion memory worker queue.
* `http_requests_total{status=~"5.."}`: Counter of service errors.

---

## 11. Running the Automated Test Suite

DataMind provides **98 comprehensive unit and integration tests** verifying data integrity, ML models, microservice APIs, and infrastructure configurations.

### 11.1 Run Entire Test Suite
Execute from repository root:
```bash
# Windows
$env:PYTHONPATH = "."
python -m unittest discover -s tests -t . -v

# Linux / macOS
PYTHONPATH=. python3 -m unittest discover -s tests -t . -v
```

### 11.2 Run Domain-Specific Test Suites
```bash
# 1. Machine Learning Pipelines (38 tests)
python -m unittest discover -s tests/ml -t .

# 2. Microservice REST APIs & Ingestion (27 tests)
python -m unittest discover -s tests/services -t .

# 3. Docker, Kubernetes, Prometheus & CI/CD (24 tests)
python -m unittest discover -s tests/infrastructure -t .
```

---

## 12. Troubleshooting & Frequently Asked Questions

### Q1: `ModuleNotFoundError: No module named 'ml'` when running tests or services
**Solution:** Set the `PYTHONPATH` environment variable to the repository root:
* Windows PowerShell: `$env:PYTHONPATH = "."`
* Windows Command Prompt: `set PYTHONPATH=.`
* Linux / macOS Bash: `export PYTHONPATH=.`

### Q2: Error compiling wheels during `pip install -r requirements.txt`
**Solution:** Ensure you are using **Python 3.11.x (64-bit)**. Python 3.12, 3.13, or 3.15 do not have pre-built binary wheels for several ML dependencies (`scipy`, `xgboost`, `shap`). Download Python 3.11.9 from [python.org](https://www.python.org/downloads/release/python-3119/).

### Q3: Ports `8000`, `8001`, `8002`, or `8003` are already in use
**Solution:** Check which process is occupying the port and terminate it:
* Windows: `Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process`
* Linux / macOS: `lsof -ti:8000 | xargs kill -9`

### Q4: Prediction service fails with `FileNotFoundError: ml/models/best_model_xgboost.joblib`
**Solution:** The model artifact must be generated by running the training pipeline:
```bash
python ml/data_pipeline/generate_dataset.py
python ml/feature_engineering/pipeline.py
python ml/training/train_models.py
```
This will train the XGBoost champion model and save the joblib artifact to `ml/models/`.

### Q5: How do I switch between SQLite (local development) and PostgreSQL (production)?
**Solution:** Update the `DATABASE_URL` environment variable in your `.env` file:
* **SQLite (Default local):** `DATABASE_URL=sqlite+aiosqlite:///data/datamind.db`
* **PostgreSQL:** `DATABASE_URL=postgresql+asyncpg://datamind_admin:datamind_prod_secret@localhost:5432/datamind`
The service auto-detects dialect differences and creates compatible tables automatically.

---

*For issues, enhancements, or questions, consult the milestone docs in [`docs/milestones/`](../docs/milestones/) or open a GitHub issue.*
