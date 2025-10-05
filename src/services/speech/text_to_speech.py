import asyncio
import logging
import tempfile
import os
import hashlib
from pathlib import Path
from typing import Optional
from gtts import gTTS
import pygame
import time

class TextToSpeech:
    """Enhanced Text-to-Speech service with caching and optimization"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize pygame mixer with better settings
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # Audio cache directory
        self.cache_dir = Path("data/audio")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache management
        self.max_cache_size_mb = 50  # Max cache size in MB
        self.cache_cleanup_threshold = 0.8  # Clean when 80% full
        
        # Track playback state
        self.is_speaking = False
        
        self.logger.info("🔊 Enhanced Text-to-Speech service initialized")
    
    async def speak(self, text: str, language: str = "en") -> bool:
        """Convert text to speech and play audio"""
        try:
            if not text or not text.strip():
                self.logger.warning("⚠️ Empty text provided to TTS")
                return False
            
            self.logger.info(f"🔊 Speaking: {text[:50]}..." if len(text) > 50 else f"🔊 Speaking: {text}")
            
            # Check cache size and cleanup if needed
            await self._check_cache_size()
            
            # Generate audio file
            audio_file = await self._generate_audio(text, language)
            
            if audio_file:
                # Play audio
                await self._play_audio(audio_file)
                return True
            else:
                self.logger.error("❌ Failed to generate audio")
            
        except Exception as e:
            self.logger.error(f"❌ TTS error: {e}")
        
        return False
    
    def stop_speaking(self):
        """Stop current speech"""
        if self.is_speaking:
            pygame.mixer.music.stop()
            self.is_speaking = False
            self.logger.info("⏹️ Speech stopped")
    
    async def _generate_audio(self, text: str, language: str) -> Optional[Path]:
        """Generate audio file from text with caching"""
        try:
            # Create stable cache filename using MD5 hash
            text_hash = hashlib.md5(f"{text}_{language}".encode()).hexdigest()
            cache_file = self.cache_dir / f"tts_{text_hash}.mp3"
            
            # Return cached file if exists
            if cache_file.exists():
                self.logger.debug(f"♻️ Using cached audio: {cache_file.name}")
                return cache_file
            
            # Generate new audio using Google TTS
            self.logger.debug("🎵 Generating new audio...")
            
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, tts.save, str(cache_file))
            
            self.logger.debug(f"✅ Generated new audio: {cache_file.name}")
            return cache_file
            
        except Exception as e:
            self.logger.error(f"❌ Audio generation error: {e}")
        
        return None
    
    async def _play_audio(self, audio_file: Path):
        """Play audio file with state tracking"""
        try:
            self.is_speaking = True
            
            # Load and play audio
            pygame.mixer.music.load(str(audio_file))
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)  # Check more frequently
            
            self.is_speaking = False
            self.logger.debug("✅ Audio playback completed")
                
        except Exception as e:
            self.is_speaking = False
            self.logger.error(f"❌ Audio playback error: {e}")
    
    async def _check_cache_size(self):
        """Check cache size and cleanup if needed"""
        try:
            # Calculate total cache size
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.mp3"))
            total_size_mb = total_size / (1024 * 1024)
            
            # Cleanup if threshold exceeded
            if total_size_mb > (self.max_cache_size_mb * self.cache_cleanup_threshold):
                self.logger.info(f"🧽 Cache size ({total_size_mb:.1f}MB) exceeds threshold, cleaning up...")
                await self._cleanup_old_cache_files()
        except Exception as e:
            self.logger.error(f"❌ Cache size check error: {e}")
    
    async def _cleanup_old_cache_files(self):
        """Remove oldest cache files to free up space"""
        try:
            # Get all cache files sorted by access time
            cache_files = list(self.cache_dir.glob("*.mp3"))
            cache_files.sort(key=lambda f: f.stat().st_atime)
            
            # Remove oldest 30% of files
            files_to_remove = int(len(cache_files) * 0.3)
            
            for cache_file in cache_files[:files_to_remove]:
                try:
                    cache_file.unlink()
                except Exception as e:
                    self.logger.debug(f"Could not delete {cache_file.name}: {e}")
            
            self.logger.info(f"✅ Cleaned up {files_to_remove} cache files")
        except Exception as e:
            self.logger.error(f"❌ Cache cleanup error: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.logger.info("🧽 Cleaning up TTS service...")
            self.stop_speaking()
            pygame.mixer.quit()
        except Exception as e:
            self.logger.debug(f"Cleanup error: {e}")
