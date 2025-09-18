"""Helper client to push telemetry towards the external controller."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx

from .controller_schema import LogEvent, MetricSnapshot, StopCommand, StopStatus

LOGGER = logging.getLogger("controller.client")

CONTROLLER_URL_ENV = "CONTROLLER_BASE_URL"
CONTROLLER_TIMEOUT_ENV = "CONTROLLER_TIMEOUT"


class ControllerClient:
    """Lightweight helper around the controller REST API."""

    def __init__(
        self,
        component: str,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.component = component
        env_url = base_url or os.getenv(CONTROLLER_URL_ENV)
        if env_url:
            self.base_url = env_url.rstrip("/")
            self.enabled = True
        else:
            self.base_url = ""
            self.enabled = False
        env_timeout = timeout or os.getenv(CONTROLLER_TIMEOUT_ENV)
        try:
            self.timeout = float(env_timeout) if env_timeout is not None else 5.0
        except ValueError:
            self.timeout = 5.0
        LOGGER.debug(
            "ControllerClient initialized for component '%s' with base_url='%s' and timeout=%.1f",
            self.component,
            self.base_url,
            self.timeout,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def emit_log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return
        event = LogEvent(component=self.component, level=level.upper(), message=message, context=context)
        await self._post("/ingest/logs", event.model_dump(mode="json"))

    async def emit_metric(self, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        snapshot = MetricSnapshot(component=self.component, payload=payload)
        await self._post("/ingest/metrics", snapshot.model_dump(mode="json"))

    async def send_stop_command(self, command: StopCommand) -> None:
        if not self.enabled:
            return
        await self._post("/commands/stop", command.model_dump(mode="json"))

    async def fetch_stop_status(self) -> Optional[StopStatus]:
        if not self.enabled:
            return None
        url = f"{self.base_url}/commands/stop"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except Exception as exc:
            LOGGER.debug("Failed to fetch stop status from controller: %s", exc, exc_info=False)
            return None
        data = response.json()
        return StopStatus.model_validate(data)

    def emit_log_nowait(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        LOGGER.debug("emit_log_nowait called with level=%s, message=%s", level, message)
        if not self.enabled:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            LOGGER.debug("emit_log_nowait called without running loop; dropping event")
            return
        loop.create_task(self.emit_log(level, message, context))

    def emit_metric_nowait(self, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            LOGGER.debug("emit_metric_nowait called without running loop; dropping event")
            return
        loop.create_task(self.emit_metric(payload))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _post(self, path: str, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except Exception as exc:
            LOGGER.debug("Failed to POST to controller at %s: %s", url, exc, exc_info=False)
