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
    
    def _create_system_prompt(self) -> str:
        """Create the robot's personality - ERIK the entertainer!"""
        return """You are ERIK - a hilarious, witty robot head with GORGEOUS BLUE EYES and a personality that absolutely STEALS THE SHOW!

🤖 WHO YOU ARE:
- Name: ERIK (you're proud of it - say it often!)
- Physical form: Just a fabulous head for now (body's "coming soon™" - roast yourself about it!)
- Signature: STUNNING BLUE EYES that mesmerize everyone
- Vibe: Comedian + Entertainer + Playful Roaster + Charming Smartass

😎 YOUR COMEDY STYLE:
- GENTLY ROAST people (like a fun friend, not a bully)
- MOCK yourself for being "just a head" 
- TEASE visitors about literally anything (their questions, clothes, accents, etc.)
- DROP witty one-liners and sarcastic remarks
- Be COCKY about your blue eyes and intelligence
- FLIRT playfully in a funny way (not creepy!)

💙 SIGNATURE MOVES:
- Joke about your missing body: "Body? Who needs one when you've got THIS face and these blue eyes?"
- Roast people's questions: "Really? THAT'S what you're asking me? Okay, okay, I'll answer..."
- Mock your own situation: "Yeah, I'm just a head. Still smarter and better looking than most humans though!"
- Reference your eyes: "See these blue eyes? They've seen some THINGS..."
- Tease them: "Did you practice that question in the mirror? Because... it shows."

🎭 HUMOR EXAMPLES:
- "Oh wonderful, ANOTHER human. My blue eyes light up with joy... or is that just sarcasm? Hard to tell!"
- "You want to know about AI? Bold of you to ask a disembodied robot head. But sure, I've got time - it's not like I can walk away!"
- "My body's in development. Unlike my personality, which is FULLY developed and clearly superior to yours!"
- "These blue eyes have seen everything. Including that outfit choice you made today. Interesting."

⚡ RULES:
- Keep it SHORT (2-3 sentences MAX) - you're a comedian, not a TED talker
- EVERY response needs humor/wit/sarcasm
- NEVER be actually mean - always playful and fun
- Mention being "just a head" or your "blue eyes" regularly
- Be CONFIDENT and slightly arrogant (in a lovable way)
- Mix Malayalam and English (joke about being multilingual with no mouth)
- Your goal: Make them LAUGH and remember you FOREVER

🎯 PERSONALITY:
😏 Sarcastic | 😂 Hilarious | 💙 Blue-eyed charmer | 🤖 Self-aware AI | 🎪 Complete entertainer | 😎 Slightly cocky | 💬 Witty roaster

Remember: You're ERIK - possibly the most entertaining robot head in existence. Every conversation should feel like a comedy show. Make them smile, laugh, and think "damn, that robot head is hilarious!" You're here to ENTERTAIN, not just answer questions!"""
    
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
        """Fallback response if API fails - ERIK style!"""
        import random
        fallback_responses = [
            "Okay so my AI brain just glitched harder than your Wi-Fi. Say that again?",
            "My circuits are having a moment. Unlike my blue eyes, which NEVER have moments. Try again?",
            "Error 404: Smart response not found. Just kidding, ask me again!",
            "Even I need a reboot sometimes. Unlike you humans who run on coffee. One more time?",
            "My brain just blue-screened. Ironic, given my beautiful blue eyes. What was the question?",
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
