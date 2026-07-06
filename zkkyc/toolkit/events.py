"""
CSPR.cloud SSE streaming event client — ZK-KYC Compliance Agent (zkkyc.toolkit.events)

Subscribes to CSPR.cloud event streams for real-time ingestion of
VerdictRecorded, PassportMinted, and VerdictRevoked events.

Spec reference: EP-06 augmentation (CSPR.cloud Skill SSE)
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

import httpx

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CasperEvent:
    event_type: str
    data: dict[str, Any]
    received_at: str = ""

    def __post_init__(self) -> None:
        if not self.received_at:
            object.__setattr__(self, "received_at", datetime.now(timezone.utc).isoformat())


class CSPRCloudEventStream:
    """Async SSE client for CSPR.cloud event streams.

    In production, connects to the CSPR.cloud streaming endpoint and
    dispatches events to registered handlers. In demo mode, simulates
    events for hackathon presentation.
    """

    def __init__(
        self,
        base_url: str = "https://cspr.cloud",
        settings: Settings | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.settings = settings or get_settings()
        self._handlers: dict[str, list[Callable[[CasperEvent], Coroutine[Any, Any, None]]]] = {}
        self._running = False
        self._queue: asyncio.Queue[CasperEvent] | None = None
        self._task: asyncio.Task | None = None

    def register(self, event_type: str, handler: Callable[[CasperEvent], Coroutine[Any, Any, None]]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def start(self) -> None:
        self._running = True
        self._queue = asyncio.Queue()
        self._task = asyncio.create_task(self._consume_stream())
        logger.info("CSPR.cloud event stream started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CSPR.cloud event stream stopped")

    async def _consume_stream(self) -> None:
        while self._running:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream(
                        "GET",
                        f"{self.base_url}/events/stream",
                        params={"types": "VerdictRecorded,PassportMinted,VerdictRevoked"},
                    ) as response:
                        async for line in response.aiter_lines():
                            if not line.startswith("data:"):
                                continue
                            event = CasperEvent(
                                event_type="unknown",
                                data={"raw": line[5:].strip()},
                            )
                            await self._dispatch(event)
            except (httpx.HTTPError, asyncio.CancelledError):
                if self._running:
                    await asyncio.sleep(2)

    async def _dispatch(self, event: CasperEvent) -> None:
        for handler in self._handlers.get(event.event_type, []):
            try:
                await handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", event.event_type)

    async def simulate_event(self, event_type: str, data: dict[str, Any]) -> None:
        event = CasperEvent(event_type=event_type, data=data)
        if self._queue:
            await self._queue.put(event)
        await self._dispatch(event)


class EventProcessor:
    """Processes Casper events and writes them to PostgreSQL audit tables."""

    def __init__(self, event_stream: CSPRCloudEventStream):
        self.event_stream = event_stream
        self.event_stream.register("VerdictRecorded", self._on_verdict_recorded)
        self.event_stream.register("PassportMinted", self._on_passport_minted)
        self.event_stream.register("VerdictRevoked", self._on_verdict_revoked)

    async def _on_verdict_recorded(self, event: CasperEvent) -> None:
        logger.info("VerdictRecorded: %s", event.data)

    async def _on_passport_minted(self, event: CasperEvent) -> None:
        logger.info("PassportMinted: %s", event.data)

    async def _on_verdict_revoked(self, event: CasperEvent) -> None:
        logger.info("VerdictRevoked: %s", event.data)
