"""
Soniox Streaming Speech-to-Text Provider
Real-time transcription using WebSocket connection

Soniox offers excellent Malayalam support with 10.7% WER
(compared to Google's 42.2% and Deepgram's lack of support)

Features:
- Ultra-low latency real-time transcription
- Excellent multilingual support including Malayalam
- Speaker diarization
- Language identification
"""
import asyncio
import logging
import json
from typing import Optional, AsyncGenerator

from src.services.speech.base_stt_provider import STTStreamResult

try:
    import websockets
except ImportError:
    websockets = None


class SonioxStreamingProvider:
    """
    Soniox Live Streaming STT Provider
    
    Features:
    - WebSocket-based real-time transcription
    - Excellent Malayalam support (10.7% WER)
    - Partial results (see text as user speaks)
    - Speaker diarization support
    - Low latency streaming
    """
    
    WEBSOCKET_URL = "wss://stt-rt.soniox.com/transcribe-websocket"
    
    def __init__(
        self,
        api_key: str,
        model: str = "stt-rt-preview",
        language_hints: Optional[list] = None,
        enable_speaker_diarization: bool = False,
        enable_endpoint_detection: bool = True
    ):
        """
        Initialize Soniox streaming provider
        
        Args:
            api_key: Soniox API key
            model: Model to use ("stt-rt-preview" for real-time)
            language_hints: List of language codes (e.g., ["ml", "en"] for Malayalam + English)
            enable_speaker_diarization: Enable speaker separation
            enable_endpoint_detection: Enable automatic endpoint detection
        """
        if websockets is None:
            raise ImportError("websockets package required. Run: pip install websockets")
        
        self.api_key = api_key
        self.model = model
        self.language_hints = language_hints or ["ml", "en"]  # Default: Malayalam + English
        self.enable_speaker_diarization = enable_speaker_diarization
        self.enable_endpoint_detection = enable_endpoint_detection
        self.logger = logging.getLogger(__name__)
        
        # Connection state
        self._ws = None
        self._is_connected = False
        
        self.logger.info(
            f"✅ Soniox Streaming initialized (model={model}, langs={self.language_hints})"
        )
    
    async def stream_transcribe(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        timeout: float = 30.0
    ) -> AsyncGenerator[STTStreamResult, None]:
        """
        Stream audio to Soniox and get real-time transcripts
        
        Args:
            audio_stream: Async generator yielding audio chunks (16-bit PCM, 16kHz, mono)
            timeout: Maximum time to wait for transcription
            
        Yields:
            STTStreamResult with partial/final transcripts
        """
        ws = None
        send_task = None
        
        # State tracking
        response_queue: asyncio.Queue = asyncio.Queue()
        audio_finished = asyncio.Event()
        connection_closed = asyncio.Event()
        accumulated_text = []
        
        provider = self
        
        try:
            self.logger.info("🎯 Starting Soniox WebSocket connection...")
            
            # Connect to Soniox WebSocket
            ws = await websockets.connect(
                self.WEBSOCKET_URL,
                ping_interval=20,
                ping_timeout=10
            )
            self._ws = ws
            self._is_connected = True
            
            self.logger.info("✅ Soniox WebSocket connected")
            
            # Send configuration message
            config = {
                "api_key": self.api_key,
                "model": self.model,
                "audio_format": "pcm_s16le",
                "sample_rate": 16000,
                "num_channels": 1,
                "language_hints": self.language_hints,
                "enable_speaker_diarization": self.enable_speaker_diarization,
                "enable_endpoint_detection": self.enable_endpoint_detection,
                "enable_language_identification": True
            }
            
            await ws.send(json.dumps(config))
            self.logger.info(f"📤 Sent config: model={self.model}, langs={self.language_hints}")
            
            # ============================================================
            # Response Receiver Task
            # ============================================================
            async def receive_responses():
                """Receive and process responses from Soniox"""
                try:
                    async for message in ws:
                        try:
                            response = json.loads(message)
                            
                            # Check for errors
                            if "error_code" in response:
                                provider.logger.error(
                                    f"❌ Soniox error {response['error_code']}: {response.get('error_message', 'Unknown')}"
                                )
                                await response_queue.put(None)
                                break
                            
                            # Check for finished
                            if response.get("finished"):
                                provider.logger.info("🏁 Soniox stream finished")
                                await response_queue.put(None)
                                break
                            
                            # Process tokens
                            tokens = response.get("tokens", [])
                            if tokens:
                                # Build text from tokens
                                final_tokens = [t for t in tokens if t.get("is_final")]
                                non_final_tokens = [t for t in tokens if not t.get("is_final")]
                                
                                # Yield final results
                                if final_tokens:
                                    final_text = "".join(t.get("text", "") for t in final_tokens)
                                    if final_text.strip():
                                        confidence = sum(t.get("confidence", 0) for t in final_tokens) / len(final_tokens)
                                        language = final_tokens[0].get("language", "ml")
                                        
                                        result = STTStreamResult(
                                            text=final_text.strip(),
                                            is_final=True,
                                            confidence=confidence,
                                            language=language
                                        )
                                        await response_queue.put(result)
                                        provider.logger.info(f"✅ Final: '{final_text.strip()}'")
                                
                                # Yield partial results
                                if non_final_tokens:
                                    partial_text = "".join(t.get("text", "") for t in non_final_tokens)
                                    if partial_text.strip():
                                        result = STTStreamResult(
                                            text=partial_text.strip(),
                                            is_final=False,
                                            confidence=0.0,
                                            language=non_final_tokens[0].get("language", "ml")
                                        )
                                        await response_queue.put(result)
                                        provider.logger.debug(f"🔄 Partial: '{partial_text.strip()}'")
                                        
                        except json.JSONDecodeError as e:
                            provider.logger.error(f"❌ Failed to parse response: {e}")
                            
                except websockets.exceptions.ConnectionClosed:
                    provider.logger.info("🔌 Soniox WebSocket closed")
                except Exception as e:
                    provider.logger.error(f"❌ Receive error: {e}")
                finally:
                    connection_closed.set()
                    await response_queue.put(None)
            
            # ============================================================
            # Audio Sending Task
            # ============================================================
            async def send_audio():
                """Send audio chunks to Soniox"""
                chunks_sent = 0
                bytes_sent = 0
                try:
                    async for chunk in audio_stream:
                        if connection_closed.is_set():
                            provider.logger.warning("⚠️ Connection closed, stopping audio send")
                            break
                        await ws.send(chunk)
                        chunks_sent += 1
                        bytes_sent += len(chunk)
                    
                    provider.logger.info(f"📤 Audio stream finished ({chunks_sent} chunks, {bytes_sent} bytes)")
                    audio_finished.set()
                    
                    # Send empty frame to signal end of audio
                    if not connection_closed.is_set():
                        await ws.send(b"")
                        provider.logger.info("📤 Sent end-of-stream signal")
                    
                except asyncio.CancelledError:
                    provider.logger.info("📤 Audio send cancelled")
                    raise
                except Exception as e:
                    provider.logger.error(f"❌ Error sending audio: {e}")
            
            # Start tasks
            receive_task = asyncio.create_task(receive_responses())
            send_task = asyncio.create_task(send_audio())
            
            # ============================================================
            # Yield Results
            # ============================================================
            final_text = None
            
            while True:
                try:
                    # Wait for result with timeout
                    wait_timeout = 5.0 if audio_finished.is_set() else timeout
                    result = await asyncio.wait_for(
                        response_queue.get(),
                        timeout=wait_timeout
                    )
                    
                    if result is None:
                        break
                    
                    yield result
                    
                    if result.is_final:
                        accumulated_text.append(result.text)
                        final_text = result.text
                        
                except asyncio.TimeoutError:
                    if audio_finished.is_set():
                        self.logger.info("⏱️ Timeout after audio finished")
                        break
                    continue
            
            # Wait for tasks to complete
            for task in [send_task, receive_task]:
                if task and not task.done():
                    try:
                        await asyncio.wait_for(task, timeout=2.0)
                    except asyncio.TimeoutError:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
            
            # Log completion
            if accumulated_text:
                full_text = " ".join(accumulated_text)
                self.logger.info(f"🎉 Transcription complete: '{full_text}'")
            else:
                self.logger.warning("⚠️ No transcript received")
                
        except Exception as e:
            self.logger.error(f"❌ Streaming error: {e}")
            import traceback
            traceback.print_exc()
            raise
            
        finally:
            self._is_connected = False
            
            # Cancel tasks
            if send_task and not send_task.done():
                send_task.cancel()
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass
            
            # Close WebSocket
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass
            
            self._ws = None
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self._is_connected
    
    async def close(self):
        """Close the connection"""
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._is_connected = False
            self._ws = None
