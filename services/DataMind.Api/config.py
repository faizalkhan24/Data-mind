"""Configuration settings for DataMind Core Fleet & Persistence API."""

from dataclasses import dataclass, field
import os
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_DEFAULT_DB_PATH = (_DATA_DIR / "datamind.db").as_posix()


@dataclass
class ApiSettings:
    """Settings loaded from environment variables or sensible local defaults."""

    app_name: str = "DataMind Fleet & Analytics API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"
        )
    )
    prediction_service_url: str = field(
        default_factory=lambda: os.getenv("PREDICTION_SERVICE_URL", "http://localhost:8000")
    )
    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8001")))
    echo_sql: bool = field(
        default_factory=lambda: os.getenv("ECHO_SQL", "false").lower() == "true"
    )


settings = ApiSettings()
