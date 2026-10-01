"""Repository pattern data access layer for DataMind."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import List, Optional, Tuple

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import Device, FailureAlert, PredictionLog, TelemetryReading, utcnow
from schemas import (
    DeviceCreate,
    DeviceUpdate,
    PredictionLogCreate,
    TelemetryCreate,
)


class DeviceRepository:
    """Data access methods for hardware device fleet."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_device_id(self, device_id: str) -> Optional[Device]:
        """Fetches a device by unique hardware ID."""
        stmt = select(Device).where(Device.device_id == device_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, device_in: DeviceCreate) -> Device:
        """Registers a new device in the fleet."""
        device = Device(
            device_id=device_in.device_id,
            firmware_version=device_in.firmware_version,
            status=device_in.status,
        )
        self.session.add(device)
        await self.session.flush()
        return device

    async def list_all(
        self, status: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Device]:
        """Lists fleet devices with optional status filter."""
        stmt = select(Device).order_by(Device.device_id)
        if status:
            stmt = stmt.where(Device.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, device_id: str, device_update: DeviceUpdate) -> Optional[Device]:
        """Updates device metadata or operational status."""
        device = await self.get_by_device_id(device_id)
        if not device:
            return None
        if device_update.status is not None:
            device.status = device_update.status
        if device_update.firmware_version is not None:
            device.firmware_version = device_update.firmware_version
        device.updated_at = utcnow()
        await self.session.flush()
        return device


class TelemetryRepository:
    """Data access methods for time-series telemetry events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_reading(self, device_id: str, telemetry_in: TelemetryCreate) -> TelemetryReading:
        """Inserts a single telemetry observation."""
        reading = TelemetryReading(
            device_id=device_id,
            timestamp=telemetry_in.timestamp,
            temperature=telemetry_in.temperature,
            voltage=telemetry_in.voltage,
            current=telemetry_in.current,
            battery_level=telemetry_in.battery_level,
            network_quality=telemetry_in.network_quality,
            error_count=telemetry_in.error_count,
            restart_count=telemetry_in.restart_count,
            uptime_hours=telemetry_in.uptime_hours,
        )
        self.session.add(reading)
        await self.session.flush()
        return reading

    async def get_history(self, device_id: str, limit: int = 100) -> List[TelemetryReading]:
        """Retrieves recent telemetry observations for a device ordered newest first."""
        stmt = (
            select(TelemetryReading)
            .where(TelemetryReading.device_id == device_id)
            .order_by(desc(TelemetryReading.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PredictionRepository:
    """Data access methods for model prediction audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_prediction(self, pred_in: PredictionLogCreate) -> PredictionLog:
        """Persists a prediction event."""
        log = PredictionLog(
            device_id=pred_in.device_id,
            timestamp=pred_in.timestamp,
            failure_probability=pred_in.failure_probability,
            prediction_label=pred_in.prediction_label,
            risk_level=pred_in.risk_level,
            latency_ms=pred_in.latency_ms,
            top_risk_factors_json=pred_in.top_risk_factors_json,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_device_history(self, device_id: str, limit: int = 50) -> List[PredictionLog]:
        """Fetches prediction logs for a specific device."""
        stmt = (
            select(PredictionLog)
            .where(PredictionLog.device_id == device_id)
            .order_by(desc(PredictionLog.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_high_risk_devices(self) -> int:
        """Counts distinct devices flagged with HIGH risk in their latest prediction."""
        stmt = (
            select(func.count(func.distinct(PredictionLog.device_id)))
            .where(PredictionLog.risk_level == "HIGH")
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)


class AlertRepository:
    """Data access methods for failure warnings and alarms."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_alert(
        self,
        device_id: str,
        alert_level: str,
        probability: float,
        summary: str,
    ) -> FailureAlert:
        """Creates a new failure alert."""
        alert = FailureAlert(
            device_id=device_id,
            alert_level=alert_level,
            status="OPEN",
            failure_probability=probability,
            diagnostic_summary=summary,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def list_alerts(
        self, status: Optional[str] = None, limit: int = 50
    ) -> List[FailureAlert]:
        """Lists alerts with optional status filter."""
        stmt = select(FailureAlert).order_by(desc(FailureAlert.created_at))
        if status:
            stmt = stmt.where(FailureAlert.status == status)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, alert_id: int, new_status: str) -> Optional[FailureAlert]:
        """Updates alert status (e.g. ACKNOWLEDGED, RESOLVED)."""
        stmt = select(FailureAlert).where(FailureAlert.id == alert_id)
        result = await self.session.execute(stmt)
        alert = result.scalars().first()
        if not alert:
            return None
        alert.status = new_status
        if new_status == "RESOLVED":
            alert.resolved_at = utcnow()
        await self.session.flush()
        return alert

    async def count_by_status_and_level(self) -> Tuple[int, int]:
        """Returns (open_alerts_count, critical_alerts_count)."""
        stmt_open = select(func.count(FailureAlert.id)).where(FailureAlert.status == "OPEN")
        stmt_crit = (
            select(func.count(FailureAlert.id))
            .where(FailureAlert.status == "OPEN")
            .where(FailureAlert.alert_level == "CRITICAL")
        )
        r_open = await self.session.execute(stmt_open)
        r_crit = await self.session.execute(stmt_crit)
        return int(r_open.scalar() or 0), int(r_crit.scalar() or 0)
