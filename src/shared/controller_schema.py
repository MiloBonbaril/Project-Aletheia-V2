"""Shared Pydantic models for controller communication."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LogEvent(BaseModel):
    """Structured log payload emitted by front/back services."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    component: str = Field(..., description="Sender component identifier")
    level: str = Field(default="INFO", description="Logging level name")
    message: str
    context: Optional[Dict[str, Any]] = Field(default=None)


class MetricSnapshot(BaseModel):
    """Aggregated metrics describing service and hardware state."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    component: str = Field(..., description="Sender component identifier")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metrics block (db stats, gpu utilisation, ...)",
    )


class StopCommand(BaseModel):
    """Emergency stop command issued by the controller UI or operators."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    initiator: str = Field(..., description="Who issued the stop command")
    reason: Optional[str] = Field(default=None)


class StopStatus(BaseModel):
    """State of the stop signal consumed by other services."""

    active: bool
    last_command: Optional[StopCommand]
