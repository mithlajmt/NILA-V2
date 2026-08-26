"""
Google Gemini Live Real-time WebSocket Provider for NILA-V2
-----------------------------------------------------------
Production full-duplex Speech-to-Speech engine.
Features:
- Sub-300ms bidirectional streaming over WebSockets
- Post-TTS Cooldown & Mic Queue Purging (Prevents Nila from hearing her own voice echo)
- Infinite Multi-Turn Dialogue Receiver Loop (while True around session.receive())
- Discrete Audio Turn Commit (session.send_client_content(turns=[...], turn_complete=True))
- Non-blocking Audio Playback Worker (asyncio.to_thread)
- Dynamic Ambient Noise Calibration at Startup
- Real-time RMS amplitude jaw lip-sync via SerialController
"""

import asyncio
import os
import time
import math
import struct
import numpy as np
import sounddevice as sd
import logging
from typing import Optional

from src.core.event_bus import EventBus
from src.core.events import SpeechAmplitudeEvent, StateChangeEvent, BrainLLMResponseEvent, TTSPlaybackEvent
from src.services.hardware.serial_controller import SerialController
from src.tools.registry import ToolRegistry
import src.tools.built_in_tools

logger = logging.getLogger(__name__)

class GeminiLiveProvider:
    """Production Gemini 3.1 Live WebSocket Provider"""

    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.model_id = getattr(settings, "GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
        self.is_running = False
        self.is_speaking = False
        self.session = None

        # Audio Configuration
        self.input_rate = 16000
        self.output_rate = 24000
        self.channels = 1
        self.chunk_size = 1024
        self.default_threshold = 500
        self.min_speech_chunks = 3
        self.trailing_silence_limit = getattr(settings, "GEMINI_LIVE_SILENCE_CHUNKS", 18)
        self.cooldown_after_speech = getattr(settings, "GEMINI_LIVE_COOLDOWN", 0.8)

        # Audio DSP & Filter Parameters
        self.filter_type = getattr(settings, "GEMINI_LIVE_FILTER_TYPE", "none").lower()
        self.robotic_effect_enabled = getattr(settings, "GEMINI_LIVE_ROBOTIC_EFFECT", False)
        self.speed_ratio = float(getattr(settings, "GEMINI_LIVE_SPEED_RATIO", 1.0))
        self.pitch_factor = float(getattr(settings, "GEMINI_LIVE_PITCH_FACTOR", 1.0))
        self.modulation_freq = float(getattr(settings, "GEMINI_LIVE_MODULATION_FREQ", 55.0))
        self.delay_buffer = np.zeros(140, dtype=np.float32)

        # Hardware & EventBus
        self.event_bus = EventBus()
        self.serial_ctrl = SerialController(settings)

    def _apply_robotic_voice_filter(self, audio_np: np.ndarray) -> np.ndarray:
        """
        Modular Real-Time Audio Filter Engine.
        Filter Presets:
        - 'none' (Default): 100% natural, clean voice (no effects).
        - 'cyber_robot': Metallic sine wave modulation resonance.
        - 'deep_beast': Deep pitch shift male beast voice.
        - 'radio_intercom': Sci-fi walkie-talkie / megaphone filter.
        - 'flanger_chassis': Hollow robot metal chassis echo chamber.
        """
        if len(audio_np) == 0:
            return audio_np

        filter_mode = self.filter_type if self.filter_type != "none" else ("cyber_robot" if self.robotic_effect_enabled else "none")
        if filter_mode == "none":
            return audio_np

        try:
            samples = audio_np.astype(np.float32)
            num_samples = len(samples)

            if filter_mode == "cyber_robot":
                # Metallic Sine Wave Modulation
                t = np.arange(num_samples) / float(self.output_rate)
                carrier = np.sin(2 * np.pi * self.modulation_freq * t)
                samples = samples * (0.85 + 0.15 * carrier)

            elif filter_mode == "deep_beast":
                # Deep Pitch Shift
                indices = np.linspace(0, num_samples - 1, max(1, int(num_samples / 0.85)))
                samples = np.interp(indices, np.arange(num_samples), samples)
                resample_indices = np.linspace(0, len(samples) - 1, num_samples)
                samples = np.interp(resample_indices, np.arange(len(samples)), samples)

            elif filter_mode == "radio_intercom":
                # Bandpass Walkie-Talkie Filter
                samples = samples - 0.45 * np.roll(samples, 1)

            elif filter_mode == "flanger_chassis":
                # Hollow Robot Metal Chassis Echo
                delay_len = len(self.delay_buffer)
                concat_samples = np.concatenate((self.delay_buffer, samples))
                delayed = concat_samples[:-delay_len][-num_samples:]
                self.delay_buffer = samples[-delay_len:]
                samples = 0.85 * samples + 0.15 * delayed

            # Soft Peak Limiter (Crackle-free output)
            max_val = np.max(np.abs(samples))
            if max_val > 30000.0:
                samples = (samples / max_val) * 30000.0

            return samples.astype(np.int16)
        except Exception:
            return audio_np

    def _calculate_rms(self, pcm_bytes: bytes) -> float:
        """Calculate RMS amplitude from 16-bit PCM audio"""
        if not pcm_bytes:
            return 0.0
        try:
            count = len(pcm_bytes) // 2
            if count == 0:
                return 0.0
            samples = struct.unpack(f"<{count}h", pcm_bytes)
            sum_squares = sum(s * s for s in samples)
            return math.sqrt(sum_squares / count)
        except Exception:
            return 0.0

    def _calculate_rms_intensity(self, pcm_bytes: bytes) -> int:
        """Calculate 0-100 amplitude intensity for jaw servo"""
        rms = self._calculate_rms(pcm_bytes)
        normalized = min(1.0, rms / 4000.0)
        return max(0, min(100, int(normalized * 100)))

    async def start_live_session(self):
        """Start the bidirectional realtime WebSocket loop"""
        if not self.api_key:
            self.logger.error("❌ GEMINI_API_KEY is missing in settings!")
            return

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            self.logger.error("❌ 'google-genai' library not installed.")
            return

        self.is_running = True
        self.logger.info("📡 Connecting to Google Gemini 3.1 Live WebSocket API...")

        client = genai.Client(
            api_key=self.api_key,
            http_options={'api_version': 'v1alpha'}
        )

        system_prompt = getattr(self.settings, "GEMINI_LIVE_SYSTEM_PROMPT", "") or self.settings.LLM_SYSTEM_PROMPT
        voice_name = getattr(self.settings, "GEMINI_LIVE_VOICE", "Puck")
        gemini_tools = ToolRegistry.get_gemini_tools()

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=system_prompt)]
            ),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
            tools=gemini_tools if gemini_tools else None
        )

        loop = asyncio.get_running_loop()
        audio_queue = asyncio.Queue()
        playback_queue = asyncio.Queue()

        # Noise calibration over 1 second
        noise_samples = []
        def calibrate_callback(indata, frames, time_info, status):
            rms = self._calculate_rms(indata.tobytes())
            noise_samples.append(rms)

        with sd.InputStream(samplerate=self.input_rate, channels=self.channels, dtype='int16', callback=calibrate_callback, blocksize=self.chunk_size):
            await asyncio.sleep(1.0)

        avg_noise = sum(noise_samples) / max(1, len(noise_samples))
        speech_threshold = max(self.default_threshold, int(avg_noise * 2.2))
        self.logger.info(f"✅ Noise Calibration Complete! Baseline: {int(avg_noise)} | Speech Threshold: {speech_threshold}")

        def mic_callback(indata, frames, time_info, status):
            if status:
                self.logger.warning(f"Mic input status: {status}")
            if not self.is_speaking:
                pcm_bytes = indata.tobytes()
                loop.call_soon_threadsafe(audio_queue.put_nowait, pcm_bytes)

        try:
            async with client.aio.live.connect(model=self.model_id, config=config) as session:
                self.session = session
                self.logger.info("🟢 Gemini 3.1 Live WebSocket Connected & Active!")
                await self.event_bus.publish(StateChangeEvent(old_state="IDLE", new_state="LISTENING", reason="Gemini Live Active"))

                # Async Worker: Non-blocking speaker output player
                playback_rate = int(self.output_rate * self.speed_ratio)
                self.logger.info(f"🔊 Speaker Playback Rate: {playback_rate} Hz (Speed Ratio: {self.speed_ratio})")

                async def player_worker():
                    with sd.OutputStream(samplerate=playback_rate, channels=self.channels, dtype='int16') as out_stream:
                        while self.is_running:
                            item = await playback_queue.get()
                            if item is None:
                                break
                            audio_bytes, intensity = item
                            await self.event_bus.publish(SpeechAmplitudeEvent(intensity=intensity))
                            if self.serial_ctrl.is_connected:
                                self.serial_ctrl.send_jaw_intensity(intensity)
                            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                            audio_np = self._apply_robotic_voice_filter(audio_np)
                            await asyncio.to_thread(out_stream.write, audio_np)
                            playback_queue.task_done()

                player_task = asyncio.create_task(player_worker())

                # Task 2: Audio Stream Sender Loop with Explicit Client Turn Content Commit
                async def send_mic_audio():
                    user_speaking = False
                    consecutive_speech_chunks = 0
                    silence_count = 0
                    turn_pcm_data = bytearray()

                    with sd.InputStream(
                        samplerate=self.input_rate,
                        channels=self.channels,
                        dtype='int16',
                        callback=mic_callback,
                        blocksize=self.chunk_size
                    ):
                        while self.is_running:
                            pcm_bytes = await audio_queue.get()
                            if self.is_speaking:
                                user_speaking = False
                                consecutive_speech_chunks = 0
                                silence_count = 0
                                turn_pcm_data.clear()
                                continue

                            rms = self._calculate_rms(pcm_bytes)
                            if rms >= speech_threshold:
                                consecutive_speech_chunks += 1
                                silence_count = 0
                                turn_pcm_data.extend(pcm_bytes)

                                if consecutive_speech_chunks >= self.min_speech_chunks and not user_speaking:
                                    user_speaking = True
                            else:
                                if user_speaking:
                                    silence_count += 1
                                    turn_pcm_data.extend(pcm_bytes)
                                    if silence_count >= self.trailing_silence_limit:
                                        user_speaking = False
                                        consecutive_speech_chunks = 0
                                        silence_count = 0

                                        if len(turn_pcm_data) > 0:
                                            pcm_payload = bytes(turn_pcm_data)
                                            turn_pcm_data.clear()

                                            self.logger.info(f"🗣️ [USER SPOKE] User finished speaking! ({len(pcm_payload)} bytes audio sent)")
                                            print("\n" + "="*60)
                                            print(f"🎤 [USER VOICE RECORDED]: Sent {len(pcm_payload)} bytes audio to Gemini")
                                            print("="*60)
                                            turn_content = types.Content(
                                                role="user",
                                                parts=[types.Part.from_bytes(data=pcm_payload, mime_type="audio/pcm")]
                                            )
                                            await session.send_client_content(turns=[turn_content], turn_complete=True)
                                else:
                                    consecutive_speech_chunks = 0
                                    turn_pcm_data.clear()

                async def receive_response_audio():
                    current_model_text = []
                    while self.is_running:
                        async for response in session.receive():
                            if not self.is_running:
                                break
                            
                            # Handle Gemini Live Tool / Function Calls
                            if hasattr(response, "tool_call") and response.tool_call:
                                for call in response.tool_call.function_calls:
                                    fn_name = call.name
                                    fn_args = dict(call.args) if hasattr(call, "args") and call.args else {}
                                    fn_id = getattr(call, "id", None)

                                    await self.event_bus.publish(StateChangeEvent(old_state="LISTENING", new_state="EXECUTING", reason=f"Executing tool {fn_name}"))
                                    tool_result_str = await ToolRegistry.execute_tool(fn_name, fn_args)

                                    try:
                                        tool_resp = types.LiveClientToolResponse(
                                            function_responses=[
                                                types.FunctionResponse(name=fn_name, id=fn_id, response={"result": tool_result_str})
                                            ]
                                        )
                                        await session.send(input=tool_resp)
                                    except Exception as te:
                                        self.logger.error(f"❌ Error sending tool response to Gemini: {te}")

                                    await self.event_bus.publish(StateChangeEvent(old_state="EXECUTING", new_state="LISTENING", reason=f"Tool {fn_name} complete"))

                            server_content = response.server_content
                            if server_content is None:
                                continue

                            # Check for user turn transcription
                            if hasattr(server_content, "user_turn") and server_content.user_turn:
                                user_parts = [p.text for p in server_content.user_turn.parts if hasattr(p, "text") and p.text]
                                if user_parts:
                                    user_transcript = ' '.join(user_parts)
                                    self.logger.info(f"🗣️ [USER TRANSCRIPTION] \"{user_transcript}\"")
                                    print("\n" + "="*60)
                                    print("🎤 USER TRANSCRIPTION:")
                                    print(f"\"{user_transcript}\"")
                                    print("="*60)

                            model_turn = server_content.model_turn
                            if model_turn is not None:
                                if not self.is_speaking:
                                    self.is_speaking = True
                                    current_model_text.clear()
                                    await self.event_bus.publish(StateChangeEvent(old_state="LISTENING", new_state="SPEAKING", reason="Gemini Live Response"))
                                    await self.event_bus.publish(TTSPlaybackEvent(status="started"))
                                    while not audio_queue.empty():
                                        try:
                                            audio_queue.get_nowait()
                                        except asyncio.QueueEmpty:
                                            break

                                for part in model_turn.parts:
                                    if hasattr(part, "text") and part.text:
                                        current_model_text.append(part.text)
                                        self.logger.info(f"🤖 [NILA SPEAKING] \"{part.text}\"")
                                        await self.event_bus.publish(BrainLLMResponseEvent(text=part.text))
                                    if part.inline_data:
                                        audio_bytes = part.inline_data.data
                                        intensity = self._calculate_rms_intensity(audio_bytes)
                                        await playback_queue.put((audio_bytes, intensity))

                            if server_content.turn_complete:
                                await playback_queue.join()
                                if current_model_text:
                                    full_spoken_text = "".join(current_model_text)
                                    print("\n" + "="*60)
                                    print("🤖 NILA RESPONDED & SPOKE:")
                                    print(f"\"{full_spoken_text}\"")
                                    print("="*60 + "\n")
                                    current_model_text.clear()
                                if self.serial_ctrl.is_connected:
                                    self.serial_ctrl.send_jaw_intensity(0)
                                await self.event_bus.publish(TTSPlaybackEvent(status="finished"))
                                await self.event_bus.publish(StateChangeEvent(old_state="SPEAKING", new_state="LISTENING", reason="Gemini Turn Complete"))
                                
                                # Post-speech cooldown: Purging mic queue and buffer
                                await asyncio.sleep(self.cooldown_after_speech)
                                while not audio_queue.empty():
                                    try:
                                        audio_queue.get_nowait()
                                    except asyncio.QueueEmpty:
                                        break
                                self.is_speaking = False
                                break

                # Send initial turn to trigger Nila's startup greeting
                try:
                    greeting_prompt = "Hello! Briefly welcome the user in 1 short sentence as Nila."
                    initial_turn = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=greeting_prompt)]
                    )
                    await session.send_client_content(turns=[initial_turn], turn_complete=True)
                except Exception as ge:
                    self.logger.warning(f"Could not send startup greeting: {ge}")

                try:
                    await asyncio.gather(send_mic_audio(), receive_response_audio())
                except asyncio.CancelledError:
                    self.logger.info("⏸️ Gemini Live session cancelled (Shutdown requested).")
                finally:
                    player_task.cancel()
                    await playback_queue.put(None)

        except asyncio.CancelledError:
            self.logger.info("⏸️ Gemini Live WebSocket session closed.")
        except Exception as e:
            self.logger.error(f"❌ Gemini Live WebSocket Session Error: {e}")
        finally:
            self.is_running = False
            self.is_speaking = False
            try:
                sd.stop()
            except Exception:
                pass
            if self.serial_ctrl.is_connected:
                self.serial_ctrl.send_jaw_intensity(0)
            self.logger.info("👋 Gemini Live WebSocket Session Ended.")

    def stop(self):
        """Stop the live session"""
        self.is_running = False
        self.is_speaking = False
        try:
            sd.stop()
        except Exception:
            pass
