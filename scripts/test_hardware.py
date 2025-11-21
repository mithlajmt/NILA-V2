import serial
import time
import sys

PORT = "/dev/ttyUSB0"
BAUD = 115200

def test_hardware():
    print(f"🔌 Connecting to {PORT}...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2) # Wait for Arduino reset
        print("✅ Connected!")
        
        print("👄 Testing Jaw (Open)...")
        ser.write(b"100\n")
        time.sleep(1)
        
        print("👄 Testing Jaw (Close)...")
        ser.write(b"0\n")
        time.sleep(1)
        
        print("👄 Testing Jaw (Half)...")
        ser.write(b"50\n")
        time.sleep(1)
        
        print("👄 Testing Jaw (Close)...")
        ser.write(b"0\n")
        
        ser.close()
        print("✅ Test Complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("👉 Try running: sudo chmod 666 /dev/ttyUSB0")

if __name__ == "__main__":
    test_hardware()
