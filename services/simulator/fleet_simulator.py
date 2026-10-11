"""DataMind Autonomous Real-Time Fleet Telemetry Simulator Daemon.

Simulates dynamic industrial IoT hardware fleets (25-50 devices) generating realistic
physical telemetry with stochastic temporal variance, gradual wear degradation,
and intermittent synthetic anomaly injections (thermal runaway, voltage sag, watchdog faults).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("datamind.simulator")


@dataclass
class SimulatedDeviceState:
    """Internal physical state tracking for an individual simulated IoT device."""

    device_id: str
    firmware_version: str = "1.2.0"
    temperature: float = 43.5
    voltage: float = 3.75
    current: float = 1.20
    battery_level: float = 90.0
    network_quality: float = 92.0
    error_count: float = 0.0
    restart_count: float = 0.0
    uptime_hours: float = 100.0
    # Degradation dynamics
    is_anomaly: bool = False
    anomaly_type: Optional[str] = None
    anomaly_ticks_remaining: int = 0

    def step(self) -> Dict[str, Any]:
        """Advances physical state by one operational tick."""
        self.uptime_hours += 0.05
        # Battery gradual depletion
        self.battery_level = max(5.0, self.battery_level - random.uniform(0.01, 0.04))

        if self.is_anomaly:
            self.anomaly_ticks_remaining -= 1
            if self.anomaly_type == "thermal":
                self.temperature = min(105.0, self.temperature + random.uniform(2.5, 6.0))
                self.current = min(4.5, self.current + random.uniform(0.1, 0.3))
            elif self.anomaly_type == "power_sag":
                self.voltage = max(2.6, self.voltage - random.uniform(0.08, 0.18))
                self.current = min(4.8, self.current + random.uniform(0.2, 0.5))
            elif self.anomaly_type == "watchdog_crash":
                self.error_count += random.randint(1, 3)
                self.restart_count += 1
                self.temperature = min(75.0, self.temperature + random.uniform(1.0, 3.0))

            if self.anomaly_ticks_remaining <= 0:
                self.is_anomaly = False
                self.anomaly_type = None
        else:
            # Baseline mean-reverting stochastic jitter
            self.temperature += (44.0 - self.temperature) * 0.1 + random.gauss(0, 0.4)
            self.temperature = max(20.0, min(65.0, self.temperature))

            self.voltage += (3.75 - self.voltage) * 0.1 + random.gauss(0, 0.02)
            self.voltage = max(3.4, min(4.1, self.voltage))

            self.current += (1.20 - self.current) * 0.1 + random.gauss(0, 0.03)
            self.current = max(0.5, min(2.0, self.current))

            self.network_quality = max(40.0, min(100.0, self.network_quality + random.gauss(0, 1.5)))

        return {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": round(self.temperature, 2),
            "voltage": round(self.voltage, 3),
            "current": round(self.current, 3),
            "battery_level": round(self.battery_level, 1),
            "network_quality": round(self.network_quality, 1),
            "error_count": float(self.error_count),
            "restart_count": float(self.restart_count),
            "uptime_hours": round(self.uptime_hours, 1),
            "firmware_version": self.firmware_version,
        }

    def inject_anomaly(self, anomaly_type: str, duration_ticks: int = 5) -> None:
        """Injects an operational failure mode into this device."""
        self.is_anomaly = True
        self.anomaly_type = anomaly_type
        self.anomaly_ticks_remaining = duration_ticks


class FleetSimulator:
    """Manages an autonomous background loop ticking live telemetry for an IoT fleet."""

    def __init__(
        self,
        device_count: int = 25,
        target_ingestion_url: Optional[str] = None,
        tick_interval_seconds: float = 2.0,
        anomaly_chance_per_tick: float = 0.08,
    ) -> None:
        self.device_count = device_count
        self.target_ingestion_url = target_ingestion_url or os.getenv(
            "DATAMIND_INGESTION_URL", "http://localhost:8002"
        )
        self.tick_interval_seconds = tick_interval_seconds
        self.anomaly_chance_per_tick = anomaly_chance_per_tick
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

        # State metrics
        self.total_ticks: int = 0
        self.total_payloads_sent: int = 0
        self.total_anomalies_injected: int = 0
        self.last_tick_time: Optional[str] = None

        # Initialize fleet devices
        self.devices: List[SimulatedDeviceState] = []
        for i in range(1, self.device_count + 1):
            firmware = "1.2.0" if i > 5 else ("1.1.0" if i > 2 else "1.0.0")
            dev = SimulatedDeviceState(
                device_id=f"DEV-{i:05d}",
                firmware_version=firmware,
                temperature=42.0 + random.uniform(-2.0, 3.0),
                voltage=3.75 + random.uniform(-0.05, 0.05),
                current=1.20 + random.uniform(-0.08, 0.08),
                battery_level=random.uniform(70.0, 98.0),
                network_quality=random.uniform(85.0, 99.0),
                uptime_hours=random.uniform(40.0, 600.0),
            )
            self.devices.append(dev)

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """Returns current operational status and transmission statistics."""
        return {
            "running": self._running,
            "device_count": len(self.devices),
            "tick_interval_seconds": self.tick_interval_seconds,
            "total_ticks": self.total_ticks,
            "total_payloads_sent": self.total_payloads_sent,
            "total_anomalies_injected": self.total_anomalies_injected,
            "last_tick_time": self.last_tick_time,
            "target_url": self.target_ingestion_url,
        }

    async def start(self) -> None:
        """Starts continuous fleet simulation loop in the background."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._simulation_loop())
        logger.info("FleetSimulator started for %d devices at interval %.1fs", len(self.devices), self.tick_interval_seconds)

    async def stop(self) -> None:
        """Gracefully halts background simulation loop."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("FleetSimulator stopped. Total events emitted: %d", self.total_payloads_sent)

    def tick_once(self) -> List[Dict[str, Any]]:
        """Advances all devices by one tick and returns generated telemetry payloads."""
        # Check for anomaly injection
        if random.random() < self.anomaly_chance_per_tick:
            target_device = random.choice(self.devices)
            anomaly_type = random.choice(["thermal", "power_sag", "watchdog_crash"])
            target_device.inject_anomaly(anomaly_type, duration_ticks=random.randint(4, 8))
            self.total_anomalies_injected += 1
            logger.info("Injected %s anomaly into %s", anomaly_type, target_device.device_id)

        readings = [d.step() for d in self.devices]
        self.total_ticks += 1
        self.total_payloads_sent += len(readings)
        self.last_tick_time = datetime.now(timezone.utc).isoformat()
        return readings

    async def _simulation_loop(self) -> None:
        """Background continuous execution loop."""
        api_key = os.getenv("DATAMIND_API_KEY", "datamind-sec-token-prod-2026")
        headers = {"X-API-Key": api_key}
        batch_url = f"{self.target_ingestion_url}/api/v1/stream/batch?auto_infer=true"

        while self._running:
            readings = self.tick_once()
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(batch_url, json={"readings": readings}, headers=headers)
                    if resp.status_code == 200:
                        logger.debug("Successfully transmitted batch of %d readings to Ingestion service", len(readings))
                    else:
                        logger.debug("Ingestion service returned %d on batch tick", resp.status_code)
            except Exception as exc:
                logger.debug("Simulator tick transmission skipped (offline): %s", exc)

            try:
                await asyncio.sleep(self.tick_interval_seconds)
            except asyncio.CancelledError:
                break


# Module-level default singleton
global_fleet_simulator = FleetSimulator()
