"""Asynchronous Streaming Event Queue and Concurrent Processing Worker.

Pulls raw telemetry events from an asynchronous queue, executes feature enrichment
via the sliding window buffer, and delivers real-time inference telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

import httpx

from buffer import FleetBufferManager
from ingestion_config import settings
from schemas import (
    BatchIngestResponse,
    DeviceWindowState,
    EnrichedTelemetryPayload,
    IngestionResponse,
    RawTelemetryReading,
    StreamStatsResponse,
)

logger = logging.getLogger(__name__)


class StreamQueueWorker:
    """Asynchronous worker that ingests streaming events and computes rolling features."""

    def __init__(
        self,
        buffer_manager: Optional[FleetBufferManager] = None,
        prediction_client: Optional[Callable[[EnrichedTelemetryPayload], Any]] = None,
    ) -> None:
        self.buffer_manager = buffer_manager or FleetBufferManager(
            max_points_per_device=settings.window_max_points
        )
        self.prediction_client = prediction_client
        self.queue: asyncio.Queue[RawTelemetryReading] = asyncio.Queue(
            maxsize=settings.queue_max_size
        )
        self._worker_tasks: List[asyncio.Task[None]] = []
        self._running = False
        self._start_time = time.time()

        # Operational metrics
        self.events_ingested: int = 0
        self.events_processed: int = 0
        self.failed_count: int = 0
        self.total_enrichment_ms: float = 0.0

    async def start(self) -> None:
        """Starts background worker tasks."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        for i in range(settings.worker_concurrency):
            task = asyncio.create_task(self._worker_loop(worker_id=i))
            self._worker_tasks.append(task)
        logger.info(
            "StreamQueueWorker started with %d workers (queue_max_size=%d).",
            settings.worker_concurrency,
            settings.queue_max_size,
        )

    async def stop(self) -> None:
        """Gracefully stops background worker tasks and drains remaining events."""
        if not self._running:
            return
        self._running = False
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        logger.info("StreamQueueWorker stopped.")

    async def enqueue(self, reading: RawTelemetryReading) -> None:
        """Enqueues a raw telemetry reading for asynchronous processing."""
        await self.queue.put(reading)
        self.events_ingested += 1

    def process_immediate(self, reading: RawTelemetryReading) -> IngestionResponse:
        """Synchronously enriches a telemetry event through the sliding window buffer."""
        t0 = time.perf_counter()
        enriched = self.buffer_manager.add_reading(reading)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        self.events_processed += 1
        self.total_enrichment_ms += latency_ms

        return IngestionResponse(
            device_id=reading.device_id,
            status="PROCESSED",
            timestamp=reading.timestamp,
            enrichment_latency_ms=round(latency_ms, 3),
            features=enriched,
            prediction=None,
        )

    def process_batch(self, readings: List[RawTelemetryReading]) -> BatchIngestResponse:
        """Enriches an entire batch of raw telemetry readings."""
        t0 = time.perf_counter()
        results: List[IngestionResponse] = []
        failed = 0

        for r in readings:
            try:
                res = self.process_immediate(r)
                results.append(res)
            except Exception as e:
                logger.error("Failed to process event for %s: %s", r.device_id, e)
                failed += 1

        total_ms = (time.perf_counter() - t0) * 1000.0
        return BatchIngestResponse(
            total_received=len(readings),
            processed_count=len(results),
            failed_count=failed,
            total_time_ms=round(total_ms, 3),
            results=results,
        )

    async def _worker_loop(self, worker_id: int) -> None:
        """Continuous consumer loop popping events from the asynchronous queue."""
        logger.debug("Worker %d loop running...", worker_id)
        while self._running:
            try:
                reading = await self.queue.get()
                self.process_immediate(reading)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.failed_count += 1
                logger.error("Worker %d encountered error: %s", worker_id, e)

    def get_stats(self) -> StreamStatsResponse:
        """Returns real-time processing statistics."""
        avg_latency = (
            self.total_enrichment_ms / self.events_processed
            if self.events_processed > 0
            else 0.0
        )
        return StreamStatsResponse(
            events_ingested=self.events_ingested,
            events_processed=self.events_processed,
            queue_depth=self.queue.qsize(),
            active_device_buffers=self.buffer_manager.active_device_count,
            avg_enrichment_latency_ms=round(avg_latency, 3),
            uptime_seconds=round(time.time() - self._start_time, 2),
        )
