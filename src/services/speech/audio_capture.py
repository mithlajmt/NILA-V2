import logging
import subprocess
import threading
import time
import re
import audioop
import shutil
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
    energy_threshold: int = 300  # Minimum RMS amplitude to consider as speech

class AudioCapture:
    """
    PipeWire / ALSA Audio Capture using 'parecord' or 'arecord'
    
    Robust for Raspberry Pi 5 / Linux audio stack:
    - Uses PipeWire/PulseAudio stack or ALSA fallback
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
        self.device_id = "default"
        
        self.logger.info(f"🎙️ AudioCapture initialized (rate={self.config.sample_rate}Hz, threshold={self.config.energy_threshold})")

    def record(self, 
               timeout: int = 30,
               silence_duration: float = 1.0,
               min_speech_duration: float = 0.5) -> Optional[bytes]:
        """
        Record audio using 'parecord' or 'arecord' subprocess
        """
        process = None
        try:
            self.logger.info(f"🎯 Listening via Audio Subprocess...")
            print("🎯 Listening... (Speak naturally)")
            
            if shutil.which('parecord'):
                cmd = [
                    'parecord',
                    '--format=s16le',
                    f'--rate={self.config.sample_rate}',
                    f'--channels={self.config.channels}',
                    '--raw',
                ]
            elif shutil.which('arecord'):
                cmd = [
                    'arecord',
                    '-f', 'S16_LE',
                    '-r', str(self.config.sample_rate),
                    '-c', str(self.config.channels),
                    '-t', 'raw',
                ]
            else:
                raise RuntimeError("Neither 'parecord' nor 'arecord' audio recording utility was found on your system.")
            
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

            # --- DYNAMIC CALIBRATION ---
            # Listen for first ~500ms to determine noise floor
            calibration_chunks = 15 # approx 450ms
            noise_energy_sum = 0
            
            print("Adjusting to background noise...", end="", flush=True)
            for _ in range(calibration_chunks):
                data = process.stdout.read(bytes_per_chunk)
                if not data: break
                rms = audioop.rms(data, 2)
                noise_energy_sum += rms
                # Keep these frames so we don't lose early speech if they start IMMEDIATELY
                # but valid speech usually doesn't start in first 0.1s of listening
                
            avg_noise = noise_energy_sum / calibration_chunks
            
            # Set threshold significantly above noise floor
            # If noise is 23000, we need threshold around 25000?
            # Or is 23000 DC offset?
            # Safe margin: Noise * 1.2 + constant
            dynamic_threshold = int(avg_noise * 1.2) + 300
            
            # Cap the threshold to avoid blocking everything if noise is insane
            # Max possible RMS for 16-bit is ~32767. 
            if dynamic_threshold > 30000:
                print(f"\n⚠️ High Noise detected ({int(avg_noise)}). Clamping threshold.")
                dynamic_threshold = 30000
                
            print(f" Done. (Noise: {int(avg_noise)} -> Threshold: {dynamic_threshold})")
            
            # ---------------------------

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
                
                # Energy Check (Gate)
                rms = audioop.rms(data, 2)
                
                # VAD Check (only if energy is above calibrated threshold)
                is_speech = False
                if rms > dynamic_threshold:
                    try:
                        is_speech = self.vad.is_speech(data, self.config.sample_rate)
                    except:
                        is_speech = False
                
                if is_speech:
                    if not has_started_speaking:
                        print(f"🗣️ Speech detected (Energy: {rms})")
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
