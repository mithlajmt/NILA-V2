"""
gTTS Provider - Simple fallback TTS
Free but limited (English only, robotic voice)
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Optional
from gtts import gTTS
import pygame
from .base_tts_provider import BaseTTSProvider


class GTTSProvider(BaseTTSProvider):
    """Google Text-to-Speech (gTTS) - Simple free TTS"""
    
    def __init__(self, settings):
        super().__init__(settings)
        
        # Initialize pygame mixer
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # Audio cache directory
        self.cache_dir = Path("data/audio/gtts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # gTTS voice settings
        self.tld = getattr(settings, 'GTTS_TLD', 'co.in')  # Top-level domain (affects accent)
        self.slow = getattr(settings, 'GTTS_SLOW', False)  # Slow speech
        self.default_lang = getattr(settings, 'GTTS_LANG', 'en')  # Default language
        
        # Cache management
        self.max_cache_size_mb = 50
        self.cache_cleanup_threshold = 0.8
        
        self.logger.info(f"✅ gTTS Provider initialized (TLD: {self.tld}, Slow: {self.slow})")
    
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Generate and play speech using gTTS"""
        try:
            if not text or not text.strip():
                self.logger.warning("⚠️ Empty text provided")
                return False
            
            # Auto-detect language if not specified
            if language is None:
                language = self.detect_language(text)
            
            # Warn if Malayalam detected
            if language == 'ml':
                self.logger.warning("⚠️ Malayalam detected but gTTS doesn't support it!")
                self.logger.info("   Consider using Google Cloud TTS instead")
                # Try English anyway
                language = 'en'
            
            self.logger.info(f"🔊 Speaking ({language}): {text[:50]}...")
            
            # Check cache size
            await self._check_cache_size()
            
            # Generate audio
            audio_file = await self._generate_audio(text, language)
            
            if audio_file:
                # Play audio
                await self._play_audio(audio_file)
                return True
            else:
                self.logger.error("❌ Failed to generate audio")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ gTTS error: {e}")
            return False
    
    async def _generate_audio(self, text: str, language: str) -> Optional[Path]:
        """Generate audio file from text"""
        try:
            # Use default language if not specified or invalid
            if not language or language == 'ml':
                language = self.default_lang
            
            # Create cache filename (include tld and slow in hash for cache differentiation)
            cache_key = f"{text}_{language}_{self.tld}_{self.slow}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"gtts_{text_hash}.mp3"
            
            # Return cached file if exists
            if cache_file.exists():
                self.logger.debug(f"♻️ Using cached audio")
                return cache_file
            
            # Generate new audio with voice settings
            self.logger.debug(f"🎵 Generating new audio (lang: {language}, tld: {self.tld}, slow: {self.slow})...")
            
            # gTTS parameters:
            # - lang: language code (e.g., 'en', 'en-us', 'en-uk', 'en-au', 'en-in')
            # - tld: top-level domain (affects accent: 'com'=US, 'co.uk'=UK, 'com.au'=Australia, 'co.in'=India)
            # - slow: slow speech (True/False)
            tts = gTTS(text=text, lang=language, tld=self.tld, slow=self.slow)
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, tts.save, str(cache_file))
            
            self.logger.debug(f"✅ Generated new audio")
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
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.mp3"))
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > (self.max_cache_size_mb * self.cache_cleanup_threshold):
                self.logger.info(f"🧽 Cache cleanup ({total_size_mb:.1f}MB)...")
                await self._cleanup_old_cache_files()
        except Exception as e:
            self.logger.error(f"❌ Cache check error: {e}")
    
    async def _cleanup_old_cache_files(self):
        """Remove oldest cache files"""
        try:
            cache_files = list(self.cache_dir.glob("*.mp3"))
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
        self.logger.info("🧽 Cleaning up gTTS provider...")
        self.stop_speaking()
        try:
            pygame.mixer.quit()
        except:
            pass
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "gTTS (Basic)"
