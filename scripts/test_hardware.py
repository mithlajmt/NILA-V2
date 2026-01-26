import serial
import time
import sys
import argparse
import serial.tools.list_ports

def get_default_port():
    # Try to find a likely port
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "USB" in p.description or "ACM" in p.description:
            return p.device
    return "/dev/ttyUSB0"

def test_hardware(port=None, baud=115200):
    target_port = port or get_default_port()
    
    print(f"🔌 Connecting to {target_port}...")
    
    try:
        ser = serial.Serial(target_port, baud, timeout=1)
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
        
    except serial.SerialException as e:
        print(f"❌ Connection Error: {e}")
        print("\nTroubleshooting:")
        print(f"1. Check if {target_port} exists (ls {target_port})")
        print("2. Check permissions (sudo chmod 666 /dev/ttyUSB0)")
        print("3. Check USB connection")
        print("4. Run 'python3 scripts/find_arduino.py' to list ports")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test NILA-V2 Hardware')
    parser.add_argument('--port', help='Serial port (e.g., /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    
    args = parser.parse_args()
    test_hardware(args.port, args.baud)
