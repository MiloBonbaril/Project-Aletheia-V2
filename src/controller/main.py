"""Controller service entrypoint.

This FastAPI app ingests logs and metrics from other components and can
broadcast emergency stop commands. The storage layer is in-memory for now,
but can be replaced by a persistent backend later on.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Any, Deque, Dict

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from shared.controller_schema import LogEvent, MetricSnapshot, StopCommand, StopStatus

LOGGER = logging.getLogger("controller")

# In-memory buffers keep the latest payloads, useful for the web dashboard.
LOG_BUFFER_SIZE = 1000
METRIC_BUFFER_SIZE = 500
_LOG_EVENTS: Deque[LogEvent] = deque(maxlen=LOG_BUFFER_SIZE)
_METRIC_EVENTS: Deque[MetricSnapshot] = deque(maxlen=METRIC_BUFFER_SIZE)

# Emergency stop coordination happens through an asyncio event for now.
_STOP_EVENT = asyncio.Event()
_STOP_REQUESTS: Deque[StopCommand] = deque(maxlen=50)


app = FastAPI(title="Project Aletheia Controller", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", status_code=status.HTTP_200_OK)
async def healthcheck() -> Dict[str, str]:
    """Basic readiness probe."""

    return {"status": "ok"}


@app.post("/ingest/logs", status_code=status.HTTP_202_ACCEPTED)
async def ingest_logs(event: LogEvent, background: BackgroundTasks) -> Dict[str, str]:
    """Store a structured log entry for later inspection."""

    _LOG_EVENTS.append(event)
    background.add_task(LOGGER.info, "[%s] %s", event.component, event.message)
    return {"status": "accepted"}


@app.post("/ingest/metrics", status_code=status.HTTP_202_ACCEPTED)
async def ingest_metrics(snapshot: MetricSnapshot) -> Dict[str, str]:
    """Persist a metrics snapshot."""

    _METRIC_EVENTS.append(snapshot)
    return {"status": "accepted"}


@app.get("/commands/stop", response_model=StopStatus)
async def get_stop_status() -> StopStatus:
    """Allow consumers to poll whether a stop signal is active."""

    last_command = _STOP_REQUESTS[-1] if _STOP_REQUESTS else None
    return StopStatus(active=_STOP_EVENT.is_set(), last_command=last_command)


@app.post("/commands/stop", status_code=status.HTTP_202_ACCEPTED)
async def trigger_stop(command: StopCommand) -> Dict[str, str]:
    """Emit an emergency stop command."""

    _STOP_REQUESTS.append(command)
    _STOP_EVENT.set()
    LOGGER.warning("Stop command received: %s", command.model_dump_json())
    return {"status": "stop_signal_active"}


@app.post("/commands/stop/reset", status_code=status.HTTP_202_ACCEPTED)
async def clear_stop() -> Dict[str, str]:
    """Clear the stop signal after the situation is resolved."""

    if not _STOP_EVENT.is_set():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop signal already cleared",
        )
    _STOP_EVENT.clear()
    LOGGER.info("Stop signal cleared")
    return {"status": "stop_signal_cleared"}


@app.get("/logs/latest")
async def list_recent_logs(limit: int = 100) -> Dict[str, Any]:
    """Expose recent logs for the dashboard."""

    limit = max(1, min(limit, LOG_BUFFER_SIZE))
    return {"items": list(_LOG_EVENTS)[-limit:]}


@app.get("/metrics/latest")
async def list_recent_metrics(limit: int = 100) -> Dict[str, Any]:
    """Expose recent metrics for the dashboard."""

    limit = max(1, min(limit, METRIC_BUFFER_SIZE))
    return {"items": list(_METRIC_EVENTS)[-limit:]}
