"""
TTS Service Factory
Creates the appropriate TTS provider based on settings
"""

import logging
from typing import Optional
from .base_tts_provider import BaseTTSProvider
from .gtts_provider import GTTSProvider
from .openai_tts_provider import OpenAITTSProvider
from .piper_provider import PiperTTSProvider
from .elevenlabs_provider import ElevenLabsTTSProvider
from .edge_tts_provider import EdgeTTSProvider


class TTSService:
    """Factory for TTS providers"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.provider: Optional[BaseTTSProvider] = None
        
        # Playback Queue for non-blocking TTS
        import asyncio
        self.playback_queue = asyncio.Queue()
        self.worker_task = None
        
        # Create provider based on settings
        self._initialize_provider()
        
    async def start(self):
        """Start the background worker"""
        self._start_worker()
        
    def _start_worker(self):
        """Start the background playback worker"""
        import asyncio
        if self.worker_task is None or self.worker_task.done():
            # Ensure we have a running loop
            try:
                loop = asyncio.get_running_loop()
                self.worker_task = loop.create_task(self._playback_worker())
                self.logger.info("🎵 TTS Background Worker started")
            except RuntimeError:
                self.logger.error("❌ Could not start TTS worker: No event loop running")
            
    async def _playback_worker(self):
        """Worker that plays audio files from queue one by one"""
        import asyncio
        self.logger.info("🎵 TTS Worker ready to play")
        
        try:
            while True:
                # Get next item
                item = await self.playback_queue.get()
                audio_path, text = item
                
                try:
                    if self.provider and audio_path:
                        self.logger.debug(f"▶️ Playing queued item: {text[:20]}...")
                        from src.utils.latency import tracker
                        tracker.track("tts_playback_start", f"Playing: {text[:10]}...")
                        await self.provider.play_audio(audio_path)
                except Exception as e:
                    self.logger.error(f"❌ Playback error in worker: {e}")
                finally:
                    self.playback_queue.task_done()
                    
        except asyncio.CancelledError:
            self.logger.info("🛑 TTS Worker cancelled")
            
    def _initialize_provider(self):
        """Initialize the TTS provider based on settings"""
        provider_name = self.settings.TTS_PROVIDER.lower()
        
        self.logger.info(f"🔧 Initializing TTS provider: {provider_name}")
        
        try:
            if provider_name == "gtts":
                self.provider = GTTSProvider(self.settings)
                
            elif provider_name == "openai":
                self.provider = OpenAITTSProvider(self.settings)
            
            elif provider_name == "piper":
                self.provider = PiperTTSProvider(self.settings)
                
            elif provider_name == "elevenlabs":
                self.provider = ElevenLabsTTSProvider(self.settings)
                
            elif provider_name == "edge":
                self.provider = EdgeTTSProvider(self.settings)
                
            elif provider_name == "google_cloud":
                from .google_cloud_tts_provider import GoogleCloudTTSProvider
                self.provider = GoogleCloudTTSProvider(self.settings)
                
            elif provider_name == "azure":
                # Future: Azure TTS provider
                self.logger.error("❌ Azure provider not yet implemented")
                raise NotImplementedError("Azure TTS provider coming soon!")
                
            else:
                self.logger.warning(f"⚠️ Unknown TTS provider: {provider_name}, falling back to gTTS")
                self.provider = GTTSProvider(self.settings)
            
            self.logger.info(f"✅ TTS Service ready: {self.provider.get_provider_name()}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize TTS provider: {e}")
            self.logger.info("   Falling back to gTTS...")
            
            try:
                self.provider = GTTSProvider(self.settings)
                self.logger.info(f"✅ Fallback TTS ready: {self.provider.get_provider_name()}")
            except Exception as fallback_error:
                self.logger.error(f"❌ Even fallback failed: {fallback_error}")
                raise
    
    async def speak(self, text: str, language: Optional[str] = None) -> bool:
        """
        Convert text to speech and play (Non-blocking / Queued)
        
        This method returns IMMEDIATELY after generation starts.
        Playback happens in the background.
        
        Args:
            text: The text to speak
            language: Language code ('en', 'ml') or None for auto-detect
            
        Returns:
            True if queued successfully, False if failed to generate
        """
        from src.utils.latency import tracker
        
        if not self.provider:
            self.logger.error("❌ No TTS provider initialized")
            return False
        
        # 1. Generate Audio (this might take 0.2s - 1.0s)
        # We await generation to ensure we don't queue invalid files
        # But this is still much faster than waiting for playback (3s-10s)
        try:
            tracker.track("tts_generation_start", f"Generating: {text[:20]}...")
            audio_path = await self.provider.generate_audio(text, language)
            tracker.track("tts_audio_ready")
            
            if audio_path:
                # 2. Add to Queue (Instant)
                self.playback_queue.put_nowait((audio_path, text))
                tracker.track("tts_request_queued")
                return True
            else:
                return False
        except Exception as e:
             self.logger.error(f"❌ TTS Generation error: {e}")
             return False

    def stop_speaking(self):
        """Stop current speech and clear queue"""
        # 1. Clear queue
        while not self.playback_queue.empty():
            try:
                self.playback_queue.get_nowait()
                self.playback_queue.task_done()
            except:
                break
                
        # 2. Stop current provider playback
        if self.provider:
            self.provider.stop_speaking()
    
    def cleanup(self):
        """Cleanup resources"""
        # Cancel worker
        if self.worker_task:
            self.worker_task.cancel()
            
        if self.provider:
            self.provider.cleanup()
    
    def get_provider_info(self) -> str:
        """Get information about current provider"""
        if self.provider:
            return self.provider.get_provider_name()
        return "No provider"
    
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        if self.provider:
            return self.provider.is_speaking
        return False
        
    async def wait_until_done(self):
        """Wait until all queued audio is finished playing"""
        if self.playback_queue:
            await self.playback_queue.join()
    
    def switch_provider(self, new_provider: str):
        """
        Switch to a different TTS provider
        
        Args:
            new_provider: Name of the new provider (gtts, openai, google_cloud, azure, piper, elevenlabs, edge)
        """
        self.logger.info(f"🔄 Switching provider from {self.settings.TTS_PROVIDER} to {new_provider}")
        
        # Cleanup old provider
        if self.provider:
            self.provider.cleanup()
        
        # Update settings
        self.settings.TTS_PROVIDER = new_provider
        
        # Reinitialize provider
        self._initialize_provider()
