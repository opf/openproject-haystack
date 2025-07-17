"""Haystack pipeline for text generation."""

from haystack_integrations.components.generators.ollama import OllamaGenerator  # type: ignore  # May not resolve in linter, but needed at runtime
from config.settings import settings
from src.models.schemas import ChatMessage, ChatCompletionRequest, WorkPackage
from src.templates.report_templates import ProjectReportAnalyzer, ProjectStatusReportTemplate
from typing import List, Tuple, Dict, Any
import uuid
import re
import requests
import logging

# Ensure ProjectReportAnalyzer and ProjectStatusReportTemplate use src.models.schemas.WorkPackage
# (If needed, update their imports in src/templates/report_templates.py)

logger = logging.getLogger(__name__)


class GenerationPipeline:
    """Pipeline for text generation using Ollama."""

    def __init__(self):
        """Initialize the generation pipeline."""
        # Validate that required models are available
        self._validate_models()

        self.generator = OllamaGenerator(
            model=settings.OLLAMA_MODEL,
            url=settings.OLLAMA_URL,
            generation_kwargs={
                "num_predict": settings.GENERATION_NUM_PREDICT,
                "temperature": settings.GENERATION_TEMPERATURE
            }
        )

    def _validate_models(self):
        """Validate that required models are available in Ollama."""
        try:
            available_models = self._get_ollama_models()
            required_models = [model.strip() for model in settings.REQUIRED_MODELS if model.strip()]

            missing_models = []
            for model in required_models:
                if model not in available_models:
                    missing_models.append(model)

            if missing_models:
                logger.error(f"Missing required models: {missing_models}")
                logger.error(f"Available models: {available_models}")
                raise RuntimeError(
                    f"Required models not found: {missing_models}. "
                    f"Available models: {available_models}. "
                    f"Please ensure the ollama-init service has completed successfully."
                )

            logger.info(f"All required models are available: {required_models}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama service: {e}")
            raise RuntimeError(
                f"Cannot connect to Ollama service at {settings.OLLAMA_URL}. "
                f"Please ensure the Ollama service is running and accessible."
            )

    def _get_ollama_models(self) -> List[str]:
        """Get list of models available in Ollama.

        Returns:
            List of available model names
        """
        try:
            response = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch models from Ollama: {e}")
            raise

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

    def generate_project_status_report(
        self,
        project_id: str,
        project_type: str,
        openproject_base_url: str,
        work_packages: List[WorkPackage],
        template_name: str = "default"
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate a project status report from work packages with RAG enhancement.

        Args:
            project_id: OpenProject project ID
            project_type: Type of project (portfolio, program, project)
            openproject_base_url: Base URL of OpenProject instance
            work_packages: List of work packages to analyze
            template_name: Name of the report template to use

        Returns:
            Tuple of (generated_report, analysis_data)
        """
        # Analyze work packages
        analyzer = ProjectReportAnalyzer()
        analysis = analyzer.analyze_work_packages(work_packages)

        # Enhance with RAG context
        try:
            from src.pipelines.rag_pipeline import rag_pipeline
            rag_context = rag_pipeline.enhance_project_report_context(
                project_id=project_id,
                project_type=project_type,
                work_packages=work_packages,
                analysis=analysis
            )
            logger.info("Enhanced report with RAG context")
        except Exception as e:
            logger.warning(f"Could not enhance with RAG context: {e}")
            rag_context = {'pmflex_context': ''}

        # Create report prompt using template with RAG enhancement
        template = ProjectStatusReportTemplate()
        prompt = template.create_enhanced_report_prompt(
            project_id=project_id,
            project_type=project_type,
            openproject_base_url=openproject_base_url,
            work_packages=work_packages,
            analysis=analysis,
            pmflex_context=rag_context.get('pmflex_context', '')
        )

        # Generate report using LLM
        generator = OllamaGenerator(
            model=settings.OLLAMA_MODEL,
            url=settings.OLLAMA_URL,
            generation_kwargs={
                "num_predict": 2500,  # Longer reports with RAG context need more tokens
                "temperature": 0.3,   # Lower temperature for more consistent reports
            }
        )

        result = generator.run(prompt)
        report_text = result["replies"][0]

        # Add RAG context info to analysis
        analysis['rag_context'] = rag_context

        return report_text, analysis

    def get_available_models(self) -> List[str]:
        """Get list of available models.

        Returns:
            List of available model names
        """
        try:
            return self._get_ollama_models()
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            # Fallback to configured model
            return [settings.OLLAMA_MODEL]


# Global pipeline instance
generation_pipeline = GenerationPipeline()
