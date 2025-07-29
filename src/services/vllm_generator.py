"""vLLM Generator for OpenAI-compatible API integration."""

import requests
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from config.settings import settings

logger = logging.getLogger(__name__)


class VLLMGenerator:
    """Generator class for vLLM using OpenAI-compatible API."""
    
    def __init__(self, model: str = None, url: str = None, generation_kwargs: Dict[str, Any] = None):
        """Initialize the vLLM generator.
        
        Args:
            model: Model name (will be overridden to Mixtral 8x22B)
            url: vLLM server URL
            generation_kwargs: Generation parameters
        """
        self.url = url or settings.VLLM_URL
        # Force override to Mixtral 8x22B regardless of input
        self.model = settings.VLLM_MODEL
        self.generation_kwargs = generation_kwargs or {}
        
        # Log model override if different from input
        if model and model != self.model:
            logger.info(f"vLLM model override: {model} -> {self.model}")
        
        # Validate vLLM service is available
        self._validate_service()
    
    def _validate_service(self):
        """Validate that vLLM service is available."""
        try:
            health_url = f"{self.url}/health"
            response = requests.get(health_url, timeout=10)
            response.raise_for_status()
            logger.info(f"vLLM service is healthy at {self.url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"vLLM service unavailable at {self.url}: {e}")
            raise RuntimeError(
                f"vLLM service is not available at {self.url}. "
                f"Please ensure the mixtral-vllm service is running. Error: {e}"
            )
    
    def run(self, prompt: str) -> Dict[str, List[str]]:
        """Generate text from a prompt using vLLM OpenAI-compatible API.
        
        Args:
            prompt: The input prompt for generation
            
        Returns:
            Dictionary with "replies" key containing list of generated responses
        """
        try:
            # Prepare the chat completion request
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.generation_kwargs.get("num_predict", 1000),
                "temperature": self.generation_kwargs.get("temperature", 0.7),
                "top_p": self.generation_kwargs.get("top_p", 0.9),
                "stop": self.generation_kwargs.get("stop", [])
            }
            
            # Make request to vLLM
            response = requests.post(
                f"{self.url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120  # Longer timeout for complex generation
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            if "choices" not in data or not data["choices"]:
                raise ValueError("Invalid response from vLLM: missing choices")
            
            # Extract the generated text
            generated_text = data["choices"][0]["message"]["content"]
            
            return {"replies": [generated_text]}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"vLLM request failed: {e}")
            raise RuntimeError(f"Failed to generate text with vLLM: {e}")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse vLLM response: {e}")
            raise RuntimeError(f"Invalid response from vLLM: {e}")
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chat completion using vLLM OpenAI-compatible API.
        
        Args:
            messages: List of chat messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            stop: Stop sequences
            tools: Function calling tools (for BlockNote)
            tool_choice: Tool choice specification
            
        Returns:
            OpenAI-compatible response
        """
        try:
            # Prepare the payload
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.generation_kwargs.get("num_predict", 1000),
                "temperature": temperature or self.generation_kwargs.get("temperature", 0.7),
                "top_p": top_p or self.generation_kwargs.get("top_p", 0.9)
            }
            
            # Add optional parameters
            if stop:
                payload["stop"] = stop
            
            # Handle function calling for BlockNote
            if tools:
                payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
            
            # Make request to vLLM
            response = requests.post(
                f"{self.url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            response.raise_for_status()
            
            # Return the raw response for compatibility
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"vLLM chat completion failed: {e}")
            raise RuntimeError(f"Failed to complete chat with vLLM: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vLLM chat response: {e}")
            raise RuntimeError(f"Invalid chat response from vLLM: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Model information dictionary
        """
        try:
            response = requests.get(
                f"{self.url}/v1/models",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if "data" in data and data["data"]:
                # Return info about our specific model
                for model in data["data"]:
                    if model.get("id") == self.model:
                        return model
            
            # Fallback response
            return {
                "id": self.model,
                "object": "model",
                "created": 0,
                "owned_by": "vllm"
            }
            
        except Exception as e:
            logger.warning(f"Could not get model info: {e}")
            return {
                "id": self.model,
                "object": "model", 
                "created": 0,
                "owned_by": "vllm"
            }
