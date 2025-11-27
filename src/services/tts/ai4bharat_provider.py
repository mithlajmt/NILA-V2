import logging
import requests
import pygame
import os
import time
from pathlib import Path
from typing import Optional
from .base_tts_provider import BaseTTSProvider
import uuid

class AI4BharatTTSProvider(BaseTTSProvider):
    """
    AI4Bharat TTS Provider (Client)
    Connects to a local/remote TTS server running Parler-TTS
    """
    
    def __init__(self, settings):
        super().__init__(settings)
        self.logger = logging.getLogger(__name__)
        
        self.api_url = f"{settings.AI4BHARAT_URL}/v1/audio/speech"
        self.description = settings.AI4BHARAT_DESCRIPTION
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init()
        except Exception as e:
            self.logger.warning(f"⚠️ Pygame mixer init failed: {e}")
            
        # Audio cache directory
        self.cache_dir = Path("data/audio/ai4bharat")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"✅ AI4Bharat Provider initialized (Server: {settings.AI4BHARAT_URL})")

    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Generate and play speech using AI4Bharat Server"""
        try:
            if not text:
                return False
                
            self.logger.info(f"🔊 Speaking (AI4Bharat): {text[:50]}...")
            self.is_speaking = True
            
            # Generate Audio
            audio_file = self._generate_audio(text)
            
            if audio_file:
                # Play Audio
                pygame.mixer.music.load(str(audio_file))
                pygame.mixer.music.play()
                
                # Wait for playback to finish
                while pygame.mixer.music.get_busy() and self.is_speaking:
                    pygame.time.Clock().tick(10)
                    
                self.is_speaking = False
                return True
            else:
                self.is_speaking = False
                return False
                
        except Exception as e:
            self.logger.error(f"❌ AI4Bharat TTS error: {e}")
            self.is_speaking = False
            return False

    def _generate_audio(self, text: str) -> Optional[Path]:
        """Call the TTS Server"""
        try:
            payload = {
                "text": text,
                "description": self.description,
                "language": "en" # Default, model handles switching
            }
            
            self.logger.debug(f"📡 Sending request to {self.api_url}...")
            response = requests.post(self.api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                # Save to file
                filename = f"ai4bharat_{uuid.uuid4()}.wav"
                filepath = self.cache_dir / filename
                
                with open(filepath, "wb") as f:
                    f.write(response.content)
                    
                self.logger.debug(f"✅ Audio received: {filepath}")
                return filepath
            else:
                self.logger.error(f"❌ Server error: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Connection error: {e}")
            self.logger.error(f"💡 HINT: Is the TTS server running? Run 'extra/tts_server/run.sh' in a separate terminal.")
            return None

    def stop_speaking(self):
        """Stop current speech"""
        if self.is_speaking:
            pygame.mixer.music.stop()
            self.is_speaking = False

    def cleanup(self):
        """Cleanup resources"""
        self.stop_speaking()
        try:
            pygame.mixer.quit()
        except:
            pass

    def get_provider_name(self) -> str:
        return "AI4Bharat (Remote)"
