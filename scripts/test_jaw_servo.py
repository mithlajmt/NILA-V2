#!/usr/bin/env python3
"""
Test script for NILA robot jaw servo on GPIO pin 12.
Mouth closed degree: 75°
Mouth maximum open degree: 110°
"""

import time
import sys

try:
    import lgpio
except ImportError:
    print("❌ lgpio not found in environment!")
    sys.exit(1)

GPIO_PIN = 12
CHIP_NUM = 0
CLOSE_ANGLE = 75.0
MAX_OPEN_ANGLE = 110.0

def angle_to_pulse_us(angle: float) -> int:
    """Map 0-180 degrees to standard 500-2500 us pulse width"""
    angle = max(0.0, min(180.0, float(angle)))
    return int(500.0 + (angle / 180.0) * 2000.0)

def main():
    print(f"🤖 Testing NILA Jaw Servo on GPIO {GPIO_PIN}...")
    print(f"Closed angle: {CLOSE_ANGLE}° (pulse: {angle_to_pulse_us(CLOSE_ANGLE)} µs)")
    print(f"Max open angle: {MAX_OPEN_ANGLE}° (pulse: {angle_to_pulse_us(MAX_OPEN_ANGLE)} µs)")
    
    try:
        h = lgpio.gpiochip_open(CHIP_NUM)
    except Exception as e:
        print(f"❌ Failed to open gpiochip {CHIP_NUM}: {e}")
        return

    try:
        lgpio.gpio_claim_output(h, GPIO_PIN)
        
        # 1. Move to closed position (75°)
        print("\n1. Moving to CLOSED position (75°)...")
        pulse = angle_to_pulse_us(CLOSE_ANGLE)
        lgpio.tx_servo(h, GPIO_PIN, pulse)
        time.sleep(1.0)
        
        # 2. Open slowly to 110°
        print("2. Opening slowly to MAX OPEN position (110°)...")
        for angle in range(int(CLOSE_ANGLE), int(MAX_OPEN_ANGLE) + 1, 2):
            lgpio.tx_servo(h, GPIO_PIN, angle_to_pulse_us(angle))
            time.sleep(0.05)
        time.sleep(0.5)
        
        # 3. Close slowly back to 75°
        print("3. Closing slowly to CLOSED position (75°)...")
        for angle in range(int(MAX_OPEN_ANGLE), int(CLOSE_ANGLE) - 1, -2):
            lgpio.tx_servo(h, GPIO_PIN, angle_to_pulse_us(angle))
            time.sleep(0.05)
        time.sleep(0.5)
        
        # 4. Simulate voice talking pulses (sound variation)
        print("4. Simulating voice sound variation (talking)...")
        import random
        for _ in range(25):
            intensity = random.uniform(10, 100)
            target_angle = CLOSE_ANGLE + (intensity / 100.0) * (MAX_OPEN_ANGLE - CLOSE_ANGLE)
            lgpio.tx_servo(h, GPIO_PIN, angle_to_pulse_us(target_angle))
            time.sleep(0.08)
            
        # Return to closed position
        print("\n5. Returning to CLOSED position (75°)...")
        lgpio.tx_servo(h, GPIO_PIN, angle_to_pulse_us(CLOSE_ANGLE))
        time.sleep(0.5)
        
        # Release pulse to prevent buzzing/jitter when idle
        lgpio.tx_servo(h, GPIO_PIN, 0)
        print("✅ Jaw servo test completed successfully!")
        
    finally:
        try:
            lgpio.tx_servo(h, GPIO_PIN, 0)
            lgpio.gpiochip_close(h)
        except Exception:
            pass

if __name__ == "__main__":
    main()

