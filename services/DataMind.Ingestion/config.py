"""Configuration settings for DataMind Streaming Ingestion Service."""

from __future__ import annotations

import os
from pydantic import BaseModel, Field


class IngestionSettings(BaseModel):
    """Configuration parameters for streaming buffer and event queue."""

    app_name: str = "DataMind Streaming Ingestion Service"
    app_version: str = "1.0.0"

    # Streaming buffer & window configuration
    window_max_points: int = Field(
        default=int(os.getenv("DATAMIND_WINDOW_MAX_POINTS", "100")),
        description="Maximum historical observations retained per device in memory buffer",
    )
    
    # Asynchronous queue settings
    queue_max_size: int = Field(
        default=int(os.getenv("DATAMIND_QUEUE_MAX_SIZE", "10000")),
        description="Maximum capacity of asynchronous ingestion queue",
    )
    worker_concurrency: int = Field(
        default=int(os.getenv("DATAMIND_WORKER_CONCURRENCY", "2")),
        description="Number of concurrent background stream consumer workers",
    )

    # Downstream service integration
    prediction_service_url: str = Field(
        default=os.getenv("DATAMIND_PREDICTION_URL", "http://localhost:8000"),
        description="Base URL for DataMind.Prediction REST service",
    )
    fleet_api_url: str = Field(
        default=os.getenv("DATAMIND_FLEET_API_URL", "http://localhost:8001"),
        description="Base URL for DataMind.Api fleet persistence service",
    )
    enable_auto_inference: bool = Field(
        default=os.getenv("DATAMIND_ENABLE_AUTO_INFERENCE", "false").lower() in ("true", "1"),
        description="Whether to forward enriched vectors to prediction service",
    )

    # Network server
    host: str = os.getenv("DATAMIND_INGESTION_HOST", "0.0.0.0")
    port: int = int(os.getenv("DATAMIND_INGESTION_PORT", "8002"))


settings = IngestionSettings()
