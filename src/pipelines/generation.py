"""Haystack pipeline for text generation."""

from haystack_integrations.components.generators.ollama import OllamaGenerator
from config.settings import settings
from src.models.schemas import ChatMessage, ChatCompletionRequest, WorkPackage, Tool, ToolChoice, FunctionCall
from src.templates.report_templates import ProjectReportAnalyzer, ProjectStatusReportTemplate
from typing import List, Tuple, Dict, Any
import uuid
import re
import requests
import logging
import json

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
        # Check if this is a BlockNote function calling request
        if self._is_blocknote_request(request):
            return self._handle_blocknote_function_call(request)
        
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
    
    def generate_project_management_hints(
        self,
        project_id: str,
        project_type: str,
        openproject_base_url: str,
        checks_results: Dict[str, Any],
        pmflex_context: str = ""
    ) -> str:
        """Generate German project management hints from check results.
        
        Args:
            project_id: OpenProject project ID
            project_type: Type of project
            openproject_base_url: Base URL of OpenProject instance
            checks_results: Results from the 10 automated checks
            pmflex_context: PMFlex context from RAG system
            
        Returns:
            Generated hints in JSON format
        """
        from src.templates.report_templates import ProjectManagementHintsTemplate
        
        # Create hints prompt using template
        template = ProjectManagementHintsTemplate()
        prompt = template.create_hints_prompt(
            project_id=project_id,
            project_type=project_type,
            openproject_base_url=openproject_base_url,
            checks_results=checks_results,
            pmflex_context=pmflex_context
        )
        
        # Generate hints using LLM with specific parameters for JSON output
        generator = OllamaGenerator(
            model=settings.OLLAMA_MODEL,
            url=settings.OLLAMA_URL,
            generation_kwargs={
                "num_predict": 2000,  # Sufficient for JSON response
                "temperature": 0.2,   # Lower temperature for more consistent JSON
                "format": "json"      # Request JSON format if supported
            }
        )
        
        result = generator.run(prompt)
        hints_json = result["replies"][0]
        
        return hints_json
    
    def _is_blocknote_request(self, request: ChatCompletionRequest) -> bool:
        """Check if this is a BlockNote function calling request.
        
        Args:
            request: Chat completion request
            
        Returns:
            True if this is a BlockNote request
        """
        if not request.tools or not request.tool_choice:
            return False
        
        # Check if there's a "json" function tool
        for tool in request.tools:
            if tool.function.name == "json":
                return True
        
        # Check if tool_choice specifies the "json" function
        if (request.tool_choice and 
            request.tool_choice.type == "function" and 
            request.tool_choice.function.get("name") == "json"):
            return True
        
        return False
    
    def _handle_blocknote_function_call(self, request: ChatCompletionRequest) -> Tuple[str, dict]:
        """Handle BlockNote function calling request.
        
        Args:
            request: Chat completion request with BlockNote function calling
            
        Returns:
            Tuple of (function_call_response, usage_info)
        """
        logger.info("Processing BlockNote function calling request")
        
        # Find the json function tool
        json_tool = None
        for tool in request.tools:
            if tool.function.name == "json":
                json_tool = tool
                break
        
        if not json_tool:
            raise ValueError("No 'json' function found in tools")
        
        # Create enhanced prompt for BlockNote operations
        prompt = self._create_blocknote_prompt(request.messages, json_tool)
        
        # Create generator with BlockNote-specific parameters
        generator = OllamaGenerator(
            model=request.model,
            url=settings.OLLAMA_URL,
            generation_kwargs={
                "num_predict": request.max_tokens or 1000,
                "temperature": request.temperature or 0.1,  # Lower temperature for more consistent JSON
                "top_p": request.top_p or 0.9,
                "stop": request.stop or [],
                "format": "json"  # Request JSON format if supported by Ollama
            }
        )
        
        # Generate response
        result = generator.run(prompt)
        response_text = result["replies"][0]
        
        # Process and validate the response
        function_arguments = self._process_blocknote_response(response_text, json_tool)
        
        # Calculate token usage
        prompt_tokens = self._estimate_tokens(prompt)
        completion_tokens = self._estimate_tokens(function_arguments)
        
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
        
        # Return as function call format (the API endpoint will format this properly)
        return function_arguments, usage
    
    def _create_blocknote_prompt(self, messages: List[ChatMessage], json_tool: Tool) -> str:
        """Create an enhanced prompt for BlockNote operations.
        
        Args:
            messages: Original chat messages
            json_tool: The JSON function tool definition
            
        Returns:
            Enhanced prompt for BlockNote operations
        """
        # Convert messages to prompt
        base_prompt = self._messages_to_prompt(messages)
        
        # Add BlockNote-specific instructions
        blocknote_instructions = f"""

IMPORTANT: You must respond with ONLY valid JSON that matches the exact schema provided. Do not include any explanatory text, markdown formatting, or additional commentary.

The JSON schema you must follow is:
{json.dumps(json_tool.function.parameters, indent=2)}

Your response must be a valid JSON object that can be parsed directly. The response should contain operations that manipulate the document blocks according to the user's request.

Remember:
- Each list item should be a separate block
- Block IDs must be preserved exactly (including trailing $)
- Use the cursor position to determine where to insert new content
- Prefer updating existing blocks over removing and adding when possible

Respond with ONLY the JSON object, no other text:"""
        
        return base_prompt + blocknote_instructions
    
    def _process_blocknote_response(self, response_text: str, json_tool: Tool) -> str:
        """Process and validate BlockNote response.
        
        Args:
            response_text: Raw response from the AI
            json_tool: The JSON function tool definition
            
        Returns:
            Validated JSON string for function arguments
        """
        try:
            # Clean the response text
            cleaned_response = response_text.strip()
            
            # Try to extract JSON if there's extra text
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                cleaned_response = json_match.group(0)
            
            # Parse and validate JSON
            parsed_json = json.loads(cleaned_response)
            
            # Basic validation - ensure it has the operations field
            if not isinstance(parsed_json, dict):
                raise ValueError("Response is not a JSON object")
            
            if "operations" not in parsed_json:
                raise ValueError("Response missing 'operations' field")
            
            if not isinstance(parsed_json["operations"], list):
                raise ValueError("'operations' field is not a list")
            
            # Validate each operation has required fields
            for i, operation in enumerate(parsed_json["operations"]):
                if not isinstance(operation, dict):
                    raise ValueError(f"Operation {i} is not an object")
                
                if "type" not in operation:
                    raise ValueError(f"Operation {i} missing 'type' field")
                
                op_type = operation["type"]
                if op_type not in ["update", "add", "delete"]:
                    raise ValueError(f"Operation {i} has invalid type: {op_type}")
                
                # Validate required fields based on operation type
                if op_type == "update":
                    if "id" not in operation or "block" not in operation:
                        raise ValueError(f"Update operation {i} missing required fields")
                elif op_type == "add":
                    if not all(field in operation for field in ["referenceId", "position", "blocks"]):
                        raise ValueError(f"Add operation {i} missing required fields")
                elif op_type == "delete":
                    if "id" not in operation:
                        raise ValueError(f"Delete operation {i} missing 'id' field")
            
            logger.info(f"Successfully validated BlockNote response with {len(parsed_json['operations'])} operations")
            return json.dumps(parsed_json, separators=(',', ':'))
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse BlockNote JSON response: {e}")
            logger.error(f"Raw response: {response_text}")
            
            # Return a fallback error operation
            fallback_response = {
                "operations": [{
                    "type": "update",
                    "id": "error",
                    "block": "<p>Error: Could not process the request. Please try again.</p>"
                }]
            }
            return json.dumps(fallback_response, separators=(',', ':'))
            
        except ValueError as e:
            logger.error(f"BlockNote response validation failed: {e}")
            logger.error(f"Raw response: {response_text}")
            
            # Return a fallback error operation
            fallback_response = {
                "operations": [{
                    "type": "update", 
                    "id": "error",
                    "block": f"<p>Validation Error: {str(e)}</p>"
                }]
            }
            return json.dumps(fallback_response, separators=(',', ':'))
    
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
