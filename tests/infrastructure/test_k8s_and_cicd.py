"""
DataMind Infrastructure Test Suite: Kubernetes & CI/CD Pipelines (Milestone 14)
================================================================================
Validates all Kubernetes manifests and GitHub Actions automated CI/CD workflows:
1. Valid YAML parsing across all Kubernetes resources
2. Adherence to Kubernetes recommended labels (app.kubernetes.io/*)
3. Zero-downtime rolling update configuration & health probes (/health)
4. Resource boundaries (CPU/Memory requests & limits)
5. HorizontalPodAutoscaler (HPA) specifications
6. Ingress path routing and backend service bindings
7. Kustomize bundle integrity
8. GitHub Actions CI/CD workflows (triggers, matrix, testing steps, container builds)
"""

from pathlib import Path
import unittest
import yaml


class TestKubernetesAndCICD(unittest.TestCase):
    """Test suite validating Kubernetes architecture and GitHub Actions CI/CD pipelines."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.k8s_dir = cls.repo_root / "infrastructure" / "k8s"
        cls.github_workflows_dir = cls.repo_root / ".github" / "workflows"

    def test_k8s_manifests_exist_and_parse_valid_yaml(self) -> None:
        """Verifies all required Kubernetes manifests exist and parse without syntax errors."""
        required_manifests = [
            "namespace.yaml",
            "configmap.yaml",
            "secrets.yaml",
            "postgres.yaml",
            "redis.yaml",
            "prediction.yaml",
            "api.yaml",
            "ingestion.yaml",
            "dashboard.yaml",
            "ingress.yaml",
            "kustomization.yaml",
        ]

        for manifest_name in required_manifests:
            manifest_path = self.k8s_dir / manifest_name
            self.assertTrue(manifest_path.exists(), f"Missing K8s manifest: {manifest_name}")
            content = manifest_path.read_text(encoding="utf-8")
            docs = list(yaml.safe_load_all(content))
            self.assertGreater(len(docs), 0, f"Manifest {manifest_name} must contain at least one document")

    def test_k8s_labels_standardization(self) -> None:
        """Verifies manifests adhere to Kubernetes standard labels (app.kubernetes.io/*)."""
        manifests_to_check = ["prediction.yaml", "api.yaml", "ingestion.yaml", "dashboard.yaml"]

        for manifest_name in manifests_to_check:
            manifest_path = self.k8s_dir / manifest_name
            docs = list(yaml.safe_load_all(manifest_path.read_text(encoding="utf-8")))

            for doc in docs:
                labels = doc.get("metadata", {}).get("labels", {})
                self.assertIn("app.kubernetes.io/name", labels, f"{manifest_name} missing app.kubernetes.io/name")
                self.assertIn("app.kubernetes.io/part-of", labels, f"{manifest_name} missing app.kubernetes.io/part-of")
                self.assertEqual(labels["app.kubernetes.io/part-of"], "datamind")

    def test_k8s_microservices_resource_limits_and_probes(self) -> None:
        """Verifies all microservices declare health probes and resource requests/limits."""
        services = {
            "prediction.yaml": 8000,
            "api.yaml": 8001,
            "ingestion.yaml": 8002,
            "dashboard.yaml": 8003,
        }

        for filename, port in services.items():
            manifest_path = self.k8s_dir / filename
            docs = list(yaml.safe_load_all(manifest_path.read_text(encoding="utf-8")))

            # Locate Deployment
            deployments = [d for d in docs if d and d.get("kind") == "Deployment"]
            self.assertEqual(len(deployments), 1, f"Deployment not found in {filename}")
            deployment = deployments[0]

            pod_spec = deployment["spec"]["template"]["spec"]
            containers = pod_spec["containers"]
            self.assertEqual(len(containers), 1)
            container = containers[0]

            # Verify health probes
            self.assertIn("readinessProbe", container, f"Missing readinessProbe in {filename}")
            self.assertEqual(container["readinessProbe"]["httpGet"]["path"], "/health")
            self.assertEqual(container["readinessProbe"]["httpGet"]["port"], port)

            self.assertIn("livenessProbe", container, f"Missing livenessProbe in {filename}")
            self.assertEqual(container["livenessProbe"]["httpGet"]["path"], "/health")
            self.assertEqual(container["livenessProbe"]["httpGet"]["port"], port)

            # Verify resource limits and requests
            resources = container.get("resources", {})
            self.assertIn("requests", resources, f"Missing resource requests in {filename}")
            self.assertIn("limits", resources, f"Missing resource limits in {filename}")
            self.assertIn("cpu", resources["requests"])
            self.assertIn("memory", resources["requests"])
            self.assertIn("cpu", resources["limits"])
            self.assertIn("memory", resources["limits"])

            # Verify rolling update strategy
            strategy = deployment["spec"].get("strategy", {})
            self.assertEqual(strategy.get("type"), "RollingUpdate")

    def test_k8s_horizontal_pod_autoscalers(self) -> None:
        """Verifies HorizontalPodAutoscaler definitions for high availability."""
        service_files = ["prediction.yaml", "api.yaml", "ingestion.yaml", "dashboard.yaml"]

        for filename in service_files:
            manifest_path = self.k8s_dir / filename
            docs = list(yaml.safe_load_all(manifest_path.read_text(encoding="utf-8")))

            hpa_docs = [d for d in docs if d and d.get("kind") == "HorizontalPodAutoscaler"]
            self.assertEqual(len(hpa_docs), 1, f"Missing HorizontalPodAutoscaler in {filename}")
            hpa = hpa_docs[0]

            spec = hpa["spec"]
            self.assertGreaterEqual(spec["minReplicas"], 2, f"minReplicas should be >= 2 for HA in {filename}")
            self.assertGreaterEqual(spec["maxReplicas"], 6, f"maxReplicas should allow burst scaling in {filename}")
            self.assertIn("metrics", spec)

    def test_k8s_ingress_routing_rules(self) -> None:
        """Verifies Ingress manifest defines routing rules for all microservices."""
        ingress_path = self.k8s_dir / "ingress.yaml"
        doc = yaml.safe_load(ingress_path.read_text(encoding="utf-8"))

        self.assertEqual(doc["kind"], "Ingress")
        self.assertEqual(doc["apiVersion"], "networking.k8s.io/v1")

        paths = doc["spec"]["rules"][0]["http"]["paths"]
        routes = {p["path"]: p["backend"]["service"]["name"] for p in paths}

        self.assertIn("/api/v1/predict", routes)
        self.assertEqual(routes["/api/v1/predict"], "datamind-prediction")

        self.assertIn("/api/v1/fleet", routes)
        self.assertEqual(routes["/api/v1/fleet"], "datamind-api")

        self.assertIn("/api/v1/stream", routes)
        self.assertEqual(routes["/api/v1/stream"], "datamind-ingestion")

        self.assertIn("/", routes)
        self.assertEqual(routes["/"], "datamind-dashboard")

    def test_k8s_kustomization_bundle(self) -> None:
        """Verifies Kustomize bundle links all manifests and configures images."""
        kustomize_path = self.k8s_dir / "kustomization.yaml"
        doc = yaml.safe_load(kustomize_path.read_text(encoding="utf-8"))

        self.assertEqual(doc.get("namespace"), "datamind")
        resources = doc.get("resources", [])
        self.assertIn("namespace.yaml", resources)
        self.assertIn("configmap.yaml", resources)
        self.assertIn("secrets.yaml", resources)
        self.assertIn("postgres.yaml", resources)
        self.assertIn("redis.yaml", resources)
        self.assertIn("prediction.yaml", resources)
        self.assertIn("api.yaml", resources)
        self.assertIn("ingestion.yaml", resources)
        self.assertIn("dashboard.yaml", resources)
        self.assertIn("ingress.yaml", resources)

        images = [img["name"] for img in doc.get("images", [])]
        self.assertIn("ghcr.io/faizalkhan24/datamind-prediction", images)
        self.assertIn("ghcr.io/faizalkhan24/datamind-api", images)
        self.assertIn("ghcr.io/faizalkhan24/datamind-ingestion", images)
        self.assertIn("ghcr.io/faizalkhan24/datamind-dashboard", images)

    def test_github_actions_ci_workflow(self) -> None:
        """Verifies CI workflow triggers, matrix configurations, and test jobs."""
        ci_path = self.github_workflows_dir / "ci.yml"
        self.assertTrue(ci_path.exists(), "CI workflow file .github/workflows/ci.yml must exist")

        doc = yaml.safe_load(ci_path.read_text(encoding="utf-8"))
        self.assertIn("name", doc)

        # Triggers
        # PyYAML parses unquoted 'on:' as boolean True!
        triggers = doc.get("on") or doc.get(True) or {}
        self.assertIn("push", triggers)
        self.assertIn("pull_request", triggers)

        # Jobs
        jobs = doc.get("jobs", {})
        self.assertIn("lint-and-validate", jobs)
        self.assertIn("test-suite", jobs)
        self.assertIn("docker-build-check", jobs)

        # Test job matrix & execution
        test_job = jobs["test-suite"]
        matrix = test_job.get("strategy", {}).get("matrix", {})
        self.assertIn("python-version", matrix)
        self.assertIn("3.11", matrix["python-version"])

        step_commands = [
            step.get("run", "")
            for step in test_job.get("steps", [])
            if "run" in step
        ]
        test_run_present = any("unittest" in cmd for cmd in step_commands)
        self.assertTrue(test_run_present, "CI test-suite job must execute python unittest")

    def test_github_actions_cd_workflow(self) -> None:
        """Verifies CD workflow multi-service container builds and staging deployment."""
        cd_path = self.github_workflows_dir / "cd.yml"
        self.assertTrue(cd_path.exists(), "CD workflow file .github/workflows/cd.yml must exist")

        doc = yaml.safe_load(cd_path.read_text(encoding="utf-8"))
        jobs = doc.get("jobs", {})
        self.assertIn("build-and-publish", jobs)
        self.assertIn("deploy-staging", jobs)

        matrix = jobs["build-and-publish"].get("strategy", {}).get("matrix", {})
        services = [item["service"] for item in matrix.get("include", [])]
        expected_services = {"prediction", "api", "ingestion", "dashboard"}
        self.assertEqual(expected_services, set(services))


if __name__ == "__main__":
    unittest.main()
