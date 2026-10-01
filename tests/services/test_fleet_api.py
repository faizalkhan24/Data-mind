"""Integration tests for DataMind Core Fleet & Persistence API."""

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient

def _load_fleet_app():
    service_dir = str(Path(__file__).resolve().parents[2] / "services" / "DataMind.Api")
    for mod in ["main", "config", "schemas", "database", "models", "repositories", "model_cache"]:
        sys.modules.pop(mod, None)
    if service_dir in sys.path:
        sys.path.remove(service_dir)
    sys.path.insert(0, service_dir)
    import main as fleet_main
    return fleet_main.app

app = _load_fleet_app()


class TestFleetApi(unittest.TestCase):
    """Test suite covering database transactions, device lifecycle, telemetry ingest, and alerting."""

    @classmethod
    def setUpClass(cls) -> None:
        """Initializes TestClient within its lifespan context."""
        cls._cm = TestClient(app)
        cls.client = cls._cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        """Closes TestClient lifespan context."""
        cls._cm.__exit__(None, None, None)

    def test_health_check(self) -> None:
        """Verifies GET /health returns 200 OK."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "HEALTHY")

    def test_device_lifecycle(self) -> None:
        """Verifies device registration, query, status update, and duplicate prevention."""
        dev_id = f"DEV-TEST-{int(datetime.now().timestamp())}"
        # 1. Register device
        create_payload = {
            "device_id": dev_id,
            "firmware_version": "1.2.0",
            "status": "ACTIVE",
        }
        resp_create = self.client.post("/api/v1/devices", json=create_payload)
        self.assertEqual(resp_create.status_code, 201)
        data = resp_create.json()
        self.assertEqual(data["device_id"], dev_id)
        self.assertEqual(data["status"], "ACTIVE")

        # 2. Get device
        resp_get = self.client.get(f"/api/v1/devices/{dev_id}")
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(resp_get.json()["device_id"], dev_id)

        # 3. Update device status
        update_payload = {"status": "MAINTENANCE", "firmware_version": "1.3.0"}
        resp_patch = self.client.patch(f"/api/v1/devices/{dev_id}", json=update_payload)
        self.assertEqual(resp_patch.status_code, 200)
        self.assertEqual(resp_patch.json()["status"], "MAINTENANCE")
        self.assertEqual(resp_patch.json()["firmware_version"], "1.3.0")

        # 4. Attempt duplicate registration -> 409 Conflict
        resp_dup = self.client.post("/api/v1/devices", json=create_payload)
        self.assertEqual(resp_dup.status_code, 409)

    def test_telemetry_ingestion_and_history(self) -> None:
        """Verifies telemetry persistence and historical time-series queries."""
        dev_id = f"DEV-TELEM-{int(datetime.now().timestamp())}"
        reading_payload = {
            "timestamp": "2026-01-04T12:00:00Z",
            "temperature": 44.5,
            "voltage": 3.74,
            "current": 1.21,
            "battery_level": 87.0,
            "network_quality": 95.0,
            "error_count": 0.0,
            "restart_count": 1.0,
            "uptime_hours": 120.0,
        }
        # Ingestion auto-registers device
        resp_ingest = self.client.post(f"/api/v1/devices/{dev_id}/telemetry", json=reading_payload)
        self.assertEqual(resp_ingest.status_code, 201)
        data = resp_ingest.json()
        self.assertEqual(data["device_id"], dev_id)
        self.assertAlmostEqual(data["temperature"], 44.5)

        # Retrieve history
        resp_hist = self.client.get(f"/api/v1/devices/{dev_id}/telemetry")
        self.assertEqual(resp_hist.status_code, 200)
        hist_data = resp_hist.json()
        self.assertIsInstance(hist_data, list)
        self.assertGreaterEqual(len(hist_data), 1)

    def test_prediction_audit_and_automated_alert(self) -> None:
        """Verifies prediction persistence and automatic creation of high-risk failure alerts."""
        dev_id = f"DEV-ALERT-{int(datetime.now().timestamp())}"
        # Auto-provision device first
        self.client.post("/api/v1/devices", json={"device_id": dev_id, "status": "ACTIVE"})

        pred_payload = {
            "device_id": dev_id,
            "timestamp": "2026-01-04T14:00:00Z",
            "failure_probability": 0.895,
            "prediction_label": 1,
            "risk_level": "HIGH",
            "latency_ms": 12.4,
            "top_risk_factors_json": '{"factors": ["battery_change_24h", "temperature"]}',
        }
        resp_pred = self.client.post(f"/api/v1/devices/{dev_id}/predictions", json=pred_payload)
        self.assertEqual(resp_pred.status_code, 201)

        # Check prediction history
        resp_hist = self.client.get(f"/api/v1/devices/{dev_id}/predictions")
        self.assertEqual(resp_hist.status_code, 200)
        self.assertEqual(len(resp_hist.json()), 1)

        # Check that high risk automatically spawned a CRITICAL alert
        resp_alerts = self.client.get("/api/v1/alerts?status=OPEN")
        self.assertEqual(resp_alerts.status_code, 200)
        alerts = resp_alerts.json()
        matching_alert = [a for a in alerts if a["device_id"] == dev_id]
        self.assertGreaterEqual(len(matching_alert), 1)
        alert_id = matching_alert[0]["id"]
        self.assertEqual(matching_alert[0]["alert_level"], "CRITICAL")

        # Resolve the alert
        resp_resolve = self.client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "RESOLVED"})
        self.assertEqual(resp_resolve.status_code, 200)
        self.assertEqual(resp_resolve.json()["status"], "RESOLVED")
        self.assertIsNotNone(resp_resolve.json()["resolved_at"])

    def test_fleet_summary(self) -> None:
        """Verifies GET /api/v1/fleet/summary aggregates devices, alerts, and high-risk totals."""
        response = self.client.get("/api/v1/fleet/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("totalDevices", data)
        self.assertIn("activeDevices", data)
        self.assertIn("openAlertsCount", data)
        self.assertIn("highRiskDevicesCount", data)
        self.assertGreaterEqual(data["totalDevices"], 1)


if __name__ == "__main__":
    unittest.main()
