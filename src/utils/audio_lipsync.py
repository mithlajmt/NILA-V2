"""
Audio Lip Sync utility for NILA-V2.

Extracts real-time amplitude envelopes from audio files (WAV, MP3, etc.)
and synchronizes jaw servo movements proportionally to speech volume.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Callable, List, Optional

import pygame

logger = logging.getLogger(__name__)

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


def extract_amplitude_envelope(audio_file: Path, chunk_ms: int = 40) -> List[int]:
    """
    Extract normalized amplitude envelope (0-100) from an audio file.
    Returns a list of intensity values where each element represents `chunk_ms` milliseconds.
    """
    if not PYDUB_AVAILABLE or not audio_file.exists():
        return []

    try:
        # Load audio file (supports MP3, WAV, etc. via ffmpeg)
        seg = AudioSegment.from_file(str(audio_file))
        seg = seg.set_channels(1)  # Convert to mono for amplitude calculation

        num_chunks = int(len(seg) / chunk_ms) + 1
        rms_values = []

        for i in range(num_chunks):
            start = i * chunk_ms
            end = min(len(seg), (i + 1) * chunk_ms)
            if start >= len(seg):
                break
            chunk = seg[start:end]
            rms_values.append(chunk.rms)

        if not rms_values:
            return []

        # Find noise floor and maximum peak
        max_rms = max(rms_values)
        if max_rms <= 0:
            return [0] * len(rms_values)

        # Dynamic range mapping with noise gate
        noise_floor = max_rms * 0.08  # 8% threshold for silence between syllables
        intensities = []

        for rms in rms_values:
            if rms < noise_floor:
                intensities.append(0)
            else:
                # Normalize above noise floor
                norm = (rms - noise_floor) / (max_rms - noise_floor)
                # Map to 0-100 with non-linear curve for expressive speech
                intensity = int(min(100.0, max(0.0, (norm ** 0.85) * 100.0)))
                intensities.append(intensity)

        return intensities

    except Exception as e:
        logger.warning(f"Could not extract amplitude envelope from {audio_file}: {e}")
        return []


async def play_audio_with_lipsync(
    audio_file: Path,
    is_speaking_check: Optional[Callable[[], bool]] = None,
    on_intensity: Optional[Callable[[int], None]] = None,
    chunk_ms: int = 40,
):
    """
    Play an audio file via pygame mixer while streaming real-time intensity updates to jaw.
    """
    try:
        from src.services.hardware.jaw_controller import JawController
        jaw = JawController()
    except Exception:
        jaw = None

    intensity_callback = on_intensity or (jaw.set_intensity if jaw else None)

    # Extract amplitude envelope before playback
    intensities = extract_amplitude_envelope(audio_file, chunk_ms=chunk_ms)

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)

        pygame.mixer.music.load(str(audio_file))
        pygame.mixer.music.play()
        start_time = time.time()

        while pygame.mixer.music.get_busy():
            if is_speaking_check and not is_speaking_check():
                pygame.mixer.music.stop()
                break

            elapsed_ms = int((time.time() - start_time) * 1000)
            idx = elapsed_ms // chunk_ms

            if intensities and idx < len(intensities):
                current_intensity = intensities[idx]
            else:
                current_intensity = 0

            if intensity_callback:
                intensity_callback(current_intensity)

            await asyncio.sleep(chunk_ms / 1000.0 * 0.85)

    except Exception as err:
        logger.error(f"Error in play_audio_with_lipsync: {err}")
    finally:
        # Ensure jaw closes firmly at end of speech
        if intensity_callback:
            intensity_callback(0)
        if jaw:
            jaw.close_jaw()

