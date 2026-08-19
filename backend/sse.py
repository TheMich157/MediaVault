import asyncio
import json
import logging
from typing import AsyncGenerator, Set
from fastapi import Request

logger = logging.getLogger(__name__)


class SSEManager:
    """Manages active SSE client connections and broadcasts events."""

    def __init__(self):
        self.connections: Set[asyncio.Queue] = set()

    async def connect(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.connections.add(queue)
        logger.info(f"SSE client connected. Total clients: {len(self.connections)}")
        return queue

    def disconnect(self, queue: asyncio.Queue):
        self.connections.discard(queue)
        logger.info(f"SSE client disconnected. Remaining: {len(self.connections)}")

    async def broadcast(self, event_type: str, data: dict):
        """Send event payload to all connected SSE clients."""
        if not self.connections:
            return

        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        dead_queues = set()
        for q in self.connections:
            try:
                q.put_nowait(payload)
            except Exception:
                dead_queues.add(q)

        for dq in dead_queues:
            self.connections.discard(dq)

    async def event_generator(self, request: Request) -> AsyncGenerator[str, None]:
        queue = await self.connect()
        try:
            # Send initial ping event
            yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # Wait for message with timeout to send keepalive comments
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            self.disconnect(queue)


sse_manager = SSEManager()
