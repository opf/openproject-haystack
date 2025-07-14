"""Configuration settings for the Haystack application."""

import os
from typing import Optional


class Settings:
    """Application settings."""
    
    # Ollama configuration
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://ollama:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral:latest")
    
    # Generation parameters
    GENERATION_NUM_PREDICT: int = int(os.getenv("GENERATION_NUM_PREDICT", "1000"))
    GENERATION_TEMPERATURE: float = float(os.getenv("GENERATION_TEMPERATURE", "0.7"))
    
    # API configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
