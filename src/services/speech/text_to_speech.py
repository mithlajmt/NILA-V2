import asyncio
import logging
import tempfile
import os
from pathlib import Path
from typing import Optional
from gtts import gTTS
import pygame

class TextToSpeech:
    """Text-to-speech service - Step 1 implementation"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        # Audio cache directory
        self.cache_dir = Path("data/audio")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("🔊 Text-to-Speech service initialized")
    
    async def speak(self, text: str, language: str = "en") -> bool:
        """Convert text to speech and play audio"""
        try:
            self.logger.info(f"🔊 Speaking: {text}")
            
            # Generate audio file
            audio_file = await self._generate_audio(text, language)
            
            if audio_file:
                # Play audio
                await self._play_audio(audio_file)
                return True
            
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
        
        return False
    
    async def _generate_audio(self, text: str, language: str) -> Optional[Path]:
        """Generate audio file from text"""
        try:
            # Create cache filename
            cache_key = hash(f"{text}_{language}")
            cache_file = self.cache_dir / f"{cache_key}.mp3"
            
            # Return cached file if exists
            if cache_file.exists():
                self.logger.debug(f"Using cached audio: {cache_file}")
                return cache_file
            
            # Generate new audio using Google TTS
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, tts.save, str(cache_file))
            
            self.logger.debug(f"Generated new audio: {cache_file}")
            return cache_file
            
        except Exception as e:
            self.logger.error(f"Audio generation error: {e}")
        
        return None
    
    async def _play_audio(self, audio_file: Path):
        """Play audio file"""
        try:
            # Load and play audio
            pygame.mixer.music.load(str(audio_file))
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
            self.logger.debug("Audio playback completed")
                
        except Exception as e:
            self.logger.error(f"Audio playback error: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            pygame.mixer.quit()
        except:
            pass
