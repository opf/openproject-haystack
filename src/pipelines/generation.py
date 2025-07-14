"""Haystack pipeline for text generation."""

from haystack_integrations.components.generators.ollama import OllamaGenerator
from config.settings import settings
from src.models.schemas import ChatMessage, ChatCompletionRequest
from typing import List, Tuple
import uuid
import re


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
    
    def chat_completion(self, request: ChatCompletionRequest) -> Tuple[str, dict]:
        """Generate chat completion response.
        
        Args:
            request: Chat completion request with messages and parameters
            
        Returns:
            Tuple of (generated_response, usage_info)
        """
        # Convert messages to a single prompt
        prompt = self._messages_to_prompt(request.messages)
        
        # Create generator with request-specific parameters
        generator = OllamaGenerator(
            model=request.model,
            url=settings.OLLAMA_URL,
            generation_kwargs={
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stop": request.stop or []
            }
        )
        
        # Generate response
        result = generator.run(prompt)
        response_text = result["replies"][0]
        
        # Calculate token usage (approximate)
        prompt_tokens = self._estimate_tokens(prompt)
        completion_tokens = self._estimate_tokens(response_text)
        
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
        
        return response_text, usage
    
    def _messages_to_prompt(self, messages: List[ChatMessage]) -> str:
        """Convert chat messages to a single prompt string.
        
        Args:
            messages: List of chat messages
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        for message in messages:
            if message.role == "system":
                prompt_parts.append(f"System: {message.content}")
            elif message.role == "user":
                prompt_parts.append(f"User: {message.content}")
            elif message.role == "assistant":
                prompt_parts.append(f"Assistant: {message.content}")
        
        # Add final prompt for assistant response
        prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        This is a rough approximation. For more accurate counting,
        you might want to use a proper tokenizer.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        return max(1, len(text) // 4)
    
    def get_available_models(self) -> List[str]:
        """Get list of available models.
        
        Returns:
            List of available model names
        """
        # For now, return the configured model
        # In a real implementation, you might query Ollama for available models
        return [settings.OLLAMA_MODEL, "mistral:latest", "llama2:latest", "codellama:latest"]


# Global pipeline instance
generation_pipeline = GenerationPipeline()
