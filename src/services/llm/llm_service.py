import logging
from typing import Optional
from .base_provider import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider

class LLMService:
    """
    LLM Service Factory - Easy switching between AI providers
    
    Usage:
        # In .env file, set:
        LLM_PROVIDER=openai        # or anthropic, google, etc.
        
        # In code:
        llm = LLMService(settings)
        response = await llm.get_response("Hello!")
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Get provider from settings
        provider_name = settings.LLM_PROVIDER.lower()
        
        # Initialize the correct provider
        self.provider = self._create_provider(provider_name)
        
        self.logger.info(f"🧠 LLM Service initialized with provider: {provider_name}")
    
    def _create_provider(self, provider_name: str) -> BaseLLMProvider:
        """Factory method to create the correct provider"""
        
        if provider_name == "openai":
            return OpenAIProvider(self.settings)
        
        elif provider_name == "anthropic":
            return AnthropicProvider(self.settings)
        
        elif provider_name == "google":
            self.logger.error("❌ Google Gemini provider not yet implemented!")
            self.logger.info("   Available providers: openai")
            self.logger.info("   Falling back to OpenAI...")
            return OpenAIProvider(self.settings)
        
        else:
            self.logger.error(f"❌ Unknown LLM provider: {provider_name}")
            self.logger.info("   Available providers: openai")
            self.logger.info("   Falling back to OpenAI...")
            return OpenAIProvider(self.settings)
    
    async def get_response(self, user_message: str, language: Optional[str] = None) -> Optional[str]:
        """Get AI response - delegates to the active provider"""
        return await self.provider.get_response(user_message, language)
    
    def clear_history(self):
        """Clear conversation history"""
        self.provider.clear_history()
    
    def get_history(self, limit: Optional[int] = None):
        """Get conversation history"""
        return self.provider.get_history(limit)
    
    def get_stats(self):
        """Get usage statistics"""
        return self.provider.get_stats()
    
    def set_personality(self, personality: str):
        """Change robot personality"""
        self.provider.set_personality(personality)
    
    def cleanup(self):
        """Cleanup resources"""
        self.provider.cleanup()
