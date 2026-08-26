"""
NILA-V2 - Fast Gemini Live Diagnostic & Speed Test Script
---------------------------------------------------------
Boots in < 0.5s without initializing offline heavy models (Whisper/Piper/ElevenLabs).
Tests Gemini 3.1 Live WebSockets, talking speed, voice selection, and microphone VAD.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import Settings
from src.services.realtime.gemini_live_provider import GeminiLiveProvider
from src.utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

async def main():
    settings = Settings()
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        logger.error("❌ GEMINI_API_KEY is missing in .env!")
        print("\nPlease set GEMINI_API_KEY in your .env file:")
        print("GEMINI_API_KEY=AIzaSyYourActualKeyHere...")
        sys.exit(1)

    print("\n" + "="*60)
    print("🤖 NILA-V2 FAST GEMINI LIVE TEST DRIVER")
    print("="*60)
    print(f"🔑 API Key: {api_key[:8]}...")
    print(f"🎙️ Voice: {settings.GEMINI_LIVE_VOICE}")
    print(f"⚡ Speed Ratio: {settings.GEMINI_LIVE_SPEED_RATIO} (1.0 = Normal, 1.25 = Fast)")
    print(f"🎭 Robotic Filter: {settings.GEMINI_LIVE_ROBOTIC_EFFECT}")
    print(f"⏸️ VAD Silence Limit: {settings.GEMINI_LIVE_SILENCE_CHUNKS} chunks (~1.15s pause allowance)")
    print("="*60 + "\n")

    provider = GeminiLiveProvider(settings)
    try:
        await provider.start_live_session()
    except KeyboardInterrupt:
        print("\n⏸️ Test stopped by user.")
    finally:
        provider.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test closed.")
