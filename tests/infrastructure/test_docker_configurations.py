"""Automated validation tests for DataMind Docker Containerization & Compose Orchestration."""

from __future__ import annotations

from pathlib import Path
import unittest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCKER_DIR = _REPO_ROOT / "infrastructure" / "docker"


class TestDockerConfigurations(unittest.TestCase):
    """Verifies Dockerfiles, Compose specs, network topologies, and security policies."""

    def setUp(self) -> None:
        self.dockerfiles = {
            "prediction": _DOCKER_DIR / "Dockerfile.prediction",
            "api": _DOCKER_DIR / "Dockerfile.api",
            "ingestion": _DOCKER_DIR / "Dockerfile.ingestion",
            "dashboard": _DOCKER_DIR / "Dockerfile.dashboard",
        }
        self.compose_file = _REPO_ROOT / "docker-compose.yml"
        self.infra_compose_file = _DOCKER_DIR / "docker-compose.yml"
        self.dockerignore_file = _REPO_ROOT / ".dockerignore"

    def test_dockerfiles_exist(self) -> None:
        """Verifies that all 4 microservice Dockerfiles exist."""
        for name, path in self.dockerfiles.items():
            self.assertTrue(path.exists(), f"Missing Dockerfile for {name} at {path}")

    def test_dockerfiles_multi_stage_structure(self) -> None:
        """Verifies that each Dockerfile implements multi-stage builds with python:3.11-slim."""
        for name, path in self.dockerfiles.items():
            content = path.read_text(encoding="utf-8")
            self.assertIn("FROM python:3.11-slim AS builder", content, f"{name} must have builder stage")
            self.assertIn("FROM python:3.11-slim AS runner", content, f"{name} must have runner stage")
            self.assertIn("COPY --from=builder", content, f"{name} must copy artifacts from builder stage")

    def test_dockerfiles_security_non_root_user(self) -> None:
        """Verifies container security standard: running under non-root unprivileged user."""
        for name, path in self.dockerfiles.items():
            content = path.read_text(encoding="utf-8")
            self.assertIn("useradd -u 10001", content, f"{name} must create UID 10001 user")
            self.assertIn("USER datamind", content, f"{name} must switch to USER datamind")

    def test_dockerfiles_healthcheck_directive(self) -> None:
        """Verifies that every container defines an automated container health probe."""
        for name, path in self.dockerfiles.items():
            content = path.read_text(encoding="utf-8")
            self.assertIn("HEALTHCHECK", content, f"{name} missing HEALTHCHECK directive")
            self.assertIn("curl -f", content, f"{name} HEALTHCHECK must probe service endpoint")

    def test_dockerfiles_ports_and_cmd(self) -> None:
        """Verifies EXPOSE directives and uvicorn entrypoint commands match architecture."""
        port_map = {
            "prediction": "8000",
            "api": "8001",
            "ingestion": "8002",
            "dashboard": "8080",
        }
        for name, path in self.dockerfiles.items():
            content = path.read_text(encoding="utf-8")
            port = port_map[name]
            self.assertIn(f"EXPOSE {port}", content, f"{name} must expose port {port}")
            self.assertIn("--port", content, f"{name} CMD must specify --port flag")
            self.assertIn(f'"{port}"', content, f"{name} CMD must specify port {port}")

    def test_docker_compose_valid_yaml_and_services(self) -> None:
        """Verifies root docker-compose.yml parses cleanly and declares all 6 services."""
        self.assertTrue(self.compose_file.exists(), "Root docker-compose.yml must exist")
        content = self.compose_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        services = data.get("services", {})
        expected_services = {"postgres", "redis", "prediction", "api", "ingestion", "dashboard"}
        self.assertEqual(expected_services, set(services.keys()))

    def test_docker_compose_service_dependencies_and_health(self) -> None:
        """Verifies health-dependent service orchestration hierarchy."""
        content = self.compose_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        services = data["services"]

        # API must depend on PostgreSQL being healthy
        api_deps = services["api"].get("depends_on", {})
        self.assertIn("postgres", api_deps)
        self.assertEqual(api_deps["postgres"].get("condition"), "service_healthy")

        # Ingestion must depend on Prediction & API being healthy
        ingestion_deps = services["ingestion"].get("depends_on", {})
        self.assertIn("prediction", ingestion_deps)
        self.assertIn("api", ingestion_deps)

        # Dashboard must depend on API & Prediction being healthy
        dashboard_deps = services["dashboard"].get("depends_on", {})
        self.assertIn("api", dashboard_deps)
        self.assertIn("prediction", dashboard_deps)

    def test_docker_compose_network_and_volume_topologies(self) -> None:
        """Verifies bridge network isolation and named persistent volumes."""
        content = self.compose_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        self.assertIn("networks", data)
        self.assertIn("datamind-net", data["networks"])

        self.assertIn("volumes", data)
        self.assertIn("pgdata", data["volumes"])
        self.assertIn("redisdata", data["volumes"])

        # Confirm all services join datamind-net
        for sname, sdef in data["services"].items():
            self.assertIn("datamind-net", sdef.get("networks", []), f"Service {sname} not on datamind-net")

    def test_dockerignore_compliance(self) -> None:
        """Verifies .dockerignore properly excludes bloat, secrets, and caches."""
        self.assertTrue(self.dockerignore_file.exists(), ".dockerignore must exist at repository root")
        content = self.dockerignore_file.read_text(encoding="utf-8")
        patterns = [p.strip() for p in content.splitlines() if p.strip() and not p.startswith("#")]
        
        required_patterns = [".git", ".venv", "__pycache__", "*.pyc", "mlruns", "mlflow.db"]
        for req in required_patterns:
            self.assertIn(req, patterns, f".dockerignore missing pattern: {req}")


if __name__ == "__main__":
    unittest.main()
