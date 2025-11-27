# tests/manual_stt_check.py
import asyncio
from src.config.settings import Settings
from src.services.speech.speech_recognizer import SpeechRecognizer

async def main():
    s = Settings()
    r = SpeechRecognizer(s)
    print("Say something…")
    text = await r.listen(timeout=30)
    print("You said:", text)
    r.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
