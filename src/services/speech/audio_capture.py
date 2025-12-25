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
    PipeWire Audio Capture using 'parecord'
    
    Robust for Raspberry Pi 5 with Bluetooth:
    - Uses PipeWire/PulseAudio stack (native to Bookworm)
    - Compatible with Bluetooth speakers (no "Device Busy" errors)
    - Full-Duplex capable
    """
    
    def __init__(self, config: Optional[AudioConfig] = None, device_name: str = "default"):
        self.config = config or AudioConfig()
        self.logger = logging.getLogger(__name__)
        
        # Voice Activity Detection
        self.vad = webrtcvad.Vad(self.config.vad_aggressiveness)
        
        # Calculate chunk size (bytes) for VAD
        # 16-bit = 2 bytes per sample
        self.chunk_size = int(self.config.sample_rate * self.config.chunk_duration_ms / 1000) * 2
        
        # Use default PipeWire source
        self.device_id = "default (PipeWire)"
        
        self.logger.info(f"🎙️ AudioCapture initialized via PipeWire (rate={self.config.sample_rate}Hz)")

    def record(self, 
               timeout: int = 30,
               silence_duration: float = 1.0,
               min_speech_duration: float = 0.5) -> Optional[bytes]:
        """
        Record audio using 'parecord' subprocess
        """
        process = None
        try:
            self.logger.info(f"🎯 Listening via PipeWire...")
            print("🎯 Listening... (Speak naturally)")
            
            # Command: parecord --format=s16le --rate=16000 --channels=1 --raw
            cmd = [
                'parecord',
                '--format=s16le',
                f'--rate={self.config.sample_rate}',
                f'--channels={self.config.channels}',
                '--raw',
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
            print(f"🎙️ Recording for {duration}s via PipeWire...")
            
            cmd = [
                'parecord',
                '--format=s16le',
                f'--rate={self.config.sample_rate}',
                f'--channels={self.config.channels}',
                '--raw',
            ]
            
            # Need to run with a duration limit, parecord doesn't have -d flag like arecord
            # We must use 'timeout' cmd or manual kill
            
            # actually we can just capture output for N seconds
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(duration)
            process.terminate()
            stdout, stderr = process.communicate()
            
            if stdout:
                print(f"✅ Success! Captured {len(stdout)} bytes")
                return stdout
            else:
                print(f"❌ Error: {stderr.decode() if stderr else 'No data'}")
                return None
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            return None
    
    def get_device_info(self) -> dict:
        """Mock info for compatibility"""
        return {"name": "PipeWire Default"}

    @staticmethod
    def list_devices():
        """Print available PipeWire sources"""
        subprocess.run(['pactl', 'list', 'short', 'sources'])
