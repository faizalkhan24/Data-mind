"""High-Performance Prediction & Explainability Engine.

Caches the champion XGBoost model and TelemetryExplainer in memory to achieve
sub-5ms inference response times without cold-start reload overhead.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SERVICE_DIR = Path(__file__).resolve().parent
if str(_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVICE_DIR))

import joblib
import numpy as np
import pandas as pd

from ml.evaluation.explainability import TelemetryExplainer
from prediction_config import settings
from schemas import (
    BatchPredictionResponse,
    ModelMetadataResponse,
    PredictionResponse,
    RiskFactorDto,
    TelemetryInput,
)

logger = logging.getLogger(__name__)


class PredictionEngine:
    """In-memory predictive serving engine with optional SHAP explainability."""

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model_path = model_path or settings.model_path
        self.model: Optional[Any] = None
        self.explainer: Optional[TelemetryExplainer] = None
        self.feature_names: List[str] = []
        self.threshold: float = settings.default_decision_threshold
        self.test_metrics: Dict[str, float] = {}
        self.start_time: float = time.time()
        self._load_model()

    def _load_model(self) -> None:
        """Loads model binary once during application startup."""
        if not self.model_path.exists():
            logger.error("Model artifact does not exist at %s", self.model_path)
            raise FileNotFoundError(f"Model artifact not found at {self.model_path}")

        logger.info("Loading production model artifact from %s...", self.model_path)
        t0 = time.perf_counter()
        artifact = joblib.load(self.model_path)

        self.model = artifact.get("model", artifact)
        self.feature_names = artifact.get("feature_names", [])
        self.threshold = float(artifact.get("threshold", settings.default_decision_threshold))
        self.test_metrics = {}
        for k, v in artifact.get("test_metrics", {}).items():
            try:
                self.test_metrics[k] = float(v)
            except (ValueError, TypeError):
                pass

        logger.info(
            "Initializing in-memory TelemetryExplainer (%d features, Threshold=%.4f)...",
            len(self.feature_names),
            self.threshold,
        )
        self.explainer = TelemetryExplainer(
            model=self.model,
            feature_names=self.feature_names,
            decision_threshold=self.threshold,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        logger.info("Production model successfully cached in memory in %.2f ms.", elapsed_ms)

    def is_ready(self) -> bool:
        """Checks if model and explainer are loaded."""
        return self.model is not None and self.explainer is not None

    def get_metadata(self) -> ModelMetadataResponse:
        """Returns metadata about the active production model."""
        return ModelMetadataResponse(
            modelName="DataMind-Device-Failure-Predictor",
            algorithm="XGBClassifier",
            featureCount=len(self.feature_names),
            features=self.feature_names,
            decisionThreshold=self.threshold,
            testMetrics=self.test_metrics,
        )

    def predict_single(
        self,
        item: TelemetryInput,
        include_explanations: bool = True,
        top_k: int = 4,
    ) -> PredictionResponse:
        """Scores a single device observation with optional SHAP explainability."""
        t0 = time.perf_counter()
        feature_dict = item.to_feature_vector(self.feature_names)

        if include_explanations:
            # Full prediction + SHAP explanation via TelemetryExplainer
            explanation = self.explainer.explain_instance(
                row_or_dict=feature_dict,
                device_id=item.device_id,
                timestamp=item.timestamp,
                top_k=top_k,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return PredictionResponse(
                deviceId=item.device_id,
                timestamp=item.timestamp,
                failureProbability=round(explanation.failure_probability, 4),
                predictionLabel=explanation.prediction_label,
                riskLevel=explanation.risk_level,
                decisionThreshold=round(self.threshold, 4),
                predictionWindowHours=24,
                latencyMs=round(elapsed_ms, 3),
                topRiskFactors=[
                    RiskFactorDto(
                        category=f.category,
                        featureName=f.feature_name,
                        featureValue=round(f.feature_value, 4),
                        attributionScore=round(f.attribution_score, 4),
                        description=f.description,
                    )
                    for f in explanation.top_risk_factors
                ],
                topMitigatingFactors=[
                    RiskFactorDto(
                        category=f.category,
                        featureName=f.feature_name,
                        featureValue=round(f.feature_value, 4),
                        attributionScore=round(f.attribution_score, 4),
                        description=f.description,
                    )
                    for f in explanation.top_mitigating_factors
                ],
            )
        else:
            # Ultra-low latency prediction path (< 1 ms, skips SHAP computation)
            df_vec = pd.DataFrame([feature_dict])[self.feature_names].astype(float)
            prob = float(self.model.predict_proba(df_vec)[0, 1])
            pred_label = 1 if prob >= self.threshold else 0
            if prob >= self.threshold:
                risk_tier = "HIGH"
            elif prob >= self.threshold * 0.45:
                risk_tier = "MEDIUM"
            else:
                risk_tier = "LOW"

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return PredictionResponse(
                deviceId=item.device_id,
                timestamp=item.timestamp,
                failureProbability=round(prob, 4),
                predictionLabel=pred_label,
                riskLevel=risk_tier,
                decisionThreshold=round(self.threshold, 4),
                predictionWindowHours=24,
                latencyMs=round(elapsed_ms, 3),
                topRiskFactors=[],
                topMitigatingFactors=[],
            )

    def predict_batch(
        self,
        items: List[TelemetryInput],
        include_explanations: bool = False,
        top_k: int = 3,
    ) -> BatchPredictionResponse:
        """Scores a batch of device observations."""
        t0 = time.perf_counter()
        predictions: List[PredictionResponse] = []
        high_risk_count = 0

        for item in items:
            pred = self.predict_single(
                item=item,
                include_explanations=include_explanations,
                top_k=top_k,
            )
            if pred.riskLevel == "HIGH":
                high_risk_count += 1
            predictions.append(pred)

        batch_latency_ms = (time.perf_counter() - t0) * 1000.0
        return BatchPredictionResponse(
            count=len(predictions),
            highRiskCount=high_risk_count,
            batchLatencyMs=round(batch_latency_ms, 2),
            predictions=predictions,
        )


# Global singleton instance created on module load
engine: Optional[PredictionEngine] = None


def get_engine() -> PredictionEngine:
    """Dependency injection helper returning the active PredictionEngine."""
    global engine
    if engine is None:
        engine = PredictionEngine()
    return engine
