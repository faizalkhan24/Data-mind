"""High-Performance In-Memory Sliding Window Buffer for Real-Time Feature Calculation.

Computes exact 25-feature telemetry representations over streaming events without lookahead
or data leakage, achieving sub-millisecond per-event enrichment latency.
"""

from __future__ import annotations

from collections import deque
import logging
import math
import threading
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from schemas import (
    DeviceWindowState,
    EnrichedTelemetryPayload,
    RawTelemetryReading,
)

logger = logging.getLogger(__name__)


class DeviceRollingBuffer:
    """Maintains a bounded historical time-series window for a single IoT device."""

    def __init__(self, device_id: str, max_points: int = 100) -> None:
        self.device_id = device_id
        self.max_points = max_points
        self._history: deque[RawTelemetryReading] = deque(maxlen=max_points)
        self._lock = threading.Lock()
        self._latest_enriched: Optional[EnrichedTelemetryPayload] = None

    def append(self, reading: RawTelemetryReading) -> EnrichedTelemetryPayload:
        """Appends a new reading to the rolling window and computes the 25-feature vector."""
        with self._lock:
            self._history.append(reading)
            enriched = self._compute_features(reading)
            self._latest_enriched = enriched
            return enriched

    def _compute_features(self, current: RawTelemetryReading) -> EnrichedTelemetryPayload:
        """Calculates trailing rolling aggregates over the in-memory window."""
        window_list = list(self._history)
        n = len(window_list)

        # Slice trailing 6h and 24h points
        # Assuming periodic readings (e.g. hourly or 1 reading per epoch)
        win_6 = window_list[-min(6, n):]
        win_24 = window_list[-min(24, n):]

        # 1. Thermal Dynamics
        temp_vals_6 = [p.temperature for p in win_6]
        temp_vals_24 = [p.temperature for p in win_24]

        temp_mean_6h = float(np.mean(temp_vals_6))
        temp_mean_24h = float(np.mean(temp_vals_24))
        temp_std_6h = float(np.std(temp_vals_6, ddof=1)) if len(temp_vals_6) > 1 else 0.0
        if math.isnan(temp_std_6h):
            temp_std_6h = 0.0

        # 1h thermal velocity: diff from immediately preceding point
        if n >= 2:
            temp_change_1h = float(current.temperature - window_list[-2].temperature)
        else:
            temp_change_1h = 0.0

        # 2. Electrical & Power Rail Dynamics
        volt_vals_6 = [p.voltage for p in win_6]
        curr_vals_6 = [p.current for p in win_6]

        volt_mean_6h = float(np.mean(volt_vals_6))
        volt_min_6h = float(np.min(volt_vals_6))
        volt_std_6h = float(np.std(volt_vals_6, ddof=1)) if len(volt_vals_6) > 1 else 0.0
        if math.isnan(volt_std_6h):
            volt_std_6h = 0.0

        curr_mean_6h = float(np.mean(curr_vals_6))

        # 3. Error Accumulation & Watchdog Reboots
        err_6h = float(sum(p.error_count for p in win_6))
        err_24h = float(sum(p.error_count for p in win_24))

        # 24h delta in restart count (restart_count is cumulative)
        baseline_24_restart = win_24[0].restart_count
        restart_count_24h = max(0.0, float(current.restart_count - baseline_24_restart))

        # 4. Battery & Connectivity
        baseline_24_battery = win_24[0].battery_level
        battery_change_24h = float(current.battery_level - baseline_24_battery)

        net_vals_6 = [p.network_quality for p in win_6]
        net_mean_6h = float(np.mean(net_vals_6))

        # 5. Device Longevity
        device_age_hours = float(current.uptime_hours)

        # 6. One-hot firmware versions
        fw_clean = current.firmware_version.strip()
        fw_1_0 = 1.0 if fw_clean == "1.0.0" else 0.0
        fw_1_1 = 1.0 if fw_clean == "1.1.0" else 0.0
        fw_1_2 = 1.0 if fw_clean == "1.2.0" else 0.0

        return EnrichedTelemetryPayload(
            device_id=current.device_id,
            timestamp=current.timestamp,
            # Instantaneous
            temperature=current.temperature,
            voltage=current.voltage,
            current=current.current,
            battery_level=current.battery_level,
            network_quality=current.network_quality,
            error_count=current.error_count,
            restart_count=current.restart_count,
            uptime_hours=current.uptime_hours,
            # Thermal
            temperature_mean_6h=temp_mean_6h,
            temperature_mean_24h=temp_mean_24h,
            temperature_std_6h=temp_std_6h,
            temperature_change_1h=temp_change_1h,
            # Electrical
            voltage_mean_6h=volt_mean_6h,
            voltage_min_6h=volt_min_6h,
            voltage_std_6h=volt_std_6h,
            current_mean_6h=curr_mean_6h,
            # Error & restarts
            error_count_6h=err_6h,
            error_count_24h=err_24h,
            restart_count_24h=restart_count_24h,
            # Battery & net
            battery_change_24h=battery_change_24h,
            network_quality_mean_6h=net_mean_6h,
            # Longevity
            device_age_hours=device_age_hours,
            # Firmware one-hot
            **{
                "firmware_version_1.0.0": fw_1_0,
                "firmware_version_1.1.0": fw_1_1,
                "firmware_version_1.2.0": fw_1_2,
            },
        )

    def get_window_state(self) -> DeviceWindowState:
        """Returns metadata regarding current buffer window occupancy."""
        with self._lock:
            pts = len(self._history)
            earliest = self._history[0].timestamp if pts > 0 else None
            latest = self._history[-1].timestamp if pts > 0 else None
            return DeviceWindowState(
                device_id=self.device_id,
                points_in_window=pts,
                capacity=self.max_points,
                earliest_timestamp=earliest,
                latest_timestamp=latest,
                latest_features=self._latest_enriched,
            )


class FleetBufferManager:
    """Manages concurrent sliding window buffers across the entire device fleet."""

    def __init__(self, max_points_per_device: int = 100) -> None:
        self.max_points_per_device = max_points_per_device
        self._buffers: Dict[str, DeviceRollingBuffer] = {}
        self._lock = threading.Lock()

    def get_or_create(self, device_id: str) -> DeviceRollingBuffer:
        """Retrieves or provisions a rolling buffer for the specified device ID."""
        with self._lock:
            if device_id not in self._buffers:
                self._buffers[device_id] = DeviceRollingBuffer(
                    device_id=device_id,
                    max_points=self.max_points_per_device,
                )
            return self._buffers[device_id]

    def add_reading(self, reading: RawTelemetryReading) -> EnrichedTelemetryPayload:
        """Ingests a reading and calculates enriched features for the device."""
        buf = self.get_or_create(reading.device_id)
        return buf.append(reading)

    def get_window_state(self, device_id: str) -> Optional[DeviceWindowState]:
        """Returns the current window state for a device, or None if never seen."""
        with self._lock:
            buf = self._buffers.get(device_id)
        if buf is None:
            return None
        return buf.get_window_state()

    @property
    def active_device_count(self) -> int:
        """Total number of active devices currently tracked in memory."""
        with self._lock:
            return len(self._buffers)

    def clear(self) -> None:
        """Clears all device buffers (useful for testing and reset)."""
        with self._lock:
            self._buffers.clear()
