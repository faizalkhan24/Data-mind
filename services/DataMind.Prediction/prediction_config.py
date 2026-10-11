"""Configuration settings for DataMind Prediction API service."""

from dataclasses import dataclass, field
import os
from pathlib import Path


_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parents[1]


def _resolve_model_path() -> Path:
    raw = os.getenv("MODEL_PATH", "ml/models/best_model_xgboost.joblib")
    p = Path(raw)
    if p.is_absolute() and p.exists():
        return p
    if (_REPO_ROOT / p).exists():
        return _REPO_ROOT / p
    if p.exists():
        return p.resolve()
    return _REPO_ROOT / p


@dataclass
class ServiceSettings:
    """Service configuration loaded from environment or defaults."""

    app_name: str = "DataMind Prediction Service"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    model_path: Path = field(default_factory=_resolve_model_path)
    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    default_decision_threshold: float = 0.7173
    sla_max_latency_ms: float = 5.0


settings = ServiceSettings()
