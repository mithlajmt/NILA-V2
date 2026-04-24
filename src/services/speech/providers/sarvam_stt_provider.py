import asyncio
import io
import wave
import logging
from typing import Optional

from src.services.speech.base_stt_provider import BaseSTTProvider, STTResult


class SarvamSTTProvider(BaseSTTProvider):
    """
    Sarvam AI STT Provider for NILA-V2
    
    Optimized for Indian languages (Malayalam, Hindi, etc.) using Saaras models.
    Supports modes like 'transcribe', 'translate' (indic to english).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "saaras:v3",
        mode: str = "transcribe"
    ):
        """
        Initialize Sarvam STT provider
        
        Args:
            api_key: Sarvam API Key
            model: Model to use (e.g., 'saaras:v3')
            mode: Operating mode ('transcribe', 'translate', 'verbatim', 'translit', 'codemix')
        """
        if not api_key:
            raise ValueError("Sarvam API key cannot be empty")
            
        self.api_key = api_key
        self.model = model
        self.mode = mode
        self.logger = logging.getLogger(__name__)

        try:
            from sarvamai import SarvamAI
            self.client = SarvamAI(api_subscription_key=self.api_key)
            self.logger.info(f"✅ Sarvam STT initialized (model={self.model}, mode={self.mode})")
        except ImportError:
            self.logger.error("❌ sarvamai package not installed. Run: pip install sarvamai")
            raise

    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> STTResult:
        """
        Transcribe raw PCM audio bytes to text using Sarvam API.
        
        Args:
            audio_bytes: Raw audio data (16-bit PCM, 16kHz, mono)
            language: (Ignored by Saaras model which auto-detects Indic languages)
            
        Returns:
            STTResult with transcribed text.
        """
        try:
            # Sarvam API expects a valid audio file format (WAV, MP3, etc.)
            # We convert raw 16kHz mono PCM bytes to WAV format in memory.
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)           # Mono
                wav_file.setsampwidth(2)           # 2 bytes = 16-bit
                wav_file.setframerate(16000)       # 16kHz
                wav_file.writeframes(audio_bytes)
            
            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"  # Important for some HTTP clients recognizing the file type

            self.logger.info(f"🎯 Sending audio to Sarvam AI (mode: {self.mode})...")

            # Run in a thread pool since SDK may be synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.speech_to_text.transcribe(
                    file=wav_buffer,
                    model=self.model,
                    mode=self.mode
                )
            )

            # Extract transcription from response
            # Format varies slightly depending on SDK, typically:
            # response.transcript or response['transcript']
            text = None
            if hasattr(response, 'transcript'):
                text = response.transcript
            elif isinstance(response, dict) and 'transcript' in response:
                text = response['transcript']
            else:
                # Fallback, just try to get the text attribute if possible
                text = str(response)

            if text:
                text = text.strip()
                self.logger.info(f"✅ Transcribed (Sarvam): '{text}'")
                return STTResult(text=text, language=language)
            elif text == "":
                # It's an empty transcript (common on silence or abort)
                return STTResult(text=None, error="No speech detected")
            else:
                self.logger.warning(f"⚠️ No transcript deeply found in Sarvam response: {response}")
                return STTResult(text=None, error="No transcription received")

        except Exception as e:
            self.logger.error(f"❌ Sarvam STT Error: {e}")
            return STTResult(text=None, error=str(e))
