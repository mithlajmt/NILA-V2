#!/usr/bin/env python3
"""
Test jaw servo serial communication.
Opens port, waits for MCU boot, sends intensity values, captures responses.
"""
import serial
import time

PORT = '/dev/ttyUSB0'
BAUD = 115200

print("Opening serial port...")
s = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

print("\n=== Reading MCU boot messages ===")
start = time.time()
while time.time() - start < 3:
    line = s.readline().decode(errors='ignore').strip()
    if line:
        print(f"MCU: {line}")

print("\n=== Sending intensity values ===")
for i in (0, 50, 100, 50, 0):
    print(f"Sending: {i}")
    s.write(f"{i}\n".encode())
    time.sleep(0.5)
    
    # Read response
    line = s.readline().decode(errors='ignore').strip()
    if line:
        print(f"MCU: {line}")
    time.sleep(0.5)

print("\n=== Test complete ===")
s.close()
print("Port closed.")
