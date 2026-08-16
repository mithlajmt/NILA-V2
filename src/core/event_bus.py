"""
NILA V2 Event Bus
Decoupled, asynchronous Pub/Sub engine with wildcard topic matching and error isolation.
"""

import asyncio
import inspect
import logging
import re
from typing import Any, Callable, Dict, List, Set, Union
from src.core.events import Event


class EventBus:
    """
    High-performance asynchronous Event Bus for NILA V2.
    
    Features:
    - Async coroutine and sync function handler support.
    - Wildcard topic matching (e.g. "stt.*", "hardware.*", "*").
    - Exception isolation (handler errors don't crash bus or publishers).
    - Thread-safe event publishing.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = logging.getLogger(__name__)
        self._subscribers: Dict[str, Set[Callable[[Event], Any]]] = {}
        self._pattern_subscribers: List[tuple[re.Pattern, Callable[[Event], Any]]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._initialized = True
        self.logger.info("⚡ EventBus initialized")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the active asyncio event loop for cross-thread dispatches"""
        self._loop = loop

    def subscribe(self, topic: str, handler: Callable[[Event], Any]):
        """
        Subscribe a handler function to a topic or wildcard pattern.
        
        Args:
            topic: Exact topic string ("stt.transcript") or pattern ("stt.*", "*")
            handler: Callback function or coroutine function receiving an Event instance
        """
        if "*" in topic or "?" in topic:
            # Convert glob-like pattern to regex (e.g., "stt.*" -> "^stt\..*$")
            regex_pattern = "^" + topic.replace(".", r"\.").replace("*", ".*").replace("?", ".") + "$"
            compiled_pattern = re.compile(regex_pattern)
            self._pattern_subscribers.append((compiled_pattern, handler))
            self.logger.debug(f"Registered pattern subscriber for '{topic}'")
        else:
            if topic not in self._subscribers:
                self._subscribers[topic] = set()
            self._subscribers[topic].add(handler)
            self.logger.debug(f"Registered subscriber for topic '{topic}'")

    def unsubscribe(self, topic: str, handler: Callable[[Event], Any]):
        """Unsubscribe a handler from a topic"""
        if topic in self._subscribers and handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)
            if not self._subscribers[topic]:
                del self._subscribers[topic]

        self._pattern_subscribers = [
            (p, h) for p, h in self._pattern_subscribers if not (h == handler)
        ]

    async def publish(self, event: Event):
        """
        Publish an event asynchronously to all matching subscribers.
        
        Args:
            event: Event object instance
        """
        handlers_to_call: List[Callable[[Event], Any]] = []

        # Exact match handlers
        if event.topic in self._subscribers:
            handlers_to_call.extend(self._subscribers[event.topic])

        # Pattern match handlers
        for pattern, handler in self._pattern_subscribers:
            if pattern.match(event.topic):
                handlers_to_call.append(handler)

        if not handlers_to_call:
            self.logger.debug(f"No subscribers for topic '{event.topic}'")
            return

        # Execute handlers with exception isolation
        tasks = []
        for handler in handlers_to_call:
            tasks.append(self._dispatch_to_handler(handler, event))

        await asyncio.gather(*tasks, return_exceptions=True)

    def publish_threadsafe(self, event: Event):
        """
        Publish an event safely from a non-async background thread.
        """
        try:
            loop = self._loop
            if loop is None:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(self.publish(event), loop)
            else:
                # Synchronous fallback if no running loop
                asyncio.run(self.publish(event))
        except Exception as e:
            self.logger.error(f"❌ Failed to publish threadsafe event '{event.topic}': {e}")

    async def _dispatch_to_handler(self, handler: Callable[[Event], Any], event: Event):
        """Invoke a single handler with error isolation"""
        try:
            if inspect.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            self.logger.error(f"❌ Error handling event '{event.topic}' in {handler.__name__}: {e}")

    def clear(self):
        """Clear all subscriptions (useful for testing)"""
        self._subscribers.clear()
        self._pattern_subscribers.clear()
