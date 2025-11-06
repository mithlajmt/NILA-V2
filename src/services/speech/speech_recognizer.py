import asyncio
import logging
import speech_recognition as sr
import webrtcvad
import collections
import time
from typing import Optional

from src.services.speech.base_stt_provider import STTResult, BaseSTTProvider
from src.services.speech.providers.google_stt_provider import GoogleSTTProvider

class SpeechRecognizer:
    """Advanced speech recognition with VAD + pluggable providers (Google / Whisper)"""

    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # SR core
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        # VAD
        self.vad = webrtcvad.Vad(2)

        # Calibration helpers
        self.last_calibration_time = 0
        self.calibration_interval = 300  # seconds
        self.ambient_noise_samples = collections.deque(maxlen=10)

        # Provider selection
        self.provider_name = settings.SPEECH_PROVIDER.lower()  # "google" | "whisper"
        self.provider: Optional[BaseSTTProvider] = None
        self.last_detected_language: Optional[str] = None

        # init provider
        self._init_provider()

        # initial calibration
        self._calibrate_microphone()
        self.logger.info(f"🎙️ STT ready with provider: {self.provider_name}")

    # ---------- provider init ----------
    def _init_provider(self):
        if self.provider_name == "whisper":
            try:
                import whisper
                model = whisper.load_model(self.settings.WHISPER_MODEL, device=self.settings.WHISPER_DEVICE)
                from src.services.speech.providers.whisper_stt_provider import WhisperSTTProvider
                lang = None if self.settings.WHISPER_LANGUAGE in ("auto", "", None) else self.settings.WHISPER_LANGUAGE
                self.provider = WhisperSTTProvider(model=model, language=lang)
                self.logger.info("🧠 Whisper provider loaded")
            except Exception as e:
                self.logger.warning(f"⚠️ Whisper init failed: {e}. Falling back to Google.")
                self.provider_name = "google"
                self.provider = GoogleSTTProvider(self.recognizer, default_language=getattr(self.settings, "STT_LANGUAGE", "en-IN"))
        else:
            self.provider = GoogleSTTProvider(self.recognizer, default_language=getattr(self.settings, "STT_LANGUAGE", "en-IN"))

    # ---------- calibration ----------
    def _calibrate_microphone(self):
        try:
            with self.microphone as source:
                self.logger.info("🔊 Calibrating mic...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                self.ambient_noise_samples.append(self.recognizer.energy_threshold)
                if self.ambient_noise_samples:
                    avg = sum(self.ambient_noise_samples) / len(self.ambient_noise_samples)
                    self.recognizer.energy_threshold = max(300, avg * 1.2)
                else:
                    self.recognizer.energy_threshold = 300
                self.recognizer.pause_threshold = 0.6
                self.recognizer.phrase_threshold = 0.3
                self.recognizer.non_speaking_duration = 0.5
                self.last_calibration_time = time.time()
                self.logger.info(f"✅ Mic calibrated (threshold={int(self.recognizer.energy_threshold)})")
        except Exception as e:
            self.logger.error(f"❌ Calibration failed: {e}")
            self.recognizer.energy_threshold = 300

    def _should_recalibrate(self) -> bool:
        return (time.time() - self.last_calibration_time) > self.calibration_interval

    # ---------- public API ----------
    async def listen(self, timeout: int = 30) -> Optional[str]:
        try:
            if self._should_recalibrate():
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._calibrate_microphone)

            self.logger.info("🎯 Ready to listen...")
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(None, self._capture_blocking, timeout)
            if not audio:
                return None

            # transcribe via provider
            assert self.provider is not None, "STT provider not initialized"
            result: STTResult = await self.provider.transcribe(audio)
            self.last_detected_language = result.language

            if result.text:
                print("✅ Transcribed successfully")
                return result.text
            else:
                if result.error:
                    print(f"❌ STT error: {result.error}")
                return None
        except Exception as e:
            self.logger.error(f"❌ listen error: {e}")
            return None

    def _capture_blocking(self, timeout: int) -> Optional[sr.AudioData]:
        try:
            print("🎯 Listening... (Speak naturally)")
            with self.microphone as source:
                start = time.time()
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
                print(f"✅ Got it! ({time.time()-start:.1f}s) Processing...")
                return audio
        except sr.WaitTimeoutError:
            print("⏱️ No speech within timeout")
            return None
        except Exception as e:
            self.logger.error(f"❌ Audio capture error: {e}")
            return None

    def get_last_language(self) -> Optional[str]:
        return self.last_detected_language

    def cleanup(self):
        self.logger.info("🧽 Cleaning up speech recognizer...")
        # if whisper was used, provider will be GC'ed; GPU cache handled elsewhere
