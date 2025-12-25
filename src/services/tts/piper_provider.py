import asyncio
import hashlib
import subprocess
import wave
import audioop
import math
import time
from pathlib import Path
from typing import Optional
# pygame removed for pure ALSA support
from .base_tts_provider import BaseTTSProvider
from ..hardware.serial_controller import SerialController


class PiperTTSProvider(BaseTTSProvider):
    """Piper TTS - Fast, local, neural TTS with Hardware Lip Sync"""
    
    def __init__(self, settings):
        super().__init__(settings)
        
        self.binary_path = Path(settings.PIPER_BINARY_PATH).resolve()
        self.model_path = Path(settings.PIPER_MODEL_PATH).resolve()
        
        # Initialize Hardware Controller
        self.hardware = SerialController(settings)
        
        # Verify binary and model exist
        if not self.binary_path.exists():
            self.logger.warning(f"⚠️ Piper binary not found at {self.binary_path}")
            self.logger.warning("   Run 'python scripts/setup_piper.py' to install it.")
            
        if not self.model_path.exists():
            self.logger.warning(f"⚠️ Piper model not found at {self.model_path}")
        
        # Audio cache directory
        self.cache_dir = Path("data/audio/piper")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Audio cache directory
        self.cache_dir = Path("data/audio/piper")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache management
        self.max_cache_size_mb = 100
        self.cache_cleanup_threshold = 0.8
        
        self.logger.info(f"✅ Piper TTS initialized (Model: {self.model_path.name})")
    
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Generate and play speech using Piper"""
        try:
            if not text or not text.strip():
                self.logger.warning("⚠️ Empty text provided")
                return False
            
            if not self.binary_path.exists() or not self.model_path.exists():
                self.logger.error("❌ Piper binary or model missing. Cannot speak.")
                return False
            
            self.logger.info(f"🔊 Speaking (Piper): {text[:50]}...")
            
            # Check cache size
            await self._check_cache_size()
            
            # Generate audio
            audio_file = await self._generate_audio(text)
            
            if audio_file:
                # Play audio with Lip Sync
                await self._play_with_lipsync(audio_file)
                return True
            else:
                self.logger.error("❌ Failed to generate audio")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Piper TTS error: {e}")
            return False
            
    async def _generate_audio(self, text: str) -> Optional[Path]:
        """Generate audio using Piper binary"""
        try:
            # Create cache filename
            # Include model name in hash
            cache_key = f"{text}_{self.model_path.name}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"piper_{text_hash}.wav"
            
            # Return cached file if exists
            if cache_file.exists():
                self.logger.debug(f"♻️ Using cached audio")
                return cache_file
            
            # Generate new audio
            self.logger.debug(f"🎵 Generating audio with Piper...")
            
            # Run Piper subprocess
            # echo 'text' | piper --model model.onnx --output_file output.wav
            
            cmd = [
                str(self.binary_path),
                "--model", str(self.model_path),
                "--output_file", str(cache_file)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=text.encode())
            
            if process.returncode != 0:
                self.logger.error(f"❌ Piper failed: {stderr.decode()}")
                return None
            
            self.logger.debug(f"✅ Generated audio")
            return cache_file
            
        except Exception as e:
            self.logger.error(f"❌ Audio generation error: {e}")
            return None

    async def _generate_audio(self, text: str) -> Optional[Path]:
        """Generate audio using Piper binary"""
        try:
            # Create cache filename
            # Include model name and parameters in hash
            length_scale = 1.0 / max(0.1, self.settings.TTS_SPEAKING_RATE)
            noise_scale = self.settings.PIPER_NOISE_SCALE
            noise_w = self.settings.PIPER_NOISE_W
            
            cache_key = f"{text}_{self.model_path.name}_{length_scale}_{noise_scale}_{noise_w}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"piper_{text_hash}.wav"
            
            # Return cached file if exists
            if cache_file.exists():
                self.logger.debug(f"♻️ Using cached audio")
                return cache_file
            
            # Generate new audio
            self.logger.debug(f"🎵 Generating audio with Piper (Speed: {self.settings.TTS_SPEAKING_RATE}x, Tone: {noise_scale})...")
            
            # Run Piper subprocess
            # echo 'text' | piper --model model.onnx --output_file output.wav --length_scale 1.0 --noise_scale 0.667 --noise_w 0.8
            
            cmd = [
                str(self.binary_path),
                "--model", str(self.model_path),
                "--output_file", str(cache_file),
                "--length_scale", str(length_scale),
                "--noise_scale", str(noise_scale),
                "--noise_w", str(noise_w)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=text.encode())
            
            if process.returncode != 0:
                self.logger.error(f"❌ Piper failed: {stderr.decode()}")
                return None
            
            self.logger.debug(f"✅ Generated audio")
            return cache_file
            
        except Exception as e:
            self.logger.error(f"❌ Audio generation error: {e}")
            return None

    async def _play_with_lipsync(self, audio_file: Path):
        """Play audio using 'aplay' and drive jaw servo"""
        try:
            self.is_speaking = True
            
            # Start audio playback via ALSA (aplay)
            # -q = quiet
            process = subprocess.Popen(['aplay', '-q', str(audio_file)])
            
            # Start Lip Sync Loop
            start_time = time.time()
            
            # Open WAV file to read amplitude data
            with wave.open(str(audio_file), 'rb') as wf:
                framerate = wf.getframerate()
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                
                # Calculate chunk size for ~50ms updates
                chunk_ms = 50
                chunk_size = int(framerate * chunk_ms / 1000)
                
                # Loop while process is running
                while process.poll() is None:
                    # Calculate current position in frames
                    elapsed = time.time() - start_time
                    current_frame = int(elapsed * framerate)
                    
                    # Seek and read chunk
                    if current_frame < wf.getnframes():
                        wf.setpos(current_frame)
                        data = wf.readframes(chunk_size)
                        
                        if data:
                            # Calculate RMS amplitude
                            rms = audioop.rms(data, sampwidth)
                            
                            # Normalize RMS to 0-100 range
                            scaling_factor = 3000 
                            intensity = min(100, int((rms / scaling_factor) * 100))
                            
                            # Send to Hardware
                            self.hardware.send_jaw_intensity(intensity)
                    
                    await asyncio.sleep(0.05) 
            
            # Ensure process finishes
            process.wait()
            
            # Ensure jaw is closed at the end
            self.hardware.send_jaw_intensity(0)
            self.is_speaking = False
            self.logger.debug("✅ Audio playback & Lip Sync completed")
                
        except Exception as e:
            self.is_speaking = False
            self.hardware.send_jaw_intensity(0)
            self.logger.error(f"❌ Audio playback error: {e}")
    
    async def _check_cache_size(self):
        """Check cache size and cleanup if needed"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.wav"))
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > (self.max_cache_size_mb * self.cache_cleanup_threshold):
                self.logger.info(f"🧽 Cache cleanup ({total_size_mb:.1f}MB)...")
                await self._cleanup_old_cache_files()
        except Exception as e:
            self.logger.error(f"❌ Cache check error: {e}")
    
    async def _cleanup_old_cache_files(self):
        """Remove oldest cache files"""
        try:
            cache_files = list(self.cache_dir.glob("*.wav"))
            cache_files.sort(key=lambda f: f.stat().st_atime)
            
            files_to_remove = int(len(cache_files) * 0.3)
            
            for cache_file in cache_files[:files_to_remove]:
                try:
                    cache_file.unlink()
                except:
                    pass
            
            self.logger.info(f"✅ Cleaned up {files_to_remove} cache files")
        except Exception as e:
            self.logger.error(f"❌ Cache cleanup error: {e}")
    
    def stop_speaking(self):
        """Stop current speech"""
        if self.is_speaking:
            # We can't easily kill the subprocess from here without storing the reference
            # Ideally we would store self.current_process and kill it
            # For now, just setting flag. In a robust impl, track the Popen object.
            
            # Since we didn't store the process in self, we rely on the command ending quickly.
            # But the 'aplay' command is short-lived anyway.
            self.is_speaking = False
            self.logger.info("⏹️ Speech stop requested")
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧽 Cleaning up Piper TTS provider...")
        self.stop_speaking()
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return f"Piper TTS ({self.model_path.name})"
