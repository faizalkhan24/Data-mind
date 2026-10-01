from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient

def _load_prediction_app():
    service_dir = str(Path(__file__).resolve().parents[2] / "services" / "DataMind.Prediction")
    for mod in ["main", "config", "schemas", "database", "models", "repositories", "model_cache"]:
        sys.modules.pop(mod, None)
    if service_dir in sys.path:
        sys.path.remove(service_dir)
    sys.path.insert(0, service_dir)
    import main as pred_main
    return pred_main.app

app = _load_prediction_app()


class TestPredictionApi(unittest.TestCase):
    """Test suite for FastAPI endpoints, schemas, latency SLAs, and error handling."""

    @classmethod
    def setUpClass(cls) -> None:
        """Initializes FastAPI test client."""
        cls.client = TestClient(app)

    def test_health_check_endpoint(self) -> None:
        """Verifies GET /health returns 200 OK and modelLoaded=True."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertTrue(data["modelLoaded"])
        self.assertIn("modelVersion", data)
        self.assertIn("uptimeSeconds", data)

    def test_model_metadata_endpoint(self) -> None:
        """Verifies GET /api/v1/model/metadata returns valid model configuration."""
        response = self.client.get("/api/v1/model/metadata")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["modelName"], "DataMind-Device-Failure-Predictor")
        self.assertEqual(data["algorithm"], "XGBClassifier")
        self.assertEqual(data["featureCount"], 25)
        self.assertEqual(len(data["features"]), 25)
        self.assertGreater(data["decisionThreshold"], 0.0)

    def test_predict_single_healthy_device(self) -> None:
        """Verifies single-device prediction for a healthy device with explanations."""
        payload = {
            "device_id": "DEV-00753",
            "timestamp": "2026-01-02T18:00:00",
            "temperature": 40.2,
            "voltage": 3.80,
            "current": 1.15,
            "battery_level": 89.0,
            "network_quality": 95.0,
            "error_count": 0.0,
            "restart_count": 0.0,
            "uptime_hours": 240.0,
            "battery_change_24h": -2.0,
            "temperature_mean_6h": 40.1,
            "voltage_min_6h": 3.78,
            "current_mean_6h": 1.14,
            "firmware_version": "1.2.0",
        }
        response = self.client.post("/api/v1/predict?include_explanations=true&top_k=4", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Process-Time-Ms", response.headers)

        data = response.json()
        self.assertEqual(data["deviceId"], "DEV-00753")
        self.assertLess(data["failureProbability"], 0.30)
        self.assertEqual(data["riskLevel"], "LOW")
        self.assertEqual(data["predictionLabel"], 0)
        self.assertIsInstance(data["topRiskFactors"], list)
        self.assertIsInstance(data["topMitigatingFactors"], list)
        self.assertGreater(len(data["topMitigatingFactors"]), 0)

    def test_predict_single_high_risk_device(self) -> None:
        """Verifies single-device prediction for a failing device with risk attribution."""
        payload = {
            "device_id": "DEV-00002",
            "timestamp": "2026-01-01T00:00:00",
            "temperature": 88.2,
            "voltage": 3.14,
            "current": 2.70,
            "battery_level": 34.0,
            "network_quality": 61.0,
            "error_count": 18.0,
            "restart_count": 4.0,
            "uptime_hours": 823.0,
            "battery_change_24h": -22.0,
            "temperature_mean_6h": 85.0,
            "voltage_min_6h": 3.05,
            "current_mean_6h": 2.65,
            "error_count_6h": 15.0,
            "restart_count_24h": 3.0,
            "firmware_version": "1.2.0",
        }
        response = self.client.post("/api/v1/predict?include_explanations=true", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["deviceId"], "DEV-00002")
        self.assertGreaterEqual(data["failureProbability"], 0.70)
        self.assertEqual(data["riskLevel"], "HIGH")
        self.assertEqual(data["predictionLabel"], 1)
        self.assertGreater(len(data["topRiskFactors"]), 0)

        # Check structure of top risk factors
        rf = data["topRiskFactors"][0]
        self.assertIn("category", rf)
        self.assertIn("featureName", rf)
        self.assertIn("attributionScore", rf)
        self.assertGreater(rf["attributionScore"], 0.0)

    def test_predict_single_without_explanations_fast_path(self) -> None:
        """Verifies ultra-fast prediction path when include_explanations=false."""
        payload = {
            "device_id": "DEV-00100",
            "temperature": 42.0,
            "voltage": 3.75,
            "current": 1.20,
            "battery_level": 90.0,
            "network_quality": 95.0,
            "error_count": 0.0,
            "restart_count": 0.0,
            "uptime_hours": 150.0,
        }
        response = self.client.post("/api/v1/predict?include_explanations=false", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["topRiskFactors"], [])
        self.assertEqual(data["topMitigatingFactors"], [])
        # Fast path execution time is under 10 ms
        self.assertLess(data["latencyMs"], 15.0)

    def test_predict_batch_endpoint(self) -> None:
        """Verifies POST /api/v1/predict/batch with multiple devices."""
        items = [
            {
                "device_id": f"DEV-BATCH-{i:03d}",
                "temperature": 41.0 + (i * 10),
                "voltage": 3.75 - (i * 0.15),
                "current": 1.2 + (i * 0.3),
                "battery_level": 90.0 - (i * 15),
                "network_quality": 90.0,
                "error_count": float(i * 2),
                "restart_count": 0.0,
                "uptime_hours": 100.0,
            }
            for i in range(4)
        ]
        response = self.client.post(
            "/api/v1/predict/batch?include_explanations=false",
            json={"items": items},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 4)
        self.assertIsInstance(data["predictions"], list)
        self.assertEqual(len(data["predictions"]), 4)

    def test_validation_error_on_out_of_range_temperature(self) -> None:
        """Verifies HTTP 422 Unprocessable Entity when temperature violates range (-40 to 150°C)."""
        payload = {
            "device_id": "DEV-INVALID",
            "temperature": 250.0,  # Invalid: > 150°C
            "voltage": 3.75,
            "current": 1.20,
            "battery_level": 80.0,
            "network_quality": 90.0,
            "uptime_hours": 50.0,
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_validation_error_on_missing_required_field(self) -> None:
        """Verifies HTTP 422 Unprocessable Entity when required field is missing."""
        payload = {
            "temperature": 45.0,
            "voltage": 3.75,
            # Missing device_id, current, battery_level, etc.
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
