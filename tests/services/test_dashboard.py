"""Unit and integration test suite for DataMind Operations Dashboard Service."""

from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest
from fastapi.testclient import TestClient

def _load_dashboard_app():
    repo_root = str(Path(__file__).resolve().parents[2])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    service_dir = str(Path(__file__).resolve().parents[2] / "services" / "DataMind.Dashboard")
    for mod in ["main", "dashboard_config", "config"]:
        sys.modules.pop(mod, None)
    if service_dir in sys.path:
        sys.path.remove(service_dir)
    sys.path.insert(0, service_dir)
    import main as dashboard_main
    return dashboard_main.app

app = _load_dashboard_app()


class TestDashboardService(unittest.TestCase):
    """Verifies static asset delivery, aggregated APIs, simulation, and alert workflows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._cm = TestClient(app)
        cls.client = cls._cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._cm.__exit__(None, None, None)

    def test_health_check(self) -> None:
        """Verifies GET /health returns 200 OK and valid configuration."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertTrue(data["static_dir_exists"])
        self.assertTrue(data["ui_ready"])
        self.assertIn("downstream_services", data)

    def test_serve_root_index_html(self) -> None:
        """Verifies GET / delivers the main SPA index.html."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers["content-type"])
        self.assertIn("DataMind — Fleet Intelligence", resp.text)
        self.assertIn("Fleet Health & Risk Inventory", resp.text)
        self.assertIn("Real-Time Diagnostic Simulator", resp.text)

    def test_static_assets_delivery(self) -> None:
        """Verifies static CSS and JavaScript files are properly delivered."""
        resp_css = self.client.get("/static/style.css")
        self.assertEqual(resp_css.status_code, 200)
        self.assertIn("text/css", resp_css.headers["content-type"])
        self.assertIn("--bg-primary", resp_css.text)

        resp_js = self.client.get("/static/app.js")
        self.assertEqual(resp_js.status_code, 200)
        self.assertIn("javascript", resp_js.headers["content-type"])
        self.assertIn("executeSimulation", resp_js.text)

    def test_dashboard_summary_endpoint(self) -> None:
        """Verifies GET /api/dashboard/summary computes fleet KPI metrics."""
        resp = self.client.get("/api/dashboard/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["total_devices"], 0)
        self.assertGreater(data["active_devices"], 0)
        self.assertGreaterEqual(data["high_risk_devices"], 0)
        self.assertGreaterEqual(data["open_alerts"], 0)
        self.assertIn("avg_inference_sla", data)
        self.assertEqual(data["system_status"], "SYSTEM HEALTHY")

    def test_dashboard_fleet_and_filtering(self) -> None:
        """Verifies GET /api/dashboard/fleet pagination, search, and risk filtering."""
        # Unfiltered listing
        resp = self.client.get("/api/dashboard/fleet?limit=20")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["devices"]), 20)
        self.assertGreaterEqual(data["total"], 20)

        # Risk filter HIGH
        resp_high = self.client.get("/api/dashboard/fleet?risk=HIGH")
        self.assertEqual(resp_high.status_code, 200)
        data_high = resp_high.json()
        self.assertTrue(all(d["risk_level"] == "HIGH" for d in data_high["devices"]))

        # Search query filter
        resp_search = self.client.get("/api/dashboard/fleet?search=DEV-00042")
        self.assertEqual(resp_search.status_code, 200)
        data_search = resp_search.json()
        self.assertEqual(len(data_search["devices"]), 1)
        self.assertEqual(data_search["devices"][0]["device_id"], "DEV-00042")

    def test_dashboard_device_detail(self) -> None:
        """Verifies GET /api/dashboard/devices/{device_id} returns specs and history."""
        resp = self.client.get("/api/dashboard/devices/DEV-00007")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["device"]["device_id"], "DEV-00007")
        self.assertEqual(len(data["history"]), 10)
        self.assertIn("temperature", data["history"][0])
        self.assertIn("voltage", data["history"][0])

    def test_diagnostic_simulation_healthy(self) -> None:
        """Verifies simulation endpoint scores healthy device as NOMINAL risk."""
        payload = {
            "device_id": "DEV-TEST-NOMINAL",
            "temperature": 42.0,
            "voltage": 3.75,
            "current": 1.15,
            "battery_level": 92.0,
            "network_quality": 95.0,
            "uptime_hours": 100.0,
            "firmware_version": "1.2.0",
        }
        resp = self.client.post("/api/dashboard/simulate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["risk_level"], "NOMINAL")
        self.assertLess(data["failure_probability"], 0.20)
        self.assertLess(data["latency_ms"], 10.0)
        self.assertGreater(len(data["top_risk_factors"]), 0)

    def test_diagnostic_simulation_high_risk(self) -> None:
        """Verifies simulation endpoint identifies thermal runaway and power sag as HIGH risk."""
        payload = {
            "device_id": "DEV-TEST-FAIL",
            "temperature": 92.0,
            "voltage": 3.05,
            "current": 3.10,
            "battery_level": 14.0,
            "network_quality": 60.0,
            "uptime_hours": 1800.0,
            "firmware_version": "1.2.0",
        }
        resp = self.client.post("/api/dashboard/simulate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["risk_level"], "HIGH")
        self.assertGreater(data["failure_probability"], 0.70)
        
        # Check SHAP attribution factors contain positive impacts
        factors = data["top_risk_factors"]
        self.assertTrue(any(f["impact"].startswith("+") for f in factors))

    def test_alerts_lifecycle(self) -> None:
        """Verifies operational alerts retrieval and state update workflows."""
        resp = self.client.get("/api/dashboard/alerts")
        self.assertEqual(resp.status_code, 200)
        alerts = resp.json()
        self.assertGreaterEqual(len(alerts), 1)

        resp_ack = self.client.patch("/api/dashboard/alerts/1", json={"status": "ACKNOWLEDGED"})
        self.assertEqual(resp_ack.status_code, 200)
        self.assertEqual(resp_ack.json()["alert"]["status"], "ACKNOWLEDGED")

        resp_res = self.client.patch("/api/dashboard/alerts/1", json={"status": "RESOLVED"})
        self.assertEqual(resp_res.status_code, 200)
        self.assertEqual(resp_res.json()["alert"]["status"], "RESOLVED")

        resp_404 = self.client.patch("/api/dashboard/alerts/99999", json={"status": "RESOLVED"})
        self.assertEqual(resp_404.status_code, 404)

    def test_register_device_endpoint(self) -> None:
        """Verifies POST /api/dashboard/devices provisions a new device."""
        dev_id = f"DEV-REG-{int(time.time())}"
        payload = {
            "device_id": dev_id,
            "firmware_version": "1.2.0",
            "status": "ACTIVE",
        }
        resp = self.client.post("/api/dashboard/devices", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["device"]["device_id"], dev_id)


if __name__ == "__main__":
    unittest.main()
