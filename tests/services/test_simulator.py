"""Unit and integration test suite for DataMind Fleet Telemetry Simulator."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from services.simulator.fleet_simulator import FleetSimulator, SimulatedDeviceState


def _load_dashboard_app():
    service_dir = str(_REPO_ROOT / "services" / "DataMind.Dashboard")
    for mod in ["main", "dashboard_config", "config"]:
        sys.modules.pop(mod, None)
    if service_dir in sys.path:
        sys.path.remove(service_dir)
    sys.path.insert(0, service_dir)
    import main as dashboard_main
    return dashboard_main.app


class TestFleetSimulator(unittest.TestCase):
    """Test suite covering simulator physics, state stepping, anomalies, and API controls."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _load_dashboard_app()
        cls._cm = TestClient(cls.app)
        cls.client = cls._cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._cm.__exit__(None, None, None)

    def test_device_state_step(self) -> None:
        """Verifies physical state advances realistically with valid metric bounds."""
        dev = SimulatedDeviceState(device_id="DEV-00001", temperature=45.0, voltage=3.75, battery_level=90.0)
        reading = dev.step()

        self.assertEqual(reading["device_id"], "DEV-00001")
        self.assertIn("timestamp", reading)
        self.assertGreater(reading["temperature"], 20.0)
        self.assertLess(reading["temperature"], 70.0)
        self.assertGreater(reading["voltage"], 3.0)
        self.assertLess(reading["voltage"], 4.5)
        self.assertGreaterEqual(reading["battery_level"], 0.0)
        self.assertLessEqual(reading["battery_level"], 100.0)
        self.assertGreaterEqual(reading["uptime_hours"], 100.0)

    def test_thermal_anomaly_injection(self) -> None:
        """Verifies anomaly injection shifts parameters into critical ranges and recovers."""
        dev = SimulatedDeviceState(device_id="DEV-00002", temperature=45.0)
        dev.inject_anomaly("thermal", duration_ticks=3)
        self.assertTrue(dev.is_anomaly)

        # Step through anomaly
        r1 = dev.step()
        self.assertGreater(r1["temperature"], 45.0)

        r2 = dev.step()
        r3 = dev.step()
        # After 3 ticks, anomaly should expire
        self.assertFalse(dev.is_anomaly)

    def test_simulator_tick_once(self) -> None:
        """Verifies tick_once advances entire fleet and records accurate metrics."""
        sim = FleetSimulator(device_count=10, tick_interval_seconds=1.0)
        readings = sim.tick_once()

        self.assertEqual(len(readings), 10)
        self.assertEqual(sim.total_ticks, 1)
        self.assertEqual(sim.total_payloads_sent, 10)
        self.assertIsNotNone(sim.last_tick_time)

    def test_dashboard_simulator_endpoints(self) -> None:
        """Verifies dashboard simulator endpoints report status and start/stop cleanly."""
        # 1. Query status
        resp_status = self.client.get("/api/dashboard/simulator/status")
        self.assertEqual(resp_status.status_code, 200)
        data = resp_status.json()
        self.assertIn("running", data)
        self.assertIn("device_count", data)

        # 2. Start simulator
        resp_start = self.client.post("/api/dashboard/simulator/start")
        self.assertEqual(resp_start.status_code, 200)
        data_start = resp_start.json()
        self.assertTrue(data_start["success"])
        self.assertTrue(data_start["status"]["running"])

        # 3. Stop simulator
        resp_stop = self.client.post("/api/dashboard/simulator/stop")
        self.assertEqual(resp_stop.status_code, 200)
        data_stop = resp_stop.json()
        self.assertTrue(data_stop["success"])
        self.assertFalse(data_stop["status"]["running"])


if __name__ == "__main__":
    unittest.main()
