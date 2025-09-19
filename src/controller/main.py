"""Controller service entrypoint with dashboard and realtime streaming."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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


class BroadcastManager:
    """Manage websocket clients and broadcast controller events."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.add(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections)
        if not connections:
            return

        payload = jsonable_encoder(message)
        stale: List[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)

        if stale:
            async with self._lock:
                for connection in stale:
                    self._connections.discard(connection)


BROADCASTER = BroadcastManager()
CONTROLLER_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(CONTROLLER_DIR / "templates"))

app = FastAPI(title="Project Aletheia Controller", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _current_stop_status() -> StopStatus:
    last_command = _STOP_REQUESTS[-1] if _STOP_REQUESTS else None
    return StopStatus(active=_STOP_EVENT.is_set(), last_command=last_command)


def _serialize_logs(logs: List[LogEvent]) -> List[Dict[str, Any]]:
    return [log.model_dump(mode="json") for log in logs]


def _serialize_metrics(metrics: List[MetricSnapshot]) -> List[Dict[str, Any]]:
    return [snapshot.model_dump(mode="json") for snapshot in metrics]


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the web dashboard shell. Dynamic data flows via WebSocket."""

    return TEMPLATES.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    await BROADCASTER.register(websocket)

    try:
        logs_snapshot = _serialize_logs(list(_LOG_EVENTS)[-100:])
        metrics_snapshot = _serialize_metrics(list(_METRIC_EVENTS)[-100:])
        stop_status = _current_stop_status().model_dump(mode="json")

        await websocket.send_json(
            {
                "type": "snapshot",
                "logs": logs_snapshot,
                "metrics": metrics_snapshot,
                "stop_status": stop_status,
            }
        )

        while True:
            # Keep the connection alive and react to client pings/messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await BROADCASTER.unregister(websocket)


@app.get("/health", status_code=status.HTTP_200_OK)
async def healthcheck() -> Dict[str, str]:
    """Basic readiness probe."""

    return {"status": "ok"}


@app.post("/ingest/logs", status_code=status.HTTP_202_ACCEPTED)
async def ingest_logs(event: LogEvent, background: BackgroundTasks) -> Dict[str, str]:
    """Store a structured log entry for later inspection."""

    _LOG_EVENTS.append(event)
    background.add_task(LOGGER.info, "[%s] %s", event.component, event.message)
    await BROADCASTER.broadcast({"type": "log", "item": event.model_dump(mode="json")})
    return {"status": "accepted"}


@app.post("/ingest/metrics", status_code=status.HTTP_202_ACCEPTED)
async def ingest_metrics(snapshot: MetricSnapshot) -> Dict[str, str]:
    """Persist a metrics snapshot."""

    _METRIC_EVENTS.append(snapshot)
    await BROADCASTER.broadcast({"type": "metric", "item": snapshot.model_dump(mode="json")})
    return {"status": "accepted"}


@app.get("/commands/stop", response_model=StopStatus)
async def get_stop_status() -> StopStatus:
    """Allow consumers to poll whether a stop signal is active."""

    return _current_stop_status()


@app.post("/commands/stop", status_code=status.HTTP_202_ACCEPTED)
async def trigger_stop(command: StopCommand) -> Dict[str, str]:
    """Emit an emergency stop command."""

    _STOP_REQUESTS.append(command)
    _STOP_EVENT.set()
    LOGGER.warning("Stop command received: %s", command.model_dump_json())

    status_payload = _current_stop_status().model_dump(mode="json")
    await BROADCASTER.broadcast({"type": "stop_status", "item": status_payload})
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
    status_payload = _current_stop_status().model_dump(mode="json")
    await BROADCASTER.broadcast({"type": "stop_status", "item": status_payload})
    return {"status": "stop_signal_cleared"}


@app.get("/logs/latest")
async def list_recent_logs(limit: int = 100) -> Dict[str, Any]:
    """Expose recent logs for the dashboard."""

    limit = max(1, min(limit, LOG_BUFFER_SIZE))
    items = _serialize_logs(list(_LOG_EVENTS)[-limit:])
    return {"items": items}


@app.get("/metrics/latest")
async def list_recent_metrics(limit: int = 100) -> Dict[str, Any]:
    """Expose recent metrics for the dashboard."""

    limit = max(1, min(limit, METRIC_BUFFER_SIZE))
    items = _serialize_metrics(list(_METRIC_EVENTS)[-limit:])
    return {"items": items}
