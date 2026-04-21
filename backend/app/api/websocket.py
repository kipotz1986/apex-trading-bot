"""
WebSocket Real-time Streaming Service.
Broadcasts portfolio, positions, and bot status updates to connected clients.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List, Dict
import json
import asyncio
from app.api import deps
from app.core import security
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.debug("websocket_connected", count=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.debug("websocket_disconnected", count=len(self.active_connections))

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
            
        data = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.error("websocket_broadcast_error", error=str(e))

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Auth Handshake (Simplified for now, in prod should check token in query/header)
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and wait for client messages (if any)
            data = await websocket.receive_text()
            # Handle incoming client commands if needed
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        manager.disconnect(websocket)

async def broadcast_updates(channel: str, data: dict):
    """Utility to broadcast data to a specific channel."""
    await manager.broadcast({
        "channel": channel,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    })
