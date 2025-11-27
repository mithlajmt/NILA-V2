import asyncio
import logging
from typing import Optional
from openai import AsyncOpenAI
from .base_provider import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider for LLM responses"""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.logger = logging.getLogger(__name__)
        
        # Check API key
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            self.logger.error("❌ OpenAI API key not found!")
            self.logger.error("   Please set OPENAI_API_KEY in .env file")
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        
        # Initialize OpenAI async client
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Model configuration
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        
        # System prompt
        self.system_prompt = self._create_system_prompt()
        
        self.logger.info(f"✅ OpenAI Provider initialized with model: {self.model}")


    
    async def get_response(self, user_message: str, language: Optional[str] = None) -> Optional[str]:
        """Get AI response from OpenAI"""
        try:
            self.logger.info(f"🧠 Getting OpenAI response for: '{user_message[:50]}...'")
            
            # Add user message to history
            self.add_to_history("user", user_message)
            
            # Prepare messages for API
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add conversation history (last N messages)
            history_to_send = self.get_history(limit=self.max_history)
            messages.extend(history_to_send)
            
            # Add language hint if Malayalam detected
            if language == "ml":
                messages.append({
                    "role": "system",
                    "content": "Note: The user spoke in Malayalam. You can acknowledge this and respond warmly. Use simple English or basic Malayalam phrases if appropriate."
                })
            
            # Call OpenAI API
            self.logger.debug(f"📡 Calling OpenAI API...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            # Extract response
            assistant_message = response.choices[0].message.content.strip()
            
            # Add to history
            self.add_to_history("assistant", assistant_message)
            
            # Update statistics
            self.stats['total_messages'] += 1
            self.stats['total_tokens_used'] += response.usage.total_tokens
            
            self.logger.info(f"✅ Response generated ({response.usage.total_tokens} tokens)")
            self.logger.debug(f"📝 Response: {assistant_message[:100]}...")
            
            return assistant_message
            
        except Exception as e:
            self.logger.error(f"❌ OpenAI API error: {e}")
            self.stats['errors'] += 1
            return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """Fallback response if API fails"""
        import random
        fallback_responses = [
            "Hmm, I'm having a bit of trouble thinking right now. Could you please repeat that?",
            "Oops! My circuits got a bit tangled. Can you say that again?",
            "Sorry, I need a moment to reboot my brain. Please try again!",
            "My AI brain hiccuped! Give me one more try?",
        ]
        return random.choice(fallback_responses)
    
    def get_stats(self):
        """Get statistics including cost estimate"""
        stats = super().get_stats()
        stats['estimated_cost'] = self._estimate_cost()
        stats['provider'] = 'OpenAI'
        stats['model'] = self.model
        return stats
    
    def _estimate_cost(self) -> float:
        """Estimate API cost based on tokens used"""
        # Approximate costs (as of 2024)
        # GPT-4: ~$0.03 per 1K tokens (input+output combined estimate)
        # GPT-3.5-turbo: ~$0.002 per 1K tokens
        if "gpt-4" in self.model.lower():
            rate = 0.03
        else:
            rate = 0.002
        
        return round((self.stats['total_tokens_used'] / 1000) * rate, 4)
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧹 Cleaning up OpenAI provider...")
        # AsyncOpenAI client doesn't need explicit cleanup
        pass
