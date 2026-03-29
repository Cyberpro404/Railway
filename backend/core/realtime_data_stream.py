"""
Real-time Data Stream Module
Handles broadcasting of sensor data to connected Frontend clients via WebSockets.
"""

import asyncio
import logging
import json
from .data_receiver import DataReceiver
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RealtimeStream:
    """Consumes an internal queue and broadcasts via WebSocket"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._running = False
        self._task = None
        self.broadcast_queue = asyncio.Queue(maxsize=100)
        self.latest_packet: Dict[str, Any] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket Client Connected ({len(self.active_connections)} active)")
        if self.latest_packet:
            try:
                await websocket.send_text(json.dumps(self.latest_packet))
            except Exception:
                self.disconnect(websocket)
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket Client Disconnected ({len(self.active_connections)} active)")
            
    async def broadcast(self, message: Dict[str, Any]):
        """Queue a message for broadcasting"""
        self.latest_packet = message
        if self.broadcast_queue.full():
            try:
                self.broadcast_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self.broadcast_queue.put(message)
            
    async def start(self):
        """Start the broadcast loop"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._broadcast_loop())
        logger.info("Realtime Broadcast Loop Started")
        
    async def stop(self):
        """Stop gracefully"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                 await self._task
            except asyncio.CancelledError:
                 pass
        logger.info("Realtime Broadcast Loop Stopped")
        
    async def _broadcast_loop(self):
        while self._running:
            try:
                # Wait for processed data
                packet = await self.broadcast_queue.get()
                
                if self.active_connections:
                    message = json.dumps(packet)

                    disconnected_clients = []
                    for connection in list(self.active_connections):
                        try:
                            await connection.send_text(message)
                        except Exception as e:
                            logger.debug(f"Send failed: {e}")
                            disconnected_clients.append(connection)
                            
                    for dc in disconnected_clients:
                        self.disconnect(dc)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast Error: {e}")
