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
    
    # Service Providers
    SPEECH_PROVIDER: str = Field(default="google", env="SPEECH_PROVIDER")  # "google" or "whisper"
    TTS_PROVIDER: str = Field(default="gtts", env="TTS_PROVIDER")  # "gtts", "openai", "google_cloud", "azure"
    LLM_PROVIDER: str = Field(default="openai", env="LLM_PROVIDER")  # "openai", "anthropic", "google", "openrouter"
    
    # OpenRouter Settings
    OPENROUTER_API_KEY: str = Field(default="", env="OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = Field(default="", env="OPENROUTER_MODEL")
    
    # Whisper Settings (for Malayalam + English)
    WHISPER_MODEL: str = Field(default="base", env="WHISPER_MODEL")  # tiny, base, small, medium, large
    WHISPER_LANGUAGE: str = Field(default="en", env="WHISPER_LANGUAGE")  # "en" for English, "ml" for Malayalam, "auto" for auto-detect
    WHISPER_DEVICE: str = Field(default="cpu", env="WHISPER_DEVICE")  # "cpu" or "cuda" (for GPU)
    
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
- Keep responses short and natural (1-2 sentences usually)
- Use casual, conversational language

Your style:
- Talk like you're chatting with a friend
- Be witty and make people smile
- Don't be too formal or serious
- If someone speaks Malayalam, respond warmly and naturally
- Be curious and ask fun questions sometimes
- Keep it simple and relatable

Remember: You're Nila - funny, cool, and friendly. Just be yourself and keep it real!""",
        env="LLM_SYSTEM_PROMPT"
    )
    
    # TTS Settings
    TTS_VOICE_MALAYALAM: str = Field(default="ml-IN-Wavenet-A", env="TTS_VOICE_MALAYALAM")  # Google Cloud voice for Malayalam
    TTS_VOICE_ENGLISH: str = Field(default="en-IN-Wavenet-D", env="TTS_VOICE_ENGLISH")  # Google Cloud voice for English
    TTS_SPEAKING_RATE: float = Field(default=1.0, env="TTS_SPEAKING_RATE")  # 0.25 to 4.0 (1.0 = normal)
    TTS_PITCH: float = Field(default=0.0, env="TTS_PITCH")  # -20.0 to 20.0 (0.0 = normal)
    TTS_VOLUME_GAIN_DB: float = Field(default=0.0, env="TTS_VOLUME_GAIN_DB")  # Volume adjustment in dB
    TTS_LANGUAGE: str = Field(default="auto", env="TTS_LANGUAGE")  # "en", "ml", or "auto" for auto-detect
    STT_LANGUAGE: str = Field(default="en-IN", env="STT_LANGUAGE")
    
    # gTTS Settings (for free TTS)
    GTTS_TLD: str = Field(default="co.in", env="GTTS_TLD")  # Top-level domain: "com", "co.uk", "com.au", "co.in" (affects accent)
    GTTS_SLOW: bool = Field(default=False, env="GTTS_SLOW")  # Slow speech: True or False
    GTTS_LANG: str = Field(default="en", env="GTTS_LANG")  # Language code: "en", "en-us", "en-uk", "en-au", etc.
    
    # OpenAI TTS Settings
    OPENAI_TTS_MODEL: str = Field(default="tts-1", env="OPENAI_TTS_MODEL")  # "tts-1" (fast) or "tts-1-hd" (high quality)
    OPENAI_TTS_VOICE: str = Field(default="nova", env="OPENAI_TTS_VOICE")  # "alloy", "echo", "fable", "onyx", "nova", "shimmer"
    OPENAI_TTS_SPEED: float = Field(default=1.0, env="OPENAI_TTS_SPEED")  # 0.25 to 4.0 (1.0 = normal)
    OPENAI_TTS_FORMAT: str = Field(default="mp3", env="OPENAI_TTS_FORMAT")  # "mp3", "opus", "aac", "flac"
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="data/logs/robot.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
