"""Haystack pipeline for text generation."""

from haystack_integrations.components.generators.ollama import OllamaGenerator
from config.settings import settings


class GenerationPipeline:
    """Pipeline for text generation using Ollama."""
    
    def __init__(self):
        """Initialize the generation pipeline."""
        self.generator = OllamaGenerator(
            model=settings.OLLAMA_MODEL,
            url=settings.OLLAMA_URL,
            generation_kwargs={
                "num_predict": settings.GENERATION_NUM_PREDICT,
                "temperature": settings.GENERATION_TEMPERATURE
            }
        )
    
    def generate(self, prompt: str) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: The input prompt for generation
            
        Returns:
            Generated text response
        """
        result = self.generator.run(prompt)
        return result["replies"][0]


# Global pipeline instance
generation_pipeline = GenerationPipeline()
