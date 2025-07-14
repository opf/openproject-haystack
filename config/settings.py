"""Configuration settings for the Haystack application."""

import os
from typing import Optional


class Settings:
    """Application settings."""
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: Optional[str] = os.getenv("LOG_FORMAT", None)
    
    # Ollama configuration
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://ollama:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral:latest")
    
    # Model management
    MODELS_TO_PULL: str = os.getenv("MODELS_TO_PULL", "mistral:latest")
    REQUIRED_MODELS: list = os.getenv("REQUIRED_MODELS", "mistral:latest").split(",")
    
    # Generation parameters
    GENERATION_NUM_PREDICT: int = int(os.getenv("GENERATION_NUM_PREDICT", "1000"))
    GENERATION_TEMPERATURE: float = float(os.getenv("GENERATION_TEMPERATURE", "0.7"))
    
    # API configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
