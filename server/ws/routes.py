import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .manager import ws_manager

logger = logging.getLogger("exhibitos.ws")
router = APIRouter()


@router.websocket("/ws/display/{channel_slug}")
async def display_websocket(websocket: WebSocket, channel_slug: str):
    """WebSocket for display clients (Pi kiosk). No auth required."""
    await ws_manager.connect_display(websocket, channel_slug)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "heartbeat":
                ws_manager._heartbeats[websocket] = datetime.now(timezone.utc)
                await websocket.send_json({"type": "heartbeat_ack", "timestamp": datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        ws_manager.disconnect_display(websocket, channel_slug)
    except Exception as e:
        logger.warning("Display WS error (channel=%s): %s", channel_slug, e)
        ws_manager.disconnect_display(websocket, channel_slug)


@router.websocket("/ws/admin")
async def admin_websocket(websocket: WebSocket):
    """WebSocket for admin dashboard. Receives real-time status updates."""
    await ws_manager.connect_admin(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat_ack", "timestamp": datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        ws_manager.disconnect_admin(websocket)
    except Exception as e:
        logger.warning("Admin WS error: %s", e)
        ws_manager.disconnect_admin(websocket)
