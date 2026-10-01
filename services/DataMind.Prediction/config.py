"""Configuration settings for DataMind Prediction API service."""

from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass
class ServiceSettings:
    """Service configuration loaded from environment or defaults."""

    app_name: str = "DataMind Prediction Service"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    model_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("MODEL_PATH", "ml/models/best_model_xgboost.joblib")
        )
    )
    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    default_decision_threshold: float = 0.7173
    sla_max_latency_ms: float = 5.0


settings = ServiceSettings()
