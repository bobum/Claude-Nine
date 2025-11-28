from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.team_subscribers: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.remove(websocket)
        # Remove from team subscriptions
        for team_id in list(self.team_subscribers.keys()):
            if websocket in self.team_subscribers[team_id]:
                self.team_subscribers[team_id].remove(websocket)

    async def subscribe_to_team(self, websocket: WebSocket, team_id: str):
        """Subscribe a connection to team updates"""
        if team_id not in self.team_subscribers:
            self.team_subscribers[team_id] = []
        if websocket not in self.team_subscribers[team_id]:
            self.team_subscribers[team_id].append(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_to_team(self, team_id: str, message: dict):
        """Send message to all clients subscribed to a team"""
        if team_id not in self.team_subscribers:
            return

        disconnected = []
        for connection in self.team_subscribers[team_id]:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            if connection in self.team_subscribers[team_id]:
                self.team_subscribers[team_id].remove(connection)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except:
            self.disconnect(websocket)


# Global connection manager instance
manager = ConnectionManager()


async def notify_team_update(team_id: str, event: str, data: dict):
    """Notify clients about team updates"""
    message = {
        "type": "team_update",
        "team_id": team_id,
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    }
    await manager.send_to_team(team_id, message)
    await manager.broadcast(message)


async def notify_agent_update(agent_id: str, team_id: str, event: str, data: dict):
    """Notify clients about agent updates"""
    message = {
        "type": "agent_update",
        "agent_id": agent_id,
        "team_id": team_id,
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    }
    await manager.send_to_team(team_id, message)
    await manager.broadcast(message)


async def notify_work_item_update(work_item_id: str, team_id: str, event: str, data: dict):
    """Notify clients about work item updates"""
    message = {
        "type": "work_item_update",
        "work_item_id": work_item_id,
        "team_id": team_id,
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    }
    if team_id:
        await manager.send_to_team(team_id, message)
    await manager.broadcast(message)


async def notify_agent_telemetry(agent_id: str, team_id: str, event: str, data: dict):
    """Notify clients about agent telemetry updates"""
    message = {
        "type": "agent_telemetry",
        "agent_id": agent_id,
        "team_id": team_id,
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    }
    await manager.send_to_team(team_id, message)
    await manager.broadcast(message)
