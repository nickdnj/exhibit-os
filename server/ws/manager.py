import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger("exhibitos.ws")


class ConnectionManager:
    """Manages WebSocket connections for display clients and admin dashboards."""

    def __init__(self):
        # Display clients: {channel_slug: [websocket, ...]}
        self.display_clients: dict[str, list[WebSocket]] = {}
        # Admin clients
        self.admin_clients: list[WebSocket] = []
        # Heartbeat tracking: {websocket: last_heartbeat_time}
        self._heartbeats: dict[WebSocket, datetime] = {}

    async def connect_display(self, websocket: WebSocket, channel_slug: str):
        await websocket.accept()
        if channel_slug not in self.display_clients:
            self.display_clients[channel_slug] = []
        self.display_clients[channel_slug].append(websocket)
        self._heartbeats[websocket] = datetime.now(timezone.utc)
        logger.info("Display client connected: channel=%s (total=%d)",
                     channel_slug, len(self.display_clients[channel_slug]))

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_clients.append(websocket)
        logger.info("Admin client connected (total=%d)", len(self.admin_clients))

    def disconnect_display(self, websocket: WebSocket, channel_slug: str):
        if channel_slug in self.display_clients:
            self.display_clients[channel_slug] = [
                ws for ws in self.display_clients[channel_slug] if ws != websocket
            ]
        self._heartbeats.pop(websocket, None)
        logger.info("Display client disconnected: channel=%s", channel_slug)

    def disconnect_admin(self, websocket: WebSocket):
        self.admin_clients = [ws for ws in self.admin_clients if ws != websocket]
        logger.info("Admin client disconnected")

    async def broadcast_to_channel(self, channel_slug: str, message: dict):
        """Send a message to all display clients on a specific channel."""
        clients = self.display_clients.get(channel_slug, [])
        dead = []
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_display(ws, channel_slug)

    async def broadcast_to_all_displays(self, message: dict):
        """Send a message to ALL display clients across all channels."""
        for slug in list(self.display_clients.keys()):
            await self.broadcast_to_channel(slug, message)

    async def broadcast_to_admins(self, message: dict):
        """Send a message to all admin dashboard clients."""
        dead = []
        for ws in self.admin_clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_admin(ws)

    async def notify_page_update(self, channel_slug: Optional[str] = None):
        """Notify display clients that the page list has changed."""
        message = {"type": "page_list_changed", "timestamp": datetime.now(timezone.utc).isoformat()}
        if channel_slug:
            await self.broadcast_to_channel(channel_slug, message)
        else:
            await self.broadcast_to_all_displays(message)

    def get_status(self) -> dict:
        """Return connection status for admin dashboard."""
        return {
            "display_clients": {
                slug: len(clients)
                for slug, clients in self.display_clients.items()
            },
            "admin_clients": len(self.admin_clients),
            "total_connections": sum(len(c) for c in self.display_clients.values()) + len(self.admin_clients),
        }


# Singleton
ws_manager = ConnectionManager()
