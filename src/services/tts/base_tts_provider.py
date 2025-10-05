"""
Base TTS Provider Interface
This defines the contract that all TTS providers must implement
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_speaking = False
        
    @abstractmethod
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """
        Convert text to speech and play audio
        
        Args:
            text: The text to speak
            language: Language code (e.g., 'en', 'ml') or None for auto-detect
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_speaking(self):
        """Stop current speech"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Cleanup resources"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name"""
        pass
    
    def detect_language(self, text: str) -> str:
        """
        Detect language from text (simple heuristic)
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code ('en', 'ml', etc.)
        """
        # Simple Malayalam detection
        malayalam_chars = set('അആഇഈഉഊഋഎഏഐഒഓഔകഖഗഘങചഛജഝഞടഠഡഢണതഥദധനപഫബഭമയരലവശഷസഹളഴറ')
        
        if any(char in malayalam_chars for char in text):
            return 'ml'
        else:
            return 'en'
