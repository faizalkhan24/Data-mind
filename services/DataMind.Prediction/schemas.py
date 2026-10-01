"""Pydantic request and response schemas for DataMind Prediction API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RiskFactorDto(BaseModel):
    """Diagnostic operational risk or mitigating factor."""

    category: str = Field(..., description="Operational failure mechanism domain")
    featureName: str = Field(..., description="Engineered telemetry feature name")
    featureValue: float = Field(..., description="Measured feature value")
    attributionScore: float = Field(..., description="SHAP log-odds attribution contribution")
    description: str = Field(..., description="Human-readable operational diagnostic")


class TelemetryInput(BaseModel):
    """Raw and engineered telemetry payload for a single device timestamp."""

    device_id: str = Field(..., example="DEV-00042", description="Unique hardware identifier")
    timestamp: Optional[str] = Field(None, example="2026-01-04T12:00:00", description="ISO-8601 observation timestamp")

    # Instantaneous primary measurements
    temperature: float = Field(..., ge=-40.0, le=150.0, example=45.2, description="Die/chassis temperature (°C)")
    voltage: float = Field(..., ge=1.0, le=10.0, example=3.75, description="Power rail voltage (V)")
    current: float = Field(..., ge=0.0, le=10.0, example=1.25, description="Current draw (A)")
    battery_level: float = Field(..., ge=0.0, le=100.0, example=85.0, description="Battery state of charge (%)")
    network_quality: float = Field(..., ge=0.0, le=100.0, example=92.0, description="Wireless link quality (%)")
    error_count: float = Field(0.0, ge=0.0, example=1.0, description="Hardware/bus errors in current hour")
    restart_count: float = Field(0.0, ge=0.0, example=0.0, description="Cumulative watchdog reboots")
    uptime_hours: float = Field(..., ge=0.0, example=120.5, description="Continuous uptime since boot (hours)")

    # Temporal & Rolling window features (defaults populated if not pre-aggregated)
    temperature_mean_6h: Optional[float] = Field(None, description="6h rolling mean temperature")
    temperature_mean_24h: Optional[float] = Field(None, description="24h rolling mean temperature")
    temperature_std_6h: Optional[float] = Field(0.0, description="6h temperature std dev")
    temperature_change_1h: Optional[float] = Field(0.0, description="1h rate of temperature change")
    voltage_mean_6h: Optional[float] = Field(None, description="6h rolling mean voltage")
    voltage_min_6h: Optional[float] = Field(None, description="6h minimum voltage (sag detector)")
    voltage_std_6h: Optional[float] = Field(0.0, description="6h voltage rail jitter")
    current_mean_6h: Optional[float] = Field(None, description="6h rolling mean current")
    error_count_6h: Optional[float] = Field(None, description="Cumulative errors in past 6h")
    error_count_24h: Optional[float] = Field(None, description="Cumulative errors in past 24h")
    restart_count_24h: Optional[float] = Field(0.0, description="Watchdog restarts in past 24h")
    battery_change_24h: Optional[float] = Field(0.0, description="24h battery capacity change (%)")
    network_quality_mean_6h: Optional[float] = Field(None, description="6h link quality mean")
    device_age_hours: Optional[float] = Field(None, description="Total lifetime device operation")

    # Firmware versions (string or one-hot)
    firmware_version: Optional[str] = Field("1.2.0", description="Firmware version string")
    firmware_version_1_0_0: Optional[float] = Field(None, alias="firmware_version_1.0.0")
    firmware_version_1_1_0: Optional[float] = Field(None, alias="firmware_version_1.1.0")
    firmware_version_1_2_0: Optional[float] = Field(None, alias="firmware_version_1.2.0")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "device_id": "DEV-00042",
                "timestamp": "2026-01-04T12:00:00",
                "temperature": 43.5,
                "voltage": 3.72,
                "current": 1.22,
                "battery_level": 88.0,
                "network_quality": 94.0,
                "error_count": 0.0,
                "restart_count": 1.0,
                "uptime_hours": 340.0,
                "firmware_version": "1.2.0",
            }
        },
    }

    def to_feature_vector(self, feature_names: List[str]) -> Dict[str, float]:
        """Converts incoming telemetry into the aligned 25-feature predictor vector."""
        # Auto-fill rolling aggregates from instantaneous measurements if omitted
        t_mean_6h = self.temperature_mean_6h if self.temperature_mean_6h is not None else self.temperature
        t_mean_24h = self.temperature_mean_24h if self.temperature_mean_24h is not None else self.temperature
        v_mean_6h = self.voltage_mean_6h if self.voltage_mean_6h is not None else self.voltage
        v_min_6h = self.voltage_min_6h if self.voltage_min_6h is not None else self.voltage
        c_mean_6h = self.current_mean_6h if self.current_mean_6h is not None else self.current
        err_6h = self.error_count_6h if self.error_count_6h is not None else self.error_count
        err_24h = self.error_count_24h if self.error_count_24h is not None else self.error_count * 2.0
        net_6h = self.network_quality_mean_6h if self.network_quality_mean_6h is not None else self.network_quality
        age = self.device_age_hours if self.device_age_hours is not None else self.uptime_hours

        # Firmware one-hot mapping
        fw = self.firmware_version or "1.2.0"
        fw_100 = 1.0 if fw == "1.0.0" else 0.0
        fw_110 = 1.0 if fw == "1.1.0" else 0.0
        fw_120 = 1.0 if fw == "1.2.0" else 0.0

        raw_map = {
            "temperature": float(self.temperature),
            "voltage": float(self.voltage),
            "current": float(self.current),
            "battery_level": float(self.battery_level),
            "network_quality": float(self.network_quality),
            "error_count": float(self.error_count),
            "restart_count": float(self.restart_count),
            "uptime_hours": float(self.uptime_hours),
            "temperature_mean_6h": float(t_mean_6h),
            "temperature_mean_24h": float(t_mean_24h),
            "temperature_std_6h": float(self.temperature_std_6h or 0.0),
            "temperature_change_1h": float(self.temperature_change_1h or 0.0),
            "voltage_mean_6h": float(v_mean_6h),
            "voltage_min_6h": float(v_min_6h),
            "voltage_std_6h": float(self.voltage_std_6h or 0.0),
            "current_mean_6h": float(c_mean_6h),
            "error_count_6h": float(err_6h),
            "error_count_24h": float(err_24h),
            "restart_count_24h": float(self.restart_count_24h or 0.0),
            "battery_change_24h": float(self.battery_change_24h or 0.0),
            "network_quality_mean_6h": float(net_6h),
            "device_age_hours": float(age),
            "firmware_version_1.0.0": float(self.firmware_version_1_0_0 if self.firmware_version_1_0_0 is not None else fw_100),
            "firmware_version_1.1.0": float(self.firmware_version_1_1_0 if self.firmware_version_1_1_0 is not None else fw_110),
            "firmware_version_1.2.0": float(self.firmware_version_1_2_0 if self.firmware_version_1_2_0 is not None else fw_120),
        }

        return {k: raw_map.get(k, 0.0) for k in feature_names}


class PredictionResponse(BaseModel):
    """Real-time prediction outcome with diagnostic explanation."""

    deviceId: str = Field(..., description="Unique hardware identifier")
    timestamp: Optional[str] = Field(None, description="Observation timestamp")
    failureProbability: float = Field(..., description="Estimated probability of failure within 24 hours")
    predictionLabel: int = Field(..., description="Binary classification (1 = failure predicted, 0 = normal)")
    riskLevel: str = Field(..., description="Operational risk tier: LOW, MEDIUM, HIGH")
    decisionThreshold: float = Field(..., description="Threshold applied to failureProbability")
    predictionWindowHours: int = Field(24, description="Forward predictive horizon")
    latencyMs: float = Field(..., description="Single-sample end-to-end inference execution time")
    topRiskFactors: List[RiskFactorDto] = Field(default_factory=list, description="Primary positive drivers pushing toward failure")
    topMitigatingFactors: List[RiskFactorDto] = Field(default_factory=list, description="Primary mitigating factors pulling toward nominal")


class BatchPredictionRequest(BaseModel):
    """Request payload containing a list of telemetry records for batch scoring."""

    items: List[TelemetryInput] = Field(..., description="List of device telemetry inputs (max 500)")


class BatchPredictionResponse(BaseModel):
    """Batch prediction result containing predictions and summary statistics."""

    count: int = Field(..., description="Total devices evaluated")
    highRiskCount: int = Field(..., description="Total devices classified as HIGH risk")
    batchLatencyMs: float = Field(..., description="Total batch execution elapsed time")
    predictions: List[PredictionResponse] = Field(..., description="Individual device predictions")


class HealthStatusResponse(BaseModel):
    """Readiness and liveness probe response."""

    status: str = Field("HEALTHY", description="Service health state")
    modelLoaded: bool = Field(..., description="Indicates if ML model artifact is loaded in memory")
    modelVersion: str = Field(..., description="Active production model version")
    uptimeSeconds: float = Field(..., description="Service uptime elapsed")


class ModelMetadataResponse(BaseModel):
    """Metadata regarding the loaded production model."""

    modelName: str
    algorithm: str
    featureCount: int
    features: List[str]
    decisionThreshold: float
    testMetrics: Dict[str, float]
