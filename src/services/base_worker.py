"""
NILA V2 Base Worker
Abstract base class for event-driven workers.
"""

from abc import ABC, abstractmethod
import logging
from typing import Optional
from src.core.event_bus import EventBus
from src.core.events import Event


class BaseWorker(ABC):
    """
    Abstract base class for NILA event workers.
    Each worker subscribes to specific event topics, processes incoming data,
    and publishes resulting events back to the EventBus.
    """

    def __init__(self, settings, name: Optional[str] = None):
        self.settings = settings
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.event_bus = EventBus()
        self.is_running = False

    @abstractmethod
    def register_subscriptions(self):
        """Register all event subscriptions on self.event_bus"""
        pass

    def start(self):
        """Start the worker and register event subscriptions"""
        if self.is_running:
            return
        self.is_running = True
        self.register_subscriptions()
        self.logger.info(f"🚀 Worker '{self.name}' started")

    def stop(self):
        """Stop the worker"""
        self.is_running = False
        self.logger.info(f"🛑 Worker '{self.name}' stopped")

    def cleanup(self):
        """Cleanup worker resources"""
        self.stop()
