#!/usr/bin/env python3
"""
Test sustained loud speech with syllable articulation.
Simulates a loud sentence lasting 4 seconds with intensity=100.
"""

import math
import time
import lgpio

GPIO_PIN = 12
CHIP_NUM = 0
CLOSE_ANGLE = 75.0
MAX_OPEN_ANGLE = 110.0
ANGLE_RANGE = MAX_OPEN_ANGLE - CLOSE_ANGLE

def angle_to_pulse_us(angle: float) -> int:
    clamped = max(0.0, min(180.0, float(angle)))
    return int(500.0 + (clamped / 180.0) * 2000.0)

def main():
    print("🤖 Testing Syllable Articulation on Continuous Loud Speech...")
    h = lgpio.gpiochip_open(CHIP_NUM)
    lgpio.gpio_claim_output(h, GPIO_PIN)

    try:
        # Move to closed initially
        lgpio.tx_servo(h, GPIO_PIN, angle_to_pulse_us(CLOSE_ANGLE))
        time.sleep(0.5)

        print("\n🗣️ Simulating a 4-second LOUD sentence (intensity = 100%)...")
        print("Mouth should actively articulate syllables between ~85° and 110° instead of freezing open!")
        
        start_time = time.time()
        freq = 4.2  # 4.2 syllables per second (natural speech tempo)
        curr_angle = CLOSE_ANGLE

        while time.time() - start_time < 4.0:
            elapsed = time.time() - start_time
            # Syllable modulation between 0.25 and 1.00
            cycle = 0.5 + 0.5 * math.sin(2.0 * math.pi * freq * elapsed)
            art = 0.25 + 0.75 * cycle
            
            target_angle = CLOSE_ANGLE + art * ANGLE_RANGE
            curr_angle = 0.45 * target_angle + 0.55 * curr_angle
            curr_angle = max(CLOSE_ANGLE, min(MAX_OPEN_ANGLE, curr_angle))
            
            pulse = angle_to_pulse_us(curr_angle)
            lgpio.tx_servo(h, GPIO_PIN, pulse)
            
            bar = "█" * int((curr_angle - CLOSE_ANGLE) / 1.5)
            print(f"\rAngle: {curr_angle:5.1f}° | {bar:<25}", end="", flush=True)
            time.sleep(0.035)

        print("\n\n🤫 Sentence finished. Closing mouth to 75°...")
        lgpio.tx_servo(h, GPIO_PIN, angle_to_pulse_us(CLOSE_ANGLE))
        time.sleep(0.3)
        lgpio.tx_servo(h, GPIO_PIN, 0)
        print("✅ Test complete!")

    finally:
        lgpio.tx_servo(h, GPIO_PIN, 0)
        lgpio.gpiochip_close(h)

if __name__ == "__main__":
    main()

