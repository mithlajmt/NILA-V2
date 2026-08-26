"""
Serial Controller for NILA-V2 Hardware
Manages communication with Arduino for Jaw and Eye control.
"""

import logging
import time
import serial
import threading
from typing import Optional

class SerialController:
    """Manages Serial communication with Arduino"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, settings=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SerialController, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance
    
    def __init__(self, settings=None):
        if self.initialized:
            return
            
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.serial_conn: Optional[serial.Serial] = None
        self.is_connected = False
        
        # Configuration
        self.port = getattr(settings, "SERIAL_PORT", "/dev/ttyUSB0")
        self.baud = getattr(settings, "SERIAL_BAUD", 115200)
        
        self.initialized = True
        self.connect()

        # EventBus Integration
        from src.core.event_bus import EventBus
        self.event_bus = EventBus()
        self.event_bus.subscribe("speech.amplitude", self._handle_hardware_event)
        self.event_bus.subscribe("hardware.jaw", self._handle_hardware_event)
        self.event_bus.subscribe("state.change", self._handle_state_change)

    def _handle_hardware_event(self, event):
        """EventBus handler for jaw amplitude updates"""
        intensity = getattr(event, "intensity", 0)
        self.send_jaw_intensity(intensity)

    def _handle_state_change(self, event):
        """EventBus handler for state transition updates"""
        new_state = getattr(event, "new_state", "IDLE")
        self.logger.debug(f"🔌 Hardware State Sync: {new_state}")
        
    def connect(self):
        """Establish serial connection"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                timeout=1
            )
            time.sleep(2)  # Wait for Arduino reset
            self.is_connected = True
            self.logger.info(f"✅ Hardware connected on {self.port}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Hardware connection failed on {self.port}: {e}")
            self.is_connected = False
            
    def send_jaw_intensity(self, intensity: int):
        """
        Send jaw intensity command (0-100)
        0 = Closed, 100 = Fully Open
        """
        if not self.is_connected or not self.serial_conn:
            return
            
        try:
            # Ensure range 0-100
            intensity = max(0, min(100, int(intensity)))
            
            # Send command string "INTENSITY\n"
            command = f"{intensity}\n"
            self.serial_conn.write(command.encode())
            
        except Exception as e:
            self.logger.error(f"❌ Serial write error: {e}")
            self.close()
            
    def close(self):
        """Close serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.is_connected = False
        self.logger.info("🔌 Hardware disconnected")
