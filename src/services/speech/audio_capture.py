"""
PipeWire-compatible audio capture for Raspberry Pi
Replaces PyAudio/speech_recognition with sounddevice for stability
"""
import logging
import numpy as np
import sounddevice as sd
import webrtcvad
import time
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class AudioConfig:
    """Audio capture configuration optimized for Raspberry Pi + Google STT"""
    sample_rate: int = 16000  # Hz (required by Google STT)
    channels: int = 1  # Mono
    dtype: str = 'int16'  # 16-bit PCM
    chunk_duration_ms: int = 30  # VAD frame size (10, 20, or 30ms)
    vad_aggressiveness: int = 2  # 0-3, higher = more aggressive


class AudioCapture:
    """
    PipeWire-native audio capture with Voice Activity Detection
    
    Designed for Raspberry Pi with:
    - USB microphone input
    - Bluetooth audio output
    - PipeWire/PulseAudio audio server
    """
    
    def __init__(self, config: Optional[AudioConfig] = None, device_name: str = ""):
        self.config = config or AudioConfig()
        self.logger = logging.getLogger(__name__)
        
        # Voice Activity Detection
        self.vad = webrtcvad.Vad(self.config.vad_aggressiveness)
        
        # Audio device
        self.device_index = self._find_best_device(device_name)
        
        # Calculate chunk size for VAD frames
        self.chunk_size = int(self.config.sample_rate * self.config.chunk_duration_ms / 1000)
        
        self.logger.info(f"🎙️ AudioCapture initialized (device={self.device_index}, rate={self.config.sample_rate}Hz)")
    
    def _find_best_device(self, preferred_name: str = "") -> Optional[int]:
        """
        Find the best input device, prioritizing USB microphones
        
        Args:
            preferred_name: Specific device name to search for (optional)
            
        Returns:
            Device index or None for system default
        """
        try:
            devices = sd.query_devices()
            self.logger.info(f"🎧 Available Audio Devices ({len(devices)} found):")
            
            input_devices = []
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    self.logger.info(f"   [{i}] {device['name']} (in={device['max_input_channels']})")
                    input_devices.append((i, device))
            
            # If specific device requested, try to find it
            if preferred_name:
                for idx, device in input_devices:
                    if preferred_name.lower() in device['name'].lower():
                        self.logger.info(f"✅ Found preferred device: '{device['name']}' at index {idx}")
                        return idx
            
            # Priority 1: USB PnP Sound Device (common on Raspberry Pi)
            for idx, device in input_devices:
                name_lower = device['name'].lower()
                if "usb pnp sound device" in name_lower or \
                   ("usb" in name_lower and "audio" in name_lower and "sysdefault" not in name_lower):
                    self.logger.info(f"✅ Found USB Microphone: '{device['name']}' at index {idx}")
                    return idx
            
            # Priority 2: Any USB device
            for idx, device in input_devices:
                if "usb" in device['name'].lower() and "sysdefault" not in device['name'].lower():
                    self.logger.info(f"✅ Found USB device: '{device['name']}' at index {idx}")
                    return idx
            
            # Priority 3: Default device
            self.logger.warning("⚠️ No USB mic found, using system default")
            return None  # None = use system default
            
        except Exception as e:
            self.logger.error(f"❌ Error finding audio device: {e}")
            return None
    
    def record(self, 
               timeout: int = 30,
               silence_duration: float = 1.5,
               min_speech_duration: float = 0.5) -> Optional[bytes]:
        """
        Record audio with Voice Activity Detection
        
        Args:
            timeout: Maximum recording time in seconds
            silence_duration: Seconds of silence to stop recording
            min_speech_duration: Minimum speech duration to consider valid
            
        Returns:
            Raw audio bytes (16-bit PCM) or None if no speech detected
        """
        try:
            self.logger.info("🎯 Listening... (Speak naturally)")
            print("🎯 Listening... (Speak naturally)")
            
            start_time = time.time()
            audio_frames = []
            speech_frames = 0
            silence_frames = 0
            silence_threshold = int(silence_duration * 1000 / self.config.chunk_duration_ms)
            min_speech_frames = int(min_speech_duration * 1000 / self.config.chunk_duration_ms)
            
            # Start recording stream
            with sd.InputStream(
                device=self.device_index,
                channels=self.config.channels,
                samplerate=self.config.sample_rate,
                dtype=self.config.dtype,
                blocksize=self.chunk_size
            ) as stream:
                
                while True:
                    # Check timeout
                    if time.time() - start_time > timeout:
                        self.logger.warning("⏱️ Recording timeout")
                        print("⏱️ No speech within timeout")
                        return None
                    
                    # Read audio chunk
                    audio_chunk, overflowed = stream.read(self.chunk_size)
                    
                    if overflowed:
                        self.logger.warning("⚠️ Audio buffer overflow (dropped frames)")
                    
                    # Convert to bytes for VAD
                    audio_bytes = audio_chunk.tobytes()
                    audio_frames.append(audio_bytes)
                    
                    # Voice Activity Detection
                    try:
                        is_speech = self.vad.is_speech(audio_bytes, self.config.sample_rate)
                    except Exception as e:
                        # VAD can fail on very quiet audio, treat as silence
                        is_speech = False
                    
                    if is_speech:
                        speech_frames += 1
                        silence_frames = 0
                    else:
                        silence_frames += 1
                    
                    # Stop if we have enough speech and then silence
                    if speech_frames >= min_speech_frames and silence_frames >= silence_threshold:
                        duration = time.time() - start_time
                        self.logger.info(f"✅ Got it! ({duration:.1f}s) Processing...")
                        print(f"✅ Got it! ({duration:.1f}s) Processing...")
                        break
            
            # Check if we got any speech
            if speech_frames < min_speech_frames:
                self.logger.warning("⚠️ No speech detected (too short or too quiet)")
                print("⚠️ No speech detected")
                return None
            
            # Combine all audio frames
            audio_data = b''.join(audio_frames)
            return audio_data
            
        except Exception as e:
            self.logger.error(f"❌ Recording error: {e}")
            print(f"❌ Recording error: {e}")
            return None
    
    def test_record(self, duration: float = 3.0) -> Optional[np.ndarray]:
        """
        Simple test recording without VAD (for debugging)
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            NumPy array of audio samples or None on error
        """
        try:
            self.logger.info(f"🎙️ Test recording for {duration}s...")
            print(f"🎙️ Recording for {duration}s...")
            
            audio = sd.rec(
                int(duration * self.config.sample_rate),
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                device=self.device_index
            )
            sd.wait()
            
            self.logger.info("✅ Test recording complete")
            print("✅ Recording complete")
            return audio.flatten()
            
        except Exception as e:
            self.logger.error(f"❌ Test recording error: {e}")
            print(f"❌ Error: {e}")
            return None
    
    def get_device_info(self) -> dict:
        """Get information about the current audio device"""
        try:
            if self.device_index is None:
                return sd.query_devices(kind='input')
            else:
                return sd.query_devices(self.device_index)
        except Exception as e:
            self.logger.error(f"❌ Error getting device info: {e}")
            return {}
    
    @staticmethod
    def list_devices():
        """List all available audio devices"""
        print("\n🎧 Available Audio Devices:")
        print("=" * 60)
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"[{i}] {device['name']}")
                print(f"    Inputs: {device['max_input_channels']}, "
                      f"Sample Rate: {device['default_samplerate']}Hz")
        print("=" * 60)
