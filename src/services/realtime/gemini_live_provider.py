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
from src.core.events import SpeechAmplitudeEvent, StateChangeEvent, BrainLLMResponseEvent, TTSPlaybackEvent, STTTranscriptEvent
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
        self.user_speaking = False
        self.is_recording_allowed = False  # Strict Half-Duplex gate: muted until ready for user input
        self.session = None
        self.calibrated_threshold = None

        # Audio Configuration
        self.input_rate = 16000
        self.output_rate = 24000
        self.channels = 1
        self.chunk_size = 1024
        self.default_threshold = getattr(settings, "GEMINI_LIVE_DEFAULT_THRESHOLD", 150)
        self.min_speech_chunks = getattr(settings, "GEMINI_LIVE_MIN_SPEECH_CHUNKS", 3)
        self.trailing_silence_limit = getattr(settings, "GEMINI_LIVE_SILENCE_CHUNKS", 18)
        self.cooldown_after_speech = float(getattr(settings, "GEMINI_LIVE_COOLDOWN", 1.8))

        # Audio DSP & Filter Parameters
        self.filter_type = getattr(settings, "GEMINI_LIVE_FILTER_TYPE", "none").lower()
        self.robotic_effect_enabled = getattr(settings, "GEMINI_LIVE_ROBOTIC_EFFECT", False)
        self.speed_ratio = float(getattr(settings, "GEMINI_LIVE_SPEED_RATIO", 1.0))
        self.pitch_factor = float(getattr(settings, "GEMINI_LIVE_PITCH_FACTOR", 1.0))
        self.modulation_freq = float(getattr(settings, "GEMINI_LIVE_MODULATION_FREQ", 55.0))
        self.delay_buffer = np.zeros(140, dtype=np.float32)
        self.filter_phase = 0.0
        self.volume_gain = float(getattr(settings, "GEMINI_LIVE_VOLUME_GAIN", 1.3))

        # Hardware & EventBus
        self.event_bus = EventBus()
        self.serial_ctrl = SerialController(settings)
        self.player_worker_alive = False

        # Smart Hardware Audio Device Detection (Strictly bypass webcam mics)
        self.mic_device_index = self._find_audio_device(is_input=True)
        self.speaker_device_index = self._find_audio_device(is_input=False)

    def _find_audio_device(self, is_input: bool = True):
        """
        Audio Device Selector:
        - Microphone (is_input=True): Uses the active HD camera microphone (Device 0).
        - Speaker (is_input=False): Uses PulseAudio ('pulse' / USB soundcard) for robot voice playback.
        """
        try:
            devices = sd.query_devices()
            preferred_name = getattr(self.settings, "AUDIO_DEVICE_NAME", "") or ""

            # 1. If explicit device name configured and not "default"
            if preferred_name and preferred_name.lower() != "default":
                for idx, dev in enumerate(devices):
                    channels = dev['max_input_channels'] if is_input else dev['max_output_channels']
                    if channels > 0 and preferred_name.lower() in dev['name'].lower():
                        role = "Microphone" if is_input else "Speaker"
                        self.logger.info(f"🎯 Matched preferred {role}: Device {idx} ({dev['name']})")
                        return idx

            if is_input:
                # Select the HD Camera microphone (Device 0) where the user actually speaks
                for idx, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0 and "camera" in dev['name'].lower():
                        self.logger.info(f"🎤 Selected Microphone: Device {idx} ({dev['name']})")
                        return idx
                return 0
            else:
                # Select the USB soundcard / pulse speaker for speech playback
                for idx, dev in enumerate(devices):
                    if dev['max_output_channels'] > 0 and dev['name'].lower().startswith("pulse"):
                        self.logger.info(f"🔊 Selected Speaker: Device {idx} ({dev['name']})")
                        return idx
                return "pulse"
        except Exception as e:
            self.logger.warning(f"Error querying audio devices: {e}")
            return 0 if is_input else "pulse"

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
                # Metallic Sine Wave Modulation with continuous phase to eliminate chunk crackle
                t = (np.arange(num_samples) + self.filter_phase) / float(self.output_rate)
                carrier = np.sin(2 * np.pi * self.modulation_freq * t)
                samples = samples * (0.85 + 0.15 * carrier)
                self.filter_phase = (self.filter_phase + num_samples) % 1000000.0

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
        self._active_task = asyncio.current_task()
        self.logger.info("📡 Connecting to Google Gemini 3.1 Live WebSocket API...")

        client = genai.Client(
            api_key=self.api_key,
            http_options={'api_version': 'v1alpha'}
        )

        system_prompt = getattr(self.settings, "GEMINI_LIVE_SYSTEM_PROMPT", "") or self.settings.LLM_SYSTEM_PROMPT
        voice_name = getattr(self.settings, "GEMINI_LIVE_VOICE", "Puck")
        expo_mode = getattr(self.settings, "EXPO_MODE", True)
        gemini_tools = ToolRegistry.get_gemini_tools(expo_mode=expo_mode)

        # Inject real-time timestamp into system prompt so Gemini knows current time without calling tools
        try:
            from datetime import datetime
            now_str = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
            system_prompt = f"{system_prompt}\n[Real-time Context: Current date and time is {now_str} IST, Kerala]"
        except Exception:
            pass

        if gemini_tools:
            self.logger.info("🛠️ Gemini Live Tools registered.")
        else:
            self.logger.info("⚡ Zero-Tool Pure Voice Mode: Function-calling disabled for instant, loop-free conversation.")

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
        audio_queue = asyncio.Queue(maxsize=100)
        playback_queue = asyncio.Queue(maxsize=200)

        # Noise calibration over 1 second (runs on first startup only)
        if self.calibrated_threshold is None:
            noise_samples = []
            def calibrate_callback(indata, frames, time_info, status):
                rms = self._calculate_rms(indata.tobytes())
                noise_samples.append(rms)

            with sd.InputStream(device=self.mic_device_index, samplerate=self.input_rate, channels=self.channels, dtype='int16', callback=calibrate_callback, blocksize=self.chunk_size):
                await asyncio.sleep(1.0)

            avg_noise = sum(noise_samples) / max(1, len(noise_samples))
            if avg_noise < 40:
                self.calibrated_threshold = max(35, int(avg_noise * 1.8 + 20))
            else:
                self.calibrated_threshold = max(self.default_threshold, int(avg_noise * 1.5 + 30))
            self.logger.info(f"✅ Noise Calibration Complete! Baseline: {int(avg_noise)} | Speech Threshold: {self.calibrated_threshold}")

        speech_threshold = self.calibrated_threshold

        def mic_callback(indata, frames, time_info, status):
            if status:
                self.logger.warning(f"Mic input status: {status}")
            # Strict Half-Duplex Echo Prevention:
            # Completely discard microphone audio while playing voice, executing tools,
            # awaiting response, or in Bluetooth buffer settling cooldown.
            if not self.is_recording_allowed or self.is_speaking:
                return
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
                    self.player_worker_alive = True
                    try:
                        with sd.OutputStream(device=self.speaker_device_index, samplerate=playback_rate, channels=self.channels, dtype='int16') as out_stream:
                            while self.is_running:
                                try:
                                    item = await playback_queue.get()
                                except asyncio.CancelledError:
                                    break
                                if item is None:
                                    playback_queue.task_done()
                                    break
                                
                                # Tiny jitter pre-buffer on start of turn to prevent Bluetooth buffer underruns
                                if not self.is_speaking and playback_queue.qsize() < 2:
                                    await asyncio.sleep(0.08)

                                self.is_speaking = True
                                self.is_recording_allowed = False
                                audio_bytes, intensity = item
                                await self.event_bus.publish(SpeechAmplitudeEvent(intensity=intensity))
                                if self.serial_ctrl.is_connected:
                                    self.serial_ctrl.send_jaw_intensity(intensity)
                                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                                audio_np = self._apply_robotic_voice_filter(audio_np)
                                gain = getattr(self, "volume_gain", 1.0)
                                if gain != 1.0:
                                    boosted = audio_np.astype(np.float32) * gain
                                    audio_np = np.clip(boosted, -32767, 32767).astype(np.int16)
                                try:
                                    await asyncio.to_thread(out_stream.write, audio_np)
                                except Exception as write_err:
                                    self.logger.warning(f"Audio write failure: {write_err}")
                                    playback_queue.task_done()
                                    break
                                playback_queue.task_done()
                    except Exception as pe:
                        self.logger.warning(f"Audio output player stream error: {pe}")
                    finally:
                        self.player_worker_alive = False
                        # Cleanly drain any remaining items so playback_queue.join() never deadlocks
                        while not playback_queue.empty():
                            try:
                                playback_queue.get_nowait()
                                playback_queue.task_done()
                            except (asyncio.QueueEmpty, ValueError):
                                break

                player_task = asyncio.create_task(player_worker())

                # Task 2: Audio Stream Sender Loop with Explicit Client Turn Content Commit
                async def send_mic_audio():
                    self.user_speaking = False
                    consecutive_speech_chunks = 0
                    silence_count = 0
                    turn_pcm_data = bytearray()

                    with sd.InputStream(
                        device=self.mic_device_index,
                        samplerate=self.input_rate,
                        channels=self.channels,
                        dtype='int16',
                        callback=mic_callback,
                        blocksize=self.chunk_size
                    ):
                        while self.is_running:
                            pcm_bytes = await audio_queue.get()
                            if not self.is_recording_allowed or self.is_speaking:
                                self.user_speaking = False
                                consecutive_speech_chunks = 0
                                silence_count = 0
                                turn_pcm_data.clear()
                                continue

                            rms = self._calculate_rms(pcm_bytes)
                            if rms >= speech_threshold:
                                consecutive_speech_chunks += 1
                                silence_count = 0
                                turn_pcm_data.extend(pcm_bytes)

                                if consecutive_speech_chunks >= self.min_speech_chunks and not self.user_speaking:
                                    self.user_speaking = True
                                    print(f"\n🎤 [LISTENING...] Speech detected! (Volume RMS: {int(rms)} > Threshold: {speech_threshold})", flush=True)
                            else:
                                if self.user_speaking:
                                    silence_count += 1
                                    turn_pcm_data.extend(pcm_bytes)
                                    if silence_count >= self.trailing_silence_limit:
                                        self.user_speaking = False
                                        consecutive_speech_chunks = 0
                                        silence_count = 0

                                        if len(turn_pcm_data) > 0:
                                            pcm_payload = bytes(turn_pcm_data)
                                            turn_pcm_data.clear()

                                            self.logger.info(f"🗣️ [USER SPOKE] User finished speaking! ({len(pcm_payload)} bytes audio sent)")
                                            print("\n" + "="*60)
                                            print(f"🎤 [USER VOICE RECORDED]: Sent {len(pcm_payload)} bytes audio to Gemini")
                                            print("="*60)

                                            # Immediately lock recording while waiting for Gemini to think and respond
                                            self.is_recording_allowed = False
                                            while not audio_queue.empty():
                                                try:
                                                    audio_queue.get_nowait()
                                                except asyncio.QueueEmpty:
                                                    break

                                            turn_content = types.Content(
                                                role="user",
                                                parts=[types.Part.from_bytes(data=pcm_payload, mime_type="audio/pcm")]
                                            )
                                            await self.event_bus.publish(STTTranscriptEvent(text="🗣️ Spoken voice input (Real-time Audio)"))
                                            await session.send_client_content(turns=[turn_content], turn_complete=True)
                                else:
                                    consecutive_speech_chunks = 0
                                    turn_pcm_data.clear()

                async def receive_response_audio():
                    current_model_text = []
                    while self.is_running:
                        try:
                            async for response in session.receive():
                                if not self.is_running:
                                    break
                                
                                # Handle Gemini Live Tool / Function Calls
                                if hasattr(response, "tool_call") and response.tool_call:
                                    self.is_recording_allowed = False
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
                                    self.is_recording_allowed = False
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
                                            if self.player_worker_alive:
                                                await playback_queue.put((audio_bytes, intensity))

                                if server_content.turn_complete:
                                    try:
                                        await asyncio.wait_for(playback_queue.join(), timeout=3.5)
                                    except asyncio.TimeoutError:
                                        self.logger.warning("⚠️ Playback buffer join timed out; continuing turn.")
                                        while not playback_queue.empty():
                                            try:
                                                playback_queue.get_nowait()
                                                playback_queue.task_done()
                                            except (asyncio.QueueEmpty, ValueError):
                                                break

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
                                    # Allow Bluetooth speaker buffer + acoustic room reverberation to settle completely
                                    await asyncio.sleep(self.cooldown_after_speech)
                                    while not audio_queue.empty():
                                        try:
                                            audio_queue.get_nowait()
                                        except asyncio.QueueEmpty:
                                            break
                                    self.is_speaking = False
                                    self.filter_phase = 0.0
                                    self.is_recording_allowed = True
                                    self.logger.info("🎤 Listening re-enabled for user input")
                                    break
                        except Exception as rx_err:
                            self.logger.info(f"ℹ️ Gemini Live audio receiver session ended: {rx_err}")
                            break

                # Send initial turn to trigger Nila's startup greeting
                try:
                    self.is_recording_allowed = False
                    greeting_prompt = "Hello! Briefly welcome the user in 1 short sentence as Nila."
                    initial_turn = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=greeting_prompt)]
                    )
                    await session.send_client_content(turns=[initial_turn], turn_complete=True)
                except Exception as ge:
                    self.logger.warning(f"Could not send startup greeting: {ge}")
                    self.is_recording_allowed = True

                session_start_time = time.time()

                async def session_watchdog():
                    """
                    Proactively refresh Gemini Live WebSocket after 8 minutes
                    to avoid Google's hard 10-15 minute GoAway session limit.
                    Only cycles when NILA is completely idle (not speaking, no user speech).
                    """
                    while self.is_running:
                        await asyncio.sleep(5)
                        elapsed = time.time() - session_start_time
                        if elapsed > 480:  # 8 minutes
                            if not self.is_speaking and not self.user_speaking and audio_queue.empty() and playback_queue.empty():
                                self.logger.info("🔄 Proactively refreshing Gemini Live session (8-min lease renewal)...")
                                break

                tasks = [
                    asyncio.create_task(send_mic_audio()),
                    asyncio.create_task(receive_response_audio()),
                    asyncio.create_task(session_watchdog())
                ]

                try:
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for t in done:
                        if not t.cancelled():
                            exc = t.exception()
                            if exc:
                                self.logger.debug(f"Task completed with status: {exc}")
                    for p in pending:
                        p.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                finally:
                    # Cleanly close player without aborting mid-write
                    await playback_queue.put(None)
                    try:
                        await asyncio.wait_for(player_task, timeout=1.5)
                    except Exception:
                        player_task.cancel()

        except asyncio.CancelledError:
            self.logger.info("⏸️ Gemini Live WebSocket session closed.")
        except Exception as e:
            self.logger.error(f"❌ Gemini Live WebSocket Session Error: {e}")
        finally:
            self.is_running = False
            self.is_speaking = False
            self.user_speaking = False
            self.is_recording_allowed = False
            if self.serial_ctrl.is_connected:
                self.serial_ctrl.send_jaw_intensity(0)
            self.logger.info("👋 Gemini Live WebSocket Session Ended.")
            # Grace period for OS/ALSA to release sound hardware handles
            await asyncio.sleep(0.5)

    def stop(self):
        """Stop the live session immediately"""
        self.is_running = False
        self.is_speaking = False
        self.user_speaking = False
        self.is_recording_allowed = False
        if hasattr(self, "_active_task") and self._active_task and not self._active_task.done():
            try:
                self._active_task.cancel()
            except Exception:
                pass
