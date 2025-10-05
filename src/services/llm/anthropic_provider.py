import logging
from typing import Optional
from .base_provider import BaseLLMProvider

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider - PLACEHOLDER for future implementation"""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.logger = logging.getLogger(__name__)
        
        self.logger.warning("⚠️ Anthropic provider not yet implemented!")
        self.logger.info("   To add Claude support:")
        self.logger.info("   1. pip install anthropic")
        self.logger.info("   2. Implement this provider")
        self.logger.info("   3. Set ANTHROPIC_API_KEY in .env")
        
        raise NotImplementedError("Anthropic provider coming soon! Use OpenAI for now.")
    
    def _create_system_prompt(self) -> str:
        """Create the robot's personality"""
        # Same personality as OpenAI for consistency
        return """You are a friendly robot..."""
    
    async def get_response(self, user_message: str, language: Optional[str] = None) -> Optional[str]:
        """Get response from Claude"""
        # TODO: Implement with anthropic library
        # from anthropic import AsyncAnthropic
        # client = AsyncAnthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        # response = await client.messages.create(...)
        pass
    
    def cleanup(self):
        """Cleanup resources"""
        pass
