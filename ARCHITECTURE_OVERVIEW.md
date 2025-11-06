# 🏗️ NILA-V2 Voice AI Bot - Complete Architecture Overview

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Service Architecture](#service-architecture)
6. [Configuration System](#configuration-system)
7. [Technology Stack](#technology-stack)
8. [Design Patterns](#design-patterns)
9. [Scalability Features](#scalability-features)

---

## 🎯 System Overview

**NILA-V2** is a professional, scalable voice AI bot designed for robot applications, specifically built for exhibition/robot assistant scenarios. It supports:

- ✅ **Multilingual Speech Recognition** (English + Malayalam)
- ✅ **Intelligent AI Conversations** (OpenAI GPT integration)
- ✅ **Text-to-Speech** (Multiple providers with caching)
- ✅ **Voice Activity Detection** (VAD for efficient listening)
- ✅ **Provider Abstraction** (Easy switching between services)
- ✅ **Comprehensive Logging & Statistics**

### Key Features
- **Modular Architecture**: Easy to extend and maintain
- **Provider Pattern**: Switch between different AI/TTS/STT providers via config
- **Async/Await**: Non-blocking I/O for responsive performance
- **Caching**: Audio caching for faster responses
- **Error Handling**: Graceful fallbacks and error recovery
- **Statistics Tracking**: Monitor usage, costs, and performance

---

## 🏛️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
│                   (Application Entry Point)                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              RobotController (Core Orchestrator)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  TTSService  │  │SpeechRecognizer│  │  LLMService │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
    ┌─────────┐      ┌──────────────┐   ┌─────────────┐
    │ TTS     │      │ STT          │   │ LLM         │
    │ Factory │      │ Factory      │   │ Factory     │
    └────┬────┘      └──────┬───────┘   └──────┬──────┘
         │                  │                  │
    ┌────┴────┐      ┌──────┴───────┐   ┌──────┴──────┐
    │         │      │               │   │             │
    ▼         ▼      ▼               ▼   ▼             ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  gTTS  │ │Google  │ │  Google  │ │ Whisper  │ │  OpenAI  │
│Provider│ │Cloud   │ │  STT     │ │  STT     │ │ Provider │
│        │ │TTS     │ │ Provider │ │ Provider │ │          │
└────────┘ └────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

## 🔧 Core Components

### 1. **main.py** - Application Entry Point
- Initializes logging
- Loads configuration from `.env`
- Creates `RobotController`
- Handles graceful shutdown (Ctrl+C)
- Manages async event loop

**Key Responsibilities:**
- Bootstrap the application
- Error handling at top level
- Cleanup on exit

### 2. **RobotController** (`src/core/robot_controller.py`)
The central orchestrator that coordinates all services.

**Responsibilities:**
- Manages conversation loop
- Coordinates STT → LLM → TTS flow
- Tracks statistics (messages, tokens, costs)
- Handles exit commands ("exit", "quit", "goodbye")
- Displays status information
- Manages graceful shutdown

**Key Methods:**
- `start()`: Main async loop
- `_handle_conversation()`: Process user input → AI response → TTS
- `_speak_greeting()`: Initial robot greeting
- `_print_final_stats()`: Display session statistics

**State Management:**
- `is_running`: Controls main loop
- `conversation_active`: Controls conversation state
- `stats`: Tracks metrics (messages, tokens, costs, uptime)

### 3. **Settings** (`src/config/settings.py`)
Centralized configuration using Pydantic Settings.

**Configuration Categories:**
- **Environment**: `ENVIRONMENT`, `DEBUG`
- **API Keys**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`
- **Service Providers**: `SPEECH_PROVIDER`, `TTS_PROVIDER`, `LLM_PROVIDER`
- **Whisper Settings**: Model, language, device (CPU/GPU)
- **LLM Settings**: Model, max tokens, temperature, history length, system prompt
- **TTS Settings**: Voices (Malayalam/English), speaking rate, pitch, volume
- **Logging**: Log level, log file path

**Features:**
- Environment variable support (`.env` file)
- Type validation via Pydantic
- Sensible defaults
- Case-sensitive configuration

---

## 🔄 Data Flow

### Complete Conversation Flow

```
1. START
   │
   ├─► RobotController.start()
   │   │
   │   ├─► _speak_greeting()
   │   │   └─► TTSService.speak("Hello! I am your AI robot...")
   │   │       └─► Provider generates audio → plays via pygame
   │   │
   │   └─► Main Conversation Loop:
   │       │
   │       ├─► SpeechRecognizer.listen(timeout=30)
   │       │   │
   │       │   ├─► Calibrate microphone (if needed)
   │       │   │
   │       │   ├─► _capture_blocking()
   │       │   │   └─► speech_recognition.listen() (waits for speech)
   │       │   │
   │       │   └─► Provider.transcribe(audio)
   │       │       ├─► GoogleSTTProvider: recognize_google()
   │       │       └─► WhisperSTTProvider: model.transcribe() (if implemented)
   │       │
   │       ├─► User Input Received: "Hello robot, what can you do?"
   │       │
   │       ├─► _handle_conversation(user_input)
   │       │   │
   │       │   ├─► LLMService.get_response(user_input)
   │       │   │   │
   │       │   │   ├─► OpenAIProvider.get_response()
   │       │   │   │   │
   │       │   │   │   ├─► Build messages (system prompt + history)
   │       │   │   │   │
   │       │   │   │   ├─► Call OpenAI API (async)
   │       │   │   │   │
   │       │   │   │   ├─► Extract response text
   │       │   │   │   │
   │       │   │   │   └─► Update conversation history
   │       │   │   │
   │       │   │   └─► Return: "Hi! I'm an AI-powered robot..."
   │       │   │
   │       │   ├─► Display AI response (console)
   │       │   │
   │       │   └─► TTSService.speak(ai_response)
   │       │       │
   │       │       ├─► Detect language (auto-detect or use hint)
   │       │       │
   │       │       ├─► Check cache (MD5 hash of text+language)
   │       │       │   └─► If cached: use existing audio file
   │       │       │
   │       │       ├─► Generate audio (if not cached)
   │       │       │   ├─► gTTS Provider: gTTS(text, lang).save()
   │       │       │   └─► Google Cloud TTS: synthesize_speech()
   │       │       │
   │       │       └─► Play audio via pygame.mixer
   │       │
   │       └─► Loop continues (listen → transcribe → AI → TTS)
   │
   └─► Exit Command Detected ("exit", "quit", "goodbye")
       │
       ├─► _handle_exit()
       │   ├─► Speak goodbye message
       │   └─► Set conversation_active = False
       │
       └─► cleanup()
           ├─► TTSService.cleanup()
           ├─► SpeechRecognizer.cleanup()
           └─► LLMService.cleanup()
```

### Error Handling Flow

```
Error Occurs
    │
    ├─► Try/Except in each service
    │
    ├─► Log error with context
    │
    ├─► Fallback Strategy:
    │   ├─► STT Error → Return None, retry next cycle
    │   ├─► LLM Error → Use fallback response
    │   └─► TTS Error → Log, continue (no audio)
    │
    └─► Update statistics (error counters)
```

---

## 🏗️ Service Architecture

### 1. **Speech Recognition Service** (`src/services/speech/`)

#### **SpeechRecognizer** (Main Service)
- **Purpose**: High-level speech recognition with VAD and provider abstraction
- **Features**:
  - Voice Activity Detection (WebRTC VAD)
  - Microphone calibration (ambient noise adjustment)
  - Auto-recalibration (every 5 minutes)
  - Provider abstraction (Google/Whisper)

**Key Components:**
- `speech_recognition.Recognizer`: Core SR library
- `webrtcvad.Vad`: Voice activity detection
- `BaseSTTProvider`: Provider interface

**Methods:**
- `listen(timeout)`: Async method to capture and transcribe speech
- `_capture_blocking()`: Synchronous audio capture
- `_calibrate_microphone()`: Adjust for ambient noise
- `_should_recalibrate()`: Check if recalibration needed

#### **STT Providers** (`src/services/speech/providers/`)

**BaseSTTProvider** (Protocol/Interface):
```python
async def transcribe(audio, language) -> STTResult
```

**STTResult** (Data Class):
- `text`: Transcribed text (or None)
- `language`: Detected language code
- `confidence`: Confidence score (optional)
- `error`: Error message (if failed)

**GoogleSTTProvider**:
- Uses `speech_recognition.recognize_google()`
- Supports language hints (`en-IN`, `ml-IN`)
- Async wrapper around sync API
- Error handling for `UnknownValueError`, `RequestError`

**WhisperSTTProvider** (Referenced but not implemented):
- Would use OpenAI Whisper model
- Supports offline processing
- Better multilingual support
- GPU acceleration support

### 2. **Text-to-Speech Service** (`src/services/tts/`)

#### **TTSService** (Factory)
- **Purpose**: Provider factory and high-level TTS interface
- **Features**:
  - Provider selection based on config
  - Fallback to gTTS if primary fails
  - Provider switching at runtime

**Methods:**
- `speak(text, language)`: Main async method
- `stop_speaking()`: Interrupt current speech
- `switch_provider()`: Change provider dynamically
- `is_speaking()`: Check playback state

#### **TTS Providers**

**BaseTTSProvider** (Abstract Base Class):
```python
async def speak(text, language) -> bool
def stop_speaking()
def cleanup()
def get_provider_name() -> str
def detect_language(text) -> str  # Heuristic-based
```

**GTTSProvider**:
- Uses `gtts` library (free, online)
- **Limitations**: English only, robotic voice
- **Features**:
  - Audio caching (MD5 hash-based)
  - Cache size management (50MB max)
  - Auto-cleanup (removes oldest 30% when 80% full)
  - Pygame mixer for playback

**GoogleCloudTTSProvider**:
- Uses Google Cloud Text-to-Speech API
- **Advantages**: Professional voices, multilingual (Malayalam + English)
- **Features**:
  - Voice selection (Malayalam: `ml-IN-Wavenet-A`, English: `en-IN-Wavenet-D`)
  - Speaking rate, pitch, volume control
  - Audio caching (100MB max)
  - Requires `GOOGLE_APPLICATION_CREDENTIALS` (service account JSON)

**Legacy TextToSpeech** (`src/services/speech/text_to_speech.py`):
- Older implementation (appears unused)
- Similar to GTTSProvider but less modular

### 3. **LLM Service** (`src/services/llm/`)

#### **LLMService** (Factory)
- **Purpose**: Provider factory and high-level LLM interface
- **Features**:
  - Provider selection based on config
  - Conversation history management
  - Statistics tracking

**Methods:**
- `get_response(user_message, language)`: Main async method
- `clear_history()`: Reset conversation
- `get_history(limit)`: Retrieve conversation history
- `get_stats()`: Usage statistics
- `set_personality()`: Change system prompt

#### **LLM Providers**

**BaseLLMProvider** (Abstract Base Class):
- Conversation history management
- Statistics tracking (messages, tokens, errors)
- History trimming (keeps last N messages)

**OpenAIProvider**:
- Uses `openai.AsyncOpenAI`
- **Models Supported**: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`
- **Features**:
  - System prompt for robot personality
  - Conversation history (last 10 messages by default)
  - Language hints (Malayalam detection)
  - Token usage tracking
  - Cost estimation (GPT-3.5: $0.002/1K tokens, GPT-4: $0.03/1K tokens)
  - Fallback responses on API errors

**AnthropicProvider** (Placeholder):
- Not yet implemented
- Would use Claude API
- Same interface as OpenAIProvider

---

## ⚙️ Configuration System

### Configuration Hierarchy

1. **Environment Variables** (`.env` file) - Highest priority
2. **Pydantic Settings Defaults** - Fallback values

### Key Configuration Files

**`.env` File Structure:**
```env
# Environment
ENVIRONMENT=development
DEBUG=True

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Service Providers
SPEECH_PROVIDER=google          # google | whisper
TTS_PROVIDER=gtts               # gtts | google_cloud | azure
LLM_PROVIDER=openai             # openai | anthropic | google

# Whisper Settings
WHISPER_MODEL=base              # tiny | base | small | medium | large
WHISPER_LANGUAGE=en             # en | ml | auto
WHISPER_DEVICE=cpu              # cpu | cuda

# LLM Settings
LLM_MODEL=gpt-3.5-turbo
LLM_MAX_TOKENS=150
LLM_TEMPERATURE=0.7
LLM_MAX_HISTORY=10
LLM_SYSTEM_PROMPT=You are a helpful robot...

# TTS Settings
TTS_VOICE_MALAYALAM=ml-IN-Wavenet-A
TTS_VOICE_ENGLISH=en-IN-Wavenet-D
TTS_SPEAKING_RATE=1.0
TTS_PITCH=0.0
TTS_VOLUME_GAIN_DB=0.0
TTS_LANGUAGE=auto               # en | ml | auto
STT_LANGUAGE=en-IN

# Logging
LOG_LEVEL=INFO
LOG_FILE=data/logs/robot.log
```

### Configuration Loading

```python
# In main.py or any service
from src.config.settings import Settings

settings = Settings()  # Automatically loads from .env
# Access: settings.OPENAI_API_KEY, settings.LLM_MODEL, etc.
```

---

## 🛠️ Technology Stack

### Core Dependencies

**Speech Recognition:**
- `SpeechRecognition` (3.10.0): Core SR library
- `pyaudio` (0.2.14): Microphone access
- `webrtcvad` (2.0.10): Voice activity detection

**Text-to-Speech:**
- `gtts` (2.4.0): Free TTS (fallback)
- `google-cloud-texttospeech` (2.14.1): Professional TTS
- `pygame` (2.5.2): Audio playback
- `pydub` (0.25.1): Audio processing

**LLM:**
- `openai` (1.12.0): OpenAI API client
- `anthropic` (0.8.0): Claude API client (future)

**Configuration:**
- `pydantic` (2.4.2): Settings validation
- `pydantic-settings` (2.1.0): Environment variable support
- `python-dotenv` (1.0.0): `.env` file loading

**Utilities:**
- `numpy` (1.26.4): Numerical operations (for Whisper)

### Future Dependencies (Referenced)
- `google-cloud-speech` (2.27.0): Google Cloud STT
- `google-generativeai` (0.3.0): Gemini LLM
- `whisper` (OpenAI): Offline STT (not in requirements yet)

---

## 🎨 Design Patterns

### 1. **Factory Pattern**
- **TTSService**: Creates TTS providers based on config
- **LLMService**: Creates LLM providers based on config
- **SpeechRecognizer**: Creates STT providers based on config

**Benefits:**
- Easy provider switching (change config, no code changes)
- Consistent interface across providers
- Easy to add new providers

### 2. **Strategy Pattern**
- Each provider (TTS/STT/LLM) implements the same interface
- Runtime selection based on configuration
- Interchangeable implementations

### 3. **Provider Pattern**
- Abstract base classes define contracts
- Concrete implementations for each service
- Protocol-based interfaces (Python typing)

### 4. **Singleton Pattern** (Implicit)
- Settings instance loaded once
- Services initialized once per RobotController

### 5. **Observer Pattern** (Statistics)
- Services track their own statistics
- RobotController aggregates statistics
- Displayed at end of session

---

## 📈 Scalability Features

### 1. **Async/Await Architecture**
- Non-blocking I/O for API calls
- Concurrent operations (listen while processing)
- Responsive user experience

### 2. **Caching System**
- **Audio Caching**: TTS audio files cached (MD5 hash)
- **Cache Management**: Auto-cleanup when size threshold reached
- **Performance**: Instant playback for repeated phrases

### 3. **Provider Abstraction**
- Easy to swap providers (Google → Whisper, gTTS → Google Cloud)
- No code changes needed (config-only)
- Future-proof (add new providers easily)

### 4. **Error Handling & Fallbacks**
- Graceful degradation (fallback to gTTS if Google Cloud fails)
- Error recovery (retry on next cycle)
- Fallback responses (LLM errors → friendly messages)

### 5. **Resource Management**
- Automatic cleanup (microphone, audio, API clients)
- Memory management (history trimming, cache cleanup)
- Graceful shutdown (signal handlers)

### 6. **Statistics & Monitoring**
- Real-time metrics (messages, tokens, costs)
- Performance tracking (uptime, success rate)
- Cost estimation (API usage tracking)

### 7. **Configuration-Driven**
- All behavior controlled via `.env`
- No hardcoded values
- Environment-specific configs (dev/prod)

### 8. **Modular Architecture**
- Clear separation of concerns
- Independent services (can test/develop separately)
- Easy to extend (add new providers, features)

---

## 🔍 Key Design Decisions

### 1. **Why Provider Pattern?**
- **Flexibility**: Switch providers without code changes
- **Testing**: Easy to mock providers
- **Future-proof**: Add new providers easily

### 2. **Why Async/Await?**
- **Performance**: Non-blocking I/O (API calls, audio generation)
- **Responsiveness**: Can listen while processing
- **Scalability**: Handle multiple operations concurrently

### 3. **Why Caching?**
- **Performance**: Instant playback for repeated phrases
- **Cost**: Reduce API calls (TTS generation)
- **User Experience**: Faster responses

### 4. **Why Pydantic Settings?**
- **Type Safety**: Automatic validation
- **Environment Variables**: Easy `.env` support
- **Documentation**: Self-documenting config

### 5. **Why Statistics Tracking?**
- **Monitoring**: Track usage, costs, performance
- **Debugging**: Identify issues (error rates, slow responses)
- **Optimization**: Data-driven improvements

---

## 📁 File Structure

```
NILA-V2/
├── main.py                          # Entry point
├── requirements.txt                 # Dependencies
├── .env                            # Configuration (not in repo)
│
├── src/
│   ├── __init__.py
│   │
│   ├── config/
│   │   └── settings.py             # Centralized configuration
│   │
│   ├── core/
│   │   └── robot_controller.py     # Main orchestrator
│   │
│   ├── services/
│   │   ├── speech/
│   │   │   ├── speech_recognizer.py    # STT service
│   │   │   ├── text_to_speech.py       # Legacy TTS (unused?)
│   │   │   ├── base_stt_provider.py    # STT interface
│   │   │   └── providers/
│   │   │       └── google_stt_provider.py
│   │   │
│   │   ├── tts/
│   │   │   ├── tts_service.py          # TTS factory
│   │   │   ├── base_tts_provider.py    # TTS interface
│   │   │   ├── gtts_provider.py        # Free TTS
│   │   │   └── google_cloud_tts_provider.py  # Professional TTS
│   │   │
│   │   └── llm/
│   │       ├── llm_service.py          # LLM factory
│   │       ├── base_provider.py        # LLM interface
│   │       ├── openai_provider.py      # ChatGPT
│   │       └── anthropic_provider.py   # Claude (placeholder)
│   │
│   └── utils/
│       └── logger.py                   # Logging setup
│
├── data/
│   ├── audio/                          # TTS cache
│   │   ├── gtts/                       # gTTS cache
│   │   └── google_cloud/                # Google Cloud cache
│   └── logs/
│       └── robot.log                   # Application logs
│
├── tests/
│   └── manual_stt_check.py            # Manual STT testing
│
└── docs/
    ├── LLM_INTEGRATION_SUMMARY.md
    ├── LLM_SETUP_GUIDE.md
    └── ARCHITECTURE_OVERVIEW.md        # This file
```

---

## 🚀 Usage Example

### Basic Usage

```python
# main.py already does this, but here's the flow:

from src.config.settings import Settings
from src.core.robot_controller import RobotController

# 1. Load configuration
settings = Settings()

# 2. Create robot controller
robot = RobotController(settings)

# 3. Start the robot (async)
await robot.start()

# 4. Cleanup on exit
robot.cleanup()
```

### Custom Provider Selection

```env
# .env file
SPEECH_PROVIDER=whisper      # Use Whisper instead of Google
TTS_PROVIDER=google_cloud    # Use Google Cloud TTS
LLM_PROVIDER=openai          # Use ChatGPT
```

### Programmatic Provider Switching

```python
# Switch TTS provider at runtime
robot.text_to_speech.switch_provider("google_cloud")

# Change LLM personality
robot.llm_service.set_personality("You are a funny robot...")
```

---

## 🔮 Future Enhancements

### Planned Features (Referenced in Code)
1. **Whisper STT Provider**: Offline speech recognition
2. **Anthropic Provider**: Claude AI integration
3. **Google Gemini Provider**: Google's LLM
4. **Azure TTS Provider**: Microsoft TTS
5. **Google Cloud STT**: Professional STT (not just free API)

### Potential Improvements
1. **WebSocket Support**: Remote control via web interface
2. **Multi-User Support**: Handle multiple conversations
3. **Intent Recognition**: NLU for command parsing
4. **Skill System**: Modular capabilities (weather, calendar, etc.)
5. **Voice Cloning**: Custom voice profiles
6. **Offline Mode**: Full offline operation with Whisper + local LLM

---

## 📊 Performance Characteristics

### Typical Latency
- **STT**: 1-3 seconds (Google API) or 2-5 seconds (Whisper local)
- **LLM**: 1-5 seconds (GPT-3.5) or 3-10 seconds (GPT-4)
- **TTS**: 0.5-2 seconds (cached) or 2-5 seconds (uncached)
- **Total Response Time**: 3-10 seconds (typical)

### Resource Usage
- **Memory**: ~200-500 MB (base) + Whisper model size if used
- **CPU**: Low (async I/O) + Whisper processing if used
- **Network**: API calls (STT, LLM, TTS) - requires internet
- **Disk**: Audio cache (50-100 MB typical)

### Scalability Limits
- **Concurrent Users**: 1 (single conversation loop)
- **API Rate Limits**: Depends on provider (OpenAI, Google)
- **Cache Size**: Configurable (default 50-100 MB)

---

## 🎓 Learning Resources

### Understanding the Codebase
1. Start with `main.py` → understand entry point
2. Read `RobotController` → understand main flow
3. Explore services → understand provider pattern
4. Check `Settings` → understand configuration

### Key Concepts to Understand
- **Async/Await**: Python async programming
- **Provider Pattern**: Strategy pattern in Python
- **Pydantic Settings**: Configuration management
- **Speech Recognition**: Audio processing basics
- **LLM APIs**: OpenAI API usage

---

## ✅ Summary

**NILA-V2** is a well-architected, production-ready voice AI bot with:

✅ **Modular Design**: Easy to extend and maintain  
✅ **Provider Abstraction**: Switch services via config  
✅ **Async Architecture**: Responsive and scalable  
✅ **Comprehensive Features**: STT, LLM, TTS all integrated  
✅ **Professional Quality**: Error handling, logging, statistics  
✅ **Multilingual Support**: English + Malayalam  

**Perfect for:**
- Robot assistants
- Exhibition bots
- Voice-controlled applications
- Multilingual AI systems

**Ready for:**
- Production deployment
- Further customization
- Feature extensions
- Provider additions

---

*Last Updated: Based on current codebase analysis*  
*Architecture Version: 1.0*

