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
    TTS_PROVIDER: str = Field(default="gtts", env="TTS_PROVIDER")  # "gtts", "google_cloud", "azure"
    LLM_PROVIDER: str = Field(default="openai", env="LLM_PROVIDER")  # "openai", "anthropic", "google"
    
    # Whisper Settings (for Malayalam + English)
    WHISPER_MODEL: str = Field(default="base", env="WHISPER_MODEL")  # tiny, base, small, medium, large
    WHISPER_LANGUAGE: str = Field(default="en", env="WHISPER_LANGUAGE")  # "en" for English, "ml" for Malayalam, "auto" for auto-detect
    WHISPER_DEVICE: str = Field(default="cpu", env="WHISPER_DEVICE")  # "cpu" or "cuda" (for GPU)
    
    # LLM Settings
    LLM_MODEL: str = Field(default="gpt-3.5-turbo", env="LLM_MODEL")  # Model name for the provider
    LLM_MAX_TOKENS: int = Field(default=150, env="LLM_MAX_TOKENS")  # Max tokens in response
    LLM_TEMPERATURE: float = Field(default=0.7, env="LLM_TEMPERATURE")  # Creativity (0.0-2.0)
    LLM_MAX_HISTORY: int = Field(default=10, env="LLM_MAX_HISTORY")  # Conversation history to keep
    LLM_SYSTEM_PROMPT: str = Field(
        default="You are a helpful, friendly robot assistant at an exhibition. Keep responses brief and engaging.",
        env="LLM_SYSTEM_PROMPT"
    )
    
    # TTS Settings
    TTS_VOICE_MALAYALAM: str = Field(default="ml-IN-Wavenet-A", env="TTS_VOICE_MALAYALAM")  # Google Cloud voice for Malayalam
    TTS_VOICE_ENGLISH: str = Field(default="en-IN-Wavenet-D", env="TTS_VOICE_ENGLISH")  # Google Cloud voice for English
    TTS_SPEAKING_RATE: float = Field(default=1.0, env="TTS_SPEAKING_RATE")  # 0.25 to 4.0 (1.0 = normal)
    TTS_PITCH: float = Field(default=0.0, env="TTS_PITCH")  # -20.0 to 20.0 (0.0 = normal)
    TTS_VOLUME_GAIN_DB: float = Field(default=0.0, env="TTS_VOLUME_GAIN_DB")  # Volume adjustment in dB
    TTS_LANGUAGE: str = Field(default="auto", env="TTS_LANGUAGE")  # "en", "ml", or "auto" for auto-detect
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="data/logs/robot.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
