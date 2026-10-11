# Milestone 11: Fleet Health Operations Console & Interactive Dashboard

> **Milestone ID:** `M11-FLEET-DASHBOARD`  
> **Status:** Completed  
> **Date:** 2026-10-11  
> **Framework:** FastAPI, Modern Vanilla JavaScript (ES2022), CSS3 Custom Properties, Responsive Glassmorphism  
> **Service Location:** `services/DataMind.Dashboard/`  
> **Inference SLA Display:** $< 0.50\,\text{ms}$ (Real-time XGBoost model scoring + SHAP attribution)  
> **Test Coverage:** 9 Automated Tests in `tests/services/test_dashboard.py` (74 Total Passing Tests)  

---

## 1. Objective & Motivation

Operating enterprise IoT fleets requires intuitive, real-time visualization of hardware health, rapid incident response, and transparent explanations for why a predictive maintenance model flagged a unit for failure. 

Milestone 11 delivers the **DataMind Fleet Health Operations Console**, an enterprise single-page application (SPA) backed by a high-performance FastAPI web gateway:
1. **Executive Fleet KPIs:** Instant visualization of active hardware counts, total fleet size, high-risk assets ($P(\text{fail}) \ge 0.70$), open incidents, and operational inference SLA.
2. **Fleet Health & Risk Inventory:** Searchable and filterable real-time device registry displaying firmware versions, operational statuses, risk probabilities, and categorical risk tags.
3. **Interactive Diagnostic Simulator:** Sandbox allowing reliability engineers to simulate complex thermodynamic and electrical conditions (e.g. thermal spikes, rapid discharge, power sag), compute instant risk predictions ($< 5\,\text{ms}$), and inspect game-theoretic SHAP risk attribution.
4. **Active Operational Incident Management:** Real-time triage center for critical hardware failure alerts with one-click state progression (`OPEN` $\to$ `ACKNOWLEDGED` $\to$ `RESOLVED`).
5. **Granular Device Telemetry Drawer / Modal:** Deep inspection modal displaying device hardware specifications, battery wear, and a trailing 10-hour audit ledger.

---

## 2. System Architecture & UI Data Flow

```
                      Operations Engineer / Web Browser
                                     │
                                     ▼ (HTTP / REST)
                      ┌──────────────────────────────┐
                      │    DataMind Web Gateway      │
                      │  services/DataMind.Dashboard │
                      │  Port: 8080 (FastAPI Server) │
                      └──────────────┬───────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  Static UI Delivery │   │   Aggregated APIs   │   │ Diagnostic Simulator│
│  - index.html       │   │  - GET /summary     │   │  - POST /simulate   │
│  - style.css        │   │  - GET /fleet       │   │  - SHAP Factor      │
│  - app.js           │   │  - PATCH /alerts    │   │    Attribution      │
└─────────────────────┘   └──────────┬──────────┘   └──────────┬──────────┘
                                     │                         │
                                     ▼                         ▼
                      ┌──────────────────────────────────────────────┐
                      │      Downstream Core Services Mesh           │
                      │  - DataMind.Api (Port 8001: SQLite/Postgres) │
                      │  - DataMind.Prediction (Port 8000: XGBoost)   │
                      │  - DataMind.Ingestion (Port 8002: Stream Q)  │
                      └──────────────────────────────────────────────┘
```

---

## 3. UI Features & Functional Components

### 3.1 Real-Time KPI Metric Cards
Displays 5 core operational indicators updated via polling every 5 seconds or via the manual Refresh button:
* **Total Fleet Devices:** Total registered hardware units.
* **Active Hardware:** Endpoints operating nominally.
* **High-Risk Units ($> 0.70$):** Devices flagged with impending failure in the next 24 hours.
* **Open Incidents:** Outstanding `CRITICAL` or `WARNING` alerts requiring engineering intervention.
* **Avg Inference SLA:** Average scoring latency achieved by the production XGBoost model ($< 0.50\,\text{ms}$).

### 3.2 Fleet Health & Risk Inventory Table
* **Instant Text Filtering:** Live search by `device_id` (e.g. `DEV-00042`).
* **Risk Severity Filtering:** Toggle between `All Risk Levels`, `High Risk Only`, and `Nominal / Low Risk`.
* **Action Drawer:** "Inspect" button opening device hardware specifications and a 10-hour historical telemetry log.

### 3.3 Interactive Diagnostic Simulator & SHAP Attribution
Engineers can stress-test the model by configuring 6 primary sensor signals:
1. **Chassis Die Temperature (°C)**
2. **Power Rail Voltage (V)**
3. **Current Draw (A)**
4. **Battery Level (%)**
5. **Wireless Link Quality (%)**
6. **Continuous Operating Uptime (h)**

**Built-In Fault Presets:**
- **Healthy:** Nominal operating temperature (44.5°C), stable power rail (3.74V), normal battery (88.0%).
- **Thermal Spike:** Extreme heat accumulation (88.5°C) with high current draw (2.45A).
- **Discharge Drop:** Accelerated battery depletion (18.0%) under heavy system uptime.
- **Power Sag:** Severe rail droop (2.95V) indicating regulator instability.

**SHAP Attribution Visualization:**
Renders horizontal divergence bars indicating feature impacts:
- **Risk-Increasing Factors (Red, $+$):** Thermal Degradation, Power Rail Droop, Rapid Battery Depletion.
- **Risk-Reducing Factors (Green, $-$):** Safe Thermal Operating Margin, Stable Supply Voltage, Optimal Battery Reserve.

### 3.4 Operational Incident Alert Management
* Displays all active failure incidents with severity pills (`CRITICAL`, `WARNING`).
* Provides optimistic UI updates for `Acknowledge` and `Resolve` workflows with backend synchronization.

---

## 4. REST API Endpoint Specifications

The Dashboard service runs on port `8080` (configured in `dashboard_config.py`):

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the single-page application `index.html`. |
| `GET` | `/health` | Readiness probe checking service health and static asset presence. |
| `GET` | `/api/dashboard/summary` | Returns aggregated KPI counts and system health state. |
| `GET` | `/api/dashboard/fleet` | Returns filtered, paginated fleet device records. |
| `GET` | `/api/dashboard/devices/{device_id}` | Returns hardware specifications and 10-hour telemetry history. |
| `POST` | `/api/dashboard/simulate` | Computes instantaneous failure risk and SHAP attribution. |
| `GET` | `/api/dashboard/alerts` | Lists active operational failure alerts. |
| `PATCH`| `/api/dashboard/alerts/{alert_id}` | Updates alert lifecycle status (`ACKNOWLEDGED` / `RESOLVED`). |

---

## 5. Verification & Test Suite

The test suite in `tests/services/test_dashboard.py` exercises all gateway routes and UI workflows:
1. `test_health_check`: Probes `/health` endpoint and verifies UI readiness.
2. `test_serve_root_index_html`: Verifies SPA entrypoint delivery with proper headers.
3. `test_static_assets_delivery`: Tests delivery and MIME types for `style.css` and `app.js`.
4. `test_dashboard_summary_endpoint`: Confirms KPI aggregation math and SLA strings.
5. `test_dashboard_fleet_and_filtering`: Validates pagination, device ID search, and `HIGH` risk filtering.
6. `test_dashboard_device_detail`: Verifies device inspection specs and 10-point telemetry timeline.
7. `test_diagnostic_simulation_healthy`: Verifies nominal telemetry inputs yield $P(\text{fail}) < 0.20$ and `NOMINAL` badge.
8. `test_diagnostic_simulation_high_risk`: Verifies thermal runaway & power sag yield $P(\text{fail}) > 0.70$ and positive SHAP risk factors.
9. `test_alerts_lifecycle`: Verifies alert retrieval, acknowledgment, resolution, and 404 handling.

```text
tests.services.test_dashboard
  - test_alerts_lifecycle: Verifies alert retrieval and status transitions. [OK]
  - test_dashboard_device_detail: Verifies device specs and telemetry timeline. [OK]
  - test_dashboard_fleet_and_filtering: Verifies search and risk filtering. [OK]
  - test_dashboard_summary_endpoint: Verifies aggregated fleet KPIs. [OK]
  - test_diagnostic_simulation_healthy: Verifies nominal simulation scoring. [OK]
  - test_diagnostic_simulation_high_risk: Verifies failure simulation and SHAP attributions. [OK]
  - test_health_check: Verifies service readiness probe. [OK]
  - test_serve_root_index_html: Verifies SPA HTML delivery. [OK]
  - test_static_assets_delivery: Verifies CSS/JS asset serving. [OK]

----------------------------------------------------------------------
Ran 9 tests in 0.113s — ALL 9 TESTS PASSED (OK)
Total Repository Suite: 74 Tests Passing (100% Green)
```

---

## 6. How to Run Locally

```powershell
# 1. Activate Python virtual environment
.venv\Scripts\activate

# 2. Launch the Fleet Health Console
python -m uvicorn services.DataMind.Dashboard.main:app --port 8080 --reload

# 3. Open in browser:
# http://localhost:8080
```
