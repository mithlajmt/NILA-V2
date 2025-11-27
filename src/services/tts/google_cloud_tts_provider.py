"""
Google Cloud Text-to-Speech Provider
Professional TTS with excellent Malayalam + English support
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Optional
import pygame
from .base_tts_provider import BaseTTSProvider


class GoogleCloudTTSProvider(BaseTTSProvider):
    """Google Cloud Text-to-Speech - Professional multilingual TTS"""
    
    def __init__(self, settings):
        super().__init__(settings)
        
        # Initialize Google Cloud TTS client
        try:
            from google.cloud import texttospeech
            self.tts_client = texttospeech.TextToSpeechClient()
            self.texttospeech = texttospeech
            
        except Exception as e:
            raise ImportError(
                f"❌ Failed to initialize Google Cloud TTS: {e}\n"
                "Make sure you have:\n"
                "1. Installed: pip install google-cloud-texttospeech\n"
                "2. Set GOOGLE_APPLICATION_CREDENTIALS in .env\n"
                "3. Created a service account with TTS API enabled"
            )
        
        # Initialize pygame mixer
        pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
        
        # Audio cache directory
        self.cache_dir = Path("data/audio/google_cloud")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Voice settings
        self.malayalam_voice = settings.TTS_VOICE_MALAYALAM
        self.english_voice = settings.TTS_VOICE_ENGLISH
        self.speaking_rate = settings.TTS_SPEAKING_RATE
        self.pitch = settings.TTS_PITCH
        self.volume_gain_db = settings.TTS_VOLUME_GAIN_DB
        
        # Cache management
        self.max_cache_size_mb = 100
        self.cache_cleanup_threshold = 0.8
        
        self.logger.info("✅ Google Cloud TTS initialized")
        self.logger.info(f"   Malayalam voice: {self.malayalam_voice}")
        self.logger.info(f"   English voice: {self.english_voice}")
    
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Generate and play speech using Google Cloud TTS"""
        try:
            if not text or not text.strip():
                self.logger.warning("⚠️ Empty text provided")
                return False
            
            # Auto-detect language if not specified
            if language is None or language == 'auto':
                language = self.detect_language(text)
            
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
            self.logger.error(f"❌ Google Cloud TTS error: {e}")
            return False
    
    async def _generate_audio(self, text: str, language: str) -> Optional[Path]:
        """Generate audio using Google Cloud TTS"""
        try:
            # Create cache filename
            cache_key = f"{text}_{language}_{self.speaking_rate}_{self.pitch}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"gcloud_{text_hash}.mp3"
            
            # Return cached file if exists
            if cache_file.exists():
                self.logger.debug(f"♻️ Using cached audio")
                return cache_file
            
            # Generate new audio
            self.logger.debug("🎵 Generating audio with Google Cloud TTS...")
            
            # Select voice based on language
            if language == 'ml':
                voice_name = self.malayalam_voice
                language_code = 'ml-IN'
            else:
                voice_name = self.english_voice
                language_code = 'en-IN'
            
            # Build the voice request
            voice = self.texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            # Build the text input
            synthesis_input = self.texttospeech.SynthesisInput(text=text)
            
            # Build the audio config
            audio_config = self.texttospeech.AudioConfig(
                audio_encoding=self.texttospeech.AudioEncoding.MP3,
                speaking_rate=self.speaking_rate,
                pitch=self.pitch,
                volume_gain_db=self.volume_gain_db
            )
            
            # Perform the text-to-speech request (run in thread pool)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.tts_client.synthesize_speech,
                synthesis_input,
                voice,
                audio_config
            )
            
            # Save the audio to file
            with open(cache_file, "wb") as out:
                out.write(response.audio_content)
            
            self.logger.debug(f"✅ Generated audio using {voice_name}")
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
        self.logger.info("🧽 Cleaning up Google Cloud TTS provider...")
        self.stop_speaking()
        try:
            pygame.mixer.quit()
        except:
            pass
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "Google Cloud TTS (Multilingual)"
