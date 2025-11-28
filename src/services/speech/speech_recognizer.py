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
        self.microphone = self._get_best_microphone()

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

    def _get_best_microphone(self) -> sr.Microphone:
        """Find the best available microphone, prioritizing USB devices"""
        try:
            # List all devices
            mic_names = sr.Microphone.list_microphone_names()
            self.logger.info(f"🎧 Available Audio Devices ({len(mic_names)} found):")
            for i, name in enumerate(mic_names):
                self.logger.info(f"   [{i}] {name}")
            
            # 1. Try to find a USB microphone (exact match for Pi)
            for i, name in enumerate(mic_names):
                name_lower = name.lower()
                # Look for USB devices, prioritize specific ones
                if "usb pnp sound device" in name_lower or \
                   ("usb" in name_lower and "audio" in name_lower and "sysdefault" not in name_lower):
                    self.logger.info(f"✅ Found USB Microphone: '{name}' at index {i}")
                    return sr.Microphone(device_index=i)
            
            # 2. Try any USB device
            for i, name in enumerate(mic_names):
                if "usb" in name.lower() and "sysdefault" not in name.lower():
                    self.logger.info(f"✅ Found USB device: '{name}' at index {i}")
                    return sr.Microphone(device_index=i)
            
            # 3. Fallback: Try default device
            self.logger.warning("⚠️ No USB Mic found, using default device")
            self.logger.warning("   This may cause issues on Raspberry Pi!")
            return sr.Microphone()
            
        except Exception as e:
            self.logger.error(f"❌ Error finding microphone: {e}")
            self.logger.info("   Falling back to default sr.Microphone()")
            return sr.Microphone()

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
        except OSError as e:
            # ALSA/Device errors often manifest as OSErrors
            self.logger.error(f"❌ Audio Device Error: {e}")
            print("⚠️ Audio device error. Retrying connection...")
            try:
                # Try to re-initialize microphone
                self.microphone = self._get_best_microphone()
            except:
                pass
            return None
        except Exception as e:
            self.logger.error(f"❌ Audio capture error: {e}")
            return None

    def get_last_language(self) -> Optional[str]:
        return self.last_detected_language

    def cleanup(self):
        self.logger.info("🧽 Cleaning up speech recognizer...")
        # if whisper was used, provider will be GC'ed; GPU cache handled elsewhere
