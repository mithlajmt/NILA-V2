import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # API Keys (for future steps)
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    GOOGLE_API_KEY: str = Field(default="", env="GOOGLE_API_KEY")
    
    # Service Providers
    SPEECH_PROVIDER: str = Field(default="google", env="SPEECH_PROVIDER")
    TTS_PROVIDER: str = Field(default="google", env="TTS_PROVIDER")
    LLM_PROVIDER: str = Field(default="openai", env="LLM_PROVIDER")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="data/logs/robot.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
