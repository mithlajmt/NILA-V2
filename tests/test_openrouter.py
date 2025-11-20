import asyncio
import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import Settings
from src.services.llm.llm_service import LLMService

# Mock environment variables for testing if not set
if not os.getenv("OPENROUTER_API_KEY"):
    print("⚠️ OPENROUTER_API_KEY not set. Please set it in .env to test properly.")
    # We can't really test without a key, but we can check if the class loads
    
async def test_openrouter():
    print("🧪 Testing OpenRouter Integration...")
    
    # Force OpenRouter provider
    os.environ["LLM_PROVIDER"] = "openrouter"
    
    try:
        settings = Settings()
        print(f"✅ Settings loaded. Provider: {settings.LLM_PROVIDER}")
        print(f"✅ Model: {settings.OPENROUTER_MODEL}")
        print(f"📜 System Prompt Preview: {settings.LLM_SYSTEM_PROMPT[:100]}...")
        
        llm = LLMService(settings)
        print("✅ LLM Service initialized")
        
        if settings.OPENROUTER_API_KEY:
            print("📡 Sending test message...")
            response = await llm.get_response("Sugamano? (Reply in Manglish)")
            print(f"🤖 Response: {response}")
        else:
            print("⚠️ Skipping API call (no key)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
