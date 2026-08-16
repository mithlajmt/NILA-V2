# 📖 NILA-V2 Developer Guide & Code Flow Walkthrough

Welcome to the **NILA V2 Developer Guide**. This document is designed for any software or AI engineer joining the NILA robotics project. It explains the exact flow of the code, how components interact, and how to independently develop or modify any subsystem without breaking the rest of the robot.

---

## 🧭 Executive Summary: How NILA V2 Works

NILA V2 is structured as a **Decoupled Event-Driven AI Robot Brain**:

1. **Main Entry Point (`main.py`)**: Initializes logger, loads `.env` config, and starts `RobotController`.
2. **Audio Capture (`src/services/speech/audio_capture.py`)**: Spawns PipeWire `parecord`/`arecord` in a background subprocess, calibrates background noise, and applies WebRTC Voice Activity Detection (VAD).
3. **Speech-to-Text (`src/services/speech/speech_recognizer.py`)**: Passes captured audio bytes to the active provider (**Deepgram**, **Faster-Whisper**, or **Google STT**) and emits an `STTTranscriptEvent` onto the `EventBus`.
4. **AI Reasoning & Personality (`src/services/llm/llm_service.py`)**: `RobotController` hears the transcript event, publishes a `BrainThinkingEvent` (which triggers `FeedbackService` audio sounds), and queries **OpenRouter** (Gemini/Llama) or **OpenAI**.
5. **Text-to-Speech (`src/services/tts/tts_service.py`)**: The generated AI text is synthesized into speech using **Piper Neural TTS** (Local ONNX), **ElevenLabs**, **Google Cloud**, or **gTTS**.
6. **Real-Time Lip-Sync (`src/services/tts/piper_provider.py`)**: While audio plays via system speaker, Python reads the 50ms WAV amplitude RMS, calculates an intensity score (0–100), and emits a `SpeechAmplitudeEvent`.
7. **Hardware Execution (`src/services/hardware/serial_controller.py`)**: `SerialController` hears the amplitude event and sends an ASCII string (`"intensity\n"`) over USB Serial (`/dev/ttyUSB0`) to Arduino (`robot_head.ino`), which moves the physical jaw servo.

---

## ⚡ The Event Bus Pattern (`src/core/event_bus.py`)

All major subsystems interact asynchronously via the `EventBus` Pub/Sub engine rather than calling each other directly.

### Key Event Topics (`src/core/events.py`):
- `audio.input`: Raw audio frame events.
- `stt.transcript`: Transcribed speech text & language payload (`STTTranscriptEvent`).
- `brain.thinking`: Thinking status (`is_thinking=True/False`) (`BrainThinkingEvent`).
- `brain.response`: Final generated LLM response text (`BrainLLMResponseEvent`).
- `tts.playback`: Synthesis & playback state (`started`, `finished`) (`TTSPlaybackEvent`).
- `speech.amplitude`: Real-time RMS audio intensity (0–100) (`SpeechAmplitudeEvent`).
- `hardware.jaw`: Direct jaw control intensity (`HardwareJawCommandEvent`).
- `hardware.gesture`: Body animation profile commands (`HardwareGestureCommandEvent`).
- `system.state`: Lifecycle updates (`running`, `shutdown`, `error`) (`SystemStateEvent`).

---

## 🗺️ Codebase Map & Subsystem Responsibilities

```text
NILA-V2/
├── main.py                             <-- Entry point. Run 'python main.py' to launch NILA.
├── ARCHITECTURE_OVERVIEW.md             <-- Deep architectural specification & sequence diagrams.
├── DEVELOPER_GUIDE.md                  <-- [THIS FILE] Developer onboarding & recipes guide.
├── requirements.txt                    <-- Python library dependencies.
├── setup.sh                            <-- Automated setup script for Pi/Linux.
│
├── src/                                <-- Core Python application
│   ├── config/
│   │   └── settings.py                 <-- Pydantic BaseSettings class loading .env configuration.
│   ├── core/
│   │   ├── event_bus.py                <-- EventBus Pub/Sub engine with wildcard matching.
│   │   ├── events.py                   <-- Strongly-typed Event data classes.
│   │   └── robot_controller.py         <-- Main orchestrator & lifecycle manager.
│   └── services/
│       ├── base_worker.py              <-- Abstract base class for background event workers.
│       ├── audio/
│       │   └── audio_player.py         <-- Pygame audio player with RMS amplitude analysis.
│       ├── feedback/
│       │   └── feedback_service.py     <-- Plays ambient audio loop during LLM thinking state.
│       ├── hardware/
│       │   └── serial_controller.py    <-- PySerial driver writing to USB Serial /dev/ttyUSB0.
│       ├── llm/
│       │   ├── base_provider.py        <-- LLM driver interface & conversation history list.
│       │   ├── llm_service.py          <-- LLM Factory (OpenAI, OpenRouter, Anthropic).
│       │   ├── openai_provider.py      <-- OpenAI ChatGPT API driver.
│       │   ├── openrouter_provider.py  <-- OpenRouter API driver (Gemini 2.5 Flash, Llama 3.1).
│       │   └── anthropic_provider.py   <-- Anthropic Claude stub driver.
│       ├── speech/
│       │   ├── audio_capture.py        <-- PipeWire audio recorder (parecord/arecord + WebRTC VAD).
│       │   ├── base_stt_provider.py    <-- STT Protocol interface & STTResult data class.
│       │   ├── speech_recognizer.py    <-- High-level STT manager.
│       │   └── providers/
│       │       ├── deepgram_stt_provider.py <-- Deepgram Nova-2 Cloud STT driver.
│       │       ├── google_stt_provider.py   <-- Google Free STT driver.
│       │       └── whisper_stt_provider.py  <-- Faster-Whisper Local INT8 ONNX driver.
│       └── tts/
│           ├── base_tts_provider.py         <-- TTS driver interface.
│           ├── tts_service.py               <-- TTS Factory.
│           ├── piper_provider.py            # Driver for local Piper TTS + Jaw lip-sync.
│           ├── elevenlabs_tts_provider.py   # Driver for ElevenLabs API.
│           ├── google_cloud_tts_provider.py # Driver for Google Cloud TTS API.
│           └── gtts_provider.py             # Driver for gTTS free API.
│
├── arduino/                            <-- Microcontroller C++ Code
│   └── robot_head/
│       ├── robot_head.ino              <-- Production sketch: 1 Jaw Servo (Pin 7) + Eye LED (Pin A1).
│       └── robot.ino                   <-- Advanced sketch: 8 Servo body movement state machine.
│
├── data/                               <-- Data & Storage
│   ├── audio/                          <-- Cached TTS output files (.wav / .mp3)
│   ├── logs/robot.log                  <-- Application log file.
│   └── models/piper/                   <-- Piper ONNX voice models (ml_IN-arjun, en_US-ryan, etc.).
│
├── scripts/                            <-- Utility & Diagnostic Scripts
│   ├── test_hardware.py                <-- Test Arduino jaw movement over serial.
│   ├── find_arduino.py                 <-- Scan connected USB serial ports.
│   └── test_decoupled.py               <-- Verify decoupled TTS audio execution.
│
├── tests/                              <-- Automated Test Suite
│   ├── test_event_bus.py               <-- Unit tests for EventBus engine.
│   └── test_openrouter.py              <-- Test OpenRouter LLM connection.
└── tools/piper/                        <-- Piper executable binary & espeak-ng data.
```

---

## 🚀 How to Work Independently on NILA V2 Components

### Task 1: Adding a New STT Engine
Want to add a new Speech-to-Text provider (e.g. AssemblyAI or Azure Speech)?
1. Open `src/services/speech/providers/` and create `assemblyai_stt_provider.py`.
2. Inherit from `BaseSTTProvider` (`src/services/speech/base_stt_provider.py`):
   ```python
   from src.services.speech.base_stt_provider import BaseSTTProvider, STTResult

   class AssemblyAISTTProvider(BaseSTTProvider):
       async def transcribe(self, audio_bytes: bytes, language: str = None) -> STTResult:
           # Your API call here...
           return STTResult(text=transcribed_text, language="en", confidence=0.95)
   ```
3. Register your provider in `src/services/speech/speech_recognizer.py` inside `_init_provider()`.
4. Add credentials to `.env` and `src/config/settings.py`.

---

### Task 2: Adding a New TTS Voice or Provider
Want to add a new Text-to-Speech provider or voice model?
1. Open `src/services/tts/` and create your provider class (e.g., `azure_tts_provider.py`).
2. Inherit from `BaseTTSProvider` (`src/services/tts/base_tts_provider.py`):
   ```python
   from .base_tts_provider import BaseTTSProvider

   class AzureTTSProvider(BaseTTSProvider):
       async def speak(self, text: str, language: str = None) -> bool:
           # Generate audio, play it, and emit amplitude events
           return True
   ```
3. Register your provider in `src/services/tts/tts_service.py` inside `_initialize_provider()`.
4. Set `TTS_PROVIDER=azure` in `.env`.

---

### Task 3: Modifying NILA's Personality or LLM Prompts
Want to change how NILA talks or add new knowledge?
1. Open `src/config/settings.py` and inspect `LLM_SYSTEM_PROMPT`.
2. Edit the prompt text to adjust tone, accent rules, or knowledge constraints.
3. You can also override the system prompt per session in `.env`:
   ```env
   LLM_SYSTEM_PROMPT="You are Nila, a witty assistant from Kerala who speaks English..."
   ```

---

### Task 4: Building a New EventBus Subscriber (e.g. Wake Word, Vision, Email Workflow)
Want to add a background feature that reacts to events (e.g., sending an email when NILA generates a response, or triggering vision)?
1. Create your worker class inheriting from `BaseWorker` (`src/services/base_worker.py`):
   ```python
   from src.services.base_worker import BaseWorker
   from src.core.events import Event

   class EmailNotificationWorker(BaseWorker):
       def register_subscriptions(self):
           # Subscribe to LLM response events
           self.event_bus.subscribe("brain.response", self.on_llm_response)

       def on_llm_response(self, event: Event):
           print(f"Sending email notification for response: {event.text}")
   ```
2. Instantiate and start your worker in `RobotController` (`src/core/robot_controller.py`).

---

### Task 5: Controlling Arduino Servos & Body Motions
Want to add body gestures (e.g. arm waving, head nodding)?
1. In `arduino/robot_head/robot_head.ino`, add a new serial command parser (e.g., `"WAVE\n"` or `"NOD\n"`).
2. In `src/services/hardware/serial_controller.py`, add a helper method or subscribe to `hardware.gesture` events:
   ```python
   def send_gesture(self, gesture_name: str):
       if self.is_connected and self.serial_conn:
           self.serial_conn.write(f"{gesture_name}\n".encode())
   ```
3. Emit a `HardwareGestureCommandEvent(gesture_name="WAVE")` anywhere in Python to trigger the physical robot movement.

---

## 🧪 Quick Test Reference Commands

Run these terminal commands to test individual hardware/software components independently:

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Test EventBus Pub/Sub Engine
python3 -m unittest tests/test_event_bus.py

# 3. Test Decoupled TTS Synthesis
python3 scripts/test_decoupled.py

# 4. Scan USB Serial Ports for Arduino
python3 scripts/find_arduino.py

# 5. Interactive Arduino Jaw Servo Test
python3 scripts/test_hardware.py --port /dev/ttyUSB0

# 6. Test OpenRouter LLM Gateway
python3 tests/test_openrouter.py

# 7. Test Microphone Audio Capture & VAD
python3 scripts/test_audio_capture.py

# 8. Launch NILA V2 Full System
python3 main.py
```

---

*Document Created: August 2026*  
*Project Maintainers: Robuverse NILA Engineering Team*
