"""Pydantic v2 schemas for DataMind Core Fleet & Persistence API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from services.security_auth import sanitize_device_id, validate_finite_number  # [VALIDATION-1], [VALIDATION-3]


class DeviceBase(BaseModel):
    """Base device fields."""

    # [VALIDATION-1]: Alphanumeric constraint + length limit to prevent injection
    device_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$", example="DEV-00042")
    firmware_version: str = Field("1.2.0", example="1.2.0")
    status: str = Field("ACTIVE", pattern=r"^(ACTIVE|MAINTENANCE|DECOMMISSIONED)$", example="ACTIVE")

    @field_validator("device_id")
    def validate_device_id(cls, v: str) -> str:
        # [VALIDATION-1]: Sanitizes and checks regex
        return sanitize_device_id(v)


class DeviceCreate(DeviceBase):
    """Payload to register a new device."""
    pass


class DeviceUpdate(BaseModel):
    """Payload to update device status or firmware."""

    firmware_version: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(ACTIVE|MAINTENANCE|DECOMMISSIONED)$", example="MAINTENANCE")


class DeviceResponse(DeviceBase):
    """Device details returned by API."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TelemetryCreate(BaseModel):
    """Single telemetry reading ingestion payload."""

    timestamp: datetime = Field(..., example="2026-01-04T12:00:00Z")
    temperature: float = Field(..., example=45.2)
    voltage: float = Field(..., example=3.75)
    current: float = Field(..., example=1.25)
    battery_level: float = Field(..., example=85.0)
    network_quality: float = Field(..., example=92.0)
    error_count: float = Field(0.0, example=1.0)
    restart_count: float = Field(0.0, example=0.0)
    uptime_hours: float = Field(..., example=120.5)

    @field_validator("temperature", "voltage", "current", "battery_level", "network_quality", "error_count", "restart_count", "uptime_hours")
    def validate_metrics_finite(cls, v: float, info) -> float:
        # [VALIDATION-3]: Prevent NaN, +Inf, -Inf poisoning in telemetry
        return validate_finite_number(v, info.field_name or "metric")


class TelemetryResponse(TelemetryCreate):
    """Persisted telemetry reading details."""

    id: int
    device_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionLogCreate(BaseModel):
    """Prediction outcome persistence payload."""

    device_id: str
    timestamp: datetime
    failure_probability: float
    prediction_label: int
    risk_level: str
    latency_ms: float
    top_risk_factors_json: Optional[str] = None


class PredictionLogResponse(PredictionLogCreate):
    """Persisted prediction record."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(BaseModel):
    """Failure alert response."""

    id: int
    device_id: str
    alert_level: str
    status: str
    failure_probability: float
    diagnostic_summary: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AlertUpdate(BaseModel):
    """Alert resolution update."""

    status: str = Field(..., example="RESOLVED")


class FleetSummaryResponse(BaseModel):
    """High-level fleet operational status."""

    totalDevices: int
    activeDevices: int
    maintenanceDevices: int
    decommissionedDevices: int
    openAlertsCount: int
    criticalAlertsCount: int
    highRiskDevicesCount: int
