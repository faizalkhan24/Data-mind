# Milestone 9: Relational Persistence Layer & Fleet Management API

> **Milestone ID:** `M9-DATABASE-PERSISTENCE`  
> **Status:** Completed  
> **Date:** 2026-10-01  
> **Framework:** FastAPI, SQLAlchemy 2.0 (Asyncio), `aiosqlite` / `asyncpg`, Pydantic v2  
> **Service Location:** `services/DataMind.Api/`  
> **Supported Backends:** SQLite (`aiosqlite`) for local development/testing, PostgreSQL (`asyncpg`) for production  

---

## 1. Objective & Motivation

A predictive intelligence platform cannot rely solely on stateless inference; it requires an enterprise persistence and fleet management backbone:
1. **Relational Entity Model:** Maintain a single source of truth for all provisioned IoT hardware devices, their firmware lifecycle, and operational status.
2. **Historical Telemetry Time-Series:** Ingest and index raw sensory time-series data (`temperature`, `voltage`, `current`, `battery_level`, `network_quality`, etc.) per device with optimized time-range queries.
3. **Inference Audit Logging:** Persist every prediction scored by `DataMind.Prediction` (failure probabilities, risk labels, inference latency, and SHAP top risk factors) for auditability, governance, and drift monitoring.
4. **Automated Incident Alerting:** Automatically create actionable `CRITICAL` or `WARNING` alerts when high-risk predictions are logged, with full incident lifecycle tracking (`OPEN` $\to$ `ACKNOWLEDGED` $\to$ `RESOLVED`).
5. **Fleet Analytics & Health Aggregation:** Provide single-query fleet overview KPIs (active units, critical alert count, high-risk device inventory) for operations centers and dashboard UIs.

---

## 2. Relational Schema Architecture

```
                    ┌────────────────────────────┐
                    │          devices           │
                    ├────────────────────────────┤
                    │ id (PK, Integer)           │
                    │ device_id (Unique, String) │◄─────────────┐
                    │ firmware_version (String)  │              │
                    │ status (Enum/String)       │              │
                    │ created_at (Timestamp)     │              │
                    │ updated_at (Timestamp)     │              │
                    └─────────────┬──────────────┘              │
                                  │                             │
             ┌────────────────────┼───────────────────┐         │
             │ 1:N (Cascade)      │ 1:N (Cascade)     │ 1:N     │
             ▼                    ▼                   ▼         │
┌─────────────────────────┐ ┌───────────────────┐ ┌─────────────┴─────────┐
│   telemetry_readings    │ │  prediction_logs  │ │    failure_alerts     │
├─────────────────────────┤ ├───────────────────┤ ├───────────────────────┤
│ id (PK)                 │ │ id (PK)           │ │ id (PK)               │
│ device_id (FK)          │ │ device_id (FK)    │ │ device_id (FK)        │
│ timestamp (Indexed)     │ │ timestamp         │ │ alert_level (CRITICAL)│
│ temperature, voltage    │ │ failure_prob      │ │ risk_score (Float)    │
│ current, battery_level  │ │ prediction_label  │ │ description (Text)    │
│ network_quality, uptime │ │ risk_level        │ │ status (OPEN/RESOLVED)│
│ error_count, restarts   │ │ latency_ms        │ │ created_at, resolved  │
└─────────────────────────┘ └───────────────────┘ └───────────────────────┘
```

### Table Indices
- `ix_telemetry_device_time`: Compound index on `(device_id, timestamp DESC)` for fast historical window slicing.
- `ix_predictions_device_time`: Compound index on `(device_id, timestamp DESC)` for audit retrieval.
- `ix_alerts_device_status`: Compound index on `(device_id, status)` for fast incident filtering.

---

## 3. Asynchronous Repository Pattern

All database interactions use modern SQLAlchemy 2.0 async conventions (`AsyncSession`, `select`, `update`), encapsulated in dedicated domain repositories:

| Repository | Responsibility | Key Methods |
| :--- | :--- | :--- |
| `DeviceRepository` | Device hardware lifecycle | `create()`, `get_by_device_id()`, `list_all()`, `update_status()` |
| `TelemetryRepository`| Time-series sensory readings | `create_reading()`, `get_history()` (ordered desc with limit) |
| `PredictionRepository`| Prediction audit records | `create_log()`, `get_history()`, `get_high_risk_device_ids()` |
| `AlertRepository` | Incident management & resolution | `create_alert()`, `list_alerts(status)`, `resolve_alert()` |

---

## 4. REST API Endpoint Specifications

The service exposes versioned REST endpoints mounted under `/api/v1/`:

### Fleet & Devices
- `POST /api/v1/devices`: Provision new IoT device. Returns `201 Created` or `409 Conflict` on duplicate.
- `GET /api/v1/devices`: List all registered devices (supports `status` filter, `limit`, `offset`).
- `GET /api/v1/devices/{device_id}`: Retrieve device details and metadata.
- `PATCH /api/v1/devices/{device_id}`: Update device status (`ACTIVE`, `MAINTENANCE`, `DECOMMISSIONED`) or firmware.

### Telemetry Ingestion
- `POST /api/v1/devices/{device_id}/telemetry`: Ingest raw sensory observation. Auto-provisions device if unseen.
- `GET /api/v1/devices/{device_id}/telemetry`: Query historical telemetry time series (`limit`, `start_time`, `end_time`).

### Predictions & Audit
- `POST /api/v1/devices/{device_id}/predictions`: Log model prediction. Automatically fires a `CRITICAL` alert if `risk_level == "HIGH"`.
- `GET /api/v1/devices/{device_id}/predictions`: Retrieve historical prediction log for device.

### Incident Alerts
- `GET /api/v1/alerts`: Query failure alerts (filter by `status=OPEN`, `status=RESOLVED`).
- `PATCH /api/v1/alerts/{alert_id}`: Update alert status (`ACKNOWLEDGED`, `RESOLVED`). Automatically timestamps `resolved_at`.

### Fleet Summary KPIs
- `GET /api/v1/fleet/summary`: Aggregated operational metrics:
  ```json
  {
    "totalDevices": 42,
    "activeDevices": 38,
    "maintenanceDevices": 4,
    "decommissionedDevices": 0,
    "openAlertsCount": 3,
    "criticalAlertsCount": 2,
    "highRiskDevicesCount": 2,
    "lastUpdated": "2026-10-01T23:56:00Z"
  }
  ```

---

## 5. Verification & Test Suite

The test suite in `tests/services/test_fleet_api.py` verifies transactional behavior, schema constraints, and business logic:
- `test_health_check`: Verifies `GET /health` returns `200 OK`.
- `test_device_lifecycle`: Tests device registration, duplicate conflict prevention (`409`), query, and status updates.
- `test_telemetry_ingestion_and_history`: Tests time-series ingestion and ordering.
- `test_prediction_audit_and_automated_alert`: Tests logging a high-risk prediction, automated creation of a `CRITICAL` alert, and alert resolution.
- `test_fleet_summary`: Validates fleet-wide aggregation metrics.

All 5 integration tests pass with zero errors.
Combined with Milestone 8 prediction tests, the service test suite contains 13 passing tests.
