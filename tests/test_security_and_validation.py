"""DataMind Comprehensive Security and Validation Test Suite.

Validates that all security hardened controls and input validation guards
enforce policies as designed:
- [SECURITY-1]: Origin-restricted CORS policies
- [SECURITY-2]: Cryptographic model checksum verification before deserialization
- [SECURITY-3]: API Key / Bearer token authentication enforcement
- [SECURITY-4]: Kubernetes non-root and capability dropping security context
- [SECURITY-5]: Kubernetes NetworkPolicy zero-trust database/cache isolation
- [SECURITY-6]: CI/CD SAST automated security scanning gate
- [VALIDATION-1]: Strict alphanumeric Device ID regex syntax sanitation
- [VALIDATION-2]: ISO-8601 datetime strict validation
- [VALIDATION-3]: NaN, Inf, and out-of-bounds float metric rejection
- [VALIDATION-4]: Bounded pagination and query parameters to mitigate DoS
"""

from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
import yaml
from fastapi import HTTPException
from pydantic import ValidationError

from services.security_auth import (
    sanitize_device_id,  # [VALIDATION-1]
    parse_iso_timestamp,  # [VALIDATION-2]
    validate_finite_number,  # [VALIDATION-3]
    verify_model_integrity,  # [SECURITY-2]
    verify_api_key,  # [SECURITY-3]
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_service_schemas(service_dir_name: str):
    """Loads schemas for a service in isolated namespace."""
    service_dir = str(_REPO_ROOT / "services" / service_dir_name)
    sys.modules.pop("schemas", None)
    for p in list(sys.path):
        if "DataMind." in p:
            sys.path.remove(p)
    sys.path.insert(0, service_dir)
    import schemas
    return schemas


class TestSecurityControls(unittest.TestCase):
    """Test suite validating all [SECURITY-1] through [SECURITY-6] controls."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = _REPO_ROOT

    # --------------------------------------------------------------------------
    # [SECURITY-1]: CORS Whitelisting
    # --------------------------------------------------------------------------
    def test_security_1_cors_whitelist_configured(self):
        """Verifies services use explicit origin whitelists rather than open wildcard."""
        service_dirs = [
            "DataMind.Prediction",
            "DataMind.Api",
            "DataMind.Ingestion",
            "DataMind.Dashboard",
        ]

        for sdir in service_dirs:
            main_py = self.repo_root / "services" / sdir / "main.py"
            content = main_py.read_text(encoding="utf-8")
            self.assertIn("_ALLOWED_ORIGINS", content, f"Missing _ALLOWED_ORIGINS whitelist in {sdir}")
            self.assertNotIn(
                'allow_origins=["*"]',
                content,
                f"Wildcard CORS allow_origins=['*'] must not be present in {sdir}",
            )
            self.assertIn("DATAMIND_CORS_ORIGINS", content, f"{sdir} must allow environment origin override")

    # --------------------------------------------------------------------------
    # [SECURITY-2]: Model Deserialization SHA-256 Verification
    # --------------------------------------------------------------------------
    def test_security_2_model_integrity_verification_pass(self):
        """Verifies verify_model_integrity passes when sha256 checksum matches."""
        model_path = self.repo_root / "ml" / "models" / "best_model_xgboost.joblib"
        if model_path.exists():
            computed = verify_model_integrity(model_path)
            self.assertEqual(len(computed), 64, "SHA-256 checksum must be a 64-character hex string")

    def test_security_2_model_integrity_tampering_detected(self):
        """Verifies verify_model_integrity raises RuntimeError when model file is modified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_model = Path(tmpdir) / "corrupt_model.joblib"
            fake_checksum = Path(tmpdir) / "corrupt_model.joblib.sha256"

            fake_model.write_bytes(b"original content")
            fake_checksum.write_text("0000000000000000000000000000000000000000000000000000000000000000", encoding="utf-8")

            with self.assertRaises(RuntimeError) as ctx:
                verify_model_integrity(fake_model)
            self.assertIn("Model integrity breach detected", str(ctx.exception))

    # --------------------------------------------------------------------------
    # [SECURITY-3]: API Authentication & Authorization
    # --------------------------------------------------------------------------
    def test_security_3_auth_bypass_in_dev_test(self):
        """Verifies verify_api_key defaults to bypass in test/dev environment when not strictly required."""
        os.environ["DATAMIND_REQUIRE_AUTH"] = "false"
        result = verify_api_key(x_api_key=None, authorization=None)
        self.assertTrue(result, "When DATAMIND_REQUIRE_AUTH is false, authentication returns True")

    def test_security_3_auth_enforcement_when_enabled(self):
        """Verifies verify_api_key enforces valid key/token when DATAMIND_REQUIRE_AUTH=true."""
        os.environ["DATAMIND_REQUIRE_AUTH"] = "true"
        os.environ["DATAMIND_API_KEY"] = "super-secret-datamind-key-2026"
        try:
            # Missing credentials -> 401
            with self.assertRaises(HTTPException) as ctx:
                verify_api_key(x_api_key=None, authorization=None)
            self.assertEqual(ctx.exception.status_code, 401)

            # Valid X-API-Key -> OK
            self.assertTrue(verify_api_key(x_api_key="super-secret-datamind-key-2026", authorization=None))

            # Valid Bearer Token -> OK
            self.assertTrue(verify_api_key(x_api_key=None, authorization="Bearer super-secret-datamind-key-2026"))

            # Invalid credentials -> 403
            with self.assertRaises(HTTPException) as ctx:
                verify_api_key(x_api_key="wrong-token", authorization=None)
            self.assertEqual(ctx.exception.status_code, 403)
        finally:
            os.environ["DATAMIND_REQUIRE_AUTH"] = "false"

    # --------------------------------------------------------------------------
    # [SECURITY-4]: Kubernetes Pod & Container Hardening
    # --------------------------------------------------------------------------
    def test_security_4_kubernetes_pod_security_context(self):
        """Verifies K8s deployments declare non-root user and drop capabilities."""
        manifest_files = ["api.yaml", "prediction.yaml", "ingestion.yaml", "dashboard.yaml"]
        for fname in manifest_files:
            mpath = self.repo_root / "infrastructure" / "k8s" / fname
            docs = list(yaml.safe_load_all(mpath.read_text(encoding="utf-8")))
            deployments = [d for d in docs if d and d.get("kind") == "Deployment"]
            self.assertEqual(len(deployments), 1)
            pod_spec = deployments[0]["spec"]["template"]["spec"]

            # Pod security context
            self.assertIn("securityContext", pod_spec, f"Missing pod securityContext in {fname}")
            self.assertTrue(pod_spec["securityContext"].get("runAsNonRoot"), f"runAsNonRoot must be true in {fname}")

            # Container security context
            container = pod_spec["containers"][0]
            self.assertIn("securityContext", container, f"Missing container securityContext in {fname}")
            c_sec = container["securityContext"]
            self.assertFalse(c_sec.get("allowPrivilegeEscalation", True))
            self.assertIn("ALL", c_sec.get("capabilities", {}).get("drop", []))

    # --------------------------------------------------------------------------
    # [SECURITY-5]: Kubernetes Network Isolation Policies
    # --------------------------------------------------------------------------
    def test_security_5_kubernetes_network_policies(self):
        """Verifies NetworkPolicy definitions restrict Postgres and Redis ingress."""
        np_path = self.repo_root / "infrastructure" / "k8s" / "networkpolicy.yaml"
        self.assertTrue(np_path.exists(), "networkpolicy.yaml must exist")
        docs = list(yaml.safe_load_all(np_path.read_text(encoding="utf-8")))

        names = [d["metadata"]["name"] for d in docs if d and d.get("kind") == "NetworkPolicy"]
        self.assertIn("datamind-postgres-isolation", names)
        self.assertIn("datamind-redis-isolation", names)
        self.assertIn("datamind-microservices-ingress", names)

    # --------------------------------------------------------------------------
    # [SECURITY-6]: CI/CD SAST Security Linting Gate
    # --------------------------------------------------------------------------
    def test_security_6_ci_workflow_sast_scan_present(self):
        """Verifies CI workflow includes Bandit SAST scanning step."""
        ci_path = self.repo_root / ".github" / "workflows" / "ci.yml"
        content = ci_path.read_text(encoding="utf-8")
        self.assertIn("bandit", content.lower(), "Bandit SAST scanner must be configured in CI workflow")


class TestValidationControls(unittest.TestCase):
    """Test suite validating all [VALIDATION-1] through [VALIDATION-4] input controls."""

    # --------------------------------------------------------------------------
    # [VALIDATION-1]: Device ID Syntax & Injection Defense
    # --------------------------------------------------------------------------
    def test_validation_1_valid_device_ids(self):
        """Verifies legitimate alphanumeric and hyphenated device identifiers pass."""
        valid_ids = ["DEV-00042", "EDGE_NODE_01", "sensor-99-abc", "D123"]
        for did in valid_ids:
            self.assertEqual(sanitize_device_id(did), did)

    def test_validation_1_injection_and_path_traversal_rejection(self):
        """Verifies SQL injection, shell injection, and path traversals are rejected."""
        malicious_ids = [
            "DEV-001; DROP TABLE devices;--",
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "DEV 00042",
            "d",  # too short (<3)
            "A" * 65,  # too long (>64)
            "DEV$NODE",
            "DEV`rm -rf /`",
        ]
        for bad_id in malicious_ids:
            with self.assertRaises((ValueError, ValidationError)):
                sanitize_device_id(bad_id)

    # --------------------------------------------------------------------------
    # [VALIDATION-2]: Strict ISO-8601 Datetime Parsing
    # --------------------------------------------------------------------------
    def test_validation_2_iso_timestamp_parsing(self):
        """Verifies valid ISO-8601 strings parse into UTC datetimes, and invalid ones raise ValueError."""
        # Valid
        dt = parse_iso_timestamp("2026-01-04T12:00:00Z")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.tzinfo, timezone.utc)

        # Invalid
        with self.assertRaises(ValueError):
            parse_iso_timestamp("not-a-timestamp")
        with self.assertRaises(ValueError):
            parse_iso_timestamp("2026/01/04 12:00:00")

    # --------------------------------------------------------------------------
    # [VALIDATION-3]: NaN / Infinity / Out-of-Bounds Rejection
    # --------------------------------------------------------------------------
    def test_validation_3_nan_and_inf_rejection(self):
        """Verifies validate_finite_number rejects NaN, +Inf, -Inf."""
        self.assertEqual(validate_finite_number(42.5, "temp"), 42.5)

        with self.assertRaises(ValueError):
            validate_finite_number(float("nan"), "temp")
        with self.assertRaises(ValueError):
            validate_finite_number(float("inf"), "voltage")
        with self.assertRaises(ValueError):
            validate_finite_number(float("-inf"), "current")

    def test_validation_3_pydantic_schema_nan_rejection(self):
        """Verifies Pydantic schemas actively reject NaN values in sensory readings."""
        pred_schemas = _load_service_schemas("DataMind.Prediction")
        PredInput = pred_schemas.TelemetryInput

        with self.assertRaises(ValidationError):
            PredInput(
                device_id="DEV-00042",
                temperature=float("nan"),
                voltage=3.75,
                current=1.25,
                battery_level=85.0,
                network_quality=92.0,
                uptime_hours=120.0,
            )

        api_schemas = _load_service_schemas("DataMind.Api")
        TelemetryCreate = api_schemas.TelemetryCreate

        with self.assertRaises(ValidationError):
            TelemetryCreate(
                timestamp=datetime.now(timezone.utc),
                temperature=float("inf"),
                voltage=3.75,
                current=1.25,
                battery_level=85.0,
                network_quality=92.0,
                uptime_hours=120.0,
            )

    # --------------------------------------------------------------------------
    # [VALIDATION-4]: Pagination Bounds in Query Parameters
    # --------------------------------------------------------------------------
    def test_validation_4_pagination_bounds_declared(self):
        """Verifies API routes declare bounded query parameters (le=500, ge=1)."""
        api_main_content = (_REPO_ROOT / "services" / "DataMind.Api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("limit: int = Query(100, ge=1, le=500", api_main_content)
        self.assertIn("limit: int = Query(50, ge=1, le=500", api_main_content)
        self.assertIn("offset: int = Query(0, ge=0", api_main_content)


if __name__ == "__main__":
    unittest.main()
