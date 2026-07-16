"""
Async Event Bus — the backbone of agent communication.

Features:
- Async pub/sub with in-memory dispatch
- Persistent storage to workflow_events table
- WebSocket broadcast to connected dashboard clients
- No agent ever calls another agent directly
"""
from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from app.core.event_types import EventType


# Type alias
EventHandler = Callable[[dict], Awaitable[None]]


class EventBus:
    """
    In-process async event bus.
    Events flow: publish() → DB persist → WebSocket broadcast → handlers
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._ws_clients: set = set()   # WebSocket connections
        self._db_session_factory = None  # injected on startup

    def set_db_factory(self, factory) -> None:
        self._db_session_factory = factory

    # ── WebSocket management ──────────────────────────────────────────
    def add_ws_client(self, ws) -> None:
        self._ws_clients.add(ws)

    def remove_ws_client(self, ws) -> None:
        self._ws_clients.discard(ws)

    # ── Subscription ──────────────────────────────────────────────────
    def subscribe(self, event_type: str | EventType, handler: EventHandler) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        self._handlers[key].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to every event (useful for logging / WebSocket broadcast)."""
        self._handlers["*"].append(handler)

    # ── Publishing ────────────────────────────────────────────────────
    async def publish(
        self,
        event_type: str | EventType,
        workflow_id: str | None = None,
        source_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> str:
        """
        Publish an event. Returns the event ID.
        1. Build event dict
        2. Persist to DB (non-blocking)
        3. Broadcast via WebSocket
        4. Call registered handlers
        """
        event_id = str(uuid.uuid4())
        key = event_type.value if isinstance(event_type, EventType) else event_type

        event_dict = {
            "id": event_id,
            "event_type": key,
            "workflow_id": workflow_id,
            "source_agent": source_agent,
            "payload": payload or {},
            "tenant_id": tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Fire-and-forget DB persist + WS broadcast
        asyncio.create_task(self._persist(event_dict))
        asyncio.create_task(self._broadcast_ws(event_dict))

        # Synchronously call type-specific handlers
        for handler in self._handlers.get(key, []):
            asyncio.create_task(handler(event_dict))

        # Call wildcard handlers
        for handler in self._handlers.get("*", []):
            asyncio.create_task(handler(event_dict))

        return event_id

    async def _persist(self, event_dict: dict) -> None:
        """Write event to database."""
        if self._db_session_factory is None:
            return
        try:
            from app.models.system import WorkflowEvent
            async with self._db_session_factory() as session:
                ev = WorkflowEvent(
                    id=event_dict["id"],
                    event_type=event_dict["event_type"],
                    workflow_id=event_dict.get("workflow_id"),
                    source_agent=event_dict.get("source_agent"),
                    payload_json=json.dumps(event_dict.get("payload", {})),
                    tenant_id=event_dict.get("tenant_id"),
                    broadcast_sent=False,
                )
                session.add(ev)
                await session.commit()
        except Exception as e:
            # Never let event persistence crash the workflow
            print(f"[EventBus] DB persist failed: {e}")

    async def _broadcast_ws(self, event_dict: dict) -> None:
        """Send event to all connected WebSocket clients."""
        if not self._ws_clients:
            return
        message = json.dumps(event_dict, default=str)
        dead = set()
        for ws in list(self._ws_clients):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._ws_clients.discard(ws)


# ── Global singleton ──────────────────────────────────────────────────
event_bus = EventBus()
