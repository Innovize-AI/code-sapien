import asyncio
import json
import logging
import uuid
from typing import List, Optional

logger = logging.getLogger(__name__)

class EventStreamManager:
    def __init__(self):
        # org_id -> List[asyncio.Queue]
        self.active_connections: dict[str, List[asyncio.Queue]] = {}

    async def subscribe(self, org_id: str):
        queue = asyncio.Queue()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = []
        
        self.active_connections[org_id].append(queue)
        logger.debug(f"New SSE subscriber for org {org_id}. Total for org: {len(self.active_connections[org_id])}")
        return queue

    async def unsubscribe(self, org_id: str, queue: asyncio.Queue):
        if org_id in self.active_connections and queue in self.active_connections[org_id]:
            self.active_connections[org_id].remove(queue)
            if not self.active_connections[org_id]:
                del self.active_connections[org_id]
            logger.debug(f"SSE subscriber disconnected from org {org_id}.")

    async def broadcast(self, data: dict, org_id: Optional[str] = None):
        """
        Broadcasts data to all subscribers of a specific organization.
        If org_id is None, it broadcasts to EVERYONE (use sparingly).
        """
        def default(obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        payload = json.dumps(data, default=default)
        event = f"data: {payload}\n\n"
        
        targets = []
        if org_id:
            if org_id in self.active_connections:
                targets = self.active_connections[org_id]
        else:
            # Global broadcast
            for queues in self.active_connections.values():
                targets.extend(queues)

        for queue in targets:
            await queue.put(event)

# Global instance for shared state across modules
event_manager = EventStreamManager()
