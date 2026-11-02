#!/usr/bin/env python3
"""
NILA-V2 - Real-Time Microphone Volume Level Test
-------------------------------------------------
Visual volume meter to test your physical microphone.
Speak into the microphone or tap it to see the volume bar rise!
"""

import sys
import time
import math
import struct
import sounddevice as sd

def calculate_rms(pcm_bytes):
    if not pcm_bytes:
        return 0
    count = len(pcm_bytes) // 2
    if count == 0:
        return 0
    samples = struct.unpack(f"<{count}h", pcm_bytes)
    sum_squares = sum(s * s for s in samples)
    return int(math.sqrt(sum_squares / count))

def main():
    print("\n" + "="*65)
    print("🎙️ NILA-V2 REAL-TIME MICROPHONE LEVEL TESTER")
    print("="*65)
    print("👉 Speak into your microphone or tap it!")
    print("   Watch the visual volume bar below in real time.")
    print("   Press CTRL+C anytime to stop.\n")

    # Use pulse device
    samplerate = 16000
    channels = 1
    blocksize = 1024

    def callback(indata, frames, time_info, status):
        pcm = indata.tobytes()
        rms = calculate_rms(pcm)
        bar_len = min(40, rms // 15)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        status_txt = "🗣️ [SPEAKING]" if rms > 50 else "   [quiet]   "
        sys.stdout.write(f"\r{status_txt} |{bar}| RMS: {rms:4d} ")
        sys.stdout.flush()

    try:
        # Device 0: HD Camera Microphone
        with sd.InputStream(device=0, samplerate=samplerate, channels=channels, dtype='int16', callback=callback, blocksize=blocksize):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n✅ Test complete.")
    except Exception as e:
        print(f"\n❌ Error opening microphone stream: {e}")

if __name__ == "__main__":
    main()
