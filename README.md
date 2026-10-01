# DataMind

DataMind is a predictive intelligence platform designed to demonstrate production-grade software engineering, data engineering, and machine learning.

## Objective

Build a system capable of ingesting device and time-series data, engineering meaningful features, training machine learning models, detecting anomalies, forecasting future behavior, and serving real-time predictions through APIs.

## Initial Use Case

Predict whether a device is likely to experience a failure within the next 24 hours.

## Planned Capabilities

* Data ingestion
* Data validation and cleaning
* Feature engineering
* Predictive modeling
* Failure prediction
* Anomaly detection
* Time-series forecasting
* Model evaluation
* Model versioning
* Real-time inference
* Explainable predictions
* REST APIs
* PostgreSQL persistence
* Dockerized deployment
* MLflow experiment tracking
* Monitoring and observability
* Kubernetes deployment

## Technology

* Python
* scikit-learn
* XGBoost
* PyTorch
* C#
* .NET
* ASP.NET Core
* PostgreSQL
* Redis
* Kafka
* Docker
* Kubernetes
* MLflow
* React
* TypeScript
* Prometheus
* Grafana

## Project Status

* [x] **Milestone 1:** Data generation and validation foundation (`ml/data_pipeline/generate_dataset.py`, `ml/data_pipeline/validate_dataset.py`)
* [x] **Milestone 2:** Exploratory data analysis and profiling (`ml/data_pipeline/eda.py`, [`docs/eda/eda_report.md`](docs/eda/eda_report.md))
* [ ] **Milestone 3:** Feature engineering pipeline
* [ ] **Milestone 4:** Baseline model & evaluation framework
* [ ] **Milestone 5:** Model progression (Logistic Regression → Random Forest → XGBoost)

Detailed milestone documentation is available in [**`docs/MILESTONE_PROGRESS.md`**](docs/MILESTONE_PROGRESS.md).

## Quickstart

Run with Python 3.11 in `.venv`:

```powershell
# 1. Generate synthetic telemetry dataset (100k records, deterministic seed 42)
python ml/data_pipeline/generate_dataset.py

# 2. Run automated data quality and validation pipeline
python ml/data_pipeline/validate_dataset.py --strict

# 3. Generate exploratory data analysis report and visual charts
python ml/data_pipeline/eda.py

# 4. Run automated test suite
python -m unittest discover -s tests -t . -v
```

## Engineering Goals

DataMind is being developed as a production-oriented engineering project rather than a simple machine learning notebook.

The project will emphasize:

* Reproducible experiments
* Clean architecture
* Testability
* Data quality
* Model evaluation
* Scalability
* Reliability
* Observability
* Explicit engineering trade-offs
