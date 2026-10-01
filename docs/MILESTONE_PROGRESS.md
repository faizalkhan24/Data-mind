# DataMind: Development Progress & Milestone Documentation

> **Status:** Milestones 1 and 2 Complete  
> **Repository:** `https://github.com/faizalkhan24/Data-mind.git`  
> **Environment:** Python 3.11.9 (`.venv`) on Windows  
> **Last Updated:** 2026-10-01  

---

## 1. Project Context & Objectives

**DataMind** is an enterprise-grade predictive intelligence platform designed to demonstrate end-to-end software engineering, data engineering, and machine learning capabilities.

The initial use case is:
> **Predict whether an IoT device will experience an operational failure within the next 24 hours (`failed_within_24h`).**

The platform emphasizes production rigor:
* **Physics-grounded data generation** rather than naive random noise.
* **Pre-ML data quality assurance** with automated schema, range, null, uniqueness, and temporal checks.
* **Strict data leakage prevention** ensuring features at time $t$ contain only information available up to time $t$.
* **Exhaustive testing** with automated unit tests for every data pipeline module.
* **Traceable Git versioning** with clear, atomic commit histories.

---

## 2. Milestone 1: Data Generation & Validation Foundation

### 2.1 Technical Objective
Construct a deterministic, physically grounded telemetry simulator capable of generating 100,000 realistic IoT telemetry records across 1,000 devices over 100 consecutive hourly timestamps, paired with an automated data validation pipeline that verifies data integrity before any model training occurs.

### 2.2 Telemetry Schema Specification
Each observation corresponds to an hourly reading for a device adhering to the following schema:

| Column Name | Data Type | Physical Units | Operational Range | Description |
| :--- | :---: | :---: | :---: | :--- |
| `device_id` | `string` | — | `DEV-00001` – `DEV-01000` | Unique hardware device identifier |
| `timestamp` | `string` | ISO-8601 | `2026-01-01T00:00:00` – `2026-01-05T03:00:00` | Hourly observation timestamp |
| `temperature` | `float64` | °C | `[31.7, 92.3]` | Operating chassis / die temperature |
| `voltage` | `float64` | V | `[2.82, 4.02]` | Power rail voltage (nominal 3.7–4.0V) |
| `current` | `float64` | A | `[0.82, 2.81]` | Current draw (nominal 1.0–1.4A) |
| `battery_level` | `int64` | % | `[16, 98]` | State of charge |
| `network_quality`| `int64` | % | `[54, 100]` | Wireless link quality metric |
| `error_count` | `int64` | count/hr | `[0, 31]` | Hardware/software error events in past hour |
| `restart_count` | `int64` | count | `[0, 13]` | Cumulative watchdog / manual restarts |
| `uptime_hours` | `float64` | hours | `[0.1, 899.7]` | Uninterrupted uptime since last restart |
| `firmware_version`| `string` | — | `{"1.0.0", "1.1.0", "1.2.0"}` | Firmware release version |
| `failed_within_24h`| `int64` | binary | `{0, 1}` | Ground truth target (1 if failure in $(t, t+24\text{h}]$) |

### 2.3 Physical Modeling Implementation (`ml/data_pipeline/generate_dataset.py`)
Rather than assigning target labels randomly, the generator simulates degradation physics:
1. **Diurnal Ambient Fluctuation:** Ambient temperature cycles according to $2.5 \times \sin(2\pi (t - 6)/24)$ °C.
2. **Healthy vs. Degraded Regimes:** 
   * **Healthy devices (~68% of fleet):** Exhibit stable nominal values, low Poisson error rates ($\lambda \approx 0.15$), and uninterrupted uptime accumulation.
   * **Failing devices (~32% of fleet):** Undergo a non-linear wear curve $\eta(t) = ((t - T_{\text{deg}}) / (T_{\text{fail}} - T_{\text{deg}}))^{1.3}$ leading into an impending failure at $T_{\text{fail}}$.
3. **Coupled Physical Degradation Signals:**
   * **Thermal Runaway:** Internal resistance and heavy processing increase die temperature by up to $+45^\circ\text{C}$ ($\sim 75^\circ\text{C} - 92^\circ\text{C}$).
   * **Current Spike:** Thermal throttling and circuit stress elevate current draw toward $2.4\text{A} - 2.8\text{A}$.
   * **Voltage Sag & Instability:** Higher current draw causes internal IR drops and battery voltage collapse down to $2.8\text{V} - 3.2\text{V}$, with increased electrical noise.
   * **Error Acceleration:** Thermal noise and under-voltage trigger accelerated bit-flips and bus timeouts, with error counts surging via Poisson rate $\lambda_{\text{err}} = 0.15 + 18 \times \eta(t)^{1.8}$ (up to 31 errors/hr).
   * **Watchdog Restarts & Uptime Resets:** Severe stress triggers watchdog crash loops; `restart_count` increments and `uptime_hours` resets to near zero.
4. **Target Ground Truth & No Leakage:**
   * $\text{failed\_within\_24h}(t) = 1$ if and only if $0 < T_{\text{fail}} - t \le 24\text{ hours}$.
   * Telemetry at time $t$ is calculated exclusively from the physical state at time $t$, preserving absolute temporal integrity.
5. **Determinism:** Seeded with `RANDOM_SEED = 42` for exact reproducibility across environments.

### 2.4 Data Validation Engine (`ml/data_pipeline/validate_dataset.py`)
A production-grade validator enforces 13 critical data quality checks:
* **Schema Verification:** Ensures all 12 required columns exist with exact naming, expected numeric/string types, and zero extra columns.
* **Completeness:** Audits for `NULL`, `NaN`, whitespace-only strings, and $\pm\infty$ across all columns.
* **Physical Range Boundaries:** Enforces operational constraints (e.g. temperature in $[-20, 120]^\circ\text{C}$, voltage in $[2.0, 6.0]\text{V}$, battery in $[0, 100]\%$).
* **Primary Key Uniqueness:** Verifies zero duplicate `(device_id, timestamp)` pairs.
* **Target Integrity:** Verifies binary values $\{0, 1\}$ and checks class balance.
* **Chronological Monotonicity:** Verifies ISO-8601 formatting and ensures timestamps strictly increment ($t_{k+1} > t_k$) per device.

### 2.5 Validation Results Summary
* **Records Evaluated:** 100,000 records across 1,000 devices.
* **Critical Check Result:** **13/13 PASSED (0 Errors, 0 Warnings)**.
* **Target Class Distribution:**
  * Class `0` (Normal): 92,648 records (**92.65%**)
  * Class `1` (Imminent Failure): 7,352 records (**7.35%**)

---

## 3. Milestone 2: Exploratory Data Analysis & Data Profiling

### 3.1 Technical Objective
Conduct a thorough statistical audit of the telemetry fleet, examine feature-target correlations, investigate anomaly distributions, assess data leakage risks, and generate visual documentation answering all 10 core analytical questions from Section 12 of the project specification.

### 3.2 Answers to the 10 Core EDA Questions

| # | Question | Finding | Empirical Detail |
| :- | :--- | :--- | :--- |
| **1** | **How many devices exist?** | **1,000 devices** | IDs: `DEV-00001` through `DEV-01000`. |
| **2** | **How many records exist?** | **100,000 records** | Exactly 100 hourly records per device spanning 4 days and 3 hours. |
| **3** | **What percentage represent failures?** | **7.35%** | 7,352 failure window records vs. 92,648 normal records. |
| **4** | **Are there missing values?** | **0 missing values** | Zero NULLs, NaNs, empty strings, or infinite values in the entire matrix. |
| **5** | **Which features correlate with failure?** | `temperature` ($+0.72$), `current` ($+0.70$), `error_count` ($+0.67$), `voltage` ($-0.66$), `battery_level` ($-0.64$) | Strong physical coupling between thermal, electrical, and computational indicators. |
| **6** | **Are there outliers?** | **Yes, physically meaningful** | Extreme values (temp up to 92.3°C, errors up to 31/hr) reflect failure dynamics, not bad data. |
| **7** | **Is the target imbalanced?** | **Yes (~12.6:1 ratio)** | 92.65% Class 0 vs. 7.35% Class 1; precision-recall optimization (PR-AUC) required. |
| **8** | **Are there duplicate observations?** | **0 duplicates** | Primary key `(device_id, timestamp)` is unique across all rows. |
| **9** | **Are there suspicious relationships?** | **None** | Physical laws hold: Joule heating ($I^2R$) couples temperature and current; internal resistance causes voltage droop under load; reboots decrement uptime. |
| **10** | **Is there possible data leakage?** | **Zero leakage detected** | All features represent strictly historical telemetry at timestamp $t$. No future lookahead or target proxies. |

### 3.3 Quantitative Class Segregation Comparison

| Feature | Class 0 Mean ± Std (Normal) | Class 1 Mean ± Std (Failing) | Shift (Class 1 - Class 0) | Pearson $r$ |
| :--- | :---: | :---: | :---: | :---: |
| `temperature` | $42.08 \pm 3.97^\circ\text{C}$ | $62.43 \pm 12.84^\circ\text{C}$ | **$+20.35^\circ\text{C}$** | $+0.7167$ |
| `current` | $1.24 \pm 0.14\text{ A}$ | $1.87 \pm 0.40\text{ A}$ | **$+0.64\text{ A}$** | $+0.6985$ |
| `error_count` | $0.28 \pm 0.63\text{ /hr}$ | $6.06 \pm 5.71\text{ /hr}$ | **$+5.78\text{ /hr}$** | $+0.6722$ |
| `voltage` | $3.77 \pm 0.07\text{ V}$ | $3.47 \pm 0.20\text{ V}$ | **$-0.30\text{ V}$** | $-0.6639$ |
| `battery_level` | $83.03 \pm 6.48\%$ | $58.59 \pm 16.37\%$ | **$-24.44\%$** | $-0.6401$ |
| `network_quality`| $90.83 \pm 4.44\%$ | $77.28 \pm 9.20\%$ | **$-13.55\%$** | $-0.5813$ |
| `uptime_hours` | $439.85 \pm 248.24\text{ h}$ | $200.15 \pm 286.15\text{ h}$ | **$-239.69\text{ h}$** | $-0.2416$ |
| `restart_count` | $0.95 \pm 2.53$ | $2.32 \pm 2.55$ | **$+1.37$** | $+0.1396$ |

### 3.4 Key Engineering Findings from EDA
1. **Outlier Preservation:** Tukey IQR analysis identified 7.07% of `temperature` values and 6.03% of `error_count` values as statistical outliers. Crucially, these outliers are concentrated almost entirely in Class 1 observations. **They must not be removed or clipped**, as they represent the primary diagnostic signal of device failure.
2. **Firmware Neutrality:** Failure rates across firmware versions `1.0.0` (7.31%), `1.1.0` (7.42%), and `1.2.0` (7.33%) are evenly distributed, confirming no single firmware version introduces artificial bias.
3. **Leakage & Validation Guardrails:**
   * At inference time, only measurements up to current time $T$ are available.
   * Model training cannot use simple random k-fold cross validation due to device-level temporal autocorrelation. Models must be evaluated using **grouped device-level splits** or **chronological train/test splits**.

### 3.5 Generated Visual Artifacts (`docs/eda/figures/`)
* [`failure_distribution.png`](file:///d:/DataMind/docs/eda/figures/failure_distribution.png): Visualizes class frequency and percentage breakdown.
* [`correlation_matrix.png`](file:///d:/DataMind/docs/eda/figures/correlation_matrix.png): Triangular correlation heatmap across all numerical features and the target.
* [`feature_distributions_by_class.png`](file:///d:/DataMind/docs/eda/figures/feature_distributions_by_class.png): Kernel Density Estimation (KDE) comparing Normal vs. Failing feature profiles.
* [`outlier_boxplots.png`](file:///d:/DataMind/docs/eda/figures/outlier_boxplots.png): Boxplots illustrating IQR spans, medians, and anomaly distributions.
* [`time_series_device_comparison.png`](file:///d:/DataMind/docs/eda/figures/time_series_device_comparison.png): 5-panel side-by-side time series trajectory comparing `DEV-00001` (healthy) and `DEV-00002` (failing).
* [`firmware_breakdown.png`](file:///d:/DataMind/docs/eda/figures/firmware_breakdown.png): Bar charts of fleet volume and failure frequency by firmware release.

---

## 4. Comprehensive File Inventory & Changes

Below is the complete tree of files introduced in Milestones 1 and 2:

```text
D:\DataMind
│
├── .gitignore                                      # Updated to ignore large sample data CSVs
│
├── data/
│   ├── raw/.gitkeep                                # Tracked directory placeholder
│   ├── processed/.gitkeep                          # Tracked directory placeholder
│   └── sample/
│       ├── .gitkeep                                # Tracked directory placeholder
│       └── device_measurements.csv                 # Generated synthetic telemetry (git-ignored, 6.64 MB)
│
├── docs/
│   ├── MILESTONE_PROGRESS.md                       # Comprehensive milestone progress document (this file)
│   └── eda/
│       ├── eda_report.md                           # Detailed 10-question EDA report
│       └── figures/
│           ├── correlation_matrix.png              # Correlation heatmap
│           ├── failure_distribution.png            # Class distribution chart
│           ├── feature_distributions_by_class.png  # KDE distribution comparison
│           ├── firmware_breakdown.png              # Firmware comparison chart
│           ├── outlier_boxplots.png                # Tukey IQR outlier boxplots
│           └── time_series_device_comparison.png   # 100-hour device comparison
│
├── ml/
│   ├── __init__.py                                 # ML package initialization
│   └── data_pipeline/
│       ├── __init__.py                             # Data pipeline subpackage initialization
│       ├── generate_dataset.py                     # Synthetic telemetry generator (seed 42)
│       ├── validate_dataset.py                     # Comprehensive dataset validation pipeline
│       └── eda.py                                  # Automated EDA engine and chart generator
│
└── tests/
    ├── __init__.py                                 # Test root initialization
    └── ml/
        ├── __init__.py                             # ML test subpackage initialization
        ├── test_generate_dataset.py                # 4 unit tests for dataset generation
        ├── test_validate_dataset.py                # 9 unit tests for dataset validation
        └── test_eda.py                             # 4 unit tests for EDA engine
```

---

## 5. Automated Test Suite Verification

Every module is covered by automated unit tests running under standard Python `unittest`:

```text
tests.ml.test_generate_dataset
  - test_deterministic_reproducibility: Verifies identical output with seed 42. [OK]
  - test_different_seeds_produce_different_data: Verifies seed divergence. [OK]
  - test_save_dataset: Verifies CSV filesystem serialization. [OK]
  - test_shape_and_columns: Verifies dimensions and schema. [OK]

tests.ml.test_validate_dataset
  - test_valid_dataset_passes: Verifies clean dataset passes all 13 checks. [OK]
  - test_missing_column_fails: Detects dropped required column. [OK]
  - test_null_value_fails: Detects NaN/null introduction. [OK]
  - test_empty_string_fails: Detects empty string values. [OK]
  - test_out_of_range_temperature_fails: Flags unrealistic temperature values (>120°C). [OK]
  - test_out_of_range_battery_fails: Flags battery values >100%. [OK]
  - test_duplicate_primary_keys_fail: Detects duplicate (device_id, timestamp). [OK]
  - test_non_binary_target_fails: Detects invalid target values (e.g. 2). [OK]
  - test_non_monotonic_timestamps_fail: Flags disordered timestamps. [OK]

tests.ml.test_eda
  - test_compute_overview: Verifies overview calculation accuracy. [OK]
  - test_compute_correlations: Verifies Pearson and Spearman computation. [OK]
  - test_compute_outliers: Verifies IQR outlier statistics. [OK]
  - test_full_pipeline_artifacts: Verifies report and all 6 figure files exist. [OK]

----------------------------------------------------------------------
Ran 17 tests in 6.480s — ALL 17 TESTS PASSED (OK)
```

---

## 6. How to Reproduce All Steps

To reproduce all dataset generation, validation, EDA, and test execution steps locally:

```powershell
# Step 1: Activate the Python 3.11 virtual environment
.venv\Scripts\activate

# Step 2: Generate the synthetic telemetry dataset
python ml\data_pipeline\generate_dataset.py

# Step 3: Run the data validation pipeline with strict error checking
python ml\data_pipeline\validate_dataset.py --strict

# Step 4: Execute the EDA pipeline to refresh reports and figures
python ml\data_pipeline\eda.py

# Step 5: Run the entire test suite
python -m unittest discover -s tests -t . -v
```

---

## 7. Git Commit History for Milestones 1 & 2

The repository preserves atomic, descriptive commit messages:

```text
851c998 Add exploratory data analysis pipeline, visual artifacts, and report
8ad82d2 Add synthetic device dataset generator and validation pipeline
1ad4b30 Initial DataMind project structure
9dbcf22 first commit
```

---

## 8. Next Step: Milestone 3 (Feature Engineering Pipeline)

With raw telemetry thoroughly validated and profiled, **Milestone 3** will implement the feature engineering pipeline (`ml/feature_engineering/pipeline.py`):
1. **Rolling Temporal Windows (1h, 6h, 24h):**
   * Trailing means: `temperature_mean_1h`, `temperature_mean_6h`, `temperature_mean_24h`
   * Volatility: `temperature_std_6h`
   * Short-term velocity: `temperature_change_1h` ($\Delta T / \Delta t$)
   * Voltage stability: `voltage_mean_6h`, `voltage_min_6h` (brownout detector)
   * Error accumulation: `error_count_1h`, `error_count_6h`, `error_count_24h`
   * Watchdog frequency: `restart_count_24h`
   * Battery drain velocity: `battery_change_24h`
   * Signal stability: `network_quality_mean_6h`
2. **Categorical Encoders:** One-hot / frequency encoding for `firmware_version`.
3. **Leakage-Free Execution:** Trailing windows calculated strictly on closed backwards-looking intervals (`closed='left'` / `closed='both'`).
4. **Automated Unit Tests:** Verifying feature calculation accuracy and boundary conditions.
