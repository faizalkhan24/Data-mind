"""Automated tests for DataMind Observability, Prometheus Metrics & Grafana Dashboards."""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import yaml

from services.observability import setup_metrics

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OBS_DIR = _REPO_ROOT / "infrastructure" / "observability"


class TestObservabilityStack(unittest.TestCase):
    """Verifies Prometheus configurations, alerting rules, Grafana provisioning, and app metrics."""

    def setUp(self) -> None:
        self.prom_config_file = _OBS_DIR / "prometheus" / "prometheus.yml"
        self.prom_alerts_file = _OBS_DIR / "prometheus" / "alerts.yml"
        self.grafana_datasource_file = _OBS_DIR / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
        self.grafana_provider_file = _OBS_DIR / "grafana" / "provisioning" / "dashboards" / "dashboards.yml"
        self.grafana_dashboard_file = _OBS_DIR / "grafana" / "dashboards" / "datamind_fleet_overview.json"
        self.compose_file = _REPO_ROOT / "docker-compose.yml"

    def test_prometheus_config_valid_yaml(self) -> None:
        """Verifies prometheus.yml syntax, scrape configs, and target endpoints."""
        self.assertTrue(self.prom_config_file.exists(), "prometheus.yml must exist")
        data = yaml.safe_load(self.prom_config_file.read_text(encoding="utf-8"))

        self.assertIn("global", data)
        self.assertIn("scrape_configs", data)
        self.assertIn("alerts.yml", data.get("rule_files", []))

        jobs = {sc["job_name"] for sc in data["scrape_configs"]}
        expected_jobs = {
            "prometheus",
            "datamind-prediction",
            "datamind-api",
            "datamind-ingestion",
            "datamind-dashboard",
        }
        self.assertTrue(expected_jobs.issubset(jobs), f"Missing jobs in prometheus.yml: {expected_jobs - jobs}")

    def test_prometheus_alerts_valid_yaml_and_rules(self) -> None:
        """Verifies alerts.yml rules syntax, expressions, and severity labels."""
        self.assertTrue(self.prom_alerts_file.exists(), "alerts.yml must exist")
        data = yaml.safe_load(self.prom_alerts_file.read_text(encoding="utf-8"))

        self.assertIn("groups", data)
        rules = []
        for g in data["groups"]:
            rules.extend(g.get("rules", []))

        alert_names = {r["alert"] for r in rules}
        expected_alerts = {
            "PredictionLatencySlaBreached",
            "HighRiskFailureCascadeSpike",
            "CoreApiHighErrorRate",
            "IngestionQueueCongestionBackpressure",
            "MicroserviceInstanceDown",
        }
        self.assertTrue(expected_alerts.issubset(alert_names), f"Missing alerts: {expected_alerts - alert_names}")

        # Validate that SLA alert checks 5ms threshold
        sla_rule = next(r for r in rules if r["alert"] == "PredictionLatencySlaBreached")
        self.assertIn("0.005", sla_rule["expr"])
        self.assertEqual(sla_rule["labels"]["severity"], "critical")

    def test_grafana_datasource_provisioning(self) -> None:
        """Verifies Grafana Prometheus datasource YAML configuration."""
        self.assertTrue(self.grafana_datasource_file.exists(), "Grafana datasource config must exist")
        data = yaml.safe_load(self.grafana_datasource_file.read_text(encoding="utf-8"))

        datasources = data.get("datasources", [])
        self.assertGreater(len(datasources), 0)
        ds = datasources[0]
        self.assertEqual(ds["type"], "prometheus")
        self.assertIn("9090", ds["url"])

    def test_grafana_dashboard_provisioning(self) -> None:
        """Verifies Grafana dashboard provider provisioning config."""
        self.assertTrue(self.grafana_provider_file.exists(), "Grafana dashboards provider must exist")
        data = yaml.safe_load(self.grafana_provider_file.read_text(encoding="utf-8"))

        providers = data.get("providers", [])
        self.assertGreater(len(providers), 0)
        self.assertEqual(providers[0]["type"], "file")
        self.assertIn("dashboards", providers[0]["options"]["path"])

    def test_grafana_fleet_dashboard_json_schema(self) -> None:
        """Verifies master fleet overview dashboard JSON schema, panels, and PromQL targets."""
        self.assertTrue(self.grafana_dashboard_file.exists(), "Dashboard JSON file must exist")
        data = json.loads(self.grafana_dashboard_file.read_text(encoding="utf-8"))

        self.assertEqual(data.get("uid"), "datamind-fleet-overview")
        self.assertIn("DataMind", data.get("title", ""))

        panels = data.get("panels", [])
        self.assertGreater(len(panels), 5)

        # Check for SLA Gauge panel
        gauge_panel = next((p for p in panels if p.get("type") == "gauge"), None)
        self.assertIsNotNone(gauge_panel, "Dashboard must include a gauge panel for SLA")
        self.assertIn("SLA", gauge_panel.get("title", ""))

    def test_docker_compose_includes_observability_services(self) -> None:
        """Verifies docker-compose.yml defines prometheus and grafana services on datamind-net."""
        data = yaml.safe_load(self.compose_file.read_text(encoding="utf-8"))
        services = data.get("services", {})

        self.assertIn("prometheus", services)
        self.assertIn("grafana", services)

        prom = services["prometheus"]
        graf = services["grafana"]

        self.assertIn("9090", str(prom.get("ports", [])))
        self.assertIn("3000", str(graf.get("ports", [])))
        self.assertIn("datamind-net", prom.get("networks", []))
        self.assertIn("datamind-net", graf.get("networks", []))

    def test_application_metrics_endpoint_integration(self) -> None:
        """Verifies FastAPI setup_metrics mounts /metrics and emits valid Prometheus exposition format."""
        test_app = FastAPI(title="TestApp")

        @test_app.get("/ping")
        async def ping() -> dict:
            return {"status": "pong"}

        setup_metrics(test_app, "test-service")
        client = TestClient(test_app)

        # Execute request to generate traffic
        resp = client.get("/ping")
        self.assertEqual(resp.status_code, 200)

        # Scrape metrics
        metrics_resp = client.get("/metrics")
        self.assertEqual(metrics_resp.status_code, 200)
        self.assertIn("text/plain", metrics_resp.headers["content-type"])
        body = metrics_resp.text
        self.assertIn("http_requests_total", body)
        self.assertIn('service="test-service"', body)
        self.assertIn('endpoint="/ping"', body)


if __name__ == "__main__":
    unittest.main()
