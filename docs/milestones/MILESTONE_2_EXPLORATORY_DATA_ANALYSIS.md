# Milestone 2: Exploratory Data Analysis & Data Profiling

> **Milestone ID:** `M2-EXPLORATORY-DATA-ANALYSIS`  
> **Status:** Completed  
> **Date:** 2026-10-01  
> **Git Commit:** `851c998 Add exploratory data analysis pipeline, visual artifacts, and report`  

---

## 1. Objective & Motivation

Milestone 2 addresses the critical pre-modeling exploratory data analysis (EDA) requirements defined in Section 12 of the DataMind specification.

The goals:
1. Answer the 10 fundamental data engineering and ML questions with concrete metrics.
2. Characterize the target variable distribution and quantify class imbalance.
3. Compute parametric (Pearson) and non-parametric (Spearman rank) feature correlations with the failure target.
4. Perform Tukey IQR outlier analysis and establish a principled preservation strategy.
5. Generate high-resolution visual diagnostic figures.
6. Formally audit data leakage risks and define cross-validation boundaries.

---

## 2. Answers to the 10 Core EDA Questions

| # | Question | Finding | Supporting Details |
| :- | :--- | :--- | :--- |
| **1** | **How many devices exist?** | **1,000 devices** | Formatted as `DEV-00001` through `DEV-01000`. |
| **2** | **How many records exist?** | **100,000 records** | Uniformly 100 hourly observations per device (4 days, 3 hours). |
| **3** | **What percentage represent failures?** | **7.35%** | 7,352 failure window records vs. 92,648 normal records. |
| **4** | **Are there missing values?** | **0 missing values** | Zero NULL, NaN, whitespace, or infinite values detected. |
| **5** | **Which features correlate with failure?** | `temperature` ($+0.72$), `current` ($+0.70$), `error_count` ($+0.67$), `voltage` ($-0.66$), `battery_level` ($-0.64$) | Strong physical coupling matching degradation dynamics. |
| **6** | **Are there outliers?** | **Yes, physically meaningful** | Outliers in `temperature` (up to 92.3°C), `error_count` (up to 31/hr), and `current` (up to 2.81A) align with actual failure states. |
| **7** | **Is the target imbalanced?** | **Yes (~12.6:1 ratio)** | 92.65% Class 0 vs. 7.35% Class 1. Evaluation must prioritize PR-AUC and F1 over raw accuracy. |
| **8** | **Are there duplicate observations?** | **0 duplicates** | Primary key `(device_id, timestamp)` is unique across all rows. |
| **9** | **Are there suspicious relationships?** | **None** | Physical laws hold: Joule heating ($I^2R$) couples temperature and current; internal resistance causes voltage droop under load; reboots decrement uptime. |
| **10** | **Is there possible data leakage?** | **Zero leakage detected** | All features represent strictly historical telemetry at timestamp $t$. No future lookahead or target proxies. |

---

## 3. Quantitative Class-Shift Comparison

Comparison between normal operating regime (**Class 0**) and the 24-hour pre-failure window (**Class 1**):

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

---

## 4. Outlier Analysis & Preservation Rationale

Using Tukey's Interquartile Range ($1.5 \times \text{IQR}$) rule:
* **Temperature:** 7,068 observations (7.07%) exceed $Q_3 + 1.5 \times \text{IQR} = 52.5^\circ\text{C}$, reaching up to 92.3°C.
* **Error Count:** 6,031 observations (6.03%) exceed 2.5 errors/hr, reaching up to 31 errors/hr.
* **Current:** 6,325 observations (6.33%) exceed 1.6A, reaching up to 2.81A.

### Engineering Decision:
These data points are **genuine physical failure symptoms**, not sensor transmission glitches or entry errors. **They must NOT be trimmed or winsorized**, as removing them would eliminate the very signal needed for early failure detection.

---

## 5. Visual Artifacts Generated

The automated EDA script (`ml/data_pipeline/eda.py`) generates 6 publication-quality figures saved in [`docs/eda/figures/`](file:///d:/DataMind/docs/eda/figures/):
* `failure_distribution.png`: Class counts bar chart and 92.65% vs 7.35% pie chart.
* `correlation_matrix.png`: Triangular correlation heatmap across all numerical features and the target.
* `feature_distributions_by_class.png`: 4x2 grid of Kernel Density Estimation (KDE) curves comparing normal and failing distributions.
* `outlier_boxplots.png`: Boxplots showing medians, quartiles, and extreme points by class.
* `time_series_device_comparison.png`: 5-panel time-series trajectories for `DEV-00001` (healthy) vs `DEV-00002` (failing).
* `firmware_breakdown.png`: Volume and failure rate breakdown across firmware versions (uniformly ~7.3%).

---

## 6. Data Leakage Assessment & Modeling Safeguards

1. **Information Horizon:** Features at observation time $t$ reflect exclusively telemetry observed at or before $t$.
2. **Cross-Validation Split Strategy:**
   * **Do NOT use random K-Fold:** Splitting rows randomly causes temporal leakage and device autocorrelation bleed.
   * **Required Strategy:** **GroupKFold** or explicit train/val/test splits partitioned **by device ID** (e.g. 700 devices train, 150 devices val, 150 devices test) or temporal cutoff splits.

---

## 7. How to Reproduce

```powershell
# Run automated EDA pipeline (regenerates figures and eda_report.md)
python ml/data_pipeline/eda.py

# Run unit tests
python -m unittest tests/ml/test_eda.py -v
```
