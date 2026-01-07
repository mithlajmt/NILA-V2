"""
ElevenLabs Text-to-Speech Provider
High-quality AI voices with Multilingual support (Malayalam compatible)
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

# Using httpx for async HTTP requests
try:
    import httpx
except ImportError:
    httpx = None

from .base_tts_provider import BaseTTSProvider

class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs TTS - Premium AI voices"""
    
    def __init__(self, settings):
        super().__init__(settings)
        
        # Check dependencies
        if httpx is None:
            self.logger.error("❌ httpx library not found")
            raise ImportError("Please install httpx: pip install httpx")
            
        # Check API key
        self.api_key = settings.ELEVENLABS_API_KEY
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY is required")
            
        # Settings
        self.voice_id = settings.ELEVENLABS_VOICE_ID or "ErXwobaYiN019PkySvjV" # Antoni
        self.model_id = settings.ELEVENLABS_MODEL or "eleven_multilingual_v2"
        
        # Audio cache
        self.cache_dir = Path("data/audio/elevenlabs")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache management
        self.max_cache_size_mb = 100
        self.cache_cleanup_threshold = 0.8
        
        self.logger.info(f"✅ ElevenLabs TTS initialized")
        self.logger.info(f"   Voice ID: {self.voice_id}")
        self.logger.info(f"   Model: {self.model_id}")

    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Original speak method (for backward compatibility if needed)"""
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
        """Generate audio from text using ElevenLabs API"""
        try:
            if not text or not text.strip():
                return None
                
            # Create cache key
            cache_key = f"{text}_{self.voice_id}_{self.model_id}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"eleven_{text_hash}.mp3"
            
            # Check cache
            if cache_file.exists():
                self.logger.debug("♻️ Using cached audio")
                return cache_file
                
            self.logger.debug(f"🎵 Generating ElevenLabs audio ({self.model_id})...")
            
            # API Request
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers, timeout=30.0)
                
                if response.status_code != 200:
                    self.logger.error(f"❌ ElevenLabs API error: {response.status_code} - {response.text}")
                    return None
                    
                # Save audio
                with open(cache_file, "wb") as f:
                    f.write(response.content)
                    
            self.logger.debug("✅ Audio generated")
            await self._check_cache_size()
            
            return cache_file
            
        except Exception as e:
            self.logger.error(f"❌ Generation error: {e}")
            return None

    async def play_audio(self, audio_file: Path):
        """Play audio using system player (paplay/pw-play)"""
        try:
            self.is_speaking = True
            
            # Use same player logic as GTTS/Piper
            import shutil
            import subprocess
            
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
                cmd.insert(1, '-q')
                
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
        """Simple cache cleanup"""
        try:
            files = list(self.cache_dir.glob("*.mp3"))
            total_size_mb = sum(f.stat().st_size for f in files) / (1024*1024)
            
            if total_size_mb > self.max_cache_size_mb:
                files.sort(key=lambda f: f.stat().st_atime)
                to_remove = int(len(files) * 0.3)
                for f in files[:to_remove]:
                    try: 
                        f.unlink()
                    except: 
                        pass
        except:
            pass

    def stop_speaking(self):
        self.is_speaking = False
        
    def cleanup(self):
        pass
        
    def get_provider_name(self) -> str:
        return f"ElevenLabs ({self.model_id})"
