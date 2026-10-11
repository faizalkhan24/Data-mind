"""Pydantic schemas and DTOs for streaming ingestion and feature enrichment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from services.security_auth import (
    sanitize_device_id,  # [VALIDATION-1]
    parse_iso_timestamp,  # [VALIDATION-2]
    validate_finite_number,  # [VALIDATION-3]
)


def utcnow() -> datetime:
    """Helper returning current UTC datetime."""
    return datetime.now(timezone.utc)


class RawTelemetryReading(BaseModel):
    """Raw sensory reading ingested from an IoT device stream."""

    # [VALIDATION-1]: Strict alphanumeric identifier constraint
    device_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$", example="DEV-00042", description="Unique hardware identifier")
    # [VALIDATION-2]: Strict ISO-8601 validation
    timestamp: datetime = Field(default_factory=utcnow, description="Observation timestamp")
    # [VALIDATION-3]: Bounded ranges and finite checks (no NaN/Inf)
    temperature: float = Field(..., ge=-40.0, le=150.0, example=45.2, description="Die temperature (°C)")
    voltage: float = Field(..., ge=1.0, le=10.0, example=3.75, description="Power rail voltage (V)")
    current: float = Field(..., ge=0.0, le=10.0, example=1.25, description="Current draw (A)")
    battery_level: float = Field(..., ge=0.0, le=100.0, example=85.0, description="Battery level (%)")
    network_quality: float = Field(..., ge=0.0, le=100.0, example=92.0, description="Signal quality (%)")
    error_count: float = Field(0.0, ge=0.0, example=0.0, description="Bus errors observed in period")
    restart_count: float = Field(0.0, ge=0.0, example=0.0, description="Cumulative restart count")
    uptime_hours: float = Field(..., ge=0.0, example=120.5, description="Continuous uptime in hours")
    firmware_version: str = Field("1.2.0", description="Firmware version string")

    @field_validator("device_id")
    def validate_device_id_syntax(cls, v: str) -> str:
        # [VALIDATION-1]: Sanitizes and verifies device identifier pattern
        return sanitize_device_id(v)

    @field_validator("timestamp", mode="before")
    def validate_timestamp_format(cls, v: Any) -> Any:
        # [VALIDATION-2]: Validates ISO-8601 string parsing
        if isinstance(v, str):
            return parse_iso_timestamp(v)
        return v

    @field_validator("temperature", "voltage", "current", "battery_level", "network_quality", "error_count", "restart_count", "uptime_hours")
    def validate_metrics_finite(cls, v: float, info) -> float:
        # [VALIDATION-3]: Guard against NaN and Inf attacks
        return validate_finite_number(v, info.field_name or "metric")

    model_config = {
        "json_schema_extra": {
            "example": {
                "device_id": "DEV-00042",
                "timestamp": "2026-01-04T12:00:00Z",
                "temperature": 45.2,
                "voltage": 3.75,
                "current": 1.25,
                "battery_level": 85.0,
                "network_quality": 92.0,
                "error_count": 0.0,
                "restart_count": 0.0,
                "uptime_hours": 120.5,
                "firmware_version": "1.2.0",
            }
        }
    }


class EnrichedTelemetryPayload(BaseModel):
    """The 25-feature engineered representation computed from sliding window buffer."""

    device_id: str
    timestamp: datetime

    # Instantaneous signals
    temperature: float
    voltage: float
    current: float
    battery_level: float
    network_quality: float
    error_count: float
    restart_count: float
    uptime_hours: float

    # Thermal dynamics
    temperature_mean_6h: float
    temperature_mean_24h: float
    temperature_std_6h: float
    temperature_change_1h: float

    # Electrical & Power dynamics
    voltage_mean_6h: float
    voltage_min_6h: float
    voltage_std_6h: float
    current_mean_6h: float

    # Error & Watchdog dynamics
    error_count_6h: float
    error_count_24h: float
    restart_count_24h: float

    # Battery & Connectivity
    battery_change_24h: float
    network_quality_mean_6h: float

    # Longevity
    device_age_hours: float

    # Encoded Firmware
    firmware_version_1_0_0: float = Field(alias="firmware_version_1.0.0")
    firmware_version_1_1_0: float = Field(alias="firmware_version_1.1.0")
    firmware_version_1_2_0: float = Field(alias="firmware_version_1.2.0")

    model_config = {
        "populate_by_name": True,
    }


class IngestionResponse(BaseModel):
    """Result of single telemetry stream event ingestion."""

    device_id: str
    status: str = Field(..., example="PROCESSED", description="'PROCESSED' or 'QUEUED'")
    timestamp: datetime
    enrichment_latency_ms: float = Field(..., description="Sliding window feature calculation time in ms")
    features: Optional[EnrichedTelemetryPayload] = None
    prediction: Optional[Dict[str, Any]] = None


class BatchIngestRequest(BaseModel):
    """Batch ingestion request containing multiple streaming readings."""

    readings: List[RawTelemetryReading] = Field(..., min_length=1)


class BatchIngestResponse(BaseModel):
    """Response summary for batch ingestion."""

    total_received: int
    processed_count: int
    failed_count: int
    total_time_ms: float
    results: List[IngestionResponse]


class DeviceWindowState(BaseModel):
    """Current state of a device's in-memory sliding window buffer."""

    device_id: str
    points_in_window: int
    capacity: int
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    latest_features: Optional[EnrichedTelemetryPayload] = None


class StreamStatsResponse(BaseModel):
    """Real-time operational metrics for the streaming ingestion worker."""

    events_ingested: int
    events_processed: int
    queue_depth: int
    active_device_buffers: int
    avg_enrichment_latency_ms: float
    uptime_seconds: float
