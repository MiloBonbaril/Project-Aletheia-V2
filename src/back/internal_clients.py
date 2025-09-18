from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from back.ollama_interface.client import OllamaClient


@dataclass
class InternalClients:
    """Bundle of shared clients that can be reused across requests."""

    ollama: OllamaClient
    http: httpx.AsyncClient


async def shutdown_clients(clients: InternalClients) -> None:
    """Close client connections gracefully when the app stops."""

    await clients.http.aclose()


def create_internal_clients(
    ollama_url: Optional[str] = None,
    http_timeout: float = 10.0,
) -> InternalClients:
    """Initialise the internal clients once at startup."""

    ollama_client = OllamaClient(api_url=ollama_url) if ollama_url else OllamaClient()
    timeout = httpx.Timeout(http_timeout)
    http_client = httpx.AsyncClient(timeout=timeout)
    return InternalClients(ollama=ollama_client, http=http_client)
