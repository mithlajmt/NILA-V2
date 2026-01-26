#!/usr/bin/env python3
"""
Quick audio device diagnostic
Check if microphone is detected and working
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import sounddevice as sd
    import numpy as np
    import audioop
    import time
    
    print("🔍 Audio Device Diagnostic")
    print("=" * 60)
    
    # List all devices
    print("\n📋 Available Audio Devices:")
    print("-" * 60)
    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"  [{i}] {device['name']}")
                print(f"      Input channels: {device['max_input_channels']}")
                print(f"      Sample rate: {device['default_samplerate']} Hz")
                if i == sd.default.device[0]:
                    print(f"      ⭐ DEFAULT INPUT DEVICE")
                print()
    except Exception as e:
        print(f"  ❌ Error listing devices: {e}")
    
    # Check default input
    print("\n🎤 Default Input Device:")
    print("-" * 60)
    try:
        default_input = sd.query_devices(kind='input')
        print(f"  Name: {default_input['name']}")
        print(f"  Channels: {default_input['max_input_channels']}")
        print(f"  Sample Rate: {default_input['default_samplerate']} Hz")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print("  ⚠️ No default input device found!")
        sys.exit(1)
    
    # Test recording
    print("\n🎙️ Testing Microphone (5 seconds)...")
    print("-" * 60)
    print("  Speak into your microphone now...")
    
    try:
        duration = 5
        sample_rate = 16000
        samples = int(duration * sample_rate)
        
        recording = sd.rec(samples, samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        
        # Analyze recording
        recording_bytes = recording.tobytes()
        max_amplitude = max(abs(sample) for sample in recording.flatten())
        avg_rms = audioop.rms(recording_bytes, 2)
        
        print(f"\n  ✅ Recording complete!")
        print(f"  📊 Max amplitude: {max_amplitude}")
        print(f"  📊 Average RMS: {int(avg_rms)}")
        
        if max_amplitude < 100:
            print(f"\n  ⚠️ WARNING: Very low amplitude detected!")
            print(f"     Mic might not be working or is muted")
            print(f"     Expected: > 1000 for normal speech")
        elif max_amplitude < 1000:
            print(f"\n  ⚠️ WARNING: Low amplitude detected")
            print(f"     Mic might be too quiet or far away")
        else:
            print(f"\n  ✅ Microphone appears to be working!")
            
    except Exception as e:
        print(f"  ❌ Error during recording: {e}")
        print(f"     Check: Is mic connected? Permissions?")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Diagnostic complete!")
    
except ImportError:
    print("❌ sounddevice not installed")
    print("   Install: pip install sounddevice")
    sys.exit(1)
