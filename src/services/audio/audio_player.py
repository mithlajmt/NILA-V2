"""
Audio Player Service
Handles audio playback and amplitude analysis for hardware synchronization.
"""

import asyncio
import logging
import wave
import audioop
import time
import pygame
from pathlib import Path
from typing import Optional, Callable

class AudioPlayer:
    """
    Handles audio playback using Pygame and calculates real-time amplitude
    for hardware synchronization (e.g., jaw movement).
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_playing = False
        
        # Initialize pygame mixer
        try:
            # Standard init, can be adjusted if needed
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
            self.logger.info("✅ AudioPlayer initialized")
        except Exception as e:
            self.logger.error(f"❌ Pygame mixer init failed: {e}")

    async def play(self, file_path: Path, on_amplitude_update: Optional[Callable[[int], None]] = None):
        """
        Play an audio file and optionally trigger a callback with amplitude data.
        
        Args:
            file_path: Path to the audio file (WAV/MP3)
            on_amplitude_update: Callback function(intensity: int) -> None
        """
        if not file_path.exists():
            self.logger.error(f"❌ Audio file not found: {file_path}")
            return

        try:
            self.is_playing = True
            
            # Start audio playback
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()
            
            # If no callback or not a WAV file (harder to read chunks from MP3 directly without decoding),
            # just wait for playback.
            # Note: For MP3s, we might need to decode to PCM first if we want accurate lip sync,
            # or just use a fake "talking" animation. 
            # For now, assuming WAV for high quality lip sync (Piper produces WAV).
            # GTTS produces MP3.
            
            is_wav = file_path.suffix.lower() == '.wav'
            
            if on_amplitude_update and is_wav:
                await self._play_with_analysis(file_path, on_amplitude_update)
            else:
                # Just wait for playback to finish
                while pygame.mixer.music.get_busy() and self.is_playing:
                    await asyncio.sleep(0.1)
                    
            self.is_playing = False
            
            # Ensure jaw is closed at the end if callback exists
            if on_amplitude_update:
                on_amplitude_update(0)
                
        except Exception as e:
            self.logger.error(f"❌ Error playing audio: {e}")
            self.is_playing = False
            if on_amplitude_update:
                on_amplitude_update(0)

    async def _play_with_analysis(self, file_path: Path, callback: Callable[[int], None]):
        """Internal method to handle WAV playback with amplitude analysis"""
        try:
            start_time = time.time()
            
            with wave.open(str(file_path), 'rb') as wf:
                framerate = wf.getframerate()
                sampwidth = wf.getsampwidth()
                
                # Calculate chunk size for ~50ms updates
                chunk_ms = 50
                chunk_size = int(framerate * chunk_ms / 1000)
                
                while pygame.mixer.music.get_busy() and self.is_playing:
                    # Calculate current position
                    elapsed = time.time() - start_time
                    current_frame = int(elapsed * framerate)
                    
                    # Seek and read
                    if current_frame < wf.getnframes():
                        wf.setpos(current_frame)
                        data = wf.readframes(chunk_size)
                        
                        if data:
                            rms = audioop.rms(data, sampwidth)
                            
                            # Normalize (adjust scaling factor as needed)
                            # Lower factor = more sensitive
                            scaling_factor = 2000 
                            intensity = min(100, int((rms / scaling_factor) * 100))
                            
                            callback(intensity)
                    
                    await asyncio.sleep(0.05)
                    
        except Exception as e:
            self.logger.error(f"❌ Amplitude analysis error: {e}")

    def stop(self):
        """Stop playback"""
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False

    def cleanup(self):
        """Cleanup resources"""
        self.stop()
        try:
            pygame.mixer.quit()
        except:
            pass
