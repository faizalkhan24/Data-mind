"""Integration tests for DataMind Streaming Ingestion & Real-Time Feature Buffer."""

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient


def _load_ingestion_app():
    service_dir = str(Path(__file__).resolve().parents[2] / "services" / "DataMind.Ingestion")
    for mod in [
        "main",
        "config",
        "schemas",
        "database",
        "models",
        "repositories",
        "model_cache",
        "buffer",
        "queue_worker",
    ]:
        sys.modules.pop(mod, None)
    if service_dir in sys.path:
        sys.path.remove(service_dir)
    sys.path.insert(0, service_dir)
    import main as ingestion_main
    return ingestion_main.app


app = _load_ingestion_app()


class TestIngestionStream(unittest.TestCase):
    """Test suite covering sliding window buffer, feature calculation, batch stream ingest, and stats."""

    @classmethod
    def setUpClass(cls) -> None:
        """Initializes TestClient inside lifespan context."""
        cls._cm = TestClient(app)
        cls.client = cls._cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        """Closes TestClient lifespan context."""
        cls._cm.__exit__(None, None, None)

    def setUp(self) -> None:
        """Resets in-memory buffers before each test."""
        self.client.delete("/api/v1/stream/buffers")

    def test_health_check(self) -> None:
        """Verifies GET /health returns 200 OK and healthy status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertIn("activeBuffers", data)

    def test_single_event_ingestion_and_feature_enrichment(self) -> None:
        """Verifies single telemetry event enrichment produces exact 25-feature vector."""
        dev_id = f"DEV-STREAM-{int(datetime.now().timestamp())}"
        payload = {
            "device_id": dev_id,
            "timestamp": "2026-01-04T12:00:00Z",
            "temperature": 45.0,
            "voltage": 3.75,
            "current": 1.25,
            "battery_level": 85.0,
            "network_quality": 90.0,
            "error_count": 0.0,
            "restart_count": 1.0,
            "uptime_hours": 100.0,
            "firmware_version": "1.2.0",
        }
        response = self.client.post("/api/v1/stream/telemetry", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["device_id"], dev_id)
        self.assertEqual(data["status"], "PROCESSED")
        self.assertLess(data["enrichment_latency_ms"], 50.0)  # sub-50ms SLA

        features = data["features"]
        self.assertIsNotNone(features)

        # Verify instantaneous features
        self.assertEqual(features["temperature"], 45.0)
        self.assertEqual(features["voltage"], 3.75)
        self.assertEqual(features["current"], 1.25)
        self.assertEqual(features["battery_level"], 85.0)

        # Verify rolling features on initial point
        self.assertEqual(features["temperature_mean_6h"], 45.0)
        self.assertEqual(features["temperature_mean_24h"], 45.0)
        self.assertEqual(features["temperature_std_6h"], 0.0)
        self.assertEqual(features["temperature_change_1h"], 0.0)
        self.assertEqual(features["voltage_mean_6h"], 3.75)
        self.assertEqual(features["voltage_min_6h"], 3.75)
        self.assertEqual(features["battery_change_24h"], 0.0)
        self.assertEqual(features["restart_count_24h"], 0.0)

        # Verify one-hot encoded firmware
        self.assertEqual(features["firmware_version_1.2.0"], 1.0)
        self.assertEqual(features["firmware_version_1.1.0"], 0.0)
        self.assertEqual(features["firmware_version_1.0.0"], 0.0)

    def test_sliding_window_temporal_dynamics(self) -> None:
        """Verifies multi-point rolling statistics, delta-T velocity, and window state retrieval."""
        dev_id = f"DEV-WINDOW-{int(datetime.now().timestamp())}"
        temps = [40.0, 42.0, 44.0, 46.0, 48.0]

        for i, t in enumerate(temps):
            payload = {
                "device_id": dev_id,
                "timestamp": f"2026-01-04T{10+i:02d}:00:00Z",
                "temperature": t,
                "voltage": 3.70 - (i * 0.02),
                "current": 1.0 + (i * 0.1),
                "battery_level": 90.0 - (i * 2.0),
                "network_quality": 95.0,
                "error_count": float(i),
                "restart_count": 0.0,
                "uptime_hours": 50.0 + i,
                "firmware_version": "1.1.0",
            }
            resp = self.client.post("/api/v1/stream/telemetry", json=payload)
            self.assertEqual(resp.status_code, 200)

        # Query window inspection endpoint
        resp_win = self.client.get(f"/api/v1/stream/devices/{dev_id}/window")
        self.assertEqual(resp_win.status_code, 200)
        win_data = resp_win.json()
        self.assertEqual(win_data["device_id"], dev_id)
        self.assertEqual(win_data["points_in_window"], 5)

        latest_feat = win_data["latest_features"]
        # Expected mean temperature over [40, 42, 44, 46, 48] is 44.0
        self.assertAlmostEqual(latest_feat["temperature_mean_6h"], 44.0, places=4)
        # Expected temp_change_1h is 48.0 - 46.0 = 2.0
        self.assertAlmostEqual(latest_feat["temperature_change_1h"], 2.0, places=4)
        # Expected battery change from initial 90.0 to 82.0 is -8.0
        self.assertAlmostEqual(latest_feat["battery_change_24h"], -8.0, places=4)
        # Expected firmware one-hot: 1.1.0 is 1.0
        self.assertEqual(latest_feat["firmware_version_1.1.0"], 1.0)
        self.assertEqual(latest_feat["firmware_version_1.2.0"], 0.0)

    def test_batch_ingestion_stream(self) -> None:
        """Verifies high-throughput batch stream ingestion across multiple devices."""
        readings = []
        for dev_idx in range(2):
            dev_id = f"DEV-BATCH-{dev_idx}-{int(datetime.now().timestamp())}"
            for pt in range(3):
                readings.append({
                    "device_id": dev_id,
                    "timestamp": f"2026-01-04T{12+pt:02d}:00:00Z",
                    "temperature": 43.0 + pt,
                    "voltage": 3.75,
                    "current": 1.20,
                    "battery_level": 80.0,
                    "network_quality": 88.0,
                    "error_count": 0.0,
                    "restart_count": 0.0,
                    "uptime_hours": 80.0 + pt,
                    "firmware_version": "1.0.0",
                })

        batch_payload = {"readings": readings}
        resp = self.client.post("/api/v1/stream/batch", json=batch_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["total_received"], 6)
        self.assertEqual(data["processed_count"], 6)
        self.assertEqual(data["failed_count"], 0)
        self.assertEqual(len(data["results"]), 6)

    def test_stats_and_error_handling(self) -> None:
        """Verifies operational stats and 404 response on unknown device window query."""
        # Query stats
        resp_stats = self.client.get("/api/v1/stream/stats")
        self.assertEqual(resp_stats.status_code, 200)
        data = resp_stats.json()
        self.assertIn("events_processed", data)
        self.assertIn("avg_enrichment_latency_ms", data)
        self.assertIn("uptime_seconds", data)

        # Unknown device window returns 404
        resp_unknown = self.client.get("/api/v1/stream/devices/NON-EXISTENT-DEVICE/window")
        self.assertEqual(resp_unknown.status_code, 404)


if __name__ == "__main__":
    unittest.main()
