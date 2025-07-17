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
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral:7B")

    # Model management
    MODELS_TO_PULL: str = os.getenv("MODELS_TO_PULL", "mistral:latest")
    REQUIRED_MODELS: list = os.getenv("REQUIRED_MODELS", "mistral:latest").split(",")

    # Generation parameters
    GENERATION_NUM_PREDICT: int = int(os.getenv("GENERATION_NUM_PREDICT", "1000"))
    GENERATION_TEMPERATURE: float = float(os.getenv("GENERATION_TEMPERATURE", "0.7"))

    # API configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # RAG Configuration
    DOCUMENTS_PATH: str = os.getenv("DOCUMENTS_PATH", "documents")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "vector_store")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    OLLAMA_EMBEDDING_URL: str = os.getenv("OLLAMA_EMBEDDING_URL", "http://localhost:11434")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    MAX_RETRIEVED_DOCS: int = int(os.getenv("MAX_RETRIEVED_DOCS", "5"))

    # OpenProject configuration
    OPENPROJECT_BASE_URL: str = os.getenv("OPENPROJECT_BASE_URL", "")
    OPENPROJECT_API_KEY: str = os.getenv("OPENPROJECT_API_KEY", "")


settings = Settings()
