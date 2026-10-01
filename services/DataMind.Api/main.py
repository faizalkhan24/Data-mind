"""DataMind Core Fleet Management & Analytics REST API.

Provides PostgreSQL/SQLite persistence, fleet device registration, telemetry ingestion,
prediction audit logging, operational alerting, and fleet health analytics.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys
import time
from typing import Any, AsyncGenerator, List, Optional

# Ensure repository root and service dir are on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SERVICE_DIR = Path(__file__).resolve().parent
if str(_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVICE_DIR))

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, init_db
from models import Device
from repositories import (
    AlertRepository,
    DeviceRepository,
    PredictionRepository,
    TelemetryRepository,
)
from schemas import (
    AlertResponse,
    AlertUpdate,
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    FleetSummaryResponse,
    PredictionLogCreate,
    PredictionLogResponse,
    TelemetryCreate,
    TelemetryResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ensures database schema is initialized on application startup."""
    logger.info("Starting %s (v%s)...", settings.app_name, settings.app_version)
    await init_db()
    yield
    logger.info("Shutting down %s...", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Core fleet management, telemetry persistence, prediction audit trail, and failure alerting API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Any) -> Response:
    """Measures HTTP request execution duration."""
    start_time = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Readiness probe for the Core API service."""
    return {
        "status": "HEALTHY",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": settings.database_url.split(":///")[0],
    }


# ==============================================================================
# Device Management Endpoints
# ==============================================================================

@app.get(f"{settings.api_prefix}/devices", response_model=List[DeviceResponse], tags=["Devices"])
async def list_devices(
    status: Optional[str] = Query(None, description="Filter by device status (ACTIVE, MAINTENANCE, DECOMMISSIONED)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[DeviceResponse]:
    """Lists hardware devices in the fleet."""
    repo = DeviceRepository(db)
    devices = await repo.list_all(status=status, limit=limit, offset=offset)
    return devices


@app.post(
    f"{settings.api_prefix}/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Devices"],
)
async def register_device(
    payload: DeviceCreate,
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """Registers a new hardware device into the fleet catalog."""
    repo = DeviceRepository(db)
    existing = await repo.get_by_device_id(payload.device_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device with ID '{payload.device_id}' is already registered.",
        )
    device = await repo.create(payload)
    return device


@app.get(f"{settings.api_prefix}/devices/{{device_id}}", response_model=DeviceResponse, tags=["Devices"])
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """Retrieves metadata for a specific hardware device."""
    repo = DeviceRepository(db)
    device = await repo.get_by_device_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )
    return device


@app.patch(f"{settings.api_prefix}/devices/{{device_id}}", response_model=DeviceResponse, tags=["Devices"])
async def update_device_status(
    device_id: str,
    payload: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """Updates device operational status or firmware version."""
    repo = DeviceRepository(db)
    device = await repo.update_status(device_id, payload)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found.",
        )
    return device


# ==============================================================================
# Telemetry Ingestion Endpoints
# ==============================================================================

@app.post(
    f"{settings.api_prefix}/devices/{{device_id}}/telemetry",
    response_model=TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Telemetry"],
)
async def ingest_telemetry(
    device_id: str,
    payload: TelemetryCreate,
    db: AsyncSession = Depends(get_db),
) -> TelemetryResponse:
    """Ingests a hardware telemetry event for a device."""
    device_repo = DeviceRepository(db)
    device = await device_repo.get_by_device_id(device_id)
    if not device:
        # Auto-provision device if not already registered
        device = await device_repo.create(DeviceCreate(device_id=device_id))

    telemetry_repo = TelemetryRepository(db)
    reading = await telemetry_repo.add_reading(device_id, payload)
    return reading


@app.get(
    f"{settings.api_prefix}/devices/{{device_id}}/telemetry",
    response_model=List[TelemetryResponse],
    tags=["Telemetry"],
)
async def get_telemetry_history(
    device_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> List[TelemetryResponse]:
    """Retrieves recent telemetry history for a device ordered newest first."""
    repo = TelemetryRepository(db)
    readings = await repo.get_history(device_id, limit=limit)
    return readings


# ==============================================================================
# Prediction Audit & Failure Alerting Endpoints
# ==============================================================================

@app.post(
    f"{settings.api_prefix}/devices/{{device_id}}/predictions",
    response_model=PredictionLogResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Predictions"],
)
async def record_prediction(
    device_id: str,
    payload: PredictionLogCreate,
    db: AsyncSession = Depends(get_db),
) -> PredictionLogResponse:
    """Logs a model prediction and triggers operational alerts if HIGH risk is detected."""
    pred_repo = PredictionRepository(db)
    log = await pred_repo.log_prediction(payload)

    # Automated alerting threshold: if HIGH risk detected, open a CRITICAL alert
    if payload.risk_level == "HIGH":
        alert_repo = AlertRepository(db)
        await alert_repo.create_alert(
            device_id=device_id,
            alert_level="CRITICAL",
            probability=payload.failure_probability,
            summary=f"Automated Alert: Impending failure predicted with {payload.failure_probability:.1%} probability.",
        )

    return log


@app.get(
    f"{settings.api_prefix}/devices/{{device_id}}/predictions",
    response_model=List[PredictionLogResponse],
    tags=["Predictions"],
)
async def get_device_predictions(
    device_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[PredictionLogResponse]:
    """Retrieves historical prediction audit trail for a device."""
    repo = PredictionRepository(db)
    return await repo.get_device_history(device_id, limit=limit)


@app.get(f"{settings.api_prefix}/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by alert status (OPEN, ACKNOWLEDGED, RESOLVED)"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[AlertResponse]:
    """Lists operational failure alerts."""
    repo = AlertRepository(db)
    return await repo.list_alerts(status=status, limit=limit)


@app.patch(f"{settings.api_prefix}/alerts/{{alert_id}}", response_model=AlertResponse, tags=["Alerts"])
async def update_alert_status(
    alert_id: int,
    payload: AlertUpdate,
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Acknowledges or resolves an operational failure alert."""
    repo = AlertRepository(db)
    alert = await repo.update_status(alert_id, payload.status)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert #{alert_id} not found.",
        )
    return alert


@app.get(f"{settings.api_prefix}/fleet/summary", response_model=FleetSummaryResponse, tags=["Analytics"])
async def get_fleet_summary(db: AsyncSession = Depends(get_db)) -> FleetSummaryResponse:
    """Computes real-time fleet health metrics, alert counts, and high-risk device totals."""
    # Count total devices by status
    stmt_total = select(func.count(Device.id))
    stmt_active = select(func.count(Device.id)).where(Device.status == "ACTIVE")
    stmt_maint = select(func.count(Device.id)).where(Device.status == "MAINTENANCE")
    stmt_decom = select(func.count(Device.id)).where(Device.status == "DECOMMISSIONED")

    r_total = await db.execute(stmt_total)
    r_act = await db.execute(stmt_active)
    r_mnt = await db.execute(stmt_maint)
    r_dcm = await db.execute(stmt_decom)

    alert_repo = AlertRepository(db)
    open_alerts, crit_alerts = await alert_repo.count_by_status_and_level()

    pred_repo = PredictionRepository(db)
    high_risk_count = await pred_repo.count_high_risk_devices()

    return FleetSummaryResponse(
        totalDevices=int(r_total.scalar() or 0),
        activeDevices=int(r_act.scalar() or 0),
        maintenanceDevices=int(r_mnt.scalar() or 0),
        decommissionedDevices=int(r_dcm.scalar() or 0),
        openAlertsCount=open_alerts,
        criticalAlertsCount=crit_alerts,
        highRiskDevicesCount=high_risk_count,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.DataMind.Api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
