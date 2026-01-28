"""
Microsoft Edge TTS Provider
Free, high-quality neural TTS with Malayalam support
"""

import asyncio
import hashlib
import subprocess
import shutil
from pathlib import Path
from typing import Optional

try:
    import edge_tts
except ImportError:
    edge_tts = None

from .base_tts_provider import BaseTTSProvider


class EdgeTTSProvider(BaseTTSProvider):
    """Microsoft Edge TTS - Free neural voices with Malayalam support"""
    
    # Voice mappings for different languages
    VOICES = {
        'en': {
            'female': 'en-US-AriaNeural',
            'male': 'en-US-GuyNeural'
        },
        'ml': {
            'female': 'ml-IN-SobhanaNeural',
            'male': 'ml-IN-MidhunNeural'
        }
    }
    
    def __init__(self, settings):
        super().__init__(settings)
        
        # Check dependencies
        if edge_tts is None:
            self.logger.error("❌ edge-tts library not found")
            raise ImportError("Please install edge-tts: pip install edge-tts")
        
        # Voice settings
        self.voice_gender = getattr(settings, 'EDGE_TTS_VOICE_GENDER', 'female').lower()
        if self.voice_gender not in ['female', 'male']:
            self.logger.warning(f"⚠️ Invalid voice gender '{self.voice_gender}', defaulting to 'female'")
            self.voice_gender = 'female'
        
        # Audio cache
        self.cache_dir = Path("data/audio/edge_tts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache management
        self.max_cache_size_mb = 100
        self.cache_cleanup_threshold = 0.8
        
        self.logger.info(f"✅ Edge TTS initialized")
        self.logger.info(f"   Voice Gender: {self.voice_gender}")
        self.logger.info(f"   Malayalam: {self.VOICES['ml'][self.voice_gender]}")
        self.logger.info(f"   English: {self.VOICES['en'][self.voice_gender]}")
    
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Generate and play speech using Edge TTS"""
        try:
            audio_path = await self.generate_audio(text, language)
            if audio_path:
                await self.play_audio(audio_path)
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Speak error: {e}")
            return False
    
    async def generate_audio(self, text: str, language: Optional[str] = None) -> Optional[Path]:
        """Generate audio from text using Edge TTS API"""
        try:
            if not text or not text.strip():
                return None
            
            # Detect language if not provided
            if language is None:
                language = self.detect_language(text)
            
            # Normalize language code
            if language.startswith('ml'):
                language = 'ml'
            elif language.startswith('en'):
                language = 'en'
            else:
                self.logger.warning(f"⚠️ Unsupported language '{language}', defaulting to English")
                language = 'en'
            
            # Select voice
            voice = self.VOICES.get(language, self.VOICES['en'])[self.voice_gender]
            
            # Create cache key
            cache_key = f"{text}_{voice}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"edge_{text_hash}.mp3"
            
            # Check cache
            if cache_file.exists():
                self.logger.debug("♻️ Using cached audio")
                return cache_file
            
            self.logger.debug(f"🎵 Generating Edge TTS audio ({voice})...")
            
            # Generate audio using edge-tts
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(cache_file))
            
            self.logger.debug("✅ Audio generated")
            await self._check_cache_size()
            
            return cache_file
            
        except Exception as e:
            self.logger.error(f"❌ Generation error: {e}")
            return None
    
    async def play_audio(self, audio_file: Path):
        """Play audio using system player (pw-play/paplay/mpg123)"""
        try:
            self.is_speaking = True
            
            # Determine best audio player
            player = None
            if shutil.which('pw-play'):
                player = 'pw-play'
            elif shutil.which('paplay'):
                player = 'paplay'
            elif shutil.which('mpg123'):
                player = 'mpg123'
            else:
                self.logger.warning("⚠️ No mp3 player found (pw-play/paplay/mpg123)")
                return
            
            cmd = [player, str(audio_file)]
            if player == 'mpg123':
                cmd.insert(1, '-q')  # Quiet mode
            
            self.logger.debug(f"🔊 Playing with {player}...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            await process.wait()
            self.logger.debug("✅ Playback complete")
            
        except Exception as e:
            self.logger.error(f"❌ Playback error: {e}")
        finally:
            self.is_speaking = False
    
    async def _check_cache_size(self):
        """Check cache size and cleanup if needed"""
        try:
            files = list(self.cache_dir.glob("*.mp3"))
            total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
            
            if total_size_mb > (self.max_cache_size_mb * self.cache_cleanup_threshold):
                self.logger.info(f"🧽 Cache cleanup ({total_size_mb:.1f}MB)...")
                await self._cleanup_old_cache_files()
        except Exception as e:
            self.logger.error(f"❌ Cache check error: {e}")
    
    async def _cleanup_old_cache_files(self):
        """Remove oldest cache files"""
        try:
            files = list(self.cache_dir.glob("*.mp3"))
            files.sort(key=lambda f: f.stat().st_atime)
            
            to_remove = int(len(files) * 0.3)
            
            for f in files[:to_remove]:
                try:
                    f.unlink()
                except:
                    pass
            
            self.logger.info(f"✅ Cleaned up {to_remove} cache files")
        except Exception as e:
            self.logger.error(f"❌ Cache cleanup error: {e}")
    
    def stop_speaking(self):
        """Stop current speech"""
        self.is_speaking = False
        self.logger.info("⏹️ Speech stop requested")
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧽 Cleaning up Edge TTS provider...")
        self.stop_speaking()
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return f"Edge TTS ({self.voice_gender})"
