# 🏗️ NILA-V2: System Architecture & Developer Guide

This document is the **Comprehensive Developer & Architecture Guide** for **NILA-V2**, the full-duplex humanoid robot platform by **Robuverse**.

---

## 1. System Architecture & Dual Operating Modes

Nila operates in two distinct modes controlled via `.env`:

```
                                      ┌──────────────────────────────────────┐
                                      │       NILA-V2 CORE ENGINE            │
                                      │   (src/core/robot_controller.py)     │
                                      └──────────────────┬───────────────────┘
                                                         │
                        ┌────────────────────────────────┴────────────────────────────────┐
                        ▼                                                                 ▼
      ┌───────────────────────────────────┐                             ┌───────────────────────────────────┐
      │     REALTIME WEBSOCKET MODE       │                             │         3-STEP PIPELINE           │
      │   (ENABLE_REALTIME_MODE=True)     │                             │   (ENABLE_REALTIME_MODE=False)    │
      └─────────────────┬─────────────────┘                             └─────────────────┬─────────────────┘
                        │                                                                 │
      ┌─────────────────┴─────────────────┐                             ┌─────────────────┼─────────────────┐
      ▼                                   ▼                             ▼                 ▼                 ▼
┌──────────────┐                  ┌──────────────┐                ┌───────────┐     ┌───────────┐     ┌───────────┐
│ Gemini Live  │                  │ Arduino Jaw  │                │ STT Engine│     │ LLM Brain │     │ TTS Engine│
│ WebSockets   │                  │ Serial Servo │                │ (Whisper /│     │ (OpenAI / │     │ (Piper /  │
│ (Sub-300ms)  │                  │ Lip-Sync     │                │ Deepgram) │     │OpenRouter)│     │ElevenLabs)│
└──────────────┘                  └──────────────┘                └───────────┘     └───────────┘     └───────────┘
```

### Mode 1: Gemini Live Multimodal WebSockets (`ENABLE_REALTIME_MODE=True`)
* **How it Works**: Full-duplex audio stream via `google-genai` SDK (`gemini-3.1-flash-live-preview`).
* **Features**: Sub-300ms latency, native spoken interruption, dynamic room noise auto-calibration, real-time RMS jaw lip-sync to Arduino via USB serial, and native WebSocket Tool/Agent Calling.

### Mode 2: 3-Step Pipeline (`ENABLE_REALTIME_MODE=False`)
* **How it Works**: Microphone ➔ STT (Whisper/Deepgram) ➔ LLM Brain (OpenRouter/OpenAI) ➔ TTS (Piper/ElevenLabs).
* **Features**: 100% offline fallback support on Raspberry Pi using local Piper ONNX Malayalam voice synthesis (`ml_IN-arjun-medium.onnx`).

---

## 2. Directory & Codebase Map

```
NILA-V2/
├── .env                        # Central Configuration (API Keys, VAD limits, Personality)
├── .env.template               # Template configuration file
├── main.py                     # Entry point for full robot application
├── README.md                   # Setup Helper & Getting Started Guide
├── DEVELOPER_GUIDE.md          # Master Architecture & Developer Expansion Guide
├── requirements.txt            # Python dependencies
├── setup.sh                    # Automated setup script for Linux & Raspberry Pi
│
├── arduino/                    # Arduino C++ sketches for servo jaw & body hardware
├── data/                       # Models & local logs
├── tools/                      # Local binaries (Piper offline Malayalam TTS engine)
│
├── scripts/                    # Diagnostic & Utility Scripts
│   ├── test_gemini_live.py     # Diagnostic driver for Gemini 3.1 Live WebSockets
│   ├── test_audio_capture.py   # Test mic input & speaker output hardware
│   ├── test_hardware.py       # Test Arduino USB serial & jaw servo lip-sync
│   ├── list_audio_devices.py   # Scan system microphones and speakers
│   ├── find_arduino.py         # Detect Arduino USB serial port (/dev/ttyUSB0)
│   ├── fix_pi_audio.sh         # Automatic ALSA / PipeWire fix for Raspberry Pi
│   └── setup_piper.py          # Download Piper TTS Malayalam voice model
│
├── tests/                      # Automated Unit & Integration Tests
│   ├── test_event_bus.py       # EventBus pub/sub tests
│   ├── test_runtime_state.py   # Robot state machine transition tests
│   └── test_wake_interruption.py # Wake-word interruption tests
│
└── src/                        # Core Source Code Package
    ├── config/                 # Environment & settings loader (settings.py)
    ├── core/                   # Master controller, state machine, event bus
    │   ├── robot_controller.py # Primary orchestrator
    │   ├── runtime.py          # Turn lifecycle manager
    │   ├── state.py            # Robot state machine (IDLE, LISTENING, THINKING, SPEAKING)
    │   ├── event_bus.py        # Async Pub/Sub event bus
    │   └── events.py           # Strongly-typed system events
    └── services/               # Modular Feature Services
        ├── realtime/           # Gemini 3.1 Live WebSocket provider (gemini_live_provider.py)
        ├── hardware/           # Serial communication to Arduino (serial_controller.py)
        ├── speech/             # STT (Whisper & Deepgram) + Wake word detector
        ├── llm/                # LLM brain services (OpenAI, Anthropic, OpenRouter)
        └── tts/                # TTS voice synthesis (Piper, ElevenLabs, gTTS, OpenAI)
```

---

## 3. Detailed Data Flow & Execution Sequence

```
1. main.py
   └── Loads Settings (src/config/settings.py)
   └── Instantiates RobotController (src/core/robot_controller.py)
       ├── Initializes SerialController (USB Arduino @ /dev/ttyUSB0)
       ├── Sets up EventBus (Pub/Sub for StateChangeEvent & SpeechAmplitudeEvent)
       └── Starts Engine Mode:
           ├── REALTIME: GeminiLiveProvider (src/services/realtime/gemini_live_provider.py)
           │   ├── 1s Room Noise Auto-Calibration ➔ Sets speech_threshold
           │   ├── Mic Callback ➔ Audio Queue ➔ VAD Silence Limit Check
           │   ├── session.send_client_content(turns=[...], turn_complete=True)
           │   └── Response Stream ➔ Speaker Playback + RMS Jaw Servo Intensity (0-100)
           └── 3-STEP: SpeechRecognizer ➔ LLMService ➔ TTSService
```

---

## 4. Troubleshooting & Modifying Behavior

### A. If Nila cuts off your speech prematurely mid-sentence:
In `.env`, increase `GEMINI_LIVE_SILENCE_CHUNKS` (default: 18 chunks ~= 1.15 seconds pause allowed):
```env
GEMINI_LIVE_SILENCE_CHUNKS=20
```

### B. Modifying Personality & System Instruction:
In `.env`, update `LLM_SYSTEM_PROMPT`:
```env
LLM_SYSTEM_PROMPT="You are Nila, a funny humanoid robot built by Robuverse in Kerala..."
```

### C. Changing Gemini Live Speaking Voice:
In `.env`, update `GEMINI_LIVE_VOICE` (Options: `Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`):
```env
GEMINI_LIVE_VOICE=Puck
```

---

## 5. Future Developer Roadmap (Where to add new code)

Follow these structural guidelines when expanding NILA-V2:

| Feature Area | Recommended File Path | Implementation Pattern |
| :--- | :--- | :--- |
| **📱 Next.js / Flutter App Control API** | `src/api/server.py` | Create a FastAPI server that exposes REST/WebSocket routes for the frontend to switch modes, edit prompts, trigger speech, or monitor state. |
| **🤖 Agent Workflows & Tools** | `src/tools/robot_actions.py` | Write Python tool functions (e.g. `move_arm()`, `search_knowledge()`) and register them in `GeminiLiveProvider` under `types.LiveConnectConfig(tools=[...])`. |
| **📷 Camera & Vision** | `src/services/vision/camera_service.py` | Stream JPEG camera frames into `session.send_client_content(...)` so Gemini Live can "see" while speaking! |
| **🧠 Long-Term Memory / RAG** | `src/services/memory/db_service.py` | Store conversation summaries in SQLite/ChromaDB and inject facts into `LLM_SYSTEM_PROMPT`. |
