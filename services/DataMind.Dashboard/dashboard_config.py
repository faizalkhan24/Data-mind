"""Configuration settings for DataMind Operations Dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field

_CURRENT_DIR = Path(__file__).resolve().parent
_STATIC_DIR = (_CURRENT_DIR / "static").as_posix()


class DashboardSettings(BaseModel):
    """Dashboard server configuration and backend service discovery."""

    app_name: str = "DataMind Fleet Health Console"
    app_version: str = "1.0.0.0"
    static_dir: str = _STATIC_DIR

    # Downstream microservice endpoints
    api_url: str = Field(
        default=os.getenv("DATAMIND_API_URL", "http://localhost:8001"),
        description="DataMind Core Persistence API URL",
    )
    prediction_url: str = Field(
        default=os.getenv("DATAMIND_PREDICTION_URL", "http://localhost:8000"),
        description="DataMind Real-Time Inference API URL",
    )
    ingestion_url: str = Field(
        default=os.getenv("DATAMIND_INGESTION_URL", "http://localhost:8002"),
        description="DataMind Streaming Ingestion API URL",
    )

    host: str = os.getenv("DATAMIND_DASHBOARD_HOST", "0.0.0.0")
    port: int = int(os.getenv("DATAMIND_DASHBOARD_PORT", "8003"))


settings = DashboardSettings()
