"""DataMind Telemetry Dataset Validator.

Performs comprehensive data quality and schema validation on device telemetry
datasets before feature engineering or model training.

Validation Categories:
1. Schema integrity (column names, required columns, expected types).
2. Missing values (NULL, NaN, whitespace, infinite values).
3. Value ranges (physical bounds, operational constraints).
4. Uniqueness (composite primary key: device_id + timestamp).
5. Target integrity (binary values {0, 1}, distribution health).
6. Timestamp validity (ISO format, strict monotonicity per device).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Set

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS: List[str] = [
    "device_id",
    "timestamp",
    "temperature",
    "voltage",
    "current",
    "battery_level",
    "network_quality",
    "error_count",
    "restart_count",
    "uptime_hours",
    "firmware_version",
    "failed_within_24h",
]

NUMERIC_COLUMNS: List[str] = [
    "temperature",
    "voltage",
    "current",
    "battery_level",
    "network_quality",
    "error_count",
    "restart_count",
    "uptime_hours",
    "failed_within_24h",
]

# Physical and operational valid range definitions
RANGE_RULES: Dict[str, Dict[str, float]] = {
    "temperature": {"min": -20.0, "max": 120.0},
    "voltage": {"min": 2.0, "max": 6.0},
    "current": {"min": 0.0, "max": 15.0},
    "battery_level": {"min": 0.0, "max": 100.0},
    "network_quality": {"min": 0.0, "max": 100.0},
    "error_count": {"min": 0.0, "max": 10000.0},
    "restart_count": {"min": 0.0, "max": 10000.0},
    "uptime_hours": {"min": 0.0, "max": 50000.0},
}


@dataclass
class CheckResult:
    """Outcome of a single validation check."""

    category: str
    check_name: str
    passed: bool
    details: str
    violations: int = 0
    severity: str = "ERROR"  # 'ERROR' or 'WARNING'


@dataclass
class ValidationSummary:
    """Aggregated report of all dataset validation checks."""

    dataset_path: str
    total_records: int
    num_devices: int
    checks: List[CheckResult] = field(default_factory=list)
    feature_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    target_distribution: Dict[str, Any] = field(default_factory=dict)
    correlations: Dict[str, float] = field(default_factory=dict)

    @property
    def passed_all_critical(self) -> bool:
        """True if zero ERROR-level checks failed."""
        return all(c.passed for c in self.checks if c.severity == "ERROR")

    @property
    def total_errors(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "ERROR")

    @property
    def total_warnings(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "WARNING")


class DatasetValidator:
    """Validates telemetry datasets against schema, range, and temporal constraints."""

    def __init__(self, df: pd.DataFrame, source_path: str = "in-memory") -> None:
        self.df = df.copy()
        self.source_path = source_path
        self.checks: List[CheckResult] = []

    def validate_schema(self) -> None:
        """Validates that all required columns are present and correctly named."""
        actual_cols = list(self.df.columns)
        missing = [c for c in REQUIRED_COLUMNS if c not in actual_cols]
        extra = [c for c in actual_cols if c not in REQUIRED_COLUMNS]

        if missing:
            self.checks.append(
                CheckResult(
                    category="Schema",
                    check_name="Required Columns Present",
                    passed=False,
                    details=f"Missing columns: {missing}",
                    violations=len(missing),
                    severity="ERROR",
                )
            )
        else:
            self.checks.append(
                CheckResult(
                    category="Schema",
                    check_name="Required Columns Present",
                    passed=True,
                    details=f"All {len(REQUIRED_COLUMNS)} required columns present",
                    violations=0,
                )
            )

        if extra:
            self.checks.append(
                CheckResult(
                    category="Schema",
                    check_name="No Unexpected Columns",
                    passed=False,
                    details=f"Extra columns found: {extra}",
                    violations=len(extra),
                    severity="WARNING",
                )
            )
        else:
            self.checks.append(
                CheckResult(
                    category="Schema",
                    check_name="No Unexpected Columns",
                    passed=True,
                    details="No extraneous columns present",
                    violations=0,
                )
            )

        # Type checks on available numeric columns
        for col in NUMERIC_COLUMNS:
            if col in self.df.columns:
                is_num = pd.api.types.is_numeric_dtype(self.df[col])
                self.checks.append(
                    CheckResult(
                        category="Data Types",
                        check_name=f"Numeric Type: {col}",
                        passed=is_num,
                        details=f"dtype={self.df[col].dtype}",
                        violations=0 if is_num else 1,
                        severity="ERROR" if not is_num else "ERROR",
                    )
                )

    def validate_missing_values(self) -> None:
        """Detects NULL, NaN, empty strings, and infinite numbers."""
        total_missing = 0
        missing_by_col = {}

        for col in self.df.columns:
            # Null or NaN
            null_count = int(self.df[col].isna().sum())

            # Whitespace / empty string if string column
            empty_count = 0
            if pd.api.types.is_string_dtype(self.df[col]) or pd.api.types.is_object_dtype(
                self.df[col]
            ):
                empty_count = int(
                    self.df[col].astype(str).str.strip().eq("").sum()
                )

            # Inf / -Inf if numeric column
            inf_count = 0
            if pd.api.types.is_numeric_dtype(self.df[col]):
                inf_count = int(np.isinf(self.df[col]).sum())

            col_issues = null_count + empty_count + inf_count
            if col_issues > 0:
                missing_by_col[col] = {
                    "nulls": null_count,
                    "empty": empty_count,
                    "inf": inf_count,
                }
                total_missing += col_issues

        passed = total_missing == 0
        details = (
            "Zero missing, empty, or infinite values detected"
            if passed
            else f"Issues found: {missing_by_col}"
        )
        self.checks.append(
            CheckResult(
                category="Completeness",
                check_name="Missing Values & Infinities",
                passed=passed,
                details=details,
                violations=total_missing,
                severity="ERROR",
            )
        )

    def validate_ranges(self) -> None:
        """Validates that numerical values fall within realistic physical ranges."""
        for col, rules in RANGE_RULES.items():
            if col not in self.df.columns:
                continue

            min_val, max_val = rules["min"], rules["max"]
            series = self.df[col].dropna()
            out_of_bounds = (series < min_val) | (series > max_val)
            violation_count = int(out_of_bounds.sum())

            passed = violation_count == 0
            details = (
                f"Range [{min_val}, {max_val}] satisfied (observed: [{series.min():.2f}, {series.max():.2f}])"
                if passed
                else f"{violation_count} values outside [{min_val}, {max_val}]"
            )

            self.checks.append(
                CheckResult(
                    category="Value Range",
                    check_name=f"Range Check: {col}",
                    passed=passed,
                    details=details,
                    violations=violation_count,
                    severity="ERROR",
                )
            )

    def validate_uniqueness(self) -> None:
        """Checks for duplicate primary key combinations (device_id + timestamp)."""
        if "device_id" not in self.df.columns or "timestamp" not in self.df.columns:
            return

        duplicates = int(self.df.duplicated(subset=["device_id", "timestamp"]).sum())
        passed = duplicates == 0
        details = (
            "All (device_id, timestamp) pairs are unique"
            if passed
            else f"{duplicates} duplicate (device_id, timestamp) records found"
        )
        self.checks.append(
            CheckResult(
                category="Uniqueness",
                check_name="Primary Key Uniqueness",
                passed=passed,
                details=details,
                violations=duplicates,
                severity="ERROR",
            )
        )

    def validate_target(self) -> None:
        """Validates that the target variable is strictly binary and well-distributed."""
        if "failed_within_24h" not in self.df.columns:
            return

        target_series = self.df["failed_within_24h"].dropna()
        unique_vals = set(target_series.unique())
        valid_vals = {0, 1}

        is_binary = unique_vals.issubset(valid_vals)
        invalid_count = int((~target_series.isin(valid_vals)).sum())

        self.checks.append(
            CheckResult(
                category="Target Validity",
                check_name="Target Binary Values {0, 1}",
                passed=is_binary,
                details=f"Distinct values: {sorted(list(unique_vals))}",
                violations=invalid_count,
                severity="ERROR",
            )
        )

        # Check positive rate distribution health
        pos_rate = float(target_series.mean())
        # Alert if degenerate (<0.5% or >50%)
        is_healthy_rate = 0.005 <= pos_rate <= 0.50
        self.checks.append(
            CheckResult(
                category="Target Validity",
                check_name="Target Class Distribution Balance",
                passed=is_healthy_rate,
                details=f"Positive rate = {pos_rate * 100:.2f}% ({int(target_series.sum())}/{len(target_series)})",
                violations=0 if is_healthy_rate else 1,
                severity="WARNING" if not is_healthy_rate else "ERROR",
            )
        )

    def validate_timestamps(self) -> None:
        """Validates timestamp formatting, parsing, and strict chronological ordering per device."""
        if "device_id" not in self.df.columns or "timestamp" not in self.df.columns:
            return

        # Check ISO parsing
        try:
            parsed_ts = pd.to_datetime(self.df["timestamp"], format="ISO8601")
            self.checks.append(
                CheckResult(
                    category="Timestamp",
                    check_name="ISO-8601 Parseability",
                    passed=True,
                    details="All timestamps conform to ISO-8601",
                    violations=0,
                )
            )
        except Exception as exc:
            self.checks.append(
                CheckResult(
                    category="Timestamp",
                    check_name="ISO-8601 Parseability",
                    passed=False,
                    details=f"Timestamp parsing failed: {exc}",
                    violations=len(self.df),
                    severity="ERROR",
                )
            )
            return

        # Check strictly monotonic increasing per device
        temp_df = pd.DataFrame(
            {"device_id": self.df["device_id"], "parsed_ts": parsed_ts}
        )
        non_monotonic_devices = 0

        for dev_id, group in temp_df.groupby("device_id", sort=False):
            diffs = group["parsed_ts"].diff().dropna()
            # Must be strictly positive
            if (diffs <= pd.Timedelta(0)).any():
                non_monotonic_devices += 1

        passed_monotonic = non_monotonic_devices == 0
        self.checks.append(
            CheckResult(
                category="Timestamp",
                check_name="Chronological Monotonicity",
                passed=passed_monotonic,
                details=(
                    "Timestamps are strictly ascending per device"
                    if passed_monotonic
                    else f"{non_monotonic_devices} devices have non-monotonic timestamps"
                ),
                violations=non_monotonic_devices,
                severity="ERROR",
            )
        )

    def compute_summary_stats(self) -> ValidationSummary:
        """Computes feature statistics, target distribution, and correlations."""
        total_rows = len(self.df)
        num_devices = int(self.df["device_id"].nunique()) if "device_id" in self.df.columns else 0

        feature_stats: Dict[str, Dict[str, float]] = {}
        for col in NUMERIC_COLUMNS:
            if col in self.df.columns:
                s = self.df[col].dropna()
                feature_stats[col] = {
                    "mean": float(s.mean()),
                    "std": float(s.std()),
                    "min": float(s.min()),
                    "p25": float(s.quantile(0.25)),
                    "median": float(s.median()),
                    "p75": float(s.quantile(0.75)),
                    "max": float(s.max()),
                }

        target_dist: Dict[str, Any] = {}
        correlations: Dict[str, float] = {}
        if "failed_within_24h" in self.df.columns:
            counts = self.df["failed_within_24h"].value_counts().to_dict()
            target_dist = {
                "count_0": int(counts.get(0, 0)),
                "count_1": int(counts.get(1, 0)),
                "rate_1": float(counts.get(1, 0) / max(1, total_rows)),
            }
            corr_series = self.df.corr(numeric_only=True)["failed_within_24h"]
            correlations = {k: round(float(v), 4) for k, v in corr_series.items()}

        return ValidationSummary(
            dataset_path=self.source_path,
            total_records=total_rows,
            num_devices=num_devices,
            checks=self.checks,
            feature_stats=feature_stats,
            target_distribution=target_dist,
            correlations=correlations,
        )

    def run_all(self) -> ValidationSummary:
        """Runs the complete validation test suite."""
        self.validate_schema()
        self.validate_missing_values()
        self.validate_ranges()
        self.validate_uniqueness()
        self.validate_target()
        self.validate_timestamps()
        return self.compute_summary_stats()


def print_report(summary: ValidationSummary) -> None:
    """Prints a formatted ASCII validation report."""
    print("=" * 80)
    print("                 DATAMIND DATASET VALIDATION REPORT")
    print("=" * 80)
    print(f"Dataset Path : {summary.dataset_path}")
    print(f"Total Rows   : {summary.total_records:,}")
    print(f"Unique Devices: {summary.num_devices:,}")
    print("-" * 80)
    print(f"{'STATUS':<8} | {'CATEGORY':<15} | {'CHECK':<32} | {'DETAILS'}")
    print("-" * 80)

    for c in summary.checks:
        status_str = "PASS" if c.passed else f"FAIL ({c.severity})"
        print(f"{status_str:<8} | {c.category:<15} | {c.check_name:<32} | {c.details}")

    print("-" * 80)
    print(
        f"Validation Outcome: {'ALL CRITICAL CHECKS PASSED' if summary.passed_all_critical else 'VALIDATION FAILED'}"
    )
    print(f"Total Errors: {summary.total_errors} | Total Warnings: {summary.total_warnings}")
    print("-" * 80)

    if summary.target_distribution:
        td = summary.target_distribution
        print("Target Distribution ('failed_within_24h'):")
        print(f"  Class 0 (Normal)          : {td.get('count_0', 0):,} ({100 - td.get('rate_1', 0)*100:.2f}%)")
        print(f"  Class 1 (Imminent Failure): {td.get('count_1', 0):,} ({td.get('rate_1', 0)*100:.2f}%)")
        print("-" * 80)

    if summary.correlations:
        print("Feature Correlations with Target ('failed_within_24h'):")
        for feat, corr_val in sorted(summary.correlations.items(), key=lambda x: abs(x[1]), reverse=True):
            if feat != "failed_within_24h":
                direction = "(+)" if corr_val > 0 else "(-)"
                print(f"  {feat:<20}: {corr_val:>7.4f} {direction}")
        print("-" * 80)

    print("Numeric Feature Ranges:")
    print(f"{'FEATURE':<18} | {'MIN':>8} | {'MEAN':>8} | {'MEDIAN':>8} | {'MAX':>8} | {'STD':>8}")
    print("-" * 80)
    for feat, stats in summary.feature_stats.items():
        if feat != "failed_within_24h":
            print(
                f"{feat:<18} | {stats['min']:>8.2f} | {stats['mean']:>8.2f} | {stats['median']:>8.2f} | {stats['max']:>8.2f} | {stats['std']:>8.2f}"
            )
    print("=" * 80)


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate telemetry dataset quality, schema, and operational bounds."
    )
    parser.add_argument(
        "--input-path",
        type=str,
        default="data/sample/device_measurements.csv",
        help="Path to CSV file to validate (default: data/sample/device_measurements.csv)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero exit code if any error check fails.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point for dataset validation."""
    args = parse_args()
    path = Path(args.input_path)

    if not path.exists():
        logger.error("Dataset file not found at: %s", path.resolve())
        sys.exit(1)

    logger.info("Loading dataset from %s...", path.resolve())
    df = pd.read_csv(path)

    validator = DatasetValidator(df, source_path=str(path))
    summary = validator.run_all()
    print_report(summary)

    if args.strict and not summary.passed_all_critical:
        sys.exit(1)


if __name__ == "__main__":
    main()
