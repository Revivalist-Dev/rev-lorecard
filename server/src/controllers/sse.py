import asyncio
import json
from datetime import datetime
from typing import Dict, Set, AsyncGenerator
from litestar import Controller, get
from litestar.response import ServerSentEvent
from logging_config import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)

# In-memory storage for SSE clients
sse_clients: Dict[str, Set[asyncio.Queue]] = {}


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    return str(obj)


class SSEController(Controller):
    path = "/sse"

    @get("/subscribe/{project_id:str}")
    async def subscribe_to_project_events(self, project_id: str) -> ServerSentEvent:
        """
        Subscribe to real-time events for a specific project.
        """
        # Create a queue for this client
        queue = asyncio.Queue()

        # Add client to the project's client set
        if project_id not in sse_clients:
            sse_clients[project_id] = set()
        sse_clients[project_id].add(queue)

        logger.debug(f"Client subscribed to project {project_id} events")

        async def event_generator() -> AsyncGenerator[dict | str, None]:
            yield {"event": "open", "data": "connection established"}

            try:
                while True:
                    try:
                        # Wait for an event, but with a timeout
                        data = await asyncio.wait_for(queue.get(), timeout=15.0)
                        if data is None:  # Sentinel value to close connection
                            break
                        yield data
                    except asyncio.TimeoutError:
                        # No event received in 15s, send a keep-alive comment
                        yield {"event": "ping", "data": "keep-alive"}
            except asyncio.CancelledError:
                logger.debug(f"Client disconnected from project {project_id}")
            finally:
                # Clean up client
                if project_id in sse_clients and queue in sse_clients[project_id]:
                    sse_clients[project_id].remove(queue)
                    if not sse_clients[project_id]:
                        del sse_clients[project_id]

        return ServerSentEvent(event_generator())

    @staticmethod
    async def send_event_to_project(project_id: str, event_type: str, data: dict):
        """
        Send an event to all clients subscribed to a project.
        """
        if project_id in sse_clients:
            event_data = {**data, "project_id": project_id}
            event = {
                "event": event_type,
                "data": json.dumps(event_data, default=json_serial),
            }

            for queue in sse_clients[project_id].copy():
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for client in project {project_id}")
                except Exception as e:
                    logger.error(f"Error sending event to client: {e}")
