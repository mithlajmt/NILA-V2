"""
TTS Services Package
Multi-provider TTS support (gTTS, Google Cloud, Azure)
"""

from .tts_service import TTSService
from .base_tts_provider import BaseTTSProvider
from .gtts_provider import GTTSProvider
from .google_cloud_tts_provider import GoogleCloudTTSProvider

__all__ = [
    'TTSService',
    'BaseTTSProvider',
    'GTTSProvider',
    'GoogleCloudTTSProvider',
]
