"""
Deepgram Streaming Speech-to-Text Provider
Real-time transcription using WebSocket connection

This is MUCH faster than the batch API:
- Batch API: Wait for full audio → upload → transcribe (2-4s)
- Streaming API: Send chunks → get partial results (200-500ms)
"""
import asyncio
import logging
from typing import Optional, AsyncGenerator

from src.services.speech.base_stt_provider import STTStreamResult


class DeepgramStreamingProvider:
    """
    Deepgram Live Streaming STT Provider
    
    Features:
    - WebSocket-based real-time transcription
    - Partial results (see text as user speaks)
    - Automatic sentence boundary detection
    - Low latency (200-500ms first result)
    
    Compatible with async audio streaming from AudioCapture
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str = "en-US",
        smart_format: bool = True,
        interim_results: bool = True,
        endpointing: int = 300  # ms of silence to detect sentence end
    ):
        """
        Initialize Deepgram streaming provider
        
        Args:
            api_key: Deepgram API key
            model: Model to use ("nova-2" is fastest + most accurate)
            language: Language code (e.g., "ml-IN", "en-US") or None for auto-detect
            smart_format: Enable smart formatting (punctuation, capitalization)
            interim_results: Get partial transcripts while user is speaking
            endpointing: Milliseconds of silence to detect sentence end
        """
        self.api_key = api_key
        self.model = model
        self.language = language if language != "auto" else None
        self.smart_format = smart_format
        self.interim_results = interim_results
        self.endpointing = endpointing
        self.logger = logging.getLogger(__name__)
        
        # Initialize Deepgram client
        try:
            from deepgram import (
                DeepgramClient,
                DeepgramClientOptions,
                LiveTranscriptionEvents,
                LiveOptions
            )
            
            self.DeepgramClient = DeepgramClient
            self.LiveTranscriptionEvents = LiveTranscriptionEvents
            self.LiveOptions = LiveOptions
            
            # Create client with options
            config = DeepgramClientOptions(
                options={"keepalive": "true"}
            )
            self.client = DeepgramClient(api_key, config)
            
            self.logger.info(
                f"✅ Deepgram Streaming initialized (model={model}, lang={language or 'auto'})"
            )
        except ImportError:
            self.logger.error(
                "❌ Deepgram SDK not installed. Run: pip install deepgram-sdk>=3.0.0"
            )
            raise
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Deepgram client: {e}")
            raise
    
    async def stream_transcribe(
        self,
        audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[STTStreamResult, None]:
        """
        Stream audio to Deepgram and get real-time transcripts
        
        Args:
            audio_stream: Async generator yielding audio chunks (bytes)
            
        Yields:
            STTStreamResult with partial/final transcripts
        """
        connection = None
        
        try:
            self.logger.info("🎯 Starting Deepgram WebSocket connection...")
            
            # Create live transcription connection
            connection = self.client.listen.asynclive.v("1")
            
            # Configure options
            options = self.LiveOptions(
                model=self.model,
                language=self.language,
                smart_format=self.smart_format,
                interim_results=self.interim_results,
                endpointing=self.endpointing,
                punctuate=True,
                encoding="linear16",
                sample_rate=16000,
                channels=1
            )
            
            # Queue to collect transcripts from callbacks
            transcript_queue = asyncio.Queue()
            
            # Event handlers
            async def on_message(self, result, **kwargs):
                """Handle incoming transcription results"""
                try:
                    sentence = result.channel.alternatives[0].transcript
                    
                    if len(sentence) > 0:
                        is_final = result.is_final
                        confidence = result.channel.alternatives[0].confidence
                        
                        stream_result = STTStreamResult(
                            text=sentence,
                            is_final=is_final,
                            confidence=confidence,
                            language=self.language
                        )
                        
                        await transcript_queue.put(stream_result)
                        
                        if is_final:
                            self.logger.info(f"✅ Final: '{sentence}' (confidence: {confidence:.2f})")
                        else:
                            self.logger.debug(f"🔄 Partial: '{sentence}'")
                            
                except Exception as e:
                    self.logger.error(f"❌ Error processing transcript: {e}")
            
            async def on_error(self, error, **kwargs):
                """Handle errors"""
                self.logger.error(f"❌ Deepgram error: {error}")
                await transcript_queue.put(None)  # Signal error
            
            async def on_close(self, **kwargs):
                """Handle connection close"""
                self.logger.info("🔌 Deepgram connection closed")
                await transcript_queue.put(None)  # Signal completion
            
            # Register event handlers
            connection.on(self.LiveTranscriptionEvents.Transcript, on_message)
            connection.on(self.LiveTranscriptionEvents.Error, on_error)
            connection.on(self.LiveTranscriptionEvents.Close, on_close)
            
            # Start connection
            if await connection.start(options) is False:
                raise Exception("Failed to start Deepgram connection")
            
            self.logger.info("✅ Deepgram WebSocket connected")
            
            # Task to send audio chunks
            async def send_audio():
                try:
                    async for chunk in audio_stream:
                        await connection.send(chunk)
                    
                    # Signal end of audio
                    await connection.finish()
                    self.logger.info("📤 Audio stream finished")
                    
                except Exception as e:
                    self.logger.error(f"❌ Error sending audio: {e}")
                    await transcript_queue.put(None)
            
            # Start sending audio in background
            send_task = asyncio.create_task(send_audio())
            
            # Yield transcripts as they arrive
            final_text = None
            while True:
                result = await transcript_queue.get()
                
                if result is None:
                    # Connection closed or error
                    break
                
                yield result
                
                if result.is_final:
                    final_text = result.text
            
            # Wait for send task to complete
            await send_task
            
            if final_text:
                self.logger.info(f"🎉 Transcription complete: '{final_text}'")
            else:
                self.logger.warning("⚠️ No final transcript received")
                
        except Exception as e:
            self.logger.error(f"❌ Streaming transcription error: {e}")
            raise
            
        finally:
            # Cleanup connection
            if connection:
                try:
                    await connection.finish()
                except:
                    pass
