import logging
import subprocess
import threading
import time
import re
import audioop
import asyncio
from typing import Optional, List, Dict, AsyncGenerator
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
        
        self.logger.info(f"🎙️ AudioCapture initialized via PipeWire (rate={self.config.sample_rate}Hz, threshold={self.config.energy_threshold})")

    async def stream_audio(self, 
                          chunk_duration_ms: int = 100,
                          timeout: float = 30.0,
                          silence_duration: float = 1.5,
                          min_speech_duration: float = 0.5) -> AsyncGenerator[bytes, None]:
        """
        Stream audio chunks asynchronously using sounddevice
        
        This is NON-BLOCKING and works with PipeWire (no ALSA conflicts!)
        
        Args:
            chunk_duration_ms: Size of each audio chunk in milliseconds
            timeout: Maximum time to listen (seconds)
            silence_duration: Stop after this many seconds of silence
            min_speech_duration: Minimum speech duration to consider valid
            
        Yields:
            Audio chunks (bytes) as they arrive from microphone
        """
        try:
            import sounddevice as sd
            import numpy as np
            
            self.logger.info("🎯 Starting async audio stream...")
            print("🎯 Listening... (Speak naturally)")
            
            # Calculate chunk size in samples
            chunk_samples = int(self.config.sample_rate * chunk_duration_ms / 1000)
            
            # Create input stream (non-blocking!)
            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype='int16',
                blocksize=chunk_samples
            )
            
            start_time = time.time()
            speech_frames = 0
            silence_frames = 0
            has_started_speaking = False
            
            # Calculate frame thresholds
            frames_per_second = 1000 / chunk_duration_ms
            silence_threshold = int(silence_duration * frames_per_second)
            min_speech_threshold = int(min_speech_duration * frames_per_second)
            
            # Dynamic noise calibration
            calibration_chunks = 10
            noise_energy_sum = 0
            
            with stream:
                print("Adjusting to background noise...", end="", flush=True)
                
                # Calibration phase
                for _ in range(calibration_chunks):
                    chunk, overflowed = stream.read(chunk_samples)
                    if overflowed:
                        self.logger.warning("⚠️ Audio buffer overflow during calibration")
                    
                    chunk_bytes = chunk.tobytes()
                    rms = audioop.rms(chunk_bytes, 2)
                    noise_energy_sum += rms
                
                avg_noise = noise_energy_sum / calibration_chunks
                dynamic_threshold = int(avg_noise * 1.2) + 300
                
                if dynamic_threshold > 30000:
                    self.logger.warning(f"⚠️ High noise detected ({int(avg_noise)}). Clamping threshold.")
                    dynamic_threshold = 30000
                
                print(f" Done. (Noise: {int(avg_noise)} → Threshold: {dynamic_threshold})")
                
                # Main streaming loop
                while True:
                    # Check timeout
                    if time.time() - start_time > timeout:
                        print("⏱️ Timeout")
                        break
                    
                    # Read audio chunk (non-blocking!)
                    chunk, overflowed = stream.read(chunk_samples)
                    if overflowed:
                        self.logger.warning("⚠️ Audio buffer overflow")
                    
                    chunk_bytes = chunk.tobytes()
                    
                    # Energy check
                    rms = audioop.rms(chunk_bytes, 2)
                    
                    # VAD check (only if energy above threshold)
                    is_speech = False
                    if rms > dynamic_threshold:
                        try:
                            # VAD requires specific chunk sizes (10, 20, or 30ms)
                            # Resample if needed
                            vad_chunk_size = int(self.config.sample_rate * self.config.chunk_duration_ms / 1000) * 2
                            if len(chunk_bytes) >= vad_chunk_size:
                                vad_chunk = chunk_bytes[:vad_chunk_size]
                                is_speech = self.vad.is_speech(vad_chunk, self.config.sample_rate)
                        except Exception as e:
                            self.logger.debug(f"VAD error: {e}")
                            is_speech = False
                    
                    if is_speech:
                        if not has_started_speaking:
                            print(f"🗣️ Speech detected (Energy: {rms})")
                            has_started_speaking = True
                        speech_frames += 1
                        silence_frames = 0
                        
                        # Yield audio chunk
                        yield chunk_bytes
                        
                    elif has_started_speaking:
                        silence_frames += 1
                        # Still yield during silence (for natural pauses)
                        yield chunk_bytes
                    
                    # Stop if we had speech and now silence
                    if has_started_speaking and silence_frames > silence_threshold:
                        if speech_frames >= min_speech_threshold:
                            print(f"✅ Capture complete ({speech_frames * chunk_duration_ms / 1000:.1f}s)")
                            break
                        else:
                            # False alarm / noise
                            self.logger.debug("False alarm, resetting")
                            has_started_speaking = False
                            speech_frames = 0
                            silence_frames = 0
                    
                    # Small async yield to prevent blocking
                    await asyncio.sleep(0)
                    
        except ImportError:
            self.logger.error("❌ sounddevice not installed. Run: pip install sounddevice")
            raise
        except Exception as e:
            self.logger.error(f"❌ Streaming error: {e}")
            raise


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
