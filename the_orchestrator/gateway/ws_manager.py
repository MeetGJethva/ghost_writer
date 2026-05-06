"""
WebSocket connection manager — maintains a set of connected clients
per conversation and broadcasts new messages to them.
Uses Redis Pub/Sub to synchronize messages across multiple processes.
"""
from __future__ import annotations

import json
import asyncio
from collections import defaultdict
from typing import Any
from fastapi import WebSocket
from the_orchestrator.gateway.redis_client import get_redis

REDIS_CHAT_CHANNEL = "chat_messages_sync"

class ConnectionManager:
    """Manages WebSocket connections grouped by conversation_id."""

    def __init__(self):
        # conversation_id -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._listener_task: asyncio.Task | None = None

    async def connect(self, conversation_id: str, websocket: WebSocket):
        print(f"[ws] Connecting to conversation: {conversation_id}")
        await websocket.accept()
        self._connections[conversation_id].add(websocket)

    def disconnect(self, conversation_id: str, websocket: WebSocket):
        self._connections[conversation_id].discard(websocket)
        if not self._connections[conversation_id]:
            del self._connections[conversation_id]

    async def broadcast_local(self, conversation_id: str, message: dict):
        """Send a JSON message ONLY to local clients on this process."""
        dead = []
        clients = self._connections.get(conversation_id, set())
        
        print(f"[ws] Local broadcast for {conversation_id}. Local connections: {len(clients)}")
        
        for ws in clients:
            try:
                await ws.send_json(message)
                print(f"[ws] Successfully sent message to client: {ws}")
            except Exception as e:
                print(f"[ws] Failed to send message to client {ws}: {e}")
                dead.append(ws)
        for ws in dead:
            self.disconnect(conversation_id, ws)

    async def broadcast(self, conversation_id: str, message: dict):
        """
        Broadcast a message to all instances. 
        This publishes the message to Redis Pub/Sub.
        """
        redis = await get_redis()
        payload = json.dumps({
            "conversation_id": conversation_id,
            "message": message
        })
        print(f"[ws] Outgoing: Publishing to Redis {REDIS_CHAT_CHANNEL} for conv {conversation_id}")
        await redis.publish(REDIS_CHAT_CHANNEL, payload)

    async def start_redis_listener(self):
        """Background task that listens to Redis and broadcasts to local WebSockets."""
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(REDIS_CHAT_CHANNEL)
        
        print(f"[ws] Started Redis Pub/Sub listener on {REDIS_CHAT_CHANNEL}")
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    print(f"[ws] Incoming from Redis: {message['data'][:100]}...")
                    data = json.loads(message["data"])
                    conv_id = data["conversation_id"]
                    msg_body = data["message"]
                    
                    # Send to local clients if any
                    await self.broadcast_local(conv_id, msg_body)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(REDIS_CHAT_CHANNEL)
            print("[ws] Redis listener cancelled.")
        except Exception as e:
            print(f"[ws] Redis listener error: {e}")

# Singleton instance used across the app
manager = ConnectionManager()
