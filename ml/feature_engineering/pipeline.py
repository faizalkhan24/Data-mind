"""DataMind Feature Engineering Pipeline.

Transforms raw device telemetry into structured, leakage-free predictive features
for machine learning model training and inference.

Key Capabilities:
1. Temporal Multi-Window Rolling Aggregations (1h, 6h, 24h trailing windows).
2. Rate-of-Change and Volatility Metrics (velocity, standard deviation, min/max).
3. Watchdog Restart & Battery Discharge Dynamics.
4. Categorical Encoding for Firmware Versions.
5. Strict Data Leakage Prevention:
   - Rolling calculations are grouped strictly by 'device_id'.
   - Windows look strictly backward (closed='left' / closed='both').
   - Independent of target variable 'failed_within_24h'.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Core predictor feature column names (excluding identifiers and target)
PREDICTOR_FEATURE_NAMES: List[str] = [
    # Instantaneous physical signals
    "temperature",
    "voltage",
    "current",
    "battery_level",
    "network_quality",
    "error_count",
    "restart_count",
    "uptime_hours",
    # Rolling thermal metrics
    "temperature_mean_6h",
    "temperature_mean_24h",
    "temperature_std_6h",
    "temperature_change_1h",
    # Rolling electrical & power metrics
    "voltage_mean_6h",
    "voltage_min_6h",
    "voltage_std_6h",
    "current_mean_6h",
    # Fault acceleration & restart metrics
    "error_count_6h",
    "error_count_24h",
    "restart_count_24h",
    # Battery & connectivity metrics
    "battery_change_24h",
    "network_quality_mean_6h",
    # Operational longevity
    "device_age_hours",
    # Encoded firmware categories
    "firmware_version_1.0.0",
    "firmware_version_1.1.0",
    "firmware_version_1.2.0",
]


class FeatureEngineeringPipeline:
    """Transforms raw IoT telemetry data into engineered feature representations."""

    def __init__(self, known_firmware_versions: Optional[List[str]] = None) -> None:
        self.known_firmware_versions = known_firmware_versions or [
            "1.0.0",
            "1.1.0",
            "1.2.0",
        ]
        self.is_fitted = False

    def fit(self, df: pd.DataFrame, y: Optional[Any] = None) -> FeatureEngineeringPipeline:
        """Fits the pipeline by inspecting firmware categories from the data."""
        if "firmware_version" in df.columns:
            observed_versions = sorted(
                list(df["firmware_version"].dropna().unique().astype(str))
            )
            # Combine known with any observed
            self.known_firmware_versions = sorted(
                list(set(self.known_firmware_versions).union(observed_versions))
            )
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforms raw telemetry records into engineered features.

        Calculates backward-looking rolling statistics per device without data leakage.
        """
        # Ensure working copy sorted by (device_id, timestamp)
        df_sorted = df.copy()
        if "timestamp" in df_sorted.columns:
            df_sorted["parsed_timestamp"] = pd.to_datetime(
                df_sorted["timestamp"], format="ISO8601"
            )
            df_sorted = df_sorted.sort_values(
                by=["device_id", "parsed_timestamp"]
            ).reset_index(drop=True)
            df_sorted = df_sorted.drop(columns=["parsed_timestamp"])
        else:
            df_sorted = df_sorted.sort_values(by=["device_id"]).reset_index(drop=True)

        grouped = df_sorted.groupby("device_id", sort=False)

        # ---------------------------------------------------------------------
        # 1. Thermal Dynamics
        # ---------------------------------------------------------------------
        # Trailing 6h and 24h rolling mean
        temp_mean_6h = grouped["temperature"].transform(
            lambda s: s.rolling(6, min_periods=1).mean()
        )
        temp_mean_24h = grouped["temperature"].transform(
            lambda s: s.rolling(24, min_periods=1).mean()
        )
        # Trailing 6h standard deviation (thermal volatility / jitter)
        temp_std_6h = grouped["temperature"].transform(
            lambda s: s.rolling(6, min_periods=1).std()
        ).fillna(0.0)
        # 1h thermal velocity: delta T over last hour within device
        temp_change_1h = grouped["temperature"].diff(1).fillna(0.0)

        # ---------------------------------------------------------------------
        # 2. Electrical & Power Rail Dynamics
        # ---------------------------------------------------------------------
        # Trailing 6h voltage mean
        volt_mean_6h = grouped["voltage"].transform(
            lambda s: s.rolling(6, min_periods=1).mean()
        )
        # Trailing 6h voltage min (detects power sags and brownout events)
        volt_min_6h = grouped["voltage"].transform(
            lambda s: s.rolling(6, min_periods=1).min()
        )
        # Trailing 6h voltage standard deviation (power rail noise/instability)
        volt_std_6h = grouped["voltage"].transform(
            lambda s: s.rolling(6, min_periods=1).std()
        ).fillna(0.0)
        # Trailing 6h current mean (detects sustained high-power load)
        curr_mean_6h = grouped["current"].transform(
            lambda s: s.rolling(6, min_periods=1).mean()
        )

        # ---------------------------------------------------------------------
        # 3. Error Accumulation & Watchdog Reboots
        # ---------------------------------------------------------------------
        # Rolling error accumulation over 6h and 24h
        err_6h = grouped["error_count"].transform(
            lambda s: s.rolling(6, min_periods=1).sum()
        )
        err_24h = grouped["error_count"].transform(
            lambda s: s.rolling(24, min_periods=1).sum()
        )
        # Watchdog restarts that occurred in the last 24h
        # restart_count is cumulative; delta over 24h yields recent restarts
        restarts_24h = grouped["restart_count"].transform(
            lambda s: s - s.shift(24).fillna(s.iloc[0])
        ).clip(lower=0)

        # ---------------------------------------------------------------------
        # 4. Battery & Network Stability
        # ---------------------------------------------------------------------
        # Battery level change over past 24h (negative = draining rate)
        battery_change_24h = grouped["battery_level"].transform(
            lambda s: s - s.shift(24).fillna(s.iloc[0])
        )
        # Trailing 6h network quality mean
        net_mean_6h = grouped["network_quality"].transform(
            lambda s: s.rolling(6, min_periods=1).mean()
        )

        # ---------------------------------------------------------------------
        # 5. Device Operational Longevity
        # ---------------------------------------------------------------------
        # Cumulative operating life (initial uptime + observation index)
        device_age = grouped.cumcount() + grouped["uptime_hours"].transform("first")

        # ---------------------------------------------------------------------
        # 6. Assembly of Feature DataFrame
        # ---------------------------------------------------------------------
        out = pd.DataFrame(index=df_sorted.index)

        # Identifiers
        if "device_id" in df_sorted.columns:
            out["device_id"] = df_sorted["device_id"]
        if "timestamp" in df_sorted.columns:
            out["timestamp"] = df_sorted["timestamp"]

        # Instantaneous base features
        out["temperature"] = df_sorted["temperature"]
        out["voltage"] = df_sorted["voltage"]
        out["current"] = df_sorted["current"]
        out["battery_level"] = df_sorted["battery_level"]
        out["network_quality"] = df_sorted["network_quality"]
        out["error_count"] = df_sorted["error_count"]
        out["restart_count"] = df_sorted["restart_count"]
        out["uptime_hours"] = df_sorted["uptime_hours"]

        # Engineered rolling features
        out["temperature_mean_6h"] = temp_mean_6h.round(2)
        out["temperature_mean_24h"] = temp_mean_24h.round(2)
        out["temperature_std_6h"] = temp_std_6h.round(3)
        out["temperature_change_1h"] = temp_change_1h.round(2)

        out["voltage_mean_6h"] = volt_mean_6h.round(3)
        out["voltage_min_6h"] = volt_min_6h.round(2)
        out["voltage_std_6h"] = volt_std_6h.round(3)
        out["current_mean_6h"] = curr_mean_6h.round(2)

        out["error_count_6h"] = err_6h.astype(int)
        out["error_count_24h"] = err_24h.astype(int)
        out["restart_count_24h"] = restarts_24h.astype(int)

        out["battery_change_24h"] = battery_change_24h.round(1)
        out["network_quality_mean_6h"] = net_mean_6h.round(2)
        out["device_age_hours"] = device_age.round(1)

        # One-hot encoded firmware categories
        if "firmware_version" in df_sorted.columns:
            fw_series = df_sorted["firmware_version"].astype(str)
            for version in self.known_firmware_versions:
                col_name = f"firmware_version_{version}"
                out[col_name] = (fw_series == version).astype(int)

        # Target label preserved if present in input
        if "failed_within_24h" in df_sorted.columns:
            out["failed_within_24h"] = df_sorted["failed_within_24h"].astype(int)

        return out

    def fit_transform(self, df: pd.DataFrame, y: Optional[Any] = None) -> pd.DataFrame:
        """Fits to data and transforms in one step."""
        return self.fit(df, y).transform(df)

    def get_feature_names(self) -> List[str]:
        """Returns the list of predictive feature column names."""
        base_features = [
            "temperature",
            "voltage",
            "current",
            "battery_level",
            "network_quality",
            "error_count",
            "restart_count",
            "uptime_hours",
            "temperature_mean_6h",
            "temperature_mean_24h",
            "temperature_std_6h",
            "temperature_change_1h",
            "voltage_mean_6h",
            "voltage_min_6h",
            "voltage_std_6h",
            "current_mean_6h",
            "error_count_6h",
            "error_count_24h",
            "restart_count_24h",
            "battery_change_24h",
            "network_quality_mean_6h",
            "device_age_hours",
        ]
        fw_features = [
            f"firmware_version_{ver}" for ver in self.known_firmware_versions
        ]
        return base_features + fw_features

    def save_metadata(self, path: str | Path) -> None:
        """Saves pipeline metadata to JSON."""
        meta = {
            "known_firmware_versions": self.known_firmware_versions,
            "feature_names": self.get_feature_names(),
        }
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        logger.info("Saved pipeline metadata to %s", target.resolve())

    @classmethod
    def load_metadata(cls, path: str | Path) -> FeatureEngineeringPipeline:
        """Loads pipeline metadata from JSON."""
        target = Path(path)
        meta = json.loads(target.read_text(encoding="utf-8"))
        pipeline = cls(known_firmware_versions=meta.get("known_firmware_versions"))
        pipeline.is_fitted = True
        return pipeline


def process_dataset_file(
    input_path: str | Path,
    output_parquet: str | Path = "data/processed/featured_telemetry.parquet",
    output_csv: Optional[str | Path] = None,
) -> pd.DataFrame:
    """Loads raw dataset, runs feature engineering, and exports processed artifacts."""
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"Source file not found at: {src.resolve()}")

    logger.info("Loading raw telemetry dataset from %s...", src.resolve())
    raw_df = pd.read_csv(src)
    logger.info("Loaded %d rows across %d devices.", len(raw_df), raw_df["device_id"].nunique())

    pipeline = FeatureEngineeringPipeline()
    featured_df = pipeline.fit_transform(raw_df)

    # Save to Parquet
    target_parquet = Path(output_parquet)
    target_parquet.parent.mkdir(parents=True, exist_ok=True)
    featured_df.to_parquet(target_parquet, index=False)
    parquet_size_mb = target_parquet.stat().st_size / (1024 * 1024)
    logger.info(
        "Exported featured dataset to Parquet: %s (%.2f MB, %d features).",
        target_parquet.resolve(),
        parquet_size_mb,
        len(pipeline.get_feature_names()),
    )

    # Optionally save to CSV
    if output_csv:
        target_csv = Path(output_csv)
        target_csv.parent.mkdir(parents=True, exist_ok=True)
        featured_df.to_csv(target_csv, index=False)
        csv_size_mb = target_csv.stat().st_size / (1024 * 1024)
        logger.info("Exported featured dataset to CSV: %s (%.2f MB).", target_csv.resolve(), csv_size_mb)

    # Save pipeline metadata
    meta_path = target_parquet.parent / "feature_pipeline_metadata.json"
    pipeline.save_metadata(meta_path)

    return featured_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DataMind Feature Engineering Pipeline CLI")
    parser.add_argument(
        "--input-path",
        type=str,
        default="data/sample/device_measurements.csv",
        help="Path to raw telemetry CSV (default: data/sample/device_measurements.csv)",
    )
    parser.add_argument(
        "--output-parquet",
        type=str,
        default="data/processed/featured_telemetry.parquet",
        help="Path for featured Parquet export (default: data/processed/featured_telemetry.parquet)",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="data/processed/featured_telemetry.csv",
        help="Optional path for featured CSV export (default: data/processed/featured_telemetry.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    process_dataset_file(
        input_path=args.input_path,
        output_parquet=args.output_parquet,
        output_csv=args.output_csv,
    )


if __name__ == "__main__":
    main()
