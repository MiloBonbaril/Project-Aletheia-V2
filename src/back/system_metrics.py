"""Periodic system metrics collection for the backend service."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from shared import ControllerClient
from back.db.session import get_engine

try:  # pragma: no cover - optional dependency based on environment
    import pynvml  # type: ignore
except ImportError:  # pragma: no cover - absence is acceptable
    pynvml = None  # type: ignore

LOGGER = logging.getLogger("back.metrics")
_NVML_INITIALISED = False


def _bytes_to_mb(value: int) -> float:
    return round(value / (1024 * 1024), 2)


def _init_nvml() -> bool:
    global _NVML_INITIALISED
    if pynvml is None:
        return False
    if _NVML_INITIALISED:
        return True
    try:
        pynvml.nvmlInit()
    except Exception as exc:  # pragma: no cover - NVML errors are environment specific
        LOGGER.debug("NVML initialisation failed: %s", exc)
        return False
    _NVML_INITIALISED = True
    return True


def _shutdown_nvml() -> None:
    global _NVML_INITIALISED
    if pynvml is None or not _NVML_INITIALISED:
        return
    try:
        pynvml.nvmlShutdown()
    except Exception:  # pragma: no cover - best effort cleanup
        pass
    _NVML_INITIALISED = False


def collect_db_metrics() -> Dict[str, Any]:
    engine = get_engine()
    if engine is None:
        return {"initialised": False}

    pool = getattr(engine.sync_engine, "pool", None)
    if pool is None:
        return {"initialised": True, "pool": None}

    pool_info: Dict[str, Any] = {}
    for attr in ("size", "checkedin", "checkedout", "overflow"):
        attr_fn = getattr(pool, attr, None)
        if callable(attr_fn):
            try:
                pool_info[attr] = attr_fn()
            except Exception as exc:  # pragma: no cover - defensive
                pool_info[attr] = f"error: {exc}"
    status_fn = getattr(pool, "status", None)
    if callable(status_fn):
        try:
            pool_info["status"] = status_fn()
        except Exception as exc:  # pragma: no cover - defensive
            pool_info["status"] = f"error: {exc}"

    return {"initialised": True, "pool": pool_info}


def collect_gpu_metrics() -> Optional[Dict[str, Any]]:
    if not _init_nvml():
        return None

    assert pynvml is not None  # for type-checkers
    try:
        device_count = pynvml.nvmlDeviceGetCount()
    except pynvml.NVMLError as exc:  # type: ignore[attr-defined]
        LOGGER.debug("NVML device count failed: %s", exc)
        return None

    devices = []
    for index in range(device_count):
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", "replace")
            utilisation = pynvml.nvmlDeviceGetUtilizationRates(handle)
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temperature: Optional[int] = None
            try:
                temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except pynvml.NVMLError:  # type: ignore[attr-defined]
                temperature = None

            devices.append(
                {
                    "index": index,
                    "name": name,
                    "utilization_gpu": utilisation.gpu,
                    "utilization_memory": utilisation.memory,
                    "memory_total_mb": _bytes_to_mb(memory.total),
                    "memory_used_mb": _bytes_to_mb(memory.used),
                    "memory_free_mb": _bytes_to_mb(memory.free),
                    "temperature_c": temperature,
                }
            )
        except pynvml.NVMLError as exc:  # type: ignore[attr-defined]
            LOGGER.debug("Failed to collect metrics for GPU %s: %s", index, exc)

    return {"device_count": device_count, "gpus": devices}


async def run_metrics_loop(
    controller_client: ControllerClient,
    *,
    interval: float = 30.0,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    LOGGER.info("Starting metrics collection loop (interval=%ss)", interval)
    try:
        while True:
            payload: Dict[str, Any] = {"event": "system_metrics"}

            db_metrics = collect_db_metrics()
            if db_metrics:
                payload["db"] = db_metrics

            gpu_metrics = collect_gpu_metrics()
            if gpu_metrics:
                payload["gpu"] = gpu_metrics

            if len(payload) > 1:
                try:
                    await controller_client.emit_metric(payload)
                except Exception as exc:
                    LOGGER.debug("Failed to push metrics to controller: %s", exc)

            if stop_event is None:
                await asyncio.sleep(interval)
            else:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval)
                    break
                except asyncio.TimeoutError:
                    continue
    except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation
        LOGGER.debug("Metrics loop cancelled")
        raise
    finally:
        _shutdown_nvml()
        LOGGER.info("Metrics collection loop stopped")
