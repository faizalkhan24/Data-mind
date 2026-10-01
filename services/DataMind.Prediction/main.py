"""DataMind Real-Time Prediction API Service.

Production-grade FastAPI service serving device failure predictions (< 5 ms SLA)
with SHAP-powered explainability and automated health probes.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys
import time
from typing import Any, AsyncGenerator, Optional

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_SERVICE_DIR = Path(__file__).resolve().parent
if str(_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVICE_DIR))

from prediction_config import settings
from predictor import PredictionEngine, get_engine
from schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthStatusResponse,
    ModelMetadataResponse,
    PredictionResponse,
    TelemetryInput,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to initialize models on startup and cleanup on shutdown."""
    logger.info("Initializing %s (v%s)...", settings.app_name, settings.app_version)
    # Warm up prediction engine and verify model is cached
    try:
        engine = get_engine()
        logger.info(
            "Prediction Engine ready: Model loaded with %d features.",
            len(engine.feature_names),
        )
    except Exception as exc:
        logger.exception("Failed to initialize Prediction Engine during startup: %s", exc)
        raise exc
    yield
    logger.info("Shutting down %s...", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-time predictive maintenance API scoring hardware failure risk within 24 hours.",
    lifespan=lifespan,
)

# Enable CORS for frontend dashboard and developer tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Any) -> Response:
    """Measures total HTTP request processing duration and attaches X-Process-Time-Ms header."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
    return response


@app.get("/health", response_model=HealthStatusResponse, tags=["Health"])
async def health_check(engine: PredictionEngine = Depends(get_engine)) -> HealthStatusResponse:
    """Readiness and liveness probe checking in-memory model status."""
    is_ready = engine.is_ready()
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    uptime = time.time() - engine.start_time

    return JSONResponse(
        status_code=status_code,
        content=HealthStatusResponse(
            status="HEALTHY" if is_ready else "DEGRADED",
            modelLoaded=is_ready,
            modelVersion=settings.app_version,
            uptimeSeconds=round(uptime, 2),
        ).model_dump(),
    )


@app.get(f"{settings.api_prefix}/model/metadata", response_model=ModelMetadataResponse, tags=["Metadata"])
async def get_model_metadata(engine: PredictionEngine = Depends(get_engine)) -> ModelMetadataResponse:
    """Retrieves operational parameters, feature schema, and holdout test metrics."""
    return engine.get_metadata()


@app.post(
    f"{settings.api_prefix}/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Predictions"],
)
async def predict_device_failure(
    payload: TelemetryInput,
    include_explanations: bool = Query(
        True,
        description="Include SHAP diagnostic factors. Set False for ultra-fast sub-millisecond mode.",
    ),
    top_k: int = Query(
        4, ge=1, le=10, description="Maximum number of risk/mitigating factors to return"
    ),
    engine: PredictionEngine = Depends(get_engine),
) -> PredictionResponse:
    """Scores real-time device telemetry to predict likelihood of failure within the next 24 hours."""
    try:
        prediction = engine.predict_single(
            item=payload,
            include_explanations=include_explanations,
            top_k=top_k,
        )
        return prediction
    except Exception as exc:
        logger.exception("Error during single-device prediction: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failure: {str(exc)}",
        ) from exc


@app.post(
    f"{settings.api_prefix}/predict/batch",
    response_model=BatchPredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Predictions"],
)
async def predict_batch(
    payload: BatchPredictionRequest,
    include_explanations: bool = Query(
        False,
        description="Include SHAP explanations for batch items (default False for batch speed)",
    ),
    engine: PredictionEngine = Depends(get_engine),
) -> BatchPredictionResponse:
    """Batch scoring for multiple device telemetry observations."""
    if len(payload.items) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum limit of 500 items.",
        )

    try:
        batch_response = engine.predict_batch(
            items=payload.items,
            include_explanations=include_explanations,
        )
        return batch_response
    except Exception as exc:
        logger.exception("Error during batch prediction: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch inference failure: {str(exc)}",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.DataMind.Prediction.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
