"""DataMind Streaming Ingestion REST & Event Service.

Exposes endpoints for streaming IoT telemetry ingestion, real-time sliding window
feature enrichment, buffer inspection, and throughput metrics.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys
import time
from typing import AsyncGenerator, Optional

# Ensure repository root and service dir are on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SERVICE_DIR = Path(__file__).resolve().parent
if str(_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVICE_DIR))

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from ingestion_config import settings
from queue_worker import StreamQueueWorker
from schemas import (
    BatchIngestRequest,
    BatchIngestResponse,
    DeviceWindowState,
    IngestionResponse,
    RawTelemetryReading,
    StreamStatsResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Global streaming queue worker instance
worker = StreamQueueWorker()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages worker startup and shutdown lifecycle."""
    logger.info("Starting %s (v%s)...", settings.app_name, settings.app_version)
    await worker.start()
    yield
    logger.info("Shutting down %s...", settings.app_name)
    await worker.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-time IoT telemetry streaming ingestion, queue buffer, and sliding window feature computation.",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next) -> Response:
    """Instruments response with server processing latency in milliseconds."""
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Readiness and liveness probe."""
    return {
        "status": "HEALTHY",
        "service": settings.app_name,
        "version": settings.app_version,
        "activeBuffers": worker.buffer_manager.active_device_count,
    }


@app.post(
    "/api/v1/stream/telemetry",
    response_model=IngestionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Streaming Ingestion"],
)
async def ingest_stream_event(reading: RawTelemetryReading) -> IngestionResponse:
    """Ingests a single streaming telemetry event and computes real-time 25-feature vector."""
    return worker.process_immediate(reading)


@app.post(
    "/api/v1/stream/batch",
    response_model=BatchIngestResponse,
    status_code=status.HTTP_200_OK,
    tags=["Streaming Ingestion"],
)
async def ingest_batch_events(batch: BatchIngestRequest) -> BatchIngestResponse:
    """Ingests and enriches a batch of telemetry events in high-throughput mode."""
    return worker.process_batch(batch.readings)


@app.get(
    "/api/v1/stream/devices/{device_id}/window",
    response_model=DeviceWindowState,
    tags=["Sliding Window Buffer"],
)
async def get_device_window_state(device_id: str) -> DeviceWindowState:
    """Inspects the current state of a device's in-memory sliding window buffer."""
    state = worker.buffer_manager.get_window_state(device_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} has no active sliding window buffer.",
        )
    return state


@app.delete(
    "/api/v1/stream/buffers",
    tags=["Sliding Window Buffer"],
)
async def clear_all_buffers() -> dict:
    """Clears all in-memory device buffers and resets worker state."""
    worker.buffer_manager.clear()
    return {"status": "SUCCESS", "message": "All device sliding window buffers cleared."}


@app.get(
    "/api/v1/stream/stats",
    response_model=StreamStatsResponse,
    tags=["Worker Metrics"],
)
async def get_stream_stats() -> StreamStatsResponse:
    """Retrieves operational throughput and queue latency statistics."""
    return worker.get_stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
