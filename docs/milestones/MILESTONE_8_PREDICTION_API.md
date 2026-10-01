# Milestone 8: Real-Time Prediction API (FastAPI)

> **Milestone ID:** `M8-PREDICTION-API`  
> **Status:** Completed  
> **Date:** 2026-10-01  
> **Framework:** FastAPI, Pydantic v2, Uvicorn  
> **Service Location:** `services/DataMind.Prediction/`  
> **Target Production Model:** `best_model_xgboost.joblib` (Champion Version 2)  

---

## 1. Objective & Motivation

Moving from offline machine learning models to production serving requires software engineering rigor:
1. **Strict Latency SLA (< 5 ms):** Single-sample prediction must return sub-millisecond inference times without cold-start model deserialization per request.
2. **In-Memory Caching:** Load the trained XGBoost model and `TelemetryExplainer` once into memory during application lifespan startup (`lifespan`).
3. **Dual-Path Serving:**
   - **Fast Path (`include_explanations=false`):** Pure XGBoost scoring ($< 1\,\text{ms}$) for high-throughput streaming pipelines.
   - **Diagnostic Path (`include_explanations=true`):** Full SHAP factor attribution (~5–14 ms) for incident investigation and alerts.
4. **Strict Schema Validation:** Pydantic v2 data transfer objects (DTOs) enforcing physical ranges and preventing corrupt telemetry from reaching the model.
5. **Production Probes:** Health readiness/liveness endpoints (`GET /health`) and model governance metadata (`GET /api/v1/model/metadata`).

---

## 2. API Architecture & Microservice Layout

```
services/DataMind.Prediction/
├── __init__.py                 # Service package initialization
├── config.py                   # Centralized configuration (paths, host, port, thresholds)
├── schemas.py                  # Pydantic v2 request/response schemas & validation
├── predictor.py                # In-memory PredictionEngine with dual-path serving
└── main.py                     # FastAPI application, lifespan manager, middleware, and routes
```

```
           HTTP Client / Ingestion Pipeline / Frontend Dashboard
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │    ProcessTimeMiddleware     │ (Adds X-Process-Time-Ms)
                      └──────────────┬───────────────┘
                                     │
                      ┌──────────────▼───────────────┐
                      │      Pydantic Validation     │ (Schema & Range Guard)
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                     ┌────────────────────────────────┐
                     │   In-Memory PredictionEngine   │
                     │  (Loaded once at App Startup)  │
                     └───────┬────────────────┬───────┘
                             │                │
            [Fast Path: < 1ms]│                │[Diagnostic Path: ~10ms]
                             ▼                ▼
                     ┌──────────────┐ ┌──────────────────────┐
                     │ Raw XGBoost  │ │ SHAP TreeExplainer   │
                     │ Scoring      │ │ Risk Factor Mapping  │
                     └───────┬──────┘ └──────────┬───────────┘
                             │                   │
                             └─────────┬─────────┘
                                       │
                                       ▼
                            PredictionResponse JSON
```

---

## 3. Endpoints Specification

### 3.1 Health & Readiness Probe
`GET /health`
* **Status:** `200 OK`
* **Response:**
```json
{
  "status": "HEALTHY",
  "modelLoaded": true,
  "modelVersion": "1.0.0",
  "uptimeSeconds": 142.5
}
```

### 3.2 Model Metadata Endpoint
`GET /api/v1/model/metadata`
* **Response:**
```json
{
  "modelName": "DataMind-Device-Failure-Predictor",
  "algorithm": "XGBClassifier",
  "featureCount": 25,
  "features": ["temperature", "voltage", "current", ...],
  "decisionThreshold": 0.7173,
  "testMetrics": {
    "pr_auc": 0.9608,
    "roc_auc": 0.9841,
    "recall": 0.9388,
    "precision": 0.9446,
    "f1": 0.9417
  }
}
```

### 3.3 Single Device Prediction Endpoint
`POST /api/v1/predict?include_explanations=true&top_k=4`
* **Request Payload:**
```json
{
  "device_id": "DEV-00002",
  "timestamp": "2026-01-01T00:00:00",
  "temperature": 88.2,
  "voltage": 3.14,
  "current": 2.70,
  "battery_level": 34.0,
  "network_quality": 61.0,
  "error_count": 18.0,
  "restart_count": 4.0,
  "uptime_hours": 823.0,
  "battery_change_24h": -22.0,
  "temperature_mean_6h": 85.0,
  "voltage_min_6h": 3.05,
  "current_mean_6h": 2.65,
  "error_count_6h": 15.0,
  "firmware_version": "1.2.0"
}
```

* **Response Payload (Headers: `X-Process-Time-Ms: 12.4`):**
```json
{
  "deviceId": "DEV-00002",
  "timestamp": "2026-01-01T00:00:00",
  "failureProbability": 0.8605,
  "predictionLabel": 1,
  "riskLevel": "HIGH",
  "decisionThreshold": 0.7173,
  "predictionWindowHours": 24,
  "latencyMs": 11.85,
  "topRiskFactors": [
    {
      "category": "Electrical Jitter / Regulator Noise",
      "featureName": "voltage_std_6h",
      "featureValue": 0.0,
      "attributionScore": 0.7621,
      "description": "Electrical rail standard deviation reached 0.000V (+0.76 log-odds)"
    },
    {
      "category": "Thermal Stress / Chassis Heat",
      "featureName": "temperature",
      "featureValue": 88.2,
      "attributionScore": 0.7289,
      "description": "Current chassis temperature is 88.2°C (+0.73 log-odds)"
    },
    {
      "category": "Electrical Load / Sustained Draw",
      "featureName": "current_mean_6h",
      "featureValue": 2.65,
      "attributionScore": 0.6558,
      "description": "Sustained 6h average current draw is 2.65A (+0.66 log-odds)"
    }
  ],
  "topMitigatingFactors": [
    {
      "category": "Battery Depletion / Rapid Drain",
      "featureName": "battery_change_24h",
      "featureValue": -22.0,
      "attributionScore": -0.852,
      "description": "24h battery capacity shifted by -22.0% (-0.85 log-odds)"
    }
  ]
}
```

### 3.4 Batch Prediction Endpoint
`POST /api/v1/predict/batch?include_explanations=false`
* Efficient vectorized batch scoring across up to 500 hardware devices.

---

## 4. Automated Unit & Integration Tests

- **Module:** [`tests/services/test_prediction_api.py`](../../tests/services/test_prediction_api.py)
- **Coverage:**
  1. `test_health_check_endpoint`: Verifies 200 OK and model readiness flag.
  2. `test_model_metadata_endpoint`: Verifies schema reflection and threshold output.
  3. `test_predict_single_healthy_device`: Verifies LOW risk prediction with mitigating factors.
  4. `test_predict_single_high_risk_device`: Verifies HIGH risk classification and risk factor extraction.
  5. `test_predict_single_without_explanations_fast_path`: Verifies sub-10ms fast inference path.
  6. `test_predict_batch_endpoint`: Verifies multi-device batch processing.
  7. `test_validation_error_on_out_of_range_temperature`: Verifies HTTP 422 on impossible physics (> 150°C).
  8. `test_validation_error_on_missing_required_field`: Verifies HTTP 422 on missing payload fields.

**Result:** **8/8 tests passed in 1.27s**.  
**Total Repository Suite:** **55/55 tests passing** across all modules.

---

## 5. How to Run the Prediction Service

```powershell
# Run the FastAPI server via Uvicorn
python -m uvicorn services.DataMind.Prediction.main:app --host 0.0.0.0 --port 8000

# Run API integration tests
python -m unittest tests/services/test_prediction_api.py -v

# Run entire repository test suite
python -m unittest discover -s tests -t . -v
```
