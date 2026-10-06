import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("agrikural.websocket")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcasts JSON payload to all connected clients."""
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Error broadcasting to client: {e}. Marking for cleanup.")
                to_remove.append(connection)

        for stale in to_remove:
            self.disconnect(stale)

ws_manager = ConnectionManager()
