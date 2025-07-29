import asyncio
import logging
import speech_recognition as sr
from typing import Optional

class SpeechRecognizer:
    """Simple speech recognition for Step 2"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Calibrate microphone
        self._calibrate_microphone()
        
        self.logger.info("Speech Recognition initialized")
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        try:
            with self.microphone as source:
                self.logger.info("Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.logger.info("Microphone calibrated")
        except Exception as e:
            self.logger.error(f"Calibration failed: {e}")
    
    async def listen(self, timeout: int = 10) -> Optional[str]:
        """Listen for speech and return text"""
        try:
            self.logger.info("Ready to listen...")
            
            # Run blocking audio capture in thread pool
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(None, self._capture_audio, timeout)
            
            if audio:
                # Run blocking transcription in thread pool
                text = await loop.run_in_executor(None, self._transcribe_audio, audio)
                return text
                
        except Exception as e:
            self.logger.error(f"Speech recognition error: {e}")
        
        return None
    
    def _capture_audio(self, timeout: int) -> Optional[sr.AudioData]:
        """Capture audio from microphone"""
        try:
            with self.microphone as source:
                print("Listening... Speak now!")  # User feedback
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                print("Got it! Processing...")
                return audio
        except sr.WaitTimeoutError:
            print("No speech detected within timeout")
            return None
        except Exception as e:
            self.logger.error(f"Audio capture error: {e}")
            return None
    
    def _transcribe_audio(self, audio: sr.AudioData) -> Optional[str]:
        """Convert audio to text"""
        try:
            text = self.recognizer.recognize_google(audio, language="en-IN")
            return text
        except sr.UnknownValueError:
            print("Could not understand the audio")
            return None
        except sr.RequestError as e:
            self.logger.error(f"Speech service error: {e}")
            return None
    
    def cleanup(self):
        """Cleanup resources"""
        pass
