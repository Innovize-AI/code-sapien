import asyncio
import json
import logging
import uuid
from typing import List

logger = logging.getLogger(__name__)

class EventStreamManager:
    def __init__(self):
        self.active_connections: List[asyncio.Queue] = []

    async def subscribe(self):
        queue = asyncio.Queue()
        self.active_connections.append(queue)
        logger.debug(f"New SSE subscriber. Total: {len(self.active_connections)}")
        return queue

    async def unsubscribe(self, queue):
        if queue in self.active_connections:
            self.active_connections.remove(queue)
            logger.debug(f"SSE subscriber disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        if not self.active_connections:
            return
        
        def default(obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        payload = json.dumps(data, default=default)
        event = f"data: {payload}\n\n"
        
        for queue in self.active_connections:
            await queue.put(event)

# Global instance for shared state across modules
event_manager = EventStreamManager()
