"""Shared Prometheus Observability & Telemetry Module for DataMind Microservices.

Instruments HTTP request counts, latency histograms, ML prediction metrics,
and streaming buffer diagnostics following standard Prometheus naming conventions.
"""

from __future__ import annotations

import time
from typing import Any, Callable
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
)

# Standard SLA-aligned latency buckets (in seconds): 0.5ms, 1ms, 2.5ms, 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s
LATENCY_BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)

# Global Metrics Definitions
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the service.",
    ["service", "method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request execution latency in seconds.",
    ["service", "method", "endpoint"],
    buckets=LATENCY_BUCKETS,
)

PREDICTION_LATENCY = Histogram(
    "datamind_prediction_latency_seconds",
    "Model inference latency in seconds (< 0.005s SLA target).",
    ["model_name"],
    buckets=LATENCY_BUCKETS,
)

PREDICTIONS_TOTAL = Counter(
    "datamind_predictions_total",
    "Total failure predictions scored by model risk category.",
    ["model_name", "risk_level"],
)

PREDICTION_PROBABILITY = Histogram(
    "datamind_prediction_risk_probability",
    "Distribution of scored failure probabilities [0.0 - 1.0].",
    ["model_name"],
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0),
)

ACTIVE_DEVICES = Gauge(
    "datamind_active_devices",
    "Current total active IoT hardware endpoints in fleet.",
)

ACTIVE_ALERTS = Gauge(
    "datamind_active_alerts",
    "Current open operational incidents by severity level.",
    ["severity"],
)

BUFFER_QUEUE_DEPTH = Gauge(
    "datamind_stream_buffer_depth",
    "Current unprocessed event count in streaming sliding window queue.",
)


def setup_metrics(app: FastAPI, service_name: str) -> None:
    """Configures Prometheus metrics endpoint and HTTP request tracking middleware."""

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable) -> Response:
        # Avoid recording metrics on metrics scrape itself
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time

        endpoint = request.url.path
        REQUEST_COUNT.labels(
            service=service_name,
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code),
        ).inc()

        REQUEST_LATENCY.labels(
            service=service_name,
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response

    @app.get("/metrics", tags=["Observability"], include_in_schema=False)
    async def metrics() -> Response:
        """Prometheus metrics scrape endpoint."""
        data = generate_latest(REGISTRY)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
