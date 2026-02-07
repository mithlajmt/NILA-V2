#!/usr/bin/env python3
"""
Test GPIO jaw servo control on Raspberry Pi.
Drives servo on BCM pin 14 through intensity values.
"""
import sys
import time
sys.path.insert(0, '/home/learnlogicai/Desktop/NILA-V2')

from src.services.hardware.serial_controller import SerialController

# Create a mock settings object with GPIO mode enabled
class MockSettings:
    SERIAL_PORT = "GPIO"
    USE_GPIO_JAW = True
    GPIO_JAW_PIN = 14
    JAW_CLOSED_ANGLE = 50
    JAW_OPEN_ANGLE = 110

settings = MockSettings()

print("=== GPIO Jaw Test ===\n")
print(f"GPIO Pin: {settings.GPIO_JAW_PIN}")
print(f"Closed Angle: {settings.JAW_CLOSED_ANGLE}°")
print(f"Open Angle: {settings.JAW_OPEN_ANGLE}°\n")

try:
    # Initialize hardware controller
    print("Initializing GPIO jaw control...")
    hw = SerialController(settings)
    
    if not hw.is_connected:
        print("❌ GPIO jaw control failed to initialize!")
        sys.exit(1)
    
    print("✅ GPIO jaw control ready\n")
    
    # Test sequence
    print("=== Testing intensity sequence ===")
    test_values = [0, 25, 50, 75, 100, 75, 50, 25, 0]
    
    for intensity in test_values:
        print(f"\nSending intensity: {intensity}")
        hw.send_jaw_intensity(intensity)
        time.sleep(1)
    
    print("\n=== Test complete ===")
    hw.close()
    print("✅ GPIO jaw test finished successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
