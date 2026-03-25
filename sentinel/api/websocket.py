"""WebSocket ConnectionManager — API-01.

Provides a module-level singleton for broadcasting typed WSEvents to all
connected dashboard clients. Dead connections are pruned on send failure.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import WebSocket

from sentinel.schemas.events import EventType, WSEvent


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events to all clients."""

    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        """Accept a WebSocket connection and register it."""
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket from the active connection list."""
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(
        self,
        event: EventType,
        episode_id: str,
        data: dict | None = None,
    ) -> None:
        """Broadcast a typed WSEvent to all connected clients.

        Dead connections (send failure) are silently pruned.

        Args:
            event:      One of the 7 EventType literal values.
            episode_id: UUID of the current investigation episode.
            data:       Optional dict payload attached to the event.
        """
        ws_event = WSEvent(
            event=event,
            timestamp=datetime.utcnow(),
            episode_id=episode_id,
            data=data or {},
        )
        msg = ws_event.model_dump_json()
        dead: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)


# Module-level singleton — used by routes and supervisor
ws_manager = ConnectionManager()
