"""
OpenAI Text-to-Speech Provider
High-quality TTS with multiple voices
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Optional
import pygame
from .base_tts_provider import BaseTTSProvider


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI Text-to-Speech - High quality with multiple voices"""
    
    def __init__(self, settings):
        super().__init__(settings)
        
        # Initialize OpenAI client
        try:
            from openai import AsyncOpenAI
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI TTS provider")
            self.client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise ImportError(
                "❌ Failed to import OpenAI library\n"
                "Make sure you have: pip install openai"
            )
        except Exception as e:
            raise ImportError(
                f"❌ Failed to initialize OpenAI TTS: {e}\n"
                "Make sure you have set OPENAI_API_KEY in .env"
            )
        
        # Initialize pygame mixer
        pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
        
        # Audio cache directory
        self.cache_dir = Path("data/audio/openai")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Voice settings
        self.model = getattr(settings, 'OPENAI_TTS_MODEL', 'tts-1')  # tts-1 or tts-1-hd
        self.voice = getattr(settings, 'OPENAI_TTS_VOICE', 'nova')  # alloy, echo, fable, onyx, nova, shimmer
        self.speed = getattr(settings, 'OPENAI_TTS_SPEED', 1.0)  # 0.25 to 4.0
        self.format = getattr(settings, 'OPENAI_TTS_FORMAT', 'mp3')  # mp3, opus, aac, flac
        
        # Cache management
        self.max_cache_size_mb = 100
        self.cache_cleanup_threshold = 0.8
        
        self.logger.info("✅ OpenAI TTS initialized")
        self.logger.info(f"   Model: {self.model}")
        self.logger.info(f"   Voice: {self.voice}")
        self.logger.info(f"   Speed: {self.speed}")
    
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Generate and play speech using OpenAI TTS"""
        try:
            if not text or not text.strip():
                self.logger.warning("⚠️ Empty text provided")
                return False
            
            self.logger.info(f"🔊 Speaking ({self.voice}): {text[:50]}...")
            
            # Check cache size
            await self._check_cache_size()
            
            # Generate audio
            audio_file = await self._generate_audio(text)
            
            if audio_file:
                # Play audio
                await self._play_audio(audio_file)
                return True
            else:
                self.logger.error("❌ Failed to generate audio")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ OpenAI TTS error: {e}")
            return False
    
    async def _generate_audio(self, text: str) -> Optional[Path]:
        """Generate audio using OpenAI TTS"""
        try:
            # Create cache filename
            cache_key = f"{text}_{self.model}_{self.voice}_{self.speed}_{self.format}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"openai_{text_hash}.{self.format}"
            
            # Return cached file if exists
            if cache_file.exists():
                self.logger.debug(f"♻️ Using cached audio")
                return cache_file
            
            # Generate new audio
            self.logger.debug(f"🎵 Generating audio with OpenAI TTS (voice: {self.voice}, speed: {self.speed})...")
            
            # Call OpenAI TTS API
            response = await self.client.audio.speech.create(
                model=self.model,  # tts-1 or tts-1-hd
                voice=self.voice,  # alloy, echo, fable, onyx, nova, shimmer
                input=text,
                speed=self.speed,  # 0.25 to 4.0
                response_format=self.format  # mp3, opus, aac, flac
            )
            
            # Save the audio to file
            # Response is a file-like object, read all content
            audio_data = response.content
            with open(cache_file, "wb") as out:
                out.write(audio_data)
            
            self.logger.debug(f"✅ Generated audio using {self.voice} voice")
            return cache_file
            
        except Exception as e:
            self.logger.error(f"❌ Audio generation error: {e}")
            return None
    
    async def _play_audio(self, audio_file: Path):
        """Play audio file"""
        try:
            self.is_speaking = True
            
            # Load and play
            pygame.mixer.music.load(str(audio_file))
            pygame.mixer.music.play()
            
            # Wait for playback
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
            
            self.is_speaking = False
            self.logger.debug("✅ Audio playback completed")
                
        except Exception as e:
            self.is_speaking = False
            self.logger.error(f"❌ Audio playback error: {e}")
    
    async def _check_cache_size(self):
        """Check cache size and cleanup if needed"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob(f"*.{self.format}"))
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > (self.max_cache_size_mb * self.cache_cleanup_threshold):
                self.logger.info(f"🧽 Cache cleanup ({total_size_mb:.1f}MB)...")
                await self._cleanup_old_cache_files()
        except Exception as e:
            self.logger.error(f"❌ Cache check error: {e}")
    
    async def _cleanup_old_cache_files(self):
        """Remove oldest cache files"""
        try:
            cache_files = list(self.cache_dir.glob(f"*.{self.format}"))
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
            pygame.mixer.music.stop()
            self.is_speaking = False
            self.logger.info("⏹️ Speech stopped")
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧽 Cleaning up OpenAI TTS provider...")
        self.stop_speaking()
        try:
            pygame.mixer.quit()
        except:
            pass
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return f"OpenAI TTS ({self.voice} voice)"

