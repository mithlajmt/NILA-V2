import asyncio
import hashlib
import base64
from pathlib import Path
from typing import Optional
import httpx

from .base_tts_provider import BaseTTSProvider

class SarvamTTSProvider(BaseTTSProvider):
    """
    Sarvam AI Text-to-Speech Provider
    Leverages the bulbul:v3 model for highly natural Indic-language speech.
    """
    
    def __init__(self, settings):
        super().__init__(settings)
        
        self.api_key = getattr(settings, 'SARVAM_API_KEY', '')
        if not self.api_key:
            self.logger.warning("⚠️ SARVAM_API_KEY not found in settings. Speech synthesis will fail.")
            
        self.speaker = getattr(settings, 'SARVAM_TTS_SPEAKER', 'ratan')
        self.pace = getattr(settings, 'SARVAM_TTS_PACE', 1.0)
        self.model = "bulbul:v3"
        self.url = "https://api.sarvam.ai/text-to-speech"
        
        # Audio cache directory
        self.cache_dir = Path("data/audio/sarvam")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache management
        self.max_cache_size_mb = 150
        self.cache_cleanup_threshold = 0.8
        
        self.logger.info(f"✅ Sarvam TTS Provider initialized (Speaker: {self.speaker}, Pace: {self.pace})")
    
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Generate and play speech using Sarvam TTS"""
        try:
            if not text or not text.strip():
                self.logger.warning("⚠️ Empty text provided")
                return False
                
            if not self.api_key:
                self.logger.error("❌ Sarvam API Key missing. Cannot speak.")
                return False
            
            # Detect language for appropriate Bulbul mapping
            if language is None:
                language_hint = self.detect_language(text)
            else:
                language_hint = language
                
            target_lang = "ml-IN" if language_hint == "ml" else "en-IN"
            self.logger.info(f"🔊 Speaking (Sarvam '{self.speaker}', lang: {target_lang}): {text[:50]}...")
            
            # Check cache and clean if needed
            await self._check_cache_size()
            
            # Generate the HTTP request
            audio_file = await self.generate_audio(text, target_lang)
            
            if audio_file:
                await self.play_audio(audio_file)
                return True
            else:
                self.logger.error("❌ Failed to generate audio with Sarvam")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Sarvam TTS error: {e}")
            return False
            
    async def generate_audio(self, text: str, language: Optional[str] = None) -> Optional[Path]:
        """Fetch and resolve the base64 audio payload from the Sarvam bulbul API"""
        try:
            target_lang = language if language else "ml-IN"
            
            # Ensure safe payload constraints 
            # Bulbul max length is ~2500 chars 
            clean_text = text[:2450].strip()
            
            # Unique cache file resolution
            cache_key = f"{clean_text}_{self.speaker}_{self.pace}_{target_lang}_{self.model}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"sarvam_{text_hash}.wav"
            
            if cache_file.exists():
                self.logger.debug("♻️ Using cached audio")
                return cache_file
                
            self.logger.debug(f"🎵 Requesting audio from Sarvam ({self.model})...")
            
            payload = {
                "inputs": [clean_text],
                "target_language_code": target_lang,
                "speaker": self.speaker,
                "pitch": 0,
                "pace": self.pace,
                "loudness": 1.5,
                "speech_sample_rate": 8000,
                "enable_preprocessing": True,
                "model": self.model
            }
            
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Async HTTP request with httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                
            if response.status_code == 200:
                data = response.json()
                
                # Extract the base64 audio based on documentation. 
                # (Sometimes returned as `audios` list, checking both formats)
                audio_base64 = None
                if "audios" in data and len(data["audios"]) > 0:
                     audio_base64 = data["audios"][0]
                elif "audio_base64" in data:
                     audio_base64 = data["audio_base64"]
                
                if not audio_base64:
                    self.logger.error(f"❌ Unrecognized response structure from Sarvam: {data.keys()}")
                    return None
                    
                audio_bytes = base64.b64decode(audio_base64)
                
                # Saving audio file locally
                with open(cache_file, "wb") as f:
                    f.write(audio_bytes)
                
                self.logger.debug("✅ Generated new audio from Sarvam")
                return cache_file
            else:
                self.logger.error(f"❌ Sarvam API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Sarvam HTTP audio generation error: {e}")
            return None

    async def play_audio(self, audio_file: Path):
        """Play the `.wav` audio output via standard players"""
        try:
            self.is_speaking = True
            
            import shutil
            import subprocess
            
            # Use pw-play or paplay, gracefully fall back to aplay
            player = None
            if shutil.which('pw-play'):
                player = 'pw-play'
            elif shutil.which('paplay'):
                player = 'paplay'
            else:
                player = 'aplay'
                
            cmd = [player, str(audio_file)]
            if player == 'aplay':
                cmd.insert(1, '-q')
                
            self.logger.debug(f"🔊 Playing with {player}...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            await process.wait()
            
            self.is_speaking = False
            self.logger.debug("✅ Audio playback completed")
                
        except Exception as e:
            self.is_speaking = False
            self.logger.error(f"❌ Audio playback error: {e}")

    async def _check_cache_size(self):
        """Monitor cache and remove old entries to prevent infinite bloat"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.wav"))
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > (self.max_cache_size_mb * self.cache_cleanup_threshold):
                self.logger.info(f"🧽 Cache cleanup ({total_size_mb:.1f}MB)...")
                await self._cleanup_old_cache_files()
        except Exception as e:
            self.logger.error(f"❌ Cache check error: {e}")

    async def _cleanup_old_cache_files(self):
        try:
            cache_files = list(self.cache_dir.glob("*.wav"))
            cache_files.sort(key=lambda f: f.stat().st_atime)
            files_to_remove = int(len(cache_files) * 0.3)
            
            for cache_file in cache_files[:files_to_remove]:
                try:
                    cache_file.unlink()
                except:
                    pass
            self.logger.info(f"✅ Cleaned up {files_to_remove} cached Sarvam audio files")
        except Exception as e:
            self.logger.error(f"❌ Cache cleanup error: {e}")

    def stop_speaking(self):
        """Halt playback tracking (does not forcefully SIGKILL the subprocess yet)"""
        if self.is_speaking:
            self.is_speaking = False
            self.logger.info("⏹️ Speech stop requested")

    def cleanup(self):
        self.logger.info("🧽 Cleaning up Sarvam TTS provider...")
        self.stop_speaking()

    def get_provider_name(self) -> str:
        return f"Sarvam ({self.speaker} - bulbul:v3)"
