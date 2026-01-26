#!/usr/bin/env python3
"""
VAD Diagnostic Script for Raspberry Pi

This script records audio using 'parecord' (PipeWire) and:
1. Calculates RMS amplitude (Volume/Energy)
2. Runs WebRTC VAD (Voice Activity Detection)
3. Prints a visual bar for volume and VAD status

Usage:
    python3 scripts/test_vad.py
"""
import subprocess
import webrtcvad
import audioop
import time
import sys
import shutil

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_MS = 30
VAD_AGGRESSIVENESS = 3  # 0-3

def main():
    print(f"🎙️ Testing VAD (Rate={SAMPLE_RATE}, Agg={VAD_AGGRESSIVENESS})")
    print("---------------------------------------------------")
    print("VOLUME   | VAD | STATUS")
    print("---------------------------------------------------")

    # Initialize VAD
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    # Calculate chunk size
    # 16-bit = 2 bytes per sample
    chunk_size = int(SAMPLE_RATE * CHUNK_MS / 1000) * 2

    # Command: parecord --format=s16le --rate=16000 --channels=1 --raw
    cmd = [
        'parecord',
        '--format=s16le',
        f'--rate={SAMPLE_RATE}',
        f'--channels={CHANNELS}',
        '--raw',
        # '--latency-msec=100' # Optional: reduce latency buffer
    ]

    process = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=chunk_size
        )

        while True:
            data = process.stdout.read(chunk_size)
            if not data or len(data) != chunk_size:
                break

            # 1. Calculate Energy (RMS)
            rms = audioop.rms(data, 2)  # 2 = sample width (16-bit)
            
            # 2. Check VAD
            try:
                is_speech = vad.is_speech(data, SAMPLE_RATE)
            except Exception as e:
                print(f"VAD Error: {e}")
                is_speech = False

            # Visuals
            bar_len = min(50, int(rms / 100))  # Scale for display
            bar = "█" * bar_len
            status = "🗣️ SPEECH" if is_speech else ".."

            # Threshold suggestion (if VAD is triggering on noise)
            # If is_speech is True but RMS is low, we have a problem.
            
            print(f"{rms:5d} |  {1 if is_speech else 0}  | {status} {bar}")

    except KeyboardInterrupt:
        print("\n⏹️ Stopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if process:
            process.terminate()

if __name__ == "__main__":
    if not shutil.which("parecord"):
        print("❌ Error: 'parecord' not found. Is PipeWire installed?")
        sys.exit(1)
    main()
