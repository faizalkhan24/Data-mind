# Milestone 3: Feature Engineering Pipeline

> **Milestone ID:** `M3-FEATURE-ENGINEERING`  
> **Status:** Completed  
> **Date:** 2026-10-01  
> **Git Commit:** `f7002d6 Add feature engineering pipeline, 25 predictor signals, and unit tests`  

---

## 1. Objective & Motivation

Milestone 3 translates raw instantaneous telemetry into a rich, leak-free predictive feature representation.

In real-world predictive maintenance:
* An instantaneous temperature spike might be transient load; a sustained 6-hour or 24-hour elevated mean (`temperature_mean_6h`, `temperature_mean_24h`) indicates cooling failure or thermal runaway.
* Voltage sag events (`voltage_min_6h`) and electrical noise (`voltage_std_6h`) expose failing power regulators before catastrophic brownout.
* Error bursts over 6h and 24h (`error_count_6h`, `error_count_24h`) capture memory corruption and bus instability.
* Watchdog restarts in the past 24h (`restart_count_24h`) identify reboot crash loops.
* Battery discharge velocity (`battery_change_24h`) signals rapid cell collapse.

---

## 2. Complete 25 Predictor Feature Inventory

The pipeline transforms the raw 12-column telemetry dataset into a 28-column matrix (2 identifiers, 1 target label, 25 predictor signals):

| Feature Name | Category | Window | Physical Rationale & Mathematical Formula |
| :--- | :---: | :---: | :--- |
| `temperature` | Instantaneous | 1h | Current chassis temperature measurement (°C) |
| `voltage` | Instantaneous | 1h | Current supply rail voltage (V) |
| `current` | Instantaneous | 1h | Current electrical draw (A) |
| `battery_level` | Instantaneous | 1h | Current battery state of charge (%) |
| `network_quality` | Instantaneous | 1h | Current wireless signal strength (%) |
| `error_count` | Instantaneous | 1h | Error events in current hour |
| `restart_count` | Instantaneous | Cumulative | Lifetime reboot counter |
| `uptime_hours` | Instantaneous | Current | Continuous uptime since last boot (hours) |
| `temperature_mean_6h` | Thermal Rolling | 6h | Trailing 6h smoothed temperature |
| `temperature_mean_24h` | Thermal Rolling | 24h | Trailing 24h baseline temperature |
| `temperature_std_6h` | Thermal Dynamics | 6h | Trailing 6h standard deviation (thermal stability) |
| `temperature_change_1h`| Thermal Velocity | 1h | Immediate 1h rate of change: $T(t) - T(t-1)$ |
| `voltage_mean_6h` | Electrical Rolling| 6h | Trailing 6h voltage mean |
| `voltage_min_6h` | Electrical Sag | 6h | Trailing 6h minimum voltage (brownout detector) |
| `voltage_std_6h` | Electrical Noise | 6h | Trailing 6h standard deviation (regulator instability) |
| `current_mean_6h` | Power Load | 6h | Trailing 6h average load current |
| `error_count_6h` | Fault History | 6h | Cumulative errors in trailing 6h |
| `error_count_24h` | Fault History | 24h | Cumulative errors in trailing 24h |
| `restart_count_24h` | Crash Frequency | 24h | Watchdog reboots in trailing 24h: $R(t) - R(t-24)$ |
| `battery_change_24h` | Battery Dynamics| 24h | Net discharge rate: $\text{batt}(t) - \text{batt}(t-24)$ |
| `network_quality_mean_6h`| Connectivity | 6h | Trailing 6h average link quality |
| `device_age_hours` | Longevity | Cumulative | Cumulative operational life: $U_0 + t$ |
| `firmware_version_1.0.0`| Categorical | — | One-hot indicator for firmware v1.0.0 |
| `firmware_version_1.1.0`| Categorical | — | One-hot indicator for firmware v1.1.0 |
| `firmware_version_1.2.0`| Categorical | — | One-hot indicator for firmware v1.2.0 |

---

## 3. Top Feature Correlations with Target (`failed_within_24h`)

The newly engineered features demonstrate strong, physically grounded correlations:

| Rank | Feature Name | Pearson $r$ | Predictive Role |
| :---: | :--- | :---: | :--- |
| 1 | `temperature` | $+0.7167$ | Primary thermal stress indicator |
| 2 | `current` | $+0.6985$ | Electrical draw under thermal runaway |
| 3 | `battery_change_24h` | **$-0.6911$** | Rapid 24h battery collapse strongly signals failure |
| 4 | `error_count` | $+0.6722$ | Instantaneous error surges |
| 5 | `voltage` | $-0.6639$ | Instantaneous power rail voltage drop |
| 6 | `battery_level` | $-0.6401$ | Low battery state of charge |
| 7 | `temperature_mean_6h` | $+0.5948$ | Sustained medium-term thermal load |
| 8 | `current_mean_6h` | $+0.5874$ | Sustained power dissipation |
| 9 | `network_quality` | $-0.5813$ | Transmission quality degradation |
| 10 | `error_count_6h` | $+0.5620$ | Cumulative error rate |
| 11 | `voltage_mean_6h` | $-0.5524$ | Sustained voltage depression |
| 12 | `voltage_min_6h` | $-0.5374$ | Severe voltage drop / brownout |
| 13 | `network_quality_mean_6h`| $-0.4859$ | Medium-term network throttling |
| 14 | `restart_count_24h` | $+0.3189$ | Watchdog crash loops |
| 15 | `voltage_std_6h` | $+0.3068$ | Voltage regulator electrical instability |
| 16 | `temperature_mean_24h`| $+0.3027$ | Long-term thermal baseline elevation |
| 17 | `temperature_std_6h` | $+0.2560$ | Thermal instability |
| 18 | `error_count_24h` | $+0.2418$ | 24-hour cumulative error build-up |
| 19 | `uptime_hours` | $-0.2416$ | Low uptime due to recent reboots |
| 20 | `temperature_change_1h`| $+0.2180$ | 1-hour thermal acceleration velocity |

---

## 4. Data Leakage Prevention Guarantees

The pipeline enforces 4 strict isolation principles:
1. **Per-Device Group Isolation:** All rolling aggregations and lag differences are computed strictly within each device partition (`df.groupby('device_id')`), completely preventing cross-device information bleed.
2. **Backwards-Looking Windows:** Rolling calculations use strictly backwards-facing windows (incorporating $t - W + 1$ to $t$). No forward-looking information ($\ge t+1$) is utilized.
3. **Target Isolation:** The target label `failed_within_24h` is completely excluded from feature generation.
4. **Boundary Condition Safety:** Missing lag periods at $t=0$ are safely imputed without leakage (e.g. initial `temperature_change_1h` is set to $0.0$; initial rolling std is set to $0.0$; 24h deltas for $t<24$ evaluate against the device's earliest observed state).

---

## 5. Output Artifacts Generated

* `data/processed/featured_telemetry.parquet`: High-performance columnar dataset (100,000 rows × 28 columns, 2.08 MB).
* `data/processed/featured_telemetry.csv`: Formatted CSV dataset (100,000 rows × 28 columns, 12.97 MB).
* `data/processed/feature_pipeline_metadata.json`: Feature registry and category metadata for inference serving.

---

## 6. Automated Unit Tests

* **Test Suite:** [`tests/ml/test_feature_engineering.py`](file:///d:/DataMind/tests/ml/test_feature_engineering.py) (7 tests).
* **Test Coverage:**
  * Feature names list matches the 25-feature specification.
  * Absence of nulls and infinities across transformed datasets.
  * Strict group isolation (verifying device B's first row never bleeds from device A's last row).
  * Rolling mean, min, and cumulative error mathematical accuracy.
  * One-hot firmware encoding mutual exclusivity (row sum = 1).
  * Pipeline metadata JSON serialization and loading.
  * Batch file processing (`process_dataset_file`) creating Parquet and CSV.
* **Result:** All 7 unit tests passed; total test suite stands at 24 passing tests.

---

## 7. How to Reproduce

```powershell
# Run feature engineering pipeline (generates Parquet, CSV, and metadata)
python ml/feature_engineering/pipeline.py

# Run unit tests
python -m unittest tests/ml/test_feature_engineering.py -v
```
