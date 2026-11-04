#!/usr/bin/env python3
"""
Test speech and jaw servo synchronization on Raspberry Pi 5 GPIO 12.
"""

import asyncio
import numpy as np
import time
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydub import AudioSegment
from pydub.generators import Sine

from src.services.hardware.jaw_controller import JawController
from src.utils.audio_lipsync import play_audio_with_lipsync

async def test_live_jaw_sync():
    print("🤖 Testing Voice-Synchronized Jaw Movement on GPIO 12...")
    
    jaw = JawController(gpio_pin=12, close_angle=75.0, max_open_angle=110.0)
    print(f"Jaw initialized: Closed={jaw.close_angle}°, Max Open={jaw.max_open_angle}°")

    # Create a test audio file with varying amplitude (quiet -> loud -> quiet -> loud)
    test_dir = Path("data/audio/tests")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_wav = test_dir / "jaw_voice_test.wav"

    print("Generating simulated voice amplitude test clip (3.5 seconds)...")
    tone_quiet = Sine(300).to_audio_segment(duration=600, volume=-20.0)
    silence = AudioSegment.silent(duration=300)
    tone_medium = Sine(450).to_audio_segment(duration=700, volume=-10.0)
    silence2 = AudioSegment.silent(duration=300)
    tone_loud = Sine(600).to_audio_segment(duration=1000, volume=0.0)
    silence3 = AudioSegment.silent(duration=600)

    combined = tone_quiet + silence + tone_medium + silence2 + tone_loud + silence3
    combined.export(str(test_wav), format="wav")

    print(f"Audio ready: {test_wav} (Duration: {len(combined)} ms)")
    print("\n▶️ Playing audio & tracking jaw angles in real-time...")
    
    def on_intensity_debug(intensity: int):
        target = jaw.close_angle + (intensity / 100.0) * (jaw.max_open_angle - jaw.close_angle)
        bars = "█" * int(intensity / 5)
        print(f"\r[Sound: {intensity:3d}% | Angle: {target:5.1f}°] {bars:<20}", end="", flush=True)
        jaw.set_intensity(intensity)

    await play_audio_with_lipsync(
        audio_file=test_wav,
        on_intensity=on_intensity_debug,
    )

    print("\n\n✅ Speech-to-jaw synchronization completed. Jaw returned to 75° (closed).")
    jaw.cleanup()

if __name__ == "__main__":
    asyncio.run(test_live_jaw_sync())
