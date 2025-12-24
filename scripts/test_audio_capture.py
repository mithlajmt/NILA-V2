#!/usr/bin/env python3
"""
Test script for PipeWire-compatible audio capture
Verifies microphone detection and recording functionality
"""
import sys
import os
import argparse
import wave
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.speech.audio_capture import AudioCapture, AudioConfig


def list_devices():
    """List all available audio input devices"""
    print("\n" + "="*60)
    print("AUDIO DEVICE DETECTION TEST")
    print("="*60)
    AudioCapture.list_devices()
    print()


def test_record(duration: float = 5.0, output_file: str = "test_recording.wav"):
    """Test audio recording and save to WAV file"""
    print("\n" + "="*60)
    print("AUDIO RECORDING TEST")
    print("="*60)
    
    # Initialize audio capture
from src.config.settings import Settings

    # Initialize audio capture
    settings = Settings()
    config = AudioConfig(
        sample_rate=16000,
        channels=1,
        vad_aggressiveness=2
    )
    
    # Use device name from settings to ensure PULSE_SOURCE fix is applied
    device_name = settings.AUDIO_DEVICE_NAME
    capture = AudioCapture(config=config, device_name=device_name)
    
    print(f"\n📍 Using device: {capture.get_device_info()['name']}")
    print(f"📊 Sample rate: {config.sample_rate}Hz")
    print(f"🎚️ Channels: {config.channels}")
    print(f"\n🎙️ Recording for {duration} seconds...")
    print("   (Speak into the microphone)\n")
    
    # Record audio
    audio_data = capture.test_record(duration=duration)
    
    if audio_data is None:
        print("❌ Recording failed!")
        return False
    
    # Save to WAV file
    try:
        with wave.open(output_file, 'wb') as wf:
            wf.setnchannels(config.channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(config.sample_rate)
            wf.writeframes(audio_data.tobytes())
        
        print(f"\n✅ Recording saved to: {output_file}")
        print(f"   Duration: {len(audio_data) / config.sample_rate:.2f}s")
        print(f"   Size: {len(audio_data) * 2} bytes")
        
        # Calculate audio statistics
        max_amplitude = np.max(np.abs(audio_data))
        rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
        
        print(f"\n📊 Audio Statistics:")
        print(f"   Max amplitude: {max_amplitude} / 32768 ({max_amplitude/32768*100:.1f}%)")
        print(f"   RMS level: {rms:.0f}")
        
        if max_amplitude < 1000:
            print("\n⚠️  WARNING: Audio level very low! Check:")
            print("   - Microphone is connected and selected")
            print("   - Microphone volume in system settings")
            print("   - Speaking close enough to microphone")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving WAV file: {e}")
        return False


def test_vad_record(timeout: int = 10):
    """Test Voice Activity Detection recording"""
    print("\n" + "="*60)
    print("VOICE ACTIVITY DETECTION TEST")
    print("="*60)
    
    # Initialize audio capture
    settings = Settings()
    config = AudioConfig(
        sample_rate=16000,
        channels=1,
        vad_aggressiveness=2
    )
    
    device_name = settings.AUDIO_DEVICE_NAME
    capture = AudioCapture(config=config, device_name=device_name)
    
    print(f"\n📍 Using device: {capture.get_device_info()['name']}")
    print(f"⏱️  Timeout: {timeout}s")
    print(f"🔇 Will stop after 1.5s of silence")
    print(f"\n🎙️ Speak now...\n")
    
    # Record with VAD
    audio_bytes = capture.record(
        timeout=timeout,
        silence_duration=1.5,
        min_speech_duration=0.5
    )
    
    if audio_bytes is None:
        print("❌ No speech detected!")
        return False
    
    # Save to WAV file
    output_file = "test_vad_recording.wav"
    try:
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        
        with wave.open(output_file, 'wb') as wf:
            wf.setnchannels(config.channels)
            wf.setsampwidth(2)
            wf.setframerate(config.sample_rate)
            wf.writeframes(audio_bytes)
        
        print(f"\n✅ VAD recording saved to: {output_file}")
        print(f"   Duration: {len(audio_array) / config.sample_rate:.2f}s")
        print(f"   Size: {len(audio_bytes)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving recording: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test PipeWire-compatible audio capture for Raspberry Pi"
    )
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help='List all available audio input devices'
    )
    parser.add_argument(
        '--record',
        type=float,
        metavar='SECONDS',
        help='Test simple recording for specified duration (e.g., --record 5)'
    )
    parser.add_argument(
        '--vad',
        action='store_true',
        help='Test Voice Activity Detection recording'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='test_recording.wav',
        help='Output WAV file name (default: test_recording.wav)'
    )
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n💡 Examples:")
        print("   python test_audio_capture.py --list-devices")
        print("   python test_audio_capture.py --record 5")
        print("   python test_audio_capture.py --vad")
        return
    
    # Run tests
    if args.list_devices:
        list_devices()
    
    if args.record:
        test_record(duration=args.record, output_file=args.output)
    
    if args.vad:
        test_vad_record()


if __name__ == "__main__":
    main()
