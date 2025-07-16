"""Ollama-based embedding service for RAG system."""

import logging
import requests
from typing import List, Union
import numpy as np
from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingService:
    """Embedding service using Ollama API."""
    
    def __init__(self, ollama_url: str = None, model_name: str = None):
        """Initialize Ollama embedding service.
        
        Args:
            ollama_url: URL of Ollama service
            model_name: Name of the embedding model
        """
        self.ollama_url = ollama_url or settings.OLLAMA_EMBEDDING_URL
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.embedding_dim = None  # Will be determined from first embedding
        
        # Validate connection and model availability
        self._validate_setup()
    
    def _validate_setup(self):
        """Validate Ollama connection and model availability."""
        try:
            # Check if Ollama is accessible
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            # Check if embedding model is available
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            if self.model_name not in model_names:
                logger.warning(f"Embedding model '{self.model_name}' not found in Ollama. Available models: {model_names}")
                logger.info(f"Attempting to pull model '{self.model_name}'...")
                self._pull_model()
            else:
                logger.info(f"Embedding model '{self.model_name}' is available")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama at {self.ollama_url}: {e}")
            raise RuntimeError(f"Cannot connect to Ollama embedding service: {e}")
    
    def _pull_model(self):
        """Pull the embedding model if not available."""
        try:
            logger.info(f"Pulling embedding model '{self.model_name}' from Ollama...")
            response = requests.post(
                f"{self.ollama_url}/api/pull",
                json={"name": self.model_name},
                timeout=300  # 5 minutes timeout for model pulling
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled embedding model '{self.model_name}'")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to pull embedding model '{self.model_name}': {e}")
            raise RuntimeError(f"Cannot pull embedding model: {e}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array containing the embedding
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": self.model_name,
                    "prompt": text
                },
                timeout=30
            )
            response.raise_for_status()
            
            embedding_data = response.json()
            embedding = np.array(embedding_data["embedding"], dtype=np.float32)
            
            # Set embedding dimension on first call
            if self.embedding_dim is None:
                self.embedding_dim = len(embedding)
                logger.info(f"Embedding dimension: {self.embedding_dim}")
            
            return embedding
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
        except KeyError as e:
            logger.error(f"Invalid response format from Ollama: {e}")
            raise RuntimeError(f"Invalid embedding response: {e}")
    
    def embed_texts(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress (for compatibility)
            
        Returns:
            Numpy array containing all embeddings
        """
        if not texts:
            return np.array([])
        
        embeddings = []
        total = len(texts)
        
        if show_progress:
            logger.info(f"Generating embeddings for {total} texts...")
        
        for i, text in enumerate(texts):
            try:
                embedding = self.embed_text(text)
                embeddings.append(embedding)
                
                if show_progress and (i + 1) % 10 == 0:
                    logger.info(f"Generated embeddings: {i + 1}/{total}")
                    
            except Exception as e:
                logger.error(f"Failed to embed text {i + 1}/{total}: {e}")
                # Continue with other texts, but log the failure
                continue
        
        if not embeddings:
            raise RuntimeError("Failed to generate any embeddings")
        
        if show_progress:
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
        
        return np.array(embeddings, dtype=np.float32)
    
    def encode(self, texts: Union[str, List[str]], show_progress_bar: bool = False) -> np.ndarray:
        """Encode texts to embeddings (sentence-transformers compatible interface).
        
        Args:
            texts: Single text or list of texts to encode
            show_progress_bar: Whether to show progress bar
            
        Returns:
            Numpy array containing embeddings
        """
        if isinstance(texts, str):
            return self.embed_text(texts)
        else:
            return self.embed_texts(texts, show_progress=show_progress_bar)
    
    def get_sentence_embedding_dimension(self) -> int:
        """Get the embedding dimension (sentence-transformers compatible).
        
        Returns:
            Embedding dimension
        """
        if self.embedding_dim is None:
            # Generate a test embedding to determine dimension
            test_embedding = self.embed_text("test")
            self.embedding_dim = len(test_embedding)
        
        return self.embedding_dim
    
    def get_model_info(self) -> dict:
        """Get information about the embedding model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "ollama_url": self.ollama_url,
            "embedding_dimension": self.embedding_dim,
            "service_type": "ollama"
        }
