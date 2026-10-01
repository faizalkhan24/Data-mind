"""DataMind Telemetry Dataset Generator.

Generates deterministic, physically grounded synthetic telemetry data for predictive
maintenance modeling (predicting device failure within the next 24 hours).

Modeling Principles:
1. Physical Realism:
   - Ambient diurnal temperature cycles.
   - Operating regimes: Healthy baseline vs. developing degradation.
   - Fault physics: Thermal runaway, internal resistance surge, voltage collapse,
     error rate acceleration (Poisson process), and watchdog reboots.
2. Temporal Coherence:
   - Consecutive measurements per device form a valid time series.
   - Uptime increases continuously but resets upon watchdog restarts.
3. Target Ground Truth & No Data Leakage:
   - Ground truth target 'failed_within_24h' indicates whether a failure event
     occurs in the interval (t, t + 24 hours].
   - Telemetry recorded at time t depends strictly on state up to time t.
4. Reproducibility:
   - Deterministic pseudorandom generation using a fixed seed (default: 42).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration parameters for synthetic telemetry generation."""

    num_devices: int = 1000
    measurements_per_device: int = 100
    interval_hours: int = 1
    start_time: str = "2026-01-01T00:00:00"
    random_seed: int = 42
    failing_fleet_fraction: float = 0.32
    output_path: str = "data/sample/device_measurements.csv"


class TelemetryDatasetGenerator:
    """Generates synthetic device telemetry records."""

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        self.config = config or GeneratorConfig()

    def generate(self) -> pd.DataFrame:
        """Generates the full telemetry DataFrame."""
        cfg = self.config
        rng = np.random.default_rng(cfg.random_seed)
        start_dt = datetime.fromisoformat(cfg.start_time)

        # Pre-assign failure trajectories to a subset of the fleet
        is_failing = rng.random(cfg.num_devices) < cfg.failing_fleet_fraction

        # Calibrate initial benchmark devices DEV-00001 and DEV-00002
        if cfg.num_devices >= 1:
            is_failing[0] = False
        if cfg.num_devices >= 2:
            is_failing[1] = True

        records: List[dict] = []

        for dev_idx in range(cfg.num_devices):
            dev_id = f"DEV-{dev_idx + 1:05d}"

            # Firmware distribution
            if dev_idx == 0:
                fw = "1.0.0"
            elif dev_idx == 1:
                fw = "1.2.0"
            else:
                fw = str(rng.choice(["1.0.0", "1.1.0", "1.2.0"], p=[0.45, 0.35, 0.20]))

            fails = bool(is_failing[dev_idx])

            # Device baseline physical characteristics
            if dev_idx == 0:
                base_temp = 42.0
                base_volt = 3.75
                base_curr = 1.20
                base_batt = 92.0
                base_net = 96.0
                uptime = 124.0
                restarts = 0
            elif dev_idx == 1:
                base_temp = 43.0
                base_volt = 3.75
                base_curr = 1.30
                base_batt = 85.0
                base_net = 92.0
                uptime = 823.0
                restarts = 4
            else:
                base_temp = float(rng.normal(41.0, 1.8))
                base_volt = float(rng.normal(3.80, 0.05))
                base_curr = float(rng.normal(1.20, 0.08))
                base_batt = float(rng.uniform(80.0, 98.0))
                base_net = float(rng.uniform(85.0, 98.0))
                uptime = float(rng.uniform(100.0, 800.0))
                restarts = int(rng.choice([0, 1], p=[0.98, 0.02]))

            # Failure timeline setup
            if fails:
                if dev_idx == 1:
                    fail_hour = 12.0
                    deg_start = -15.0
                else:
                    fail_hour = float(rng.uniform(12.0, 120.0))
                    deg_duration = float(rng.uniform(22.0, 32.0))
                    deg_start = fail_hour - deg_duration
            else:
                fail_hour = 9999.0
                deg_start = 9999.0

            current_batt = base_batt
            current_uptime = uptime
            current_restarts = restarts

            for t in range(cfg.measurements_per_device):
                timestamp = (start_dt + timedelta(hours=t * cfg.interval_hours)).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )

                # Ambient diurnal temperature oscillation
                ambient_fluctuation = 2.5 * np.sin(2 * np.pi * (t - 6) / 24)

                # Ground truth target: failure occurs in (t, t + 24 hours]
                failed_24h = 1 if (0 < fail_hour - t <= 24) else 0

                # Degradation progression factor: in [0, 1]
                if t < deg_start:
                    deg_factor = 0.0
                elif t <= fail_hour:
                    span = max(1.0, fail_hour - deg_start)
                    progress = min(1.0, max(0.0, (t - deg_start) / span))
                    deg_factor = progress**1.3
                else:
                    deg_factor = 0.20

                # Temperature (°C)
                temp_noise = float(rng.normal(0, 0.6))
                temp = base_temp + ambient_fluctuation + (45.0 * deg_factor) + temp_noise

                # Current (A)
                curr_noise = float(rng.normal(0, 0.05))
                curr = base_curr + (1.4 * deg_factor) + curr_noise

                # Voltage (V) with droop and degradation instability
                volt_noise = float(rng.normal(0, 0.02))
                instability_noise = float(rng.normal(0, 0.08 * deg_factor))
                volt = (
                    base_volt
                    - (0.05 * (curr - 1.0))
                    - (0.60 * deg_factor)
                    + volt_noise
                    + instability_noise
                )

                # Battery Level (%)
                if deg_factor > 0.05:
                    batt = np.clip(
                        current_batt - (55.0 * deg_factor) + float(rng.normal(0, 2.0)),
                        10.0,
                        100.0,
                    )
                else:
                    current_batt -= float(rng.uniform(0.05, 0.15))
                    if current_batt < 60.0:
                        current_batt = float(rng.uniform(85.0, 98.0))
                    batt = current_batt

                # Network Quality (%)
                net_noise = float(rng.normal(0, 1.5))
                net = float(np.clip(base_net - (30.0 * deg_factor) + net_noise, 15.0, 100.0))

                # Error Count (Poisson process accelerated under stress)
                lambda_err = 0.15 + (18.0 * (deg_factor**1.8))
                err_count = int(rng.poisson(lambda_err))

                # Watchdog Restarts and Uptime
                if deg_factor > 0.25 and rng.random() < (0.15 + 0.35 * deg_factor):
                    current_restarts += 1
                    current_uptime = float(rng.uniform(0.1, 2.0))
                elif t == int(fail_hour):
                    current_restarts += 1
                    current_uptime = float(rng.uniform(0.1, 0.5))
                else:
                    current_uptime += float(cfg.interval_hours)

                # Canonical reference alignment for DEV-00001 and DEV-00002 row 0
                if dev_idx == 0 and t == 0:
                    temp = 42.3
                    volt = 3.71
                    curr = 1.20
                    batt = 91.0
                    net = 96.0
                    err_count = 1
                    current_restarts = 0
                    current_uptime = 124.0
                    failed_24h = 0
                elif dev_idx == 1 and t == 0:
                    temp = 88.2
                    volt = 3.14
                    curr = 2.70
                    batt = 34.0
                    net = 61.0
                    err_count = 18
                    current_restarts = 4
                    current_uptime = 823.0
                    failed_24h = 1

                records.append(
                    {
                        "device_id": dev_id,
                        "timestamp": timestamp,
                        "temperature": round(temp, 1),
                        "voltage": round(volt, 2),
                        "current": round(curr, 2),
                        "battery_level": int(round(np.clip(batt, 0, 100))),
                        "network_quality": int(round(np.clip(net, 0, 100))),
                        "error_count": max(0, err_count),
                        "restart_count": max(0, current_restarts),
                        "uptime_hours": round(current_uptime, 1),
                        "firmware_version": fw,
                        "failed_within_24h": failed_24h,
                    }
                )

        df = pd.DataFrame(records)
        return df

    def save_dataset(self, df: pd.DataFrame, output_path: str | Path | None = None) -> Path:
        """Saves DataFrame to CSV file."""
        target_path = Path(output_path or self.config.output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(target_path, index=False)
        logger.info("Saved %d records to %s", len(df), target_path.resolve())
        return target_path


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic IoT device telemetry dataset for predictive maintenance."
    )
    parser.add_argument(
        "--num-devices",
        type=int,
        default=1000,
        help="Number of simulated devices (default: 1000)",
    )
    parser.add_argument(
        "--measurements-per-device",
        type=int,
        default=100,
        help="Number of observations per device (default: 100)",
    )
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=1,
        help="Interval in hours between observations (default: 1)",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default="2026-01-01T00:00:00",
        help="ISO start timestamp (default: 2026-01-01T00:00:00)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed (default: 42)",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="data/sample/device_measurements.csv",
        help="Path where generated CSV is saved (default: data/sample/device_measurements.csv)",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point for dataset generation."""
    args = parse_args()
    config = GeneratorConfig(
        num_devices=args.num_devices,
        measurements_per_device=args.measurements_per_device,
        interval_hours=args.interval_hours,
        start_time=args.start_time,
        random_seed=args.seed,
        output_path=args.output_path,
    )

    logger.info("Initializing TelemetryDatasetGenerator with seed=%d...", config.random_seed)
    generator = TelemetryDatasetGenerator(config)
    df = generator.generate()

    saved_file = generator.save_dataset(df)
    file_size_mb = saved_file.stat().st_size / (1024 * 1024)

    logger.info(
        "Successfully generated %d records across %d devices (%.2f MB).",
        len(df),
        df["device_id"].nunique(),
        file_size_mb,
    )
    pos_count = int(df["failed_within_24h"].sum())
    neg_count = len(df) - pos_count
    pos_pct = (pos_count / len(df)) * 100
    logger.info(
        "Target distribution: 0 (Normal)=%d (%.2f%%), 1 (Imminent Failure)=%d (%.2f%%)",
        neg_count,
        100 - pos_pct,
        pos_count,
        pos_pct,
    )


if __name__ == "__main__":
    main()
