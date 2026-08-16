"""
ElevenLabs Text-to-Speech Provider
Ultra-realistic AI voice synthesis
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Optional
import httpx
import pygame
from .base_tts_provider import BaseTTSProvider


class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs Text-to-Speech provider"""
    
    def __init__(self, settings):
        super().__init__(settings)
        
        self.api_key = getattr(settings, 'ELEVENLABS_API_KEY', '') or ''
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY is required for ElevenLabs TTS provider")
            
        self.voice_id = getattr(settings, 'ELEVENLABS_VOICE_ID', 'j36Me84eUGSrrHkIwAZQ')
        self.model_id = getattr(settings, 'ELEVENLABS_MODEL_ID', 'eleven_v3')
        
        # Audio cache directory
        self.cache_dir = Path("data/audio/elevenlabs")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize pygame mixer if not initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
            
        self.logger.info(f"✅ ElevenLabs TTS initialized (Voice ID: {self.voice_id}, Model: {self.model_id})")
        
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Generate and play speech using ElevenLabs API"""
        try:
            if not text or not text.strip():
                self.logger.warning("⚠️ Empty text provided")
                return False
                
            self.logger.info(f"🔊 Speaking (ElevenLabs {self.voice_id[:6]}...): {text[:50]}...")
            
            # Generate audio file
            audio_file = await self._generate_audio(text)
            
            if audio_file:
                await self._play_audio(audio_file)
                return True
            else:
                self.logger.error("❌ Failed to generate audio from ElevenLabs")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ ElevenLabs TTS error: {e}")
            return False
            
    async def _generate_audio(self, text: str) -> Optional[Path]:
        """Call ElevenLabs REST API to generate speech audio"""
        try:
            cache_key = f"{text}_{self.voice_id}_{self.model_id}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = self.cache_dir / f"elevenlabs_{text_hash}.mp3"
            
            if cache_file.exists():
                self.logger.debug("♻️ Using cached ElevenLabs audio")
                return cache_file
                
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            payload = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
            if response.status_code == 200:
                with open(cache_file, "wb") as f:
                    f.write(response.content)
                self.logger.debug(f"✅ Generated ElevenLabs audio ({len(response.content)} bytes)")
                return cache_file
            else:
                self.logger.error(f"❌ ElevenLabs API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Audio generation failed: {e}")
            return None
            
    async def _play_audio(self, audio_file: Path):
        """Play audio file using Pygame mixer"""
        try:
            self.is_speaking = True
            pygame.mixer.music.load(str(audio_file))
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
                
            self.is_speaking = False
            self.logger.debug("✅ Audio playback completed")
        except Exception as e:
            self.is_speaking = False
            self.logger.error(f"❌ Audio playback error: {e}")

    def stop_speaking(self):
        """Stop audio playback"""
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self.is_speaking = False
        except Exception as e:
            self.logger.error(f"❌ Stop speaking error: {e}")

    def cleanup(self):
        """Cleanup resources"""
        self.stop_speaking()

    def get_provider_name(self) -> str:
        return f"ElevenLabs TTS ({self.voice_id})"
