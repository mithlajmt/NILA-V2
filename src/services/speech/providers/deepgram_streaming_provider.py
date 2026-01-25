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
        endpointing: int = 300,  # ms of silence to detect sentence end
        utterance_end_ms: int = 1000  # ms to wait for utterance end after speech
    ):
        """
        Initialize Deepgram streaming provider
        
        Args:
            api_key: Deepgram API key
            model: Model to use ("nova-2" is fastest + most accurate)
            language: Language code (e.g., "ml", "en-US", "hi") or "multi" for multilingual
            smart_format: Enable smart formatting (punctuation, capitalization)
            interim_results: Get partial transcripts while user is speaking
            endpointing: Milliseconds of silence to detect sentence end
            utterance_end_ms: Milliseconds to wait for utterance end signal
        """
        self.api_key = api_key
        self.model = model
        # Handle language - use None for auto-detect, or specific language
        if language in ("auto", "multi", ""):
            self.language = None  # Auto-detect
        else:
            self.language = language
        self.smart_format = smart_format
        self.interim_results = interim_results
        self.endpointing = endpointing
        self.utterance_end_ms = utterance_end_ms
        self.logger = logging.getLogger(__name__)
        
        # Connection state
        self._connection = None
        self._is_connected = False
        
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
        audio_stream: AsyncGenerator[bytes, None],
        timeout: float = 30.0
    ) -> AsyncGenerator[STTStreamResult, None]:
        """
        Stream audio to Deepgram and get real-time transcripts
        
        Args:
            audio_stream: Async generator yielding audio chunks (bytes)
            timeout: Maximum time to wait for transcription after audio ends
            
        Yields:
            STTStreamResult with partial/final transcripts
        """
        connection = None
        send_task = None
        
        # State tracking
        transcript_queue: asyncio.Queue = asyncio.Queue()
        audio_finished = asyncio.Event()
        connection_closed = asyncio.Event()
        got_any_transcript = False
        accumulated_text = []
        
        # Capture provider instance for use in callbacks
        provider = self
        
        try:
            self.logger.info("🎯 Starting Deepgram WebSocket connection...")
            
            # Create live transcription connection
            connection = self.client.listen.asynclive.v("1")
            self._connection = connection
            
            # Configure options
            # Note: If language is None, Deepgram will auto-detect
            options_dict = {
                "model": self.model,
                "smart_format": self.smart_format,
                "interim_results": self.interim_results,
                "endpointing": self.endpointing,
                "utterance_end_ms": self.utterance_end_ms,
                "punctuate": True,
                "encoding": "linear16",
                "sample_rate": 16000,
                "channels": 1
            }
            
            # Only add language if specified (otherwise auto-detect)
            if self.language:
                options_dict["language"] = self.language
            
            options = self.LiveOptions(**options_dict)
            
            # ============================================================
            # Event Handlers - Using *args, **kwargs for SDK compatibility
            # ============================================================
            
            async def on_open(*args, **kwargs):
                """Handle connection open"""
                provider.logger.info("🔌 Deepgram WebSocket opened")
                provider._is_connected = True
            
            async def on_message(*args, **kwargs):
                """Handle incoming transcription results"""
                nonlocal got_any_transcript
                try:
                    # Extract result from args
                    result = None
                    for arg in args:
                        if hasattr(arg, 'channel'):
                            result = arg
                            break
                    
                    # Also check kwargs
                    if result is None:
                        result = kwargs.get('result')
                    
                    if result is None:
                        provider.logger.debug(f"📩 on_message called but no result found. args={len(args)}, kwargs={list(kwargs.keys())}")
                        return
                    
                    # Safety check for valid result structure
                    if not hasattr(result, 'channel') or not result.channel:
                        provider.logger.debug("📩 Result has no channel")
                        return
                    if not result.channel.alternatives:
                        provider.logger.debug("📩 Result has no alternatives")
                        return
                    
                    sentence = result.channel.alternatives[0].transcript
                    
                    # Log every message for debugging
                    is_final = getattr(result, 'is_final', False)
                    provider.logger.debug(f"📩 Transcript: '{sentence}' (final={is_final})")
                    
                    if len(sentence) > 0:
                        got_any_transcript = True
                        confidence = result.channel.alternatives[0].confidence or 0.0
                        
                        stream_result = STTStreamResult(
                            text=sentence,
                            is_final=is_final,
                            confidence=confidence,
                            language=provider.language
                        )
                        
                        await transcript_queue.put(stream_result)
                        
                        if is_final:
                            accumulated_text.append(sentence)
                            provider.logger.info(f"✅ Final: '{sentence}' (confidence: {confidence:.2f})")
                        else:
                            provider.logger.info(f"🔄 Partial: '{sentence}'")
                            
                except Exception as e:
                    provider.logger.error(f"❌ Error processing transcript: {e}")
                    import traceback
                    traceback.print_exc()
            
            async def on_utterance_end(*args, **kwargs):
                """Handle utterance end - user stopped speaking"""
                provider.logger.info("🔇 Utterance end detected")
            
            async def on_speech_started(*args, **kwargs):
                """Handle speech start detection"""
                provider.logger.info("🎙️ Deepgram detected speech start")
            
            async def on_metadata(*args, **kwargs):
                """Handle metadata"""
                provider.logger.debug(f"📊 Metadata received")
            
            async def on_error(*args, **kwargs):
                """Handle errors"""
                # Try to extract error from args
                error = args[1] if len(args) > 1 else kwargs.get('error', 'Unknown error')
                provider.logger.error(f"❌ Deepgram error: {error}")
                # Don't immediately close - let the loop handle it
            
            async def on_close(*args, **kwargs):
                """Handle connection close"""
                provider.logger.info("🔌 Deepgram connection closed")
                provider._is_connected = False
                connection_closed.set()
                await transcript_queue.put(None)  # Signal completion
            
            # Register all event handlers
            connection.on(self.LiveTranscriptionEvents.Open, on_open)
            connection.on(self.LiveTranscriptionEvents.Transcript, on_message)
            connection.on(self.LiveTranscriptionEvents.Error, on_error)
            connection.on(self.LiveTranscriptionEvents.Close, on_close)
            
            # Start connection
            started = await connection.start(options)
            if started is False:
                raise Exception("Failed to start Deepgram connection")
            
            self.logger.info("✅ Deepgram WebSocket connected")
            self._is_connected = True
            
            # ============================================================
            # Audio Sending Task
            # ============================================================
            async def send_audio():
                """Send audio chunks to Deepgram"""
                chunks_sent = 0
                bytes_sent = 0
                try:
                    async for chunk in audio_stream:
                        if connection_closed.is_set():
                            provider.logger.warning("⚠️ Connection closed, stopping audio send")
                            break
                        await connection.send(chunk)
                        chunks_sent += 1
                        bytes_sent += len(chunk)
                    
                    provider.logger.info(f"📤 Audio stream finished ({chunks_sent} chunks, {bytes_sent} bytes)")
                    audio_finished.set()
                    
                    # Give Deepgram time to process before signaling finish
                    # This is important - Deepgram needs time to process the audio
                    await asyncio.sleep(0.5)
                    
                    # Signal to Deepgram that we're done sending audio
                    if not connection_closed.is_set():
                        try:
                            await connection.finish()
                            provider.logger.info("📤 Sent finish signal to Deepgram")
                        except Exception as e:
                            provider.logger.debug(f"Finish signal note: {e}")
                    
                except asyncio.CancelledError:
                    provider.logger.info("📤 Audio send cancelled")
                    raise
                except Exception as e:
                    provider.logger.error(f"❌ Error sending audio: {e}")
            
            # Start sending audio in background
            send_task = asyncio.create_task(send_audio())
            
            # ============================================================
            # Yield Transcripts with Timeout Protection
            # ============================================================
            final_text = None
            
            while True:
                try:
                    # Wait for result with timeout
                    # Use longer timeout after audio finishes to allow Deepgram to process
                    if audio_finished.is_set():
                        wait_timeout = 5.0  # Give Deepgram 5 seconds after audio ends
                    else:
                        wait_timeout = timeout
                    
                    result = await asyncio.wait_for(
                        transcript_queue.get(),
                        timeout=wait_timeout
                    )
                    
                    if result is None:
                        # Connection closed
                        self.logger.debug("Received None from queue - connection closed")
                        break
                    
                    yield result
                    
                    if result.is_final:
                        final_text = result.text
                        
                except asyncio.TimeoutError:
                    if audio_finished.is_set():
                        # Audio done and no more results coming
                        self.logger.info("⏱️ Timeout waiting for transcripts after audio finished")
                        break
                    else:
                        # Still waiting for audio, continue
                        continue
            
            # Wait for send task to complete
            if send_task and not send_task.done():
                try:
                    await asyncio.wait_for(send_task, timeout=2.0)
                except asyncio.TimeoutError:
                    send_task.cancel()
                    try:
                        await send_task
                    except asyncio.CancelledError:
                        pass
            
            # Log completion status
            if accumulated_text:
                full_text = " ".join(accumulated_text)
                self.logger.info(f"🎉 Transcription complete: '{full_text}'")
            elif final_text:
                self.logger.info(f"🎉 Transcription complete: '{final_text}'")
            elif got_any_transcript:
                self.logger.info("🎉 Got partial transcripts but no final")
            else:
                self.logger.warning("⚠️ No final transcript received")
                self.logger.warning("   Possible causes: wrong language, no speech detected, or API issue")
                
        except asyncio.CancelledError:
            self.logger.info("🚫 Streaming transcription cancelled")
            raise
        except Exception as e:
            self.logger.error(f"❌ Streaming transcription error: {e}")
            import traceback
            traceback.print_exc()
            raise
            
        finally:
            # ============================================================
            # Cleanup
            # ============================================================
            self._is_connected = False
            
            # Cancel send task if still running
            if send_task and not send_task.done():
                send_task.cancel()
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass
            
            # Close connection gracefully
            if connection and not connection_closed.is_set():
                try:
                    await connection.finish()
                except Exception:
                    pass
            
            self._connection = None
    
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected"""
        return self._is_connected
    
    async def close(self):
        """Manually close the connection"""
        if self._connection and self._is_connected:
            try:
                await self._connection.finish()
            except Exception:
                pass
            self._is_connected = False
            self._connection = None
