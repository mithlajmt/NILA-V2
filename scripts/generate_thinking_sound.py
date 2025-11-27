import math
import wave
import struct
import os
import random

def generate_thinking_sound(filename="data/audio/sfx/thinking.wav"):
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Audio parameters
    sample_rate = 44100
    duration = 2.0  # seconds
    
    # Generate audio data
    audio = []
    num_samples = int(sample_rate * duration)
    
    for i in range(num_samples):
        t = i / sample_rate
        
        # Carrier: 800Hz, Modulator: 4Hz (pulse speed)
        carrier = math.sin(2 * math.pi * 800 * t)
        modulator = (math.sin(2 * math.pi * 4 * t) + 1) / 2
        
        # Noise
        noise = random.gauss(0, 0.05)
        
        # Combine
        sample = (carrier * modulator * 0.3) + (noise * 0.1)
        
        # Fade in/out
        fade_len = int(0.1 * sample_rate)
        if i < fade_len:
            sample *= (i / fade_len)
        elif i > num_samples - fade_len:
            sample *= ((num_samples - i) / fade_len)
            
        # Clamp and scale
        sample = max(-1.0, min(1.0, sample))
        audio.append(int(sample * 32767))
    
    # Save to WAV
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack(f'<{len(audio)}h', *audio))
        
    print(f"✅ Generated thinking sound: {filename}")

if __name__ == "__main__":
    generate_thinking_sound()
