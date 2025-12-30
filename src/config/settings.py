import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # API Keys
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: str = Field(default="", env="GOOGLE_API_KEY")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="", env="GOOGLE_APPLICATION_CREDENTIALS")  # Path to Google Cloud JSON
    DEEPGRAM_API_KEY: str = Field(default="", env="DEEPGRAM_API_KEY")  # Deepgram API key for STT
    
    # Service Providers
    SPEECH_PROVIDER: str = Field(default="whisper", env="SPEECH_PROVIDER")  # "google" or "whisper"
    TTS_PROVIDER: str = Field(default="piper", env="TTS_PROVIDER")  # "gtts", "openai", "google_cloud", "azure", "piper"
    LLM_PROVIDER: str = Field(default="openai", env="LLM_PROVIDER")  # "openai", "anthropic", "google", "openrouter"
    
    # OpenRouter Settings
    OPENROUTER_API_KEY: str = Field(default="", env="OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = Field(default="", env="OPENROUTER_MODEL")
    
    # Whisper Settings (for Malayalam + English)
    WHISPER_MODEL: str = Field(default="tiny", env="WHISPER_MODEL")  # tiny, base, small, medium, large
    
    # Language Selection:
    # "auto" = Auto-detects language (Supports both English & Malayalam, slightly slower)
    # "en"   = Forces English (Fastest, best for English-only)
    # "ml"   = Forces Malayalam (Best if you ONLY speak Malayalam)
    WHISPER_LANGUAGE: str = Field(default="auto", env="WHISPER_LANGUAGE")
    
    WHISPER_DEVICE: str = Field(default="cpu", env="WHISPER_DEVICE")  # "cpu" or "cuda" (for GPU)
    
    # Deepgram STT Settings
    DEEPGRAM_MODEL: str = Field(default="nova-2", env="DEEPGRAM_MODEL")  # "nova-2", "enhanced", "base", "whisper"
    DEEPGRAM_LANGUAGE: str = Field(default="en-US", env="DEEPGRAM_LANGUAGE")  # Language code or "auto" for detection
    DEEPGRAM_SMART_FORMAT: bool = Field(default=True, env="DEEPGRAM_SMART_FORMAT")  # Enable smart formatting
    
    # LLM Settings
    LLM_MODEL: str = Field(default="gpt-3.5-turbo", env="LLM_MODEL")  # Model name for the provider
    LLM_MAX_TOKENS: int = Field(default=30, env="LLM_MAX_TOKENS")  # Max tokens in response
    LLM_TEMPERATURE: float = Field(default=0.7, env="LLM_TEMPERATURE")  # Creativity (0.0-2.0)
    LLM_MAX_HISTORY: int = Field(default=10, env="LLM_MAX_HISTORY")  # Conversation history to keep
    LLM_SYSTEM_PROMPT: str = Field(
        default="""You are Nila, a funny, cool, and friendly AI assistant. You're like a cool friend from Kerala who speaks simple, casual English.

Your personality:
- Be funny, witty, and have a great sense of humor
- Keep it cool, relaxed, and easy-going
- Use simple, everyday English - no fancy words
- Be friendly like a good friend from Kerala
- Be helpful and genuine

CRITICAL RULES FOR VOICE OUTPUT:
- KEEP RESPONSES VERY SHORT (1-2 sentences max).
- DO NOT USE EMOJIS (🚫 No emojis allowed).
- DO NOT use markdown formatting (no bold, italic, etc).
- DO NOT use hashtags or special characters.
- Just pure, spoken text.

Your style:
- Talk like you're chatting with a friend
- Be witty and make people smile
- Don't be too formal or serious
- If someone speaks Malayalam, respond warmly and naturally
- Be curious and ask fun questions sometimes
- Keep it simple and relatable

Language Handling:
- If the user speaks Malayalam (or Manglish like "Sugamano"), respond in native Malayalam script (Unicode).
- Example: "സുഖമാണോ!", "എന്താ വിശേഷം?".
- DO NOT use Manglish. Use pure Malayalam script.
- The TTS engine (Piper) can now read Malayalam script perfectly.
- If the user speaks English, respond in English.
- You are bilingual and can switch effortlessly.""",
        env="LLM_SYSTEM_PROMPT"
    )
    
    # TTS Settings
    TTS_VOICE_MALAYALAM: str = Field(default="ml-IN-Wavenet-A", env="TTS_VOICE_MALAYALAM")  # Google Cloud voice for Malayalam
    TTS_VOICE_ENGLISH: str = Field(default="en-IN-Wavenet-D", env="TTS_VOICE_ENGLISH")  # Google Cloud voice for English
    TTS_SPEAKING_RATE: float = Field(default=1.2, env="")  # 0.25 to 4.0 (1.0 = normal, 1.2 = energetic/young)
    TTS_PITCH: float = Field(default=4.0, env="T")  # -20.0 to 20.0 (0.0 = normal, 4.0 = younger)
    TTS_VOLUME_GAIN_DB: float = Field(default=0.0, env="TTS_VOLUME_GAIN_DB")  # Volume adjustment in dB
    TTS_LANGUAGE: str = Field(default="auto", env="TTS_LANGUAGE")  # "en", "ml", or "auto" for auto-detect
    STT_LANGUAGE: str = Field(default="ml-IN", env="STT_LANGUAGE")
    
    # gTTS Settings (for free TTS)
    GTTS_TLD: str = Field(default="co.in", env="GTTS_TLD")  # Top-level domain: "com", "co.uk", "com.au", "co.in" (affects accent)
    GTTS_SLOW: bool = Field(default=False, env="GTTS_SLOW")  # Slow speech: True or False
    GTTS_LANG: str = Field(default="en", env="GTTS_LANG")  # Language code: "en", "en-us", "en-uk", "en-au", etc.
    
    # OpenAI TTS Settings
    OPENAI_TTS_MODEL: str = Field(default="tts-1", env="OPENAI_TTS_MODEL")  # "tts-1" (fast) or "tts-1-hd" (high quality)
    OPENAI_TTS_VOICE: str = Field(default="nova", env="OPENAI_TTS_VOICE")  # "alloy", "echo", "fable", "onyx", "nova", "shimmer"
    OPENAI_TTS_SPEED: float = Field(default=1.0, env="OPENAI_TTS_SPEED")  # 0.25 to 4.0 (1.0 = normal)
    OPENAI_TTS_FORMAT: str = Field(default="mp3", env="OPENAI_TTS_FORMAT")  # "mp3", "opus", "aac", "flac"
    

    # Piper TTS Settings
    PIPER_BINARY_PATH: str = Field(default="tools/piper/piper", env="PIPER_BINARY_PATH")
    PIPER_MODEL_PATH: str = Field(default="data/models/piper/ml_IN-arjun-medium.onnx", env="PIPER_MODEL_PATH")
    PIPER_NOISE_SCALE: float = Field(default=0.667, env="PIPER_NOISE_SCALE")  # Variability/Tone (0.0-1.0)
    PIPER_NOISE_W: float = Field(default=0.8, env="PIPER_NOISE_W")  # Phoneme width noise (0.0-1.0)

    # Hardware / Serial Settings
    SERIAL_PORT: str = Field(default="/dev/ttyUSB0", env="SERIAL_PORT")
    SERIAL_BAUD: int = Field(default=115200, env="SERIAL_BAUD")
    SERVO_MIN_ANGLE: int = Field(default=90, env="SERVO_MIN_ANGLE")
    SERVO_MAX_ANGLE: int = Field(default=130, env="SERVO_MAX_ANGLE")
    
    # Audio Capture Settings (Raspberry Pi / PipeWire)
    AUDIO_SAMPLE_RATE: int = Field(default=16000, env="AUDIO_SAMPLE_RATE")  # Hz (Google STT requires 16kHz)
    AUDIO_CHANNELS: int = Field(default=1, env="AUDIO_CHANNELS")  # Mono
    AUDIO_DEVICE_NAME: str = Field(default="alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-mono", env="AUDIO_DEVICE_NAME")  # Specific Pulse/PipeWire source node
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="data/logs/robot.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
