"""
TTS Service Factory
Creates the appropriate TTS provider based on settings
"""

import logging
from typing import Optional
from .base_tts_provider import BaseTTSProvider
from .gtts_provider import GTTSProvider
from .google_cloud_tts_provider import GoogleCloudTTSProvider


class TTSService:
    """Factory class to create and manage TTS providers"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.provider: Optional[BaseTTSProvider] = None
        
        # Create provider based on settings
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the TTS provider based on settings"""
        provider_name = self.settings.TTS_PROVIDER.lower()
        
        self.logger.info(f"🔧 Initializing TTS provider: {provider_name}")
        
        try:
            if provider_name == "gtts":
                self.provider = GTTSProvider(self.settings)
                
            elif provider_name == "google_cloud":
                self.provider = GoogleCloudTTSProvider(self.settings)
                
            elif provider_name == "azure":
                # Future: Azure TTS provider
                self.logger.error("❌ Azure provider not yet implemented")
                raise NotImplementedError("Azure TTS provider coming soon!")
                
            else:
                self.logger.warning(f"⚠️ Unknown TTS provider: {provider_name}, falling back to gTTS")
                self.provider = GTTSProvider(self.settings)
            
            self.logger.info(f"✅ TTS Service ready: {self.provider.get_provider_name()}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize TTS provider: {e}")
            self.logger.info("   Falling back to gTTS...")
            
            try:
                self.provider = GTTSProvider(self.settings)
                self.logger.info(f"✅ Fallback TTS ready: {self.provider.get_provider_name()}")
            except Exception as fallback_error:
                self.logger.error(f"❌ Even fallback failed: {fallback_error}")
                raise
    
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """
        Convert text to speech and play
        
        Args:
            text: The text to speak
            language: Language code ('en', 'ml') or None for auto-detect
            
        Returns:
            True if successful, False otherwise
        """
        if not self.provider:
            self.logger.error("❌ No TTS provider initialized")
            return False
        
        return await self.provider.speak(text, language)
    
    def stop_speaking(self):
        """Stop current speech"""
        if self.provider:
            self.provider.stop_speaking()
    
    def cleanup(self):
        """Cleanup resources"""
        if self.provider:
            self.provider.cleanup()
    
    def get_provider_info(self) -> str:
        """Get information about current provider"""
        if self.provider:
            return self.provider.get_provider_name()
        return "No provider"
    
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        if self.provider:
            return self.provider.is_speaking
        return False
    
    def switch_provider(self, new_provider: str):
        """
        Switch to a different TTS provider
        
        Args:
            new_provider: Name of the new provider (gtts, google_cloud, azure)
        """
        self.logger.info(f"🔄 Switching provider from {self.settings.TTS_PROVIDER} to {new_provider}")
        
        # Cleanup old provider
        if self.provider:
            self.provider.cleanup()
        
        # Update settings
        self.settings.TTS_PROVIDER = new_provider
        
        # Reinitialize provider
        self._initialize_provider()
