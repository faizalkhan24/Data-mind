# Milestone 1: Data Generation & Validation Foundation

> **Milestone ID:** `M1-DATA-FOUNDATION`  
> **Status:** Completed  
> **Date:** 2026-10-01  
> **Git Commit:** `8ad82d2 Add synthetic device dataset generator and validation pipeline`  

---

## 1. Objective & Motivation

The objective of Milestone 1 is to establish a rigorous, physically grounded data foundation for the DataMind predictive maintenance platform.

Rather than relying on naive independent random noise (which trivializes or breaks ML modeling), we model:
1. **Realistic physical device behavior:** Temperature dynamics, internal resistance, current load, power supply sagging, Poisson error bursts, and watchdog reboots.
2. **Ground-truth failure horizons:** Defining the binary label `failed_within_24h` strictly as whether a device failure occurs in $(t, t + 24\text{ hours}]$, avoiding target leakage.
3. **Automated pre-ML validation:** An automated quality gate enforcing 13 schema, completeness, operational range, uniqueness, and temporal monotonicity checks.

---

## 2. Telemetry Schema Specification

The dataset schema contains 12 columns per observation:

| Column Name | Type | Unit | Operational Range | Description |
| :--- | :---: | :---: | :---: | :--- |
| `device_id` | `string` | — | `DEV-00001` – `DEV-01000` | Device hardware ID |
| `timestamp` | `string` | ISO-8601 | `2026-01-01T00:00:00` – `2026-01-05T03:00:00` | Hourly observation timestamp |
| `temperature` | `float64` | °C | `[-20.0, 120.0]` (Observed: `[31.7, 92.3]`) | Chassis / die temperature |
| `voltage` | `float64` | V | `[2.0, 6.0]` (Observed: `[2.82, 4.02]`) | Power supply rail voltage |
| `current` | `float64` | A | `[0.0, 15.0]` (Observed: `[0.82, 2.81]`) | Electrical load current |
| `battery_level` | `int64` | % | `[0, 100]` (Observed: `[16, 98]`) | Battery state of charge |
| `network_quality`| `int64` | % | `[0, 100]` (Observed: `[54, 100]`) | Link quality index |
| `error_count` | `int64` | count/hr | `[0, 10000]` (Observed: `[0, 31]`) | Hardware/software errors in past hour |
| `restart_count` | `int64` | count | `[0, 10000]` (Observed: `[0, 13]`) | Cumulative reboot counter |
| `uptime_hours` | `float64` | hours | `[0.0, 50000.0]` (Observed: `[0.1, 899.7]`)| Continuous uptime since last boot |
| `firmware_version`| `string` | — | `{"1.0.0", "1.1.0", "1.2.0"}` | Firmware release version |
| `failed_within_24h`| `int64` | binary | `{0, 1}` | Target: 1 if failure in next 24h, else 0 |

---

## 3. Implementation Details

### 3.1 Synthetic Generator (`ml/data_pipeline/generate_dataset.py`)
* **Fleet Configuration:** 1,000 devices × 100 consecutive measurements = 100,000 records.
* **Deterministic Seed:** `RANDOM_SEED = 42`.
* **Physics & Degradation Equations:**
  * **Ambient Diurnal Oscillation:** $T_{\text{ambient}}(t) = 2.5 \cdot \sin(2\pi (t - 6)/24)$ °C.
  * **Degradation Factor:** For failing devices ($\sim 32\%$ of fleet), wear accelerates non-linearly:
    $$\eta(t) = \left(\frac{t - T_{\text{deg}}}{T_{\text{fail}} - T_{\text{deg}}}\right)^{1.3} \quad \text{for } t \in [T_{\text{deg}}, T_{\text{fail}}]$$
  * **Coupled Signals:**
    * $\text{Temperature}: T(t) = T_{\text{base}} + T_{\text{ambient}} + 45.0 \cdot \eta(t) + \epsilon_{\text{thermal}}$
    * $\text{Current}: I(t) = I_{\text{base}} + 1.4 \cdot \eta(t) + \epsilon_{\text{curr}}$
    * $\text{Voltage}: V(t) = V_{\text{base}} - 0.05(I - 1.0) - 0.60 \cdot \eta(t) + \epsilon_{\text{volt}} + \epsilon_{\text{instability}}$
    * $\text{Errors}: \lambda_{\text{err}} = 0.15 + 18.0 \cdot \eta(t)^{1.8} \implies \text{Poisson}(\lambda_{\text{err}})$
    * $\text{Restarts & Uptime}$: Watchdog resets trigger during high wear, resetting uptime to near-zero and incrementing `restart_count`.
* **Benchmark Calibration:**
  * `DEV-00001` at $t=0$: Normal (`temp=42.3, volt=3.71, curr=1.2, batt=91, net=96, err=1, restart=0, uptime=124.0, fw=1.0.0, failed=0`).
  * `DEV-00002` at $t=0$: Imminent Failure (`temp=88.2, volt=3.14, curr=2.7, batt=34, net=61, err=18, restart=4, uptime=823.0, fw=1.2.0, failed=1`).

### 3.2 Data Validator (`ml/data_pipeline/validate_dataset.py`)
Enforces 13 automated checks:
1. `Required Columns Present`: All 12 required columns exist.
2. `No Unexpected Columns`: Zero unknown columns.
3. `Numeric Types`: Verifies floating-point and integer types.
4. `Missing Values & Infinities`: Zero `NaN`, `NULL`, empty strings, or $\pm\infty$.
5. `Range Checks`: Physical bounds for all 8 numerical features.
6. `Primary Key Uniqueness`: All 100,000 `(device_id, timestamp)` pairs unique.
7. `Target Binary Values`: Target values restricted to $\{0, 1\}$.
8. `Target Class Distribution`: Checks positive class proportion health.
9. `ISO-8601 Parseability`: Valid datetime format parsing.
10. `Chronological Monotonicity`: Timestamps strictly ascending per device ($t_{k+1} > t_k$).

---

## 4. Quantitative Validation Results

Execution output from `python ml/data_pipeline/validate_dataset.py --strict`:

```text
================================================================================
                 DATAMIND DATASET VALIDATION REPORT
================================================================================
Dataset Path : data\sample\device_measurements.csv
Total Rows   : 100,000
Unique Devices: 1,000
--------------------------------------------------------------------------------
STATUS   | CATEGORY        | CHECK                            | DETAILS
--------------------------------------------------------------------------------
PASS     | Schema          | Required Columns Present         | All 12 required columns present
PASS     | Schema          | No Unexpected Columns            | No extraneous columns present
PASS     | Data Types      | Numeric Type: temperature        | dtype=float64
PASS     | Data Types      | Numeric Type: voltage            | dtype=float64
PASS     | Data Types      | Numeric Type: current            | dtype=float64
PASS     | Data Types      | Numeric Type: battery_level      | dtype=int64
PASS     | Data Types      | Numeric Type: network_quality    | dtype=int64
PASS     | Data Types      | Numeric Type: error_count        | dtype=int64
PASS     | Data Types      | Numeric Type: restart_count      | dtype=int64
PASS     | Data Types      | Numeric Type: uptime_hours       | dtype=float64
PASS     | Data Types      | Numeric Type: failed_within_24h  | dtype=int64
PASS     | Completeness    | Missing Values & Infinities      | Zero missing, empty, or infinite values detected
PASS     | Value Range     | Range Check: temperature         | Range [-20.0, 120.0] satisfied (observed: [31.70, 92.30])
PASS     | Value Range     | Range Check: voltage             | Range [2.0, 6.0] satisfied (observed: [2.82, 4.02])
PASS     | Value Range     | Range Check: current             | Range [0.0, 15.0] satisfied (observed: [0.82, 2.81])
PASS     | Value Range     | Range Check: battery_level       | Range [0.0, 100.0] satisfied (observed: [16.00, 98.00])
PASS     | Value Range     | Range Check: network_quality     | Range [0.0, 100.0] satisfied (observed: [54.00, 100.00])
PASS     | Value Range     | Range Check: error_count         | Range [0.0, 10000.0] satisfied (observed: [0.00, 31.00])
PASS     | Value Range     | Range Check: restart_count       | Range [0.0, 10000.0] satisfied (observed: [0.00, 13.00])
PASS     | Value Range     | Range Check: uptime_hours        | Range [0.0, 50000.0] satisfied (observed: [0.10, 899.70])
PASS     | Uniqueness      | Primary Key Uniqueness           | All (device_id, timestamp) pairs are unique
PASS     | Target Validity | Target Binary Values {0, 1}      | Distinct values: [0, 1]
PASS     | Target Validity | Target Class Distribution Balance | Positive rate = 7.35% (7352/100000)
PASS     | Timestamp       | ISO-8601 Parseability            | All timestamps conform to ISO-8601
PASS     | Timestamp       | Chronological Monotonicity       | Timestamps are strictly ascending per device
--------------------------------------------------------------------------------
Validation Outcome: ALL CRITICAL CHECKS PASSED (0 Errors, 0 Warnings)
--------------------------------------------------------------------------------
Target Distribution ('failed_within_24h'):
  Class 0 (Normal)          : 92,648 (92.65%)
  Class 1 (Imminent Failure): 7,352 (7.35%)
================================================================================
```

---

## 5. Automated Unit Tests

* **Test Suite:** [`tests/ml/test_generate_dataset.py`](file:///d:/DataMind/tests/ml/test_generate_dataset.py) (4 tests) & [`tests/ml/test_validate_dataset.py`](file:///d:/DataMind/tests/ml/test_validate_dataset.py) (9 tests).
* **Test Coverage:**
  * Seed reproducibility (seed 42 produces identical dataframes).
  * Random seed divergence.
  * Schema dimensions and required columns.
  * Filesystem saving.
  * Validation rules (missing columns, NaN injection, empty strings, out-of-bounds ranges, duplicate keys, invalid targets, non-monotonic timestamps).
* **Result:** All 13 unit tests passed in 0.49s.

---

## 6. How to Reproduce

```powershell
# Generate dataset
python ml/data_pipeline/generate_dataset.py

# Run validation pipeline
python ml/data_pipeline/validate_dataset.py --strict

# Run tests
python -m unittest discover -s tests -t . -v
```
