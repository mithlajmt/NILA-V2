import asyncio
import logging
import speech_recognition as sr
# import webrtcvad
import collections
import pyaudio
from typing import Optional, List
import time
import io

class SpeechRecognizer:
    """Advanced speech recognition with VAD and multi-provider support (Google + Whisper)"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Voice Activity Detection (WebRTC VAD)
        # self.vad = webrtcvad.Vad(2)  # Aggressiveness: 0-3 (2 is moderate)
        
        # Speech detection settings
        self.frame_duration_ms = 30  # Frame duration in ms (10, 20, or 30)
        self.padding_duration_ms = 300  # Silence padding before/after speech
        self.speech_start_frames = 10  # Frames to confirm speech started
        self.speech_end_frames = 20  # Frames to confirm speech ended
        
        # Calibration tracking
        self.last_calibration_time = 0
        self.calibration_interval = 300  # Re-calibrate every 5 minutes
        self.ambient_noise_samples = collections.deque(maxlen=10)
        
        # Whisper model (lazy loading)
        self.whisper_model = None
        self.whisper_available = False
        
        # Check which provider to use
        self.provider = settings.SPEECH_PROVIDER.lower()  # "google" or "whisper"
        
        # Initialize Whisper if selected
        if self.provider == "whisper":
            self._init_whisper()
        
        # Initial calibration
        self._calibrate_microphone()
        
        provider_name = "Whisper (Multilingual)" if self.provider == "whisper" else "Google Speech API"
        self.logger.info(f"🎙️ Advanced Speech Recognition initialized with VAD + {provider_name}")
    
    def _init_whisper(self):
        """Initialize Whisper model (lazy loading)"""
        try:
            import whisper
            
            model_size = self.settings.WHISPER_MODEL  # tiny, base, small, medium, large
            device = self.settings.WHISPER_DEVICE  # cpu or cuda
            
            self.logger.info(f"📥 Loading Whisper model '{model_size}' on {device.upper()}...")
            self.whisper_model = whisper.load_model(model_size, device=device)
            self.whisper_available = True
            
            self.logger.info(f"✅ Whisper model loaded successfully!")
            self.logger.info(f"   Supports: Malayalam (ml), English (en), and 97+ other languages")
            
        except ImportError:
            self.logger.warning("⚠️ Whisper not installed. Run: pip install openai-whisper torch torchaudio")
            self.logger.info("   Falling back to Google Speech Recognition")
            self.provider = "google"
            self.whisper_available = False
        except Exception as e:
            self.logger.error(f"❌ Failed to load Whisper: {e}")
            self.logger.info("   Falling back to Google Speech Recognition")
            self.provider = "google"
            self.whisper_available = False
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise with error handling"""
        try:
            with self.microphone as source:
                self.logger.info("🔊 Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                
                # Store ambient energy level
                self.ambient_noise_samples.append(self.recognizer.energy_threshold)
                
                # Fine-tune for PROFESSIONAL responsive detection
                # Use average of recent calibrations if available
                if len(self.ambient_noise_samples) > 0:
                    avg_threshold = sum(self.ambient_noise_samples) / len(self.ambient_noise_samples)
                    # INCREASED threshold to avoid false triggers
                    self.recognizer.energy_threshold = max(400, avg_threshold * 1.3)
                else:
                    self.recognizer.energy_threshold = 400  # Higher default
                
                # PROFESSIONAL SETTINGS - Better accuracy, no false recordings
                self.recognizer.pause_threshold = 0.8  # Silence duration to consider phrase complete
                self.recognizer.phrase_threshold = 0.3  # Minimum speech (higher = less sensitive to noise)
                self.recognizer.non_speaking_duration = 0.8  # Seconds of silence to stop
                
                self.last_calibration_time = time.time()
                
                self.logger.info(f"✅ Microphone calibrated - Threshold: {int(self.recognizer.energy_threshold)}")
        except Exception as e:
            self.logger.error(f"❌ Calibration failed: {e}")
            # Set safe defaults
            self.recognizer.energy_threshold = 300
            self.recognizer.pause_threshold = 0.6
            self.recognizer.phrase_threshold = 0.3
    
    def _should_recalibrate(self) -> bool:
        """Check if we need to recalibrate based on time"""
        return (time.time() - self.last_calibration_time) > self.calibration_interval
    
    async def listen(self, timeout: int = 30) -> Optional[str]:
        """Listen for speech with VAD and return text"""
        try:
            # Periodic recalibration
            if self._should_recalibrate():
                self.logger.info("🔄 Performing periodic recalibration...")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._calibrate_microphone)
            
            self.logger.info("🎯 Ready to listen...")
            
            # Run blocking audio capture in thread pool
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(None, self._capture_audio_with_vad, timeout)
            
            if audio:
                # Run blocking transcription in thread pool
                text = await loop.run_in_executor(None, self._transcribe_audio, audio)
                return text
                
        except Exception as e:
            self.logger.error(f"❌ Speech recognition error: {e}")
        
        return None
    
    def _capture_audio_with_vad(self, timeout: int) -> Optional[sr.AudioData]:
        """Capture audio with PROFESSIONAL Voice Activity Detection - stops when you stop talking!"""
        try:
            print("🎯 Listening... (Speak now!)")
            
            # Use dynamic listening with automatic silence detection
            with self.microphone as source:
                start_time = time.time()
                print("⏳ Waiting for speech...")
                
                try:
                    # FIXED: Max 20 seconds recording + better noise filtering
                    audio = self.recognizer.listen(
                        source,
                        timeout=timeout,  # Max time to WAIT for speech to START (30s)
                        phrase_time_limit=20,  # MAX 20 seconds of recording!
                    )
                    
                    elapsed = time.time() - start_time
                    print(f"✅ Recording complete! ({elapsed:.1f}s) - Processing...")
                    return audio
                    
                except sr.WaitTimeoutError:
                    print("⏱️ Timeout - No speech detected. Try speaking louder.")
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ Audio capture error: {e}")
            return None
    
    def _transcribe_audio(self, audio: sr.AudioData) -> Optional[str]:
        """Convert audio to text using selected provider (Google or Whisper)"""
        if self.provider == "whisper" and self.whisper_available:
            return self._transcribe_with_whisper(audio)
        else:
            return self._transcribe_with_google(audio)
    
    def _transcribe_with_google(self, audio: sr.AudioData) -> Optional[str]:
        """Convert audio to text using Google Speech Recognition"""
        try:
            print("🔍 Transcribing with Google...")
            
            # Try Google Speech Recognition
            text = self.recognizer.recognize_google(
                audio, 
                language="en-IN",  # Indian English
                show_all=False  # Get only best result
            )
            
            if text:
                print(f"✅ Transcribed successfully")
                return text.strip()
            else:
                print("⚠️ Empty transcription")
                return None
                
        except sr.UnknownValueError:
            print("❌ Could not understand the audio - please speak more clearly")
            return None
        except sr.RequestError as e:
            self.logger.error(f"❌ Speech service error: {e}")
            print("❌ Network error - please check your internet connection")
            return None
        except Exception as e:
            self.logger.error(f"❌ Transcription error: {e}")
            return None
    
    def _transcribe_with_whisper(self, audio: sr.AudioData) -> Optional[str]:
        """Convert audio to text using Whisper (supports Malayalam + English)"""
        try:
            print("🔍 Transcribing with Whisper (Multilingual)...")
            
            # Convert audio data to format Whisper expects
            import numpy as np
            
            # Get raw audio data
            audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
            
            # Convert to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Get language setting
            language = self.settings.WHISPER_LANGUAGE  # "en", "ml", or None for auto-detect
            
            # Transcribe with Whisper
            if language == "auto" or language is None:
                # Auto-detect language
                result = self.whisper_model.transcribe(audio_np, fp16=False)
                detected_lang = result.get('language', 'unknown')
                print(f"🌍 Detected language: {detected_lang}")
            else:
                # Use specified language
                result = self.whisper_model.transcribe(audio_np, language=language, fp16=False)
            
            text = result["text"].strip()
            
            if text:
                print(f"✅ Transcribed successfully")
                return text
            else:
                print("⚠️ Empty transcription")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Whisper transcription error: {e}")
            print(f"❌ Whisper error: {e}")
            
            # Fallback to Google if Whisper fails
            self.logger.info("   Falling back to Google Speech Recognition...")
            return self._transcribe_with_google(audio)
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧽 Cleaning up speech recognizer...")
        
        # Unload Whisper model to free memory
        if self.whisper_model is not None:
            del self.whisper_model
            self.whisper_model = None
            
            # Try to clear CUDA cache if using GPU
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
