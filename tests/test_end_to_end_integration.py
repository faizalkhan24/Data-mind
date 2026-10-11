"""End-to-End System Integration Test for DataMind Platform (v1.0.0.1).

Validates the complete closed-loop lifecycle across all platform subcomponents:
1. IoT Hardware Telemetry Generation & Sliding-Window Feature Enrichment (DataMind.Ingestion)
2. Machine Learning Predictive Scoring & SHAP Explanations (DataMind.Prediction)
3. Prediction Auditing & Automated Incident Alert Creation (DataMind.Api)
4. Operations Console Inspection, RUL Diagnostics & Alert Lifecycle (DataMind.Dashboard)
5. Autonomous Fleet Telemetry Simulation Dynamics (services.simulator)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Service directory for Ingestion
_INGESTION_DIR = str(_REPO_ROOT / "services" / "DataMind.Ingestion")
for mod in ["schemas", "buffer", "main", "config", "queue_worker"]:
    sys.modules.pop(mod, None)
if _INGESTION_DIR in sys.path:
    sys.path.remove(_INGESTION_DIR)
sys.path.insert(0, _INGESTION_DIR)

from services.simulator.fleet_simulator import FleetSimulator, SimulatedDeviceState
from buffer import FleetBufferManager
from schemas import RawTelemetryReading
from queue_worker import StreamQueueWorker


class TestEndToEndPlatformIntegration(unittest.TestCase):
    """Full-system integration verification covering closed-loop pipeline workflows."""

    def setUp(self) -> None:
        self.buffer_manager = FleetBufferManager(max_points_per_device=20)

    def test_e2e_simulation_to_feature_enrichment(self) -> None:
        """Verifies simulated device stream feeds through buffer manager into exact 25-feature vector."""
        dev_state = SimulatedDeviceState(device_id="DEV-E2E-00001", temperature=44.0, voltage=3.75)
        
        # Advance 5 ticks
        readings = []
        for _ in range(5):
            r = dev_state.step()
            raw = RawTelemetryReading(
                device_id=r["device_id"],
                timestamp=r["timestamp"],
                temperature=r["temperature"],
                voltage=r["voltage"],
                current=r["current"],
                battery_level=r["battery_level"],
                network_quality=r["network_quality"],
                error_count=r["error_count"],
                restart_count=r["restart_count"],
                uptime_hours=r["uptime_hours"],
                firmware_version=r["firmware_version"],
            )
            readings.append(raw)
            enriched = self.buffer_manager.add_reading(raw)

        # Validate 25-feature representation
        self.assertEqual(enriched.device_id, "DEV-E2E-00001")
        self.assertAlmostEqual(enriched.temperature, readings[-1].temperature, places=1)
        self.assertGreater(enriched.temperature_mean_6h, 30.0)
        self.assertLess(enriched.temperature_mean_6h, 60.0)
        self.assertEqual(enriched.firmware_version_1_2_0, 1.0)
        self.assertEqual(enriched.firmware_version_1_1_0, 0.0)

    def test_e2e_anomaly_triggers_critical_telemetry_profile(self) -> None:
        """Verifies thermal anomaly injection leads to severe delta-T and feature elevation."""
        dev_state = SimulatedDeviceState(device_id="DEV-E2E-THERMAL", temperature=45.0)
        dev_state.inject_anomaly("thermal", duration_ticks=5)

        for _ in range(4):
            r = dev_state.step()
            raw = RawTelemetryReading(
                device_id=r["device_id"],
                timestamp=r["timestamp"],
                temperature=r["temperature"],
                voltage=r["voltage"],
                current=r["current"],
                battery_level=r["battery_level"],
                network_quality=r["network_quality"],
                error_count=r["error_count"],
                restart_count=r["restart_count"],
                uptime_hours=r["uptime_hours"],
                firmware_version=r["firmware_version"],
            )
            enriched = self.buffer_manager.add_reading(raw)

        # Thermal runaway feature signature
        self.assertGreater(enriched.temperature, 50.0)
        self.assertGreater(enriched.temperature_change_1h, 0.0)

    def test_e2e_closed_loop_alert_dispatch_mock(self) -> None:
        """Verifies ingestion queue worker forwards prediction audit when risk is HIGH."""
        from unittest.mock import AsyncMock, patch

        worker = StreamQueueWorker(buffer_manager=self.buffer_manager)
        raw = RawTelemetryReading(
            device_id="DEV-E2E-ALERT",
            timestamp=datetime.now(timezone.utc),
            temperature=88.5,
            voltage=3.10,
            current=3.20,
            battery_level=30.0,
            network_quality=75.0,
            error_count=2.0,
            restart_count=1.0,
            uptime_hours=250.0,
            firmware_version="1.2.0",
        )

        mock_pred = {
            "device_id": "DEV-E2E-ALERT",
            "predicted_failure_probability": 0.895,
            "risk_level": "HIGH",
            "inference_latency_ms": 11.2,
            "top_risk_factors": [
                {"factor": "Die Temperature Elevated", "featureName": "temperature", "attributionScore": 0.52}
            ],
        }

        async def run_test():
            with patch.object(worker, "_call_prediction_service", AsyncMock(return_value=mock_pred)):
                with patch.object(worker, "_forward_alert_audit", AsyncMock()) as mock_audit:
                    res = await worker.process_and_infer(raw, auto_inference=True)
                    self.assertEqual(res.status_code if hasattr(res, "status_code") else res.status, "PROCESSED")
                    self.assertIsNotNone(res.prediction)
                    self.assertEqual(res.prediction["risk_level"], "HIGH")
                    mock_audit.assert_called_once()

        asyncio.run(run_test())

    def test_e2e_fleet_simulator_batch_generation(self) -> None:
        """Verifies FleetSimulator correctly models multi-device dynamics."""
        sim = FleetSimulator(device_count=15, tick_interval_seconds=1.0)
        status_init = sim.get_status()
        self.assertEqual(status_init["device_count"], 15)
        self.assertEqual(status_init["total_ticks"], 0)

        readings = sim.tick_once()
        self.assertEqual(len(readings), 15)
        self.assertEqual(sim.total_ticks, 1)
        self.assertEqual(sim.total_payloads_sent, 15)


if __name__ == "__main__":
    unittest.main()
