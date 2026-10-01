# Milestone 10: Streaming Ingestion & Real-Time Event Buffer

> **Milestone ID:** `M10-STREAMING-INGESTION`  
> **Status:** Completed  
> **Date:** 2026-10-02  
> **Framework:** FastAPI, Asyncio Queue Worker, NumPy, Pydantic v2  
> **Service Location:** `services/DataMind.Ingestion/`  
> **Enrichment Throughput:** Sub-millisecond per event ($< 0.1\,\text{ms}$)  

---

## 1. Objective & Motivation

In production IoT ecosystems, hardware telemetry arrives continuously as asynchronous event streams rather than static batch files. However, the machine learning failure model (`best_model_xgboost.joblib`) requires **25 temporal features**—including 6-hour and 24-hour rolling averages, rates of change, and cumulative restart differentials—that cannot be derived from a single instantaneous sensor reading alone.

Milestone 10 delivers the streaming ingestion backbone:
1. **Real-Time Sliding Window Buffer:** Maintains an in-memory, bounded ring buffer (`DeviceRollingBuffer`) for every active device in the fleet with zero lookahead and zero data leakage.
2. **Instantaneous Feature Enrichment:** Incrementally calculates the exact 25-feature vector required by `DataMind.Prediction` in $< 0.1\,\text{ms}$ upon arrival of every raw telemetry packet.
3. **Asynchronous Queue Worker:** Implements `StreamQueueWorker` with an asynchronous bounded queue (`asyncio.Queue`), decoupling ingestion ingestion from downstream prediction scoring and database persistence.
4. **State Inspection & Diagnostics:** Exposes endpoints to inspect device sliding window state (points in memory, earliest/latest timestamps, computed features) and real-time worker throughput metrics.

---

## 2. Streaming Architecture & Data Flow

```
                      IoT Hardware Devices / Event Publishers
                                        │
                                        ▼ (HTTP POST Stream)
                      ┌──────────────────────────────────┐
                      │    Stream Ingestion Endpoints    │
                      │  POST /api/v1/stream/telemetry   │
                      │  POST /api/v1/stream/batch       │
                      └────────────────┬─────────────────┘
                                       │
                                       ▼
                      ┌──────────────────────────────────┐
                      │      Async Ingestion Queue       │ (Bounded Buffer)
                      │    asyncio.Queue (depth 10k)     │
                      └────────────────┬─────────────────┘
                                       │
                      ┌────────────────┴─────────────────┐
                      │    StreamQueueWorker Consumer    │
                      └────────────────┬─────────────────┘
                                       │
                                       ▼
                      ┌──────────────────────────────────┐
                      │     FleetBufferManager (RAM)     │
                      │   ┌───────────────────────────┐  │
                      │   │ DeviceRollingBuffer (DEV) │  │
                      │   │  - Slices trailing 6h/24h │  │
                      │   │  - Computes ΔT & ΔBattery │  │
                      │   │  - Emits 25-Feature Vector│  │
                      │   └───────────────────────────┘  │
                      └────────────────┬─────────────────┘
                                       │
             ┌─────────────────────────┴─────────────────────────┐
             ▼                                                   ▼
┌──────────────────────────┐                       ┌───────────────────────────┐
│   DataMind.Prediction    │                       │       DataMind.Api        │
│  (Real-Time Inference)   │                       │ (Relational Persistence)  │
└──────────────────────────┘                       └───────────────────────────┘
```

---

## 3. Real-Time Feature Calculation Engine

The rolling buffer calculates features that match the offline training pipeline (`ml/feature_engineering/pipeline.py`) with zero leakage:

| Feature Domain | Features Computed | Rolling Calculation |
| :--- | :--- | :--- |
| **Instantaneous** | `temperature`, `voltage`, `current`, `battery_level`, `network_quality`, `error_count`, `restart_count`, `uptime_hours` | Passed directly from latest sensory observation. |
| **Thermal Dynamics** | `temperature_mean_6h`, `temperature_mean_24h`, `temperature_std_6h`, `temperature_change_1h` | Mean and sample std dev ($\text{ddof}=1$) over trailing $\le 6$ and $\le 24$ points; $\Delta T = T_t - T_{t-1}$. |
| **Power Dynamics** | `voltage_mean_6h`, `voltage_min_6h`, `voltage_std_6h`, `current_mean_6h` | Minimum voltage detects brownout/power sag; std dev detects rail instability. |
| **Fault Acceleration** | `error_count_6h`, `error_count_24h`, `restart_count_24h` | Cumulative error sums; $\Delta \text{restart} = \text{restarts}_t - \text{restarts}_{t-24}$. |
| **Battery & Net** | `battery_change_24h`, `network_quality_mean_6h` | $\Delta \text{battery} = \text{battery}_t - \text{battery}_{t-24}$ (identifies abnormal discharge rates). |
| **Longevity & FW** | `device_age_hours`, `firmware_version_1.0.0`, `firmware_version_1.1.0`, `firmware_version_1.2.0` | Device operating uptime and one-hot categorical encoding. |

---

## 4. REST API Endpoint Specifications

The service runs independently on port `8002` (configurable via `ingestion_config.py`):

### Ingestion Endpoints
- `POST /api/v1/stream/telemetry`: Ingests single telemetry event. Computes 25 features and returns `IngestionResponse` with latency telemetry.
- `POST /api/v1/stream/batch`: Ingests a batch of telemetry events in high-throughput mode.

### Buffer Inspection & Fleet State
- `GET /api/v1/stream/devices/{device_id}/window`: Returns `DeviceWindowState` showing points in memory, timestamps, and current feature vector.
- `DELETE /api/v1/stream/buffers`: Clears all active device buffers and resets state.

### Worker Health & Metrics
- `GET /api/v1/stream/stats`: Returns operational throughput, active device count, queue depth, and average enrichment latency.
- `GET /health`: Standard container readiness/liveness probe.

---

## 5. Verification & Test Suite

The test suite in `tests/services/test_ingestion_stream.py` verifies all streaming mechanics:
1. `test_health_check`: Probes `/health` endpoint and active buffer counts.
2. `test_single_event_ingestion_and_feature_enrichment`: Ingests a single observation, confirms all 25 features are populated accurately, and verifies sub-50ms SLA.
3. `test_sliding_window_temporal_dynamics`: Ingests sequential readings, verifies rolling means, thermal velocity ($\Delta T$), and 24h battery differentials.
4. `test_batch_ingestion_stream`: Exercises multi-device batch streaming.
5. `test_stats_and_error_handling`: Verifies throughput stats, 404 behavior for unknown devices, and buffer cleanup.

All 5 tests pass with zero errors in **0.06 seconds**.
Across all microservices (`DataMind.Prediction`, `DataMind.Api`, `DataMind.Ingestion`), **18 service tests** and **65 total repository tests** pass with 100% integrity.
