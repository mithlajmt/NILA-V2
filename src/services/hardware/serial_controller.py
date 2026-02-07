"""
Serial Controller for Torres Hardware
Manages communication with Arduino for Jaw and Eye control.
"""

import logging
import time
import serial
import serial.tools.list_ports
try:
    from gpiozero import PWMOutputDevice, Device
    _HAVE_GPIOZERO = True
except Exception:
    PWMOutputDevice = None
    Device = None
    _HAVE_GPIOZERO = False
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
            return  # Only initialize once
            
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.serial_conn: Optional[serial.Serial] = None
        self.is_connected = False
        self._reader_thread = None
        self._reader_thread_running = False
        
        # Configuration
        self.port = getattr(settings, "SERIAL_PORT", "/dev/ttyUSB0")
        self.baud = getattr(settings, "SERIAL_BAUD", 115200)
        # GPIO jaw mode (use Raspberry Pi GPIO instead of serial)
        self.gpio_mode = False
        self._gpio_pwm = None
        
        if getattr(settings, "USE_GPIO_JAW", False) or str(self.port).upper() == "GPIO":
            self.gpio_mode = True
            # Use BCM numbering by default
            self.gpio_jaw_pin = getattr(settings, "GPIO_JAW_PIN", 14)
            self.jaw_closed_angle = getattr(settings, "JAW_CLOSED_ANGLE", 50)
            self.jaw_open_angle = getattr(settings, "JAW_OPEN_ANGLE", 110)
        
        self.initialized = True
        
        # If gpio_mode, initialize GPIO instead of serial
        if self.gpio_mode:
            self._init_gpio()
        else:
            self.connect()

    def _init_gpio(self):
        """Set up Raspberry Pi GPIO for servo control using gpiozero."""
        if not _HAVE_GPIOZERO:
            self.logger.warning("⚠️ gpiozero not available; GPIO jaw disabled")
            self.gpio_mode = False
            return
        try:
            # Set up the pin factory for Pi 5 (lazy initialization)
            if Device is not None:
                try:
                    from gpiozero.pins.lgpio import LGPIOFactory
                    Device.pin_factory = LGPIOFactory()
                    self.logger.debug("✅ LGPIOFactory set for gpiozero")
                except ImportError:
                    self.logger.debug("⚠️ LGPIOFactory not available, using default")
            
            # Create PWMOutputDevice for servo control on BCM pin
            self._gpio_pwm = PWMOutputDevice(
                pin=self.gpio_jaw_pin,
                frequency=50
            )
            # Start PWM at closed angle
            closed_angle = int(self.jaw_closed_angle)
            duty = self._angle_to_duty(closed_angle) / 100.0  # gpiozero expects 0.0-1.0
            self._gpio_pwm.value = duty
            self.logger.debug(f"✅ GPIO jaw control initialized on BCM {self.gpio_jaw_pin}")
            self.is_connected = True
        except Exception as e:
            self.logger.warning(f"⚠️ GPIO initialization failed: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            self.gpio_mode = False
            self.is_connected = False

    def _angle_to_duty(self, angle: float) -> float:
        """Convert servo angle (0-180) to PWM duty cycle for 50Hz."""
        # Typical mapping: 2.5% -> 0deg, 12.5% -> 180deg
        return 2.5 + (angle / 180.0) * 10.0
        
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
            # Start serial reader thread to capture MCU prints
            try:
                if not self._reader_thread_running:
                    self._reader_thread_running = True
                    self._reader_thread = threading.Thread(target=self._serial_reader, daemon=True)
                    self._reader_thread.start()
            except Exception:
                pass
            
        except Exception as e:
            self.logger.warning(f"⚠️ Hardware connection failed on {self.port}: {e}")
            self.is_connected = False
            # Try auto-detecting a USB/ACM serial port as a fallback
            try:
                ports = list(serial.tools.list_ports.comports())
                for p in ports:
                    desc = (p.description or "").lower()
                    if 'usb' in desc or 'acm' in desc or 'arduino' in desc or 'stm' in desc:
                        try_port = p.device
                        self.logger.info(f"🔎 Trying fallback serial port {try_port}")
                        try:
                            self.serial_conn = serial.Serial(port=try_port, baudrate=self.baud, timeout=1)
                            time.sleep(2)
                            self.port = try_port
                            self.is_connected = True
                            self.logger.info(f"✅ Hardware connected on {self.port} (auto-detected)")
                            # Start serial reader thread to capture MCU prints
                            try:
                                if not self._reader_thread_running:
                                    self._reader_thread_running = True
                                    self._reader_thread = threading.Thread(target=self._serial_reader, daemon=True)
                                    self._reader_thread.start()
                            except Exception:
                                pass
                            return
                        except Exception:
                            continue
            except Exception:
                pass
            
    def send_jaw_intensity(self, intensity: int):
        """
        Send jaw intensity command (0-100)
        0 = Closed, 100 = Fully Open
        """
        # If using GPIO mode, drive servo via PWM on Pi GPIO
        if self.gpio_mode:
            try:
                intensity = max(0, min(100, int(intensity)))
                # Map intensity to angle
                closed = float(self.jaw_closed_angle)
                open_a = float(self.jaw_open_angle)
                angle = closed + (intensity / 100.0) * (open_a - closed)
                duty = self._angle_to_duty(angle)
                if self._gpio_pwm is None:
                    # try to (re)initialize gpio
                    self._init_gpio()
                    if self._gpio_pwm is None:
                        self.logger.warning("⚠️ GPIO PWM not available, dropping jaw command")
                        return
                # gpiozero expects 0.0-1.0 range
                self._gpio_pwm.value = duty / 100.0
                self.logger.debug(f"➡️ GPIO jaw angle set: {angle:.1f}° (intensity={intensity}) duty={duty:.2f}%")
            except Exception as e:
                self.logger.error(f"❌ GPIO jaw control error: {e}")
            return
            
        try:
            # Ensure range 0-100
            intensity = max(0, min(100, int(intensity)))
            
            # Send command string "INTENSITY\n"
            command = f"{intensity}\n"
            self.logger.info(f"➡️ Writing to serial {self.port}: {command.strip()}")
            self.serial_conn.write(command.encode())
            self.logger.info("✅ Serial write successful")
            
        except Exception as e:
            self.logger.error(f"❌ Serial write error: {e}")
            # Try to reconnect once
            try:
                self.close()
                self.connect()
            except Exception:
                pass
            
    def close(self):
        """Close serial connection"""
        # Stop reader thread
        try:
            self._reader_thread_running = False
        except Exception:
            pass
        # Stop GPIO PWM if used
        try:
            if self.gpio_mode and self._gpio_pwm is not None:
                try:
                    self._gpio_pwm.close()
                except Exception:
                    pass
                self._gpio_pwm = None
                self.logger.debug("🔌 GPIO jaw control stopped")
        except Exception:
            pass

        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.is_connected = False
        self.logger.info("🔌 Hardware disconnected")

    def _serial_reader(self):
        """Background thread: read lines from MCU and log them."""
        while self._reader_thread_running:
            try:
                if not self.serial_conn or not self.serial_conn.is_open:
                    time.sleep(0.2)
                    continue

                line = self.serial_conn.readline()
                if not line:
                    continue
                try:
                    text = line.decode(errors='ignore').strip()
                except Exception:
                    text = str(line)

                if text:
                    self.logger.info(f"📡 MCU: {text}")
            except Exception:
                # On any read error, sleep briefly and retry
                try:
                    time.sleep(0.2)
                except Exception:
                    pass
