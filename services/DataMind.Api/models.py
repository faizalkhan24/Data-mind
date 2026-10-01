"""SQLAlchemy 2.0 ORM domain models for DataMind."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utcnow() -> datetime:
    """Helper returning current UTC datetime."""
    return datetime.now(timezone.utc)


class Device(Base):
    """IoT device hardware entity."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    firmware_version: Mapped[str] = mapped_column(String(32), default="1.2.0", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    telemetry_readings: Mapped[List["TelemetryReading"]] = relationship(
        "TelemetryReading", back_populates="device", cascade="all, delete-orphan"
    )
    prediction_logs: Mapped[List["PredictionLog"]] = relationship(
        "PredictionLog", back_populates="device", cascade="all, delete-orphan"
    )
    failure_alerts: Mapped[List["FailureAlert"]] = relationship(
        "FailureAlert", back_populates="device", cascade="all, delete-orphan"
    )


class TelemetryReading(Base):
    """Time-series hardware telemetry observation."""

    __tablename__ = "telemetry_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), index=True, nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    voltage: Mapped[float] = mapped_column(Float, nullable=False)
    current: Mapped[float] = mapped_column(Float, nullable=False)
    battery_level: Mapped[float] = mapped_column(Float, nullable=False)
    network_quality: Mapped[float] = mapped_column(Float, nullable=False)
    error_count: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    restart_count: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    uptime_hours: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="telemetry_readings")

    __table_args__ = (
        Index("ix_telemetry_device_time", "device_id", "timestamp"),
    )


class PredictionLog(Base):
    """Historical audit log of real-time failure predictions."""

    __tablename__ = "prediction_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), index=True, nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    failure_probability: Mapped[float] = mapped_column(Float, nullable=False)
    prediction_label: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    top_risk_factors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="prediction_logs")

    __table_args__ = (
        Index("ix_predictions_device_risk", "device_id", "risk_level"),
    )


class FailureAlert(Base):
    """Actionable failure alert triggered on high-risk prediction events."""

    __tablename__ = "failure_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), index=True, nullable=False
    )
    alert_level: Mapped[str] = mapped_column(String(16), default="CRITICAL", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", index=True, nullable=False)
    failure_probability: Mapped[float] = mapped_column(Float, nullable=False)
    diagnostic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="failure_alerts")

    __table_args__ = (
        Index("ix_alerts_device_status", "device_id", "status"),
    )
