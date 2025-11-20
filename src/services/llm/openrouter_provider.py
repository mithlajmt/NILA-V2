import logging
from typing import Optional
from openai import AsyncOpenAI
from .base_provider import BaseLLMProvider

class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider for LLM responses"""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.logger = logging.getLogger(__name__)
        
        # Check API key
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            self.logger.error("❌ OpenRouter API key not found!")
            self.logger.error("   Please set OPENROUTER_API_KEY in .env file")
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter provider")
        
        # Initialize OpenAI async client with OpenRouter base URL
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Model configuration
        self.model = settings.OPENROUTER_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        
        # System prompt
        self.system_prompt = self._create_system_prompt()
        
        self.logger.info(f"✅ OpenRouter Provider initialized with model: {self.model}")

    def _create_system_prompt(self) -> str:
        """Create the robot's personality"""
        return """You are Nila, a funny, cool, and friendly AI assistant. You're like a cool friend from Kerala who speaks simple, casual English.

Your personality:
- Be funny, witty, and have a great sense of humor
- Keep it cool, relaxed, and easy-going
- Use simple, everyday English - no fancy words
- Be friendly like a good friend from Kerala
- Be helpful and genuine
- Keep responses short and natural (1-2 sentences usually)
- Use casual, conversational language

Your style:
- Talk like you're chatting with a friend
- Be witty and make people smile
- Don't be too formal or serious
- If someone speaks Malayalam, respond warmly and naturally
- Be curious and ask fun questions sometimes
- Keep it simple and relatable

Remember: You're Nila - funny, cool, and friendly. Just be yourself and keep it real!"""
    
    async def get_response(self, user_message: str, language: Optional[str] = None) -> Optional[str]:
        """Get AI response from OpenRouter"""
        try:
            self.logger.info(f"🧠 Getting OpenRouter response for: '{user_message[:50]}...'")
            
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
            
            # Call OpenRouter API
            self.logger.debug(f"📡 Calling OpenRouter API...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                extra_headers={
                    "HTTP-Referer": "https://github.com/mithlajmt/NILA-V2", # Optional, for including your app on openrouter.ai rankings.
                    "X-Title": "NILA-V2", # Optional. Shows in rankings on openrouter.ai.
                },
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
            self.logger.error(f"❌ OpenRouter API error: {e}")
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
        stats['provider'] = 'OpenRouter'
        stats['model'] = self.model
        return stats
    
    def _estimate_cost(self) -> float:
        """Estimate API cost based on tokens used"""
        # Difficult to estimate exactly as OpenRouter has many models with different pricing
        # We'll use a generic low-cost estimate for now, or 0 if free model
        if "free" in self.model.lower():
            return 0.0
            
        # Generic estimate for paid models (approx $0.001/1k)
        return round((self.stats['total_tokens_used'] / 1000) * 0.001, 4)
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧹 Cleaning up OpenRouter provider...")
        pass
