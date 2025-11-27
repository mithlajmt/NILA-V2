import serial.tools.list_ports
import sys

def find_arduino():
    print("🔍 Scanning for Serial Ports...")
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("❌ No serial ports found!")
        return

    arduino_ports = []
    
    print(f"\nFound {len(ports)} ports:")
    for p in ports:
        print(f"  - {p.device} : {p.description} [{p.hwid}]")
        if "USB" in p.description or "ACM" in p.description or "Arduino" in p.description:
            arduino_ports.append(p.device)
            
    print("\nAnalysis:")
    if arduino_ports:
        print(f"✅ Potential Arduino devices found: {', '.join(arduino_ports)}")
        print(f"👉 Try using: {arduino_ports[0]}")
    else:
        print("⚠️ No obvious Arduino/USB serial devices found.")
        print("👉 Check your USB cable and connection.")
        print("👉 If using a clone Arduino, you might need drivers (CH340/CP210x).")

if __name__ == "__main__":
    find_arduino()
