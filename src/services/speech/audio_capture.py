import logging
import subprocess
import threading
import time
import re
from typing import Optional, List, Dict
from dataclasses import dataclass
import webrtcvad

@dataclass
class AudioConfig:
    """Audio capture configuration optimized for Raspberry Pi + Google STT"""
    sample_rate: int = 16000  # Hz (required by Google STT)
    channels: int = 1  # Mono
    chunk_duration_ms: int = 30  # VAD frame size (10, 20, or 30ms)
    vad_aggressiveness: int = 3  # 0-3, higher = more aggressive (filters more noise)


class AudioCapture:
    """
    Pure ALSA Audio Capture using 'arecord'
    
    Robust for Raspberry Pi robots:
    - Bypasses PipeWire/PulseAudio complexities
    - Uses native kernel drivers via ALSA
    - Zero latency, no timeouts
    """
    
    def __init__(self, config: Optional[AudioConfig] = None, device_name: str = ""):
        self.config = config or AudioConfig()
        self.logger = logging.getLogger(__name__)
        
        # Voice Activity Detection
        self.vad = webrtcvad.Vad(self.config.vad_aggressiveness)
        
        # Calculate chunk size (bytes) for VAD
        # 16-bit = 2 bytes per sample
        self.chunk_size = int(self.config.sample_rate * self.config.chunk_duration_ms / 1000) * 2
        
        # Find the hardware device string (e.g. "plughw:1,0")
        self.device_id = self._find_alsa_device(device_name)
        
        self.logger.info(f"🎙️ AudioCapture initialized (device={self.device_id}, rate={self.config.sample_rate}Hz)")

    def _find_alsa_device(self, preferred_name: str = "") -> str:
        """Parse 'arecord -l' to find the USB microphone card"""
        try:
            # Run arecord -l to list capture devices
            result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
            output = result.stdout
            
            # Regex to find card and device numbers
            # Example: card 2: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]
            cards = {}
            for line in output.split('\n'):
                match = re.search(r'card (\d+):.*?\[(.*?)\], device (\d+):', line)
                if match:
                    card_idx = match.group(1)
                    name = match.group(2)
                    dev_idx = match.group(3)
                    cards[f"{card_idx},{dev_idx}"] = name
                    self.logger.info(f"   Found ALSA Device: card {card_idx}, dev {dev_idx} [{name}]")

            # 1. Try preferred name
            if preferred_name:
                for hw_id, name in cards.items():
                    if preferred_name.lower() in name.lower():
                        self.logger.info(f"✅ Found preferred device: {name} -> plughw:{hw_id}")
                        return f"plughw:{hw_id}"

            # 2. Look for "USB"
            for hw_id, name in cards.items():
                if "usb" in name.lower():
                    self.logger.info(f"✅ Found USB Microphone: {name} -> plughw:{hw_id}")
                    return f"plughw:{hw_id}"
            
            # 3. Fallback to default (OS decides)
            self.logger.warning("⚠️ No USB mic found. Using system default 'default'")
            return "default"
            
        except Exception as e:
            self.logger.error(f"❌ Error finding ALSA devices: {e}")
            return "default"

    def record(self, 
               timeout: int = 30,
               silence_duration: float = 1.0,
               min_speech_duration: float = 0.5) -> Optional[bytes]:
        """
        Record audio using 'arecord' subprocess
        """
        process = None
        try:
            self.logger.info(f"🎯 Listening on {self.device_id}...")
            print("🎯 Listening... (Speak naturally)")
            
            # Command: arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -t raw
            cmd = [
                'arecord',
                '-D', self.device_id,
                '-f', 'S16_LE',
                '-r', str(self.config.sample_rate),
                '-c', str(self.config.channels),
                '-t', 'raw',
                '-q'  # Quiet mode
            ]
            
            # Start recording process
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                bufsize=self.chunk_size
            )
            
            start_time = time.time()
            audio_frames = []
            speech_frames = 0
            silence_frames = 0
            
            # Convert durations to frame counts
            bytes_per_chunk = self.chunk_size
            # Each chunk is chunk_duration_ms (e.g. 30ms)
            chunk_ms = self.config.chunk_duration_ms
            
            silence_threshold = int(silence_duration * 1000 / chunk_ms)
            min_speech_threshold = int(min_speech_duration * 1000 / chunk_ms)
            
            has_started_speaking = False

            while True:
                # Check timeout
                if time.time() - start_time > timeout:
                    print("⏱️ Timeout")
                    break

                # Read raw bytes from stdout
                data = process.stdout.read(bytes_per_chunk)
                if not data or len(data) != bytes_per_chunk:
                    break
                
                audio_frames.append(data)
                
                # VAD Check
                try:
                    is_speech = self.vad.is_speech(data, self.config.sample_rate)
                except:
                    is_speech = False
                
                if is_speech:
                    if not has_started_speaking:
                        print("🗣️ Speech detected...")
                        has_started_speaking = True
                    speech_frames += 1
                    silence_frames = 0
                elif has_started_speaking:
                    silence_frames += 1
                
                # Stop if we had speech and now silence
                if has_started_speaking and silence_frames > silence_threshold:
                    if speech_frames >= min_speech_threshold:
                        print(f"✅ Capture complete ({len(audio_frames) * chunk_ms / 1000:.1f}s)")
                        break
                    else:
                        # False alarm / noise
                        has_started_speaking = False
                        speech_frames = 0
                        silence_frames = 0
                        audio_frames = [] # Reset buffer

            # Cleanup
            process.terminate()
            
            if speech_frames >= min_speech_threshold:
                return b''.join(audio_frames)
            else:
                return None

        except Exception as e:
            self.logger.error(f"❌ Recording error: {e}")
            return None
        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=0.5)
                except:
                    process.kill()

    def test_record(self, duration: float = 3.0) -> Optional[bytes]:
        """Simple timed recording"""
        try:
            print(f"🎙️ Recording for {duration}s on {self.device_id}...")
            
            cmd = [
                'arecord',
                '-D', self.device_id,
                '-f', 'S16_LE',
                '-r', str(self.config.sample_rate),
                '-c', str(self.config.channels),
                '-t', 'raw',
                '-d', str(int(duration)), # Duration in seconds
                '-q'
            ]
            
            result = subprocess.run(cmd, capture_output=True)
            
            if result.returncode == 0:
                print(f"✅ Success! Captured {len(result.stdout)} bytes")
                return result.stdout
            else:
                print(f"❌ Error: {result.stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            return None
    
    def get_device_info(self) -> dict:
        """Mock info for compatibility"""
        return {"name": self.device_id}

    @staticmethod
    def list_devices():
        """Print available ALSA devices"""
        subprocess.run(['arecord', '-l'])
