import logging
import pygame
import os
from pathlib import Path
import threading
import time

class FeedbackService:
    """
    Manages audio/visual feedback for the robot.
    Scalable design to add LED patterns or other feedback types later.
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.is_thinking = False
        self._stop_event = threading.Event()
        self._thread = None
        
        # Audio setup
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.audio_enabled = True
        except Exception as e:
            self.logger.warning(f"⚠️ Feedback audio disabled: {e}")
            self.audio_enabled = False
            
        # Assets
        self.assets_dir = Path("data/audio/sfx")
        self.thinking_sound = self.assets_dir / "thinking.wav"

        # EventBus Integration
        from src.core.event_bus import EventBus
        self.event_bus = EventBus()
        self.event_bus.subscribe("brain.thinking", self._handle_thinking_event)

    def _handle_thinking_event(self, event):
        """EventBus handler for brain thinking state"""
        is_thinking = getattr(event, "is_thinking", False)
        if is_thinking:
            self.start_thinking()
        else:
            self.stop_thinking()
        
    def start_thinking(self):
        """Start the 'thinking' feedback loop"""
        if self.is_thinking:
            return
            
        self.is_thinking = True
        self._stop_event.clear()
        
        # Start feedback thread
        self._thread = threading.Thread(target=self._thinking_loop)
        self._thread.daemon = True
        self._thread.start()
        self.logger.info("🤔 Started thinking feedback")
        
    def stop_thinking(self):
        """Stop the 'thinking' feedback"""
        if not self.is_thinking:
            return
            
        self.is_thinking = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
            
        # Stop audio immediately
        if self.audio_enabled:
            pygame.mixer.music.stop()
            
        self.logger.info("💡 Stopped thinking feedback")
        
    def _thinking_loop(self):
        """Loop to play random thinking sounds"""
        import random
        
        thinking_dir = self.assets_dir / "thinking"
        
        try:
            while not self._stop_event.is_set():
                if self.audio_enabled and thinking_dir.exists():
                    # Get all audio files (wav and mp3)
                    sounds = list(thinking_dir.glob("*.wav")) + list(thinking_dir.glob("*.mp3"))
                    
                    if sounds:
                        # Pick a random sound (though now there's likely only one)
                        sound_file = random.choice(sounds)
                        
                        # Play it
                        try:
                            pygame.mixer.music.load(str(sound_file))
                            pygame.mixer.music.play()
                            
                            # Wait while playing
                            while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                                time.sleep(0.1)
                                
                        except Exception as e:
                            self.logger.error(f"❌ Error playing thinking sound: {e}")
                    
                    # Small pause before repeating if still thinking
                    time.sleep(0.5)
                else:
                    time.sleep(0.5)
                
        except Exception as e:
            self.logger.error(f"❌ Feedback loop error: {e}")
            
    def play_sound(self, sound_name: str):
        """Play a one-shot sound effect"""
        if not self.audio_enabled:
            return
            
        try:
            sound_path = self.assets_dir / f"{sound_name}.wav"
            if sound_path.exists():
                sound = pygame.mixer.Sound(str(sound_path))
                sound.play()
        except Exception as e:
            self.logger.error(f"❌ Failed to play sound {sound_name}: {e}")

    def cleanup(self):
        self.stop_thinking()
        if self.audio_enabled:
            pygame.mixer.quit()
