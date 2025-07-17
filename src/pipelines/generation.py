"""Haystack pipeline for text generation."""

from haystack_integrations.components.generators.ollama import OllamaGenerator
from config.settings import settings
from src.models.schemas import ChatMessage, ChatCompletionRequest, WorkPackage, Tool, ToolChoice, FunctionCall, ToolCall, ToolCallFunction
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
        logger.info(f"🚀 GENERATING PROJECT STATUS REPORT")
        logger.info(f"Project ID: {project_id} | Type: {project_type}")
        logger.info(f"OpenProject URL: {openproject_base_url}")
        logger.info(f"Work packages to analyze: {len(work_packages)}")
        logger.info(f"Template: {template_name}")
        
        # Log summary of work packages being processed
        if work_packages:
            logger.info("Work packages summary for report generation:")
            for i, wp in enumerate(work_packages[:10], 1):  # Show first 10
                status_name = wp.status.get("name", "No Status") if wp.status else "No Status"
                logger.info(f"  {i}. WP {wp.id}: '{wp.subject}' | Status: '{status_name}'")
            
            if len(work_packages) > 10:
                logger.info(f"  ... and {len(work_packages) - 10} more work packages")
        else:
            logger.warning("No work packages provided for report generation!")
        
        # Analyze work packages
        logger.info("Starting work package analysis...")
        analyzer = ProjectReportAnalyzer()
        analysis = analyzer.analyze_work_packages(work_packages)
        logger.info("Work package analysis completed")
        
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
    ) -> List[Dict[str, Any]]:
        """Generate German project management hints from check results.
        
        Args:
            project_id: OpenProject project ID
            project_type: Type of project
            openproject_base_url: Base URL of OpenProject instance
            checks_results: Results from the 10 automated checks
            pmflex_context: PMFlex context from RAG system
            
        Returns:
            List of hint dictionaries with title and description
        """
        from src.templates.report_templates import ProjectManagementHintsTemplate
        
        logger.info("=== STARTING HINT GENERATION (IMPROVED) ===")
        
        # First, always use the hint optimizer to generate a baseline
        from src.utils.hint_optimizer import hint_optimizer
        baseline_json = hint_optimizer.generate_enhanced_fallback_hints(checks_results)
        baseline_hints = json.loads(baseline_json)["hints"]
        
        logger.info(f"Generated {len(baseline_hints)} baseline hints from optimizer")
        
        # Try to enhance with LLM if available
        try:
            # Create a simpler prompt that asks for structured text, not JSON
            template = ProjectManagementHintsTemplate()
            prompt = template.create_simple_hints_prompt(
                project_id=project_id,
                project_type=project_type,
                openproject_base_url=openproject_base_url,
                checks_results=checks_results,
                pmflex_context=pmflex_context
            )
            
            # Generate hints using LLM with simpler parameters
            generator = OllamaGenerator(
                model=settings.OLLAMA_MODEL,
                url=settings.OLLAMA_URL,
                generation_kwargs={
                    "num_predict": 2000,  # Reduced for simpler text output
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "stop": ["Hinweis 11:", "Hint 11:"],  # Stop after 10 hints
                }
            )
            
            result = generator.run(prompt)
            llm_response = result["replies"][0]
            
            logger.info(f"LLM response length: {len(llm_response)} characters")
            
            # Parse the structured text response
            enhanced_hints = self._parse_structured_hints(llm_response)
            
            if enhanced_hints and len(enhanced_hints) > 0:
                logger.info(f"Successfully parsed {len(enhanced_hints)} enhanced hints from LLM")
                # Merge with baseline hints, preferring enhanced ones
                return self._merge_hints(enhanced_hints, baseline_hints)
            else:
                logger.warning("Could not parse enhanced hints, using baseline")
                return baseline_hints
                
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            logger.info("Falling back to baseline hints")
            return baseline_hints
    
    def _parse_structured_hints(self, text: str) -> List[Dict[str, Any]]:
        """Parse structured hint text into list of hint dictionaries.
        
        Args:
            text: Structured text with numbered hints
            
        Returns:
            List of parsed hints
        """
        hints = []
        
        try:
            # Split by hint numbers (e.g., "1.", "2.", etc.)
            import re
            hint_pattern = r'(\d+)\.\s*([^:]+):\s*([^0-9]+?)(?=\d+\.|$)'
            matches = re.findall(hint_pattern, text, re.DOTALL)
            
            for match in matches[:10]:  # Max 10 hints
                number, title, description = match
                title = title.strip()
                description = description.strip()
                
                if title and description:
                    hints.append({
                        "checked": False,
                        "title": title[:60],  # Ensure max length
                        "description": description
                    })
            
            # If regex didn't work, try line-based parsing
            if not hints:
                lines = text.split('\n')
                current_hint = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if this is a new hint (starts with number)
                    if re.match(r'^\d+\.', line):
                        if current_hint and current_hint.get("title") and current_hint.get("description"):
                            hints.append(current_hint)
                        
                        # Extract title from the line
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            title = parts[0].lstrip('0123456789. ').strip()
                            description = parts[1].strip()
                            current_hint = {
                                "checked": False,
                                "title": title[:60],
                                "description": description
                            }
                        else:
                            title = line.lstrip('0123456789. ').strip()
                            current_hint = {
                                "checked": False,
                                "title": title[:60],
                                "description": ""
                            }
                    elif current_hint and not current_hint.get("description"):
                        # This line is the description
                        current_hint["description"] = line
                    elif current_hint:
                        # Append to existing description
                        current_hint["description"] += " " + line
                
                # Don't forget the last hint
                if current_hint and current_hint.get("title") and current_hint.get("description"):
                    hints.append(current_hint)
            
            return hints[:10]  # Ensure max 10 hints
            
        except Exception as e:
            logger.error(f"Failed to parse structured hints: {e}")
            return []
    
    def _merge_hints(self, enhanced_hints: List[Dict[str, Any]], baseline_hints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge enhanced and baseline hints, removing duplicates.
        
        Args:
            enhanced_hints: Hints from LLM
            baseline_hints: Hints from optimizer
            
        Returns:
            Merged list of hints
        """
        merged = []
        seen_titles = set()
        
        # Add enhanced hints first
        for hint in enhanced_hints:
            title_lower = hint["title"].lower()
            if title_lower not in seen_titles:
                merged.append(hint)
                seen_titles.add(title_lower)
        
        # Add baseline hints if we need more
        for hint in baseline_hints:
            if len(merged) >= 10:
                break
            title_lower = hint["title"].lower()
            if title_lower not in seen_titles:
                merged.append(hint)
                seen_titles.add(title_lower)
        
        return merged[:10]  # Ensure max 10 hints
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from LLM response.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Cleaned JSON string
        """
        logger.info("=== STARTING JSON CLEANING PROCESS ===")
        logger.info(f"Original response length: {len(response)}")
        logger.info(f"Original response type: {type(response)}")
        logger.info(f"Original response repr: {repr(response)}")
        logger.info(f"Original response starts with: {response[:100] if response else 'EMPTY'}")
        logger.info(f"Original response ends with: {response[-100:] if response else 'EMPTY'}")
        
        # Remove markdown code blocks
        cleaned = re.sub(r'```json\s*', '', response)
        logger.info(f"After removing '```json': {repr(cleaned)}")
        
        cleaned = re.sub(r'```\s*$', '', cleaned)
        logger.info(f"After removing closing '```': {repr(cleaned)}")
        
        # Remove any leading/trailing whitespace
        cleaned = cleaned.strip()
        logger.info(f"After stripping whitespace: {repr(cleaned)}")
        logger.info(f"Cleaned response length: {len(cleaned)}")
        
        if not cleaned:
            logger.error("Cleaned response is empty!")
            raise ValueError("Response is empty after cleaning")
        
        # Check what the cleaned response starts with
        logger.info(f"Cleaned response starts with: {cleaned[:50]}...")
        logger.info(f"Cleaned response ends with: {cleaned[-50:]}")
        
        # Handle the specific case where response starts with malformed JSON
        if cleaned.startswith('"hints"') or cleaned.startswith('\n  "hints"') or '"hints"' in cleaned[:20]:
            logger.warning("=== DETECTED INCOMPLETE JSON STARTING WITH 'hints' ===")
            logger.warning(f"This is the problematic case! Response: {repr(cleaned)}")
            return self._reconstruct_incomplete_json(cleaned)
        
        # Handle case where response doesn't start with {
        if not cleaned.startswith('{'):
            logger.warning(f"=== RESPONSE DOESN'T START WITH BRACE ===")
            logger.warning(f"Response starts with: {repr(cleaned[:20])}")
            # Try to find the start of JSON
            json_start = cleaned.find('{')
            if json_start != -1:
                cleaned = cleaned[json_start:]
                logger.info(f"Found JSON start at position {json_start}")
                logger.info(f"Extracted JSON: {repr(cleaned)}")
            else:
                logger.error("No JSON structure found in response")
                logger.error(f"Searched for {{ in: {repr(cleaned)}")
                raise ValueError("No valid JSON structure found in response")
        
        # Try to extract JSON block
        logger.info("=== ATTEMPTING TO EXTRACT JSON BLOCK ===")
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            extracted = json_match.group(0)
            logger.info(f"Extracted JSON block: {repr(extracted)}")
            cleaned = extracted
        else:
            logger.warning("No JSON block found with regex")
        
        # Fix common JSON issues
        logger.info("=== FIXING COMMON JSON ISSUES ===")
        before_trailing_comma_fix = cleaned
        cleaned = re.sub(r',\s*}', '}', cleaned)  # Remove trailing commas before }
        if cleaned != before_trailing_comma_fix:
            logger.info("Fixed trailing commas before }")
            
        before_trailing_comma_array_fix = cleaned
        cleaned = re.sub(r',\s*]', ']', cleaned)  # Remove trailing commas before ]
        if cleaned != before_trailing_comma_array_fix:
            logger.info("Fixed trailing commas before ]")
        
        # Ensure JSON is complete
        logger.info("=== CHECKING IF JSON IS COMPLETE ===")
        is_complete = self._is_json_complete(cleaned)
        logger.info(f"JSON completeness check result: {is_complete}")
        
        if not is_complete:
            logger.warning("JSON appears incomplete, attempting to complete it")
            before_completion = cleaned
            cleaned = self._complete_json_structure(cleaned)
            logger.info(f"Before completion: {repr(before_completion)}")
            logger.info(f"After completion: {repr(cleaned)}")
        
        logger.info("=== FINAL CLEANED JSON ===")
        logger.info(f"Final cleaned JSON: {repr(cleaned)}")
        logger.info(f"Final cleaned JSON length: {len(cleaned)}")
        
        return cleaned
    
    def _reconstruct_incomplete_json(self, response: str) -> str:
        """Reconstruct incomplete JSON that starts with 'hints'.
        
        Args:
            response: Incomplete JSON response
            
        Returns:
            Reconstructed JSON string
        """
        logger.info("=== STARTING JSON RECONSTRUCTION ===")
        logger.info(f"Input response length: {len(response)}")
        logger.info(f"Input response type: {type(response)}")
        logger.info(f"Input response repr: {repr(response)}")
        logger.info(f"Input response full content: {response}")
        
        # Handle the case where response is just whitespace + "hints"
        response = response.strip()
        logger.info(f"After stripping: {repr(response)}")
        
        if not response:
            logger.error("Response is empty after stripping")
            raise ValueError("Empty response after stripping")
        
        # Check if response is extremely short (likely truncated)
        if len(response) < 10:
            logger.warning(f"Response extremely short ({len(response)} chars): '{response}' - creating fallback")
            return '{"hints": []}'
        
        # Find the "hints" part
        logger.info("=== SEARCHING FOR 'hints' ===")
        hints_start = response.find('"hints"')
        logger.info(f"Found 'hints' at position: {hints_start}")
        
        if hints_start == -1:
            logger.error("Could not find 'hints' in response")
            logger.error(f"Response content: {repr(response)}")
            # Try to create a minimal valid JSON with the available content
            logger.info("Creating minimal fallback JSON")
            return '{"hints": []}'
        
        # Extract from "hints" onwards
        hints_part = response[hints_start:]
        logger.info(f"=== EXTRACTED HINTS PART ===")
        logger.info(f"Hints part length: {len(hints_part)}")
        logger.info(f"Hints part repr: {repr(hints_part)}")
        logger.info(f"Hints part content: {hints_part}")
        
        # Try to build proper JSON structure
        if hints_part.startswith('"hints"'):
            logger.info("Hints part starts with '\"hints\"'")
            # Check if it has a colon after hints
            if ':' in hints_part:
                logger.info("Found colon in hints part")
                # Good, we have "hints": something
                reconstructed = '{' + hints_part
                logger.info(f"Reconstructed with brace: {repr(reconstructed)}")
            else:
                logger.warning("No colon found in hints part")
                # Missing colon, add it with empty array
                reconstructed = '{"hints": []}'
                logger.info("Created empty array fallback")
        else:
            logger.warning("Hints part doesn't start with '\"hints\"'")
            # Handle case where hints_part is literally just "hints" or similar
            if hints_part.strip() == '"hints"' or hints_part.strip() == 'hints':
                reconstructed = '{"hints": []}'
                logger.info("Found bare 'hints', creating empty array")
            else:
                reconstructed = '{' + hints_part
                logger.info(f"Added brace: {repr(reconstructed)}")
        
        # Ensure we have a valid JSON structure
        logger.info("=== ENSURING VALID JSON STRUCTURE ===")
        if not reconstructed.startswith('{'):
            logger.warning("Reconstructed doesn't start with brace, adding")
            reconstructed = '{' + reconstructed
        
        logger.info(f"After ensuring starts with brace: {repr(reconstructed)}")
        
        # Try to properly close the JSON
        logger.info("=== ATTEMPTING TO CLOSE JSON ===")
        if not reconstructed.rstrip().endswith('}'):
            logger.info("JSON doesn't end with brace, attempting to close")
            # Look for the end of the hints array
            if ']' in reconstructed:
                logger.info("Found closing bracket, adding brace after it")
                # Find the last ] and add closing brace after it
                last_bracket = reconstructed.rfind(']')
                logger.info(f"Last bracket at position: {last_bracket}")
                if last_bracket != -1:
                    reconstructed = reconstructed[:last_bracket + 1] + '}'
                    logger.info(f"Added closing brace: {repr(reconstructed)}")
                else:
                    # No closing bracket found, add both
                    reconstructed += ']}'
                    logger.info("Added both closing bracket and brace")
            else:
                logger.info("No closing bracket found, attempting to add array structure")
                # No array structure found, try to add it
                if '"hints"' in reconstructed and ':' in reconstructed:
                    logger.info("Found hints and colon, attempting to complete")
                    # We have "hints": but no array, complete it
                    colon_pos = reconstructed.find(':', reconstructed.find('"hints"'))
                    logger.info(f"Colon position: {colon_pos}")
                    if colon_pos != -1:
                        # Check what comes after the colon
                        after_colon = reconstructed[colon_pos + 1:].strip()
                        logger.info(f"After colon: {repr(after_colon)}")
                        if not after_colon or after_colon == '':
                            reconstructed = reconstructed[:colon_pos + 1] + ' []}'
                            logger.info("Added empty array after colon")
                        else:
                            reconstructed += ']}'
                            logger.info("Added closing bracket and brace")
                    else:
                        reconstructed += ']}'
                        logger.info("Added closing bracket and brace (no colon)")
                else:
                    reconstructed += ']}'
                    logger.info("Added closing bracket and brace (no hints/colon)")
        
        # Final validation - ensure we have a complete JSON structure
        logger.info("=== FINAL VALIDATION ===")
        logger.info(f"Before final validation: {repr(reconstructed)}")
        if not (reconstructed.startswith('{') and reconstructed.endswith('}')):
            logger.warning("Reconstructed JSON doesn't have proper boundaries, creating fallback")
            reconstructed = '{"hints": []}'
        
        logger.info(f"=== FINAL RECONSTRUCTED JSON ===")
        logger.info(f"Final JSON: {repr(reconstructed)}")
        logger.info(f"Final JSON content: {reconstructed}")
        
        return reconstructed
    
    def _is_json_complete(self, json_str: str) -> bool:
        """Check if JSON string appears to be complete.
        
        Args:
            json_str: JSON string to check
            
        Returns:
            True if JSON appears complete
        """
        if not json_str.strip():
            return False
        
        # Count braces and brackets
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        # Basic completeness check
        return (open_braces == close_braces and 
                open_brackets == close_brackets and 
                json_str.strip().startswith('{') and 
                json_str.strip().endswith('}'))
    
    def _complete_json_structure(self, json_str: str) -> str:
        """Attempt to complete an incomplete JSON structure.
        
        Args:
            json_str: Incomplete JSON string
            
        Returns:
            Completed JSON string
        """
        logger.info("Attempting to complete JSON structure")
        
        # Count missing closing characters
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        completed = json_str.rstrip()
        
        # Add missing closing brackets
        missing_brackets = open_brackets - close_brackets
        if missing_brackets > 0:
            completed += ']' * missing_brackets
        
        # Add missing closing braces
        missing_braces = open_braces - close_braces
        if missing_braces > 0:
            completed += '}' * missing_braces
        
        logger.info(f"Completed JSON by adding {missing_brackets} brackets and {missing_braces} braces")
        return completed
    
    def _create_fallback_hints_json(self, checks_results: Dict[str, Any]) -> str:
        """Create a fallback JSON response when LLM generation fails.
        
        Uses the enhanced hint optimizer for better context-aware hints.
        
        Args:
            checks_results: Results from the 10 automated checks
            
        Returns:
            Valid JSON string with fallback hints
        """
        logger.info("Creating enhanced fallback hints using hint optimizer")
        
        try:
            # Use the enhanced hint optimizer for better fallback hints
            from src.utils.hint_optimizer import hint_optimizer
            return hint_optimizer.generate_enhanced_fallback_hints(checks_results)
        except Exception as e:
            logger.error(f"Enhanced fallback failed, using basic fallback: {e}")
            
            # Basic fallback as last resort
            hints = []
            
            # Generate hints based on check results
            if checks_results.get("deadline_health", {}).get("severity") == "critical":
                overdue_count = checks_results["deadline_health"].get("overdue_count", 0)
                hints.append({
                    "checked": False,
                    "title": "Überfällige Termine bearbeiten",
                    "description": f"Es gibt {overdue_count} überfällige Arbeitspakete. Prüfen Sie diese umgehend und definieren Sie neue realistische Termine."
                })
            
            if checks_results.get("missing_dates", {}).get("severity") == "warning":
                missing_count = checks_results["missing_dates"].get("missing_dates_count", 0)
                hints.append({
                    "checked": False,
                    "title": "Fehlende Fälligkeitstermine ergänzen",
                    "description": f"{missing_count} Arbeitspakete haben keine Fälligkeitstermine. Planen Sie diese zeitlich ein."
                })
            
            if checks_results.get("resource_balance", {}).get("severity") == "warning":
                unassigned_count = checks_results["resource_balance"].get("unassigned_count", 0)
                if unassigned_count > 0:
                    hints.append({
                        "checked": False,
                        "title": "Nicht zugewiesene Aufgaben bearbeiten",
                        "description": f"{unassigned_count} Arbeitspakete sind nicht zugewiesen. Weisen Sie diese Teammitgliedern zu."
                    })
            
            if checks_results.get("documentation_completeness", {}).get("severity") == "warning":
                incomplete_count = checks_results["documentation_completeness"].get("incomplete_count", 0)
                hints.append({
                    "checked": False,
                    "title": "Dokumentation vervollständigen",
                    "description": f"{incomplete_count} Arbeitspakete haben unvollständige Dokumentation. Ergänzen Sie Beschreibungen."
                })
            
            # If no specific hints were generated, add a general one
            if not hints:
                hints.append({
                    "checked": False,
                    "title": "Projektübersicht prüfen",
                    "description": "Überprüfen Sie den aktuellen Projektstatus und stellen Sie sicher, dass alle Arbeitspakete ordnungsgemäß verwaltet werden."
                })
            
            # Limit to maximum 5 hints
            hints = hints[:5]
            
            fallback_response = {"hints": hints}
            return json.dumps(fallback_response, ensure_ascii=False, separators=(',', ':'))
    
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
        
        # Create generator with BlockNote-specific parameters optimized for substantial content
        generator = OllamaGenerator(
            model=request.model,
            url=settings.OLLAMA_URL,
            generation_kwargs={
                "num_predict": request.max_tokens or 3500,  # Significantly increased to ensure JSON completion
                "temperature": request.temperature or 0.2,  # Slightly higher for more creative content
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
        
        # Detect the type of request to apply appropriate prompting strategy
        request_type = self._detect_request_type(messages)
        
        if request_type == "simple_operation":
            # Use minimal prompting for simple operations like translations
            blocknote_instructions = self._get_simple_operation_instructions()
        elif request_type == "improvement_operation":
            # Use focused prompting for text improvement operations
            blocknote_instructions = self._get_improvement_operation_instructions()
        else:
            # Use comprehensive prompting for content creation
            blocknote_instructions = self._get_comprehensive_content_instructions()
        
        return base_prompt + blocknote_instructions
    
    def _detect_request_type(self, messages: List[ChatMessage]) -> str:
        """Detect the type of request to apply appropriate prompting strategy.
        
        Args:
            messages: Chat messages to analyze
            
        Returns:
            Request type: "simple_operation", "improvement_operation", or "content_creation"
        """
        # Get the last user message to analyze the request
        user_messages = [msg for msg in messages if msg.role == "user"]
        if not user_messages:
            return "content_creation"
        
        last_message = user_messages[-1].content.lower()
        
        # Keywords that indicate improvement operations (enhance existing text)
        improvement_keywords = [
            "improve", "improve writing", "verbessern", "verbesserung",
            "enhance", "polish", "refine", "make better", "better",
            "optimize", "optimieren", "upgrade", "revise", "überarbeiten"
        ]
        
        # Check for improvement operations first (more specific)
        for keyword in improvement_keywords:
            if keyword in last_message:
                logger.info(f"Detected improvement operation request: {keyword}")
                return "improvement_operation"
        
        # Keywords that indicate simple operations
        simple_operation_keywords = [
            "translate", "übersetze", "übersetzung", "translation",
            "format", "formatiere", "formatting",
            "fix", "correct", "korrigiere", "korrektur",
            "change", "ändere", "ändern", "replace", "ersetze",
            "bold", "italic", "fett", "kursiv",
            "uppercase", "lowercase", "großbuchstaben", "kleinbuchstaben"
        ]
        
        # Check if the request contains simple operation keywords
        for keyword in simple_operation_keywords:
            if keyword in last_message:
                logger.info(f"Detected simple operation request: {keyword}")
                return "simple_operation"
        
        # Check for translation patterns
        translation_patterns = [
            r"translate.*to\s+\w+",
            r"übersetze.*ins?\s+\w+",
            r"in\s+\w+\s+übersetzen",
            r"to\s+\w+\s+translation"
        ]
        
        for pattern in translation_patterns:
            if re.search(pattern, last_message):
                logger.info(f"Detected translation request: {pattern}")
                return "simple_operation"
        
        # Default to content creation for comprehensive responses
        logger.info("Detected content creation request")
        return "content_creation"
    
    def _get_simple_operation_instructions(self) -> str:
        """Get instructions for simple operations like translations.
        
        Returns:
            Simple operation instructions
        """
        return """

CRITICAL JSON COMPLETION REQUIREMENTS:
- You MUST respond with ONLY complete, valid JSON that matches the exact schema
- NO explanatory text, NO markdown, NO comments, NO incomplete responses
- The JSON MUST be complete with all opening and closing braces, brackets, and quotes
- NEVER stop generating until the JSON is completely finished
- End your response with the final closing brace }

SIMPLE OPERATION REQUIREMENTS:
- For translations: Replace ONLY with the translated text, add NOTHING else
- For formatting: Apply ONLY the requested formatting change
- For corrections: Make ONLY the necessary corrections
- DO NOT add explanations, headers, disclaimers, or additional content
- DO NOT generate comprehensive content - keep it minimal and focused
- ONLY perform the specific operation requested by the user

JSON SCHEMA REQUIREMENTS:
- Root object MUST have "operations" array
- Each operation MUST have "type" field: "update", "add", or "delete"
- Update operations MUST have: type, id, block (where block is a single HTML string)
- Add operations MUST have: type, referenceId, position, blocks (where blocks is array of HTML strings)
- Delete operations MUST have: type, id
- ALL strings must be properly escaped and quoted
- ALL objects and arrays must be properly closed

CRITICAL RULES:
- Block IDs must be preserved exactly (including trailing $)
- For simple operations, typically use only ONE "update" operation
- The "block" content should contain ONLY the result of the operation
- DO NOT add extra blocks or additional content

Example for translation:
{"operations":[{"type":"update","id":"block-id$","block":"<p>Dies ist auf Deutsch</p>"}]}

RESPOND WITH ONLY COMPLETE, VALID JSON - NO OTHER TEXT:"""
    
    def _get_improvement_operation_instructions(self) -> str:
        """Get instructions for text improvement operations.
        
        Returns:
            Improvement operation instructions
        """
        return """

CRITICAL JSON COMPLETION REQUIREMENTS:
- You MUST respond with ONLY complete, valid JSON that matches the exact schema
- NO explanatory text, NO markdown, NO comments, NO incomplete responses
- The JSON MUST be complete with all opening and closing braces, brackets, and quotes
- NEVER stop generating until the JSON is completely finished
- End your response with the final closing brace }

IMPROVEMENT OPERATION REQUIREMENTS:
- Take the selected text and return ONLY an improved version of that same text
- DO NOT create comprehensive guides or educational content about improvement
- DO NOT add explanations, headers, disclaimers, or additional content
- FOCUS on enhancing the existing text: grammar, clarity, style, flow
- Keep the same meaning and intent, just make it better written
- Maintain the original length and structure unless improvement requires changes

IMPROVEMENT FOCUS AREAS:
- Grammar and spelling corrections
- Sentence structure and flow
- Word choice and vocabulary
- Clarity and readability
- Professional tone (if appropriate)
- Conciseness without losing meaning

JSON SCHEMA REQUIREMENTS:
- Root object MUST have "operations" array
- Each operation MUST have "type" field: "update", "add", or "delete"
- Update operations MUST have: type, id, block (where block is a single HTML string)
- Add operations MUST have: type, referenceId, position, blocks (where blocks is array of HTML strings)
- Delete operations MUST have: type, id
- ALL strings must be properly escaped and quoted
- ALL objects and arrays must be properly closed

CRITICAL RULES:
- Block IDs must be preserved exactly (including trailing $)
- For improvement operations, typically use only ONE "update" operation
- The "block" content should contain ONLY the improved version of the original text
- DO NOT add extra blocks or additional content
- Each "block" field MUST contain EXACTLY ONE HTML element

EXAMPLE - Original: "Das ist auf Deutsch"
GOOD IMPROVEMENT: {"operations":[{"type":"update","id":"block-id$","block":"<p>Dies ist ein Text in deutscher Sprache.</p>"}]}
BAD IMPROVEMENT: {"operations":[{"type":"update","id":"block-id$","block":"<h1>Improving German Text</h1><p>Dies ist ein Text in deutscher Sprache.</p><p>Here are some tips for improving German writing...</p>"}]}

RESPOND WITH ONLY COMPLETE, VALID JSON - NO OTHER TEXT:"""
    
    def _get_comprehensive_content_instructions(self) -> str:
        """Get instructions for comprehensive content creation.
        
        Returns:
            Comprehensive content instructions
        """
        return """

CRITICAL JSON FORMAT REQUIREMENTS - FOLLOW EXACTLY:
- You MUST respond with ONLY complete, valid JSON that matches the EXACT schema below
- NO explanatory text, NO markdown, NO comments, NO incomplete responses
- The JSON MUST start with { and end with }
- NEVER stop generating until the JSON is completely finished

MANDATORY JSON STRUCTURE - DO NOT DEVIATE:
{
  "operations": [
    {
      "type": "update",
      "id": "exact-block-id-with-dollar$",
      "block": "<single-html-element>content</single-html-element>"
    },
    {
      "type": "add", 
      "referenceId": "exact-block-id-with-dollar$",
      "position": "after",
      "blocks": [
        "<single-html-element>content1</single-html-element>",
        "<single-html-element>content2</single-html-element>"
      ]
    }
  ]
}

FORBIDDEN JSON FORMATS (DO NOT USE):
- [{"name":"operations","array":[...]}] (name/value format)
- [{"type":"update",...}] (array at root level)
- {"type":"update",...} (single operation without operations wrapper)

CONTENT GENERATION REQUIREMENTS:
- Generate COMPREHENSIVE, DETAILED content - not just titles or brief summaries
- Create substantial, informative content that fully addresses the user's request
- For essays, articles, or explanations: provide multiple paragraphs with detailed information
- For lists: include detailed descriptions, not just simple items
- Match the depth and quality of professional content (like OpenAI GPT-4)

DOCUMENT MANIPULATION STRATEGY:
- If document is empty (has <p></p>): UPDATE the empty block with substantial content, then ADD more blocks for comprehensive coverage
- For longer content: Use multiple operations to create well-structured documents
- Break content into logical paragraphs using separate blocks
- Create proper document flow with headings, paragraphs, and lists as appropriate

CRITICAL BLOCK STRUCTURE RULES:
- Each "block" field MUST contain EXACTLY ONE HTML element (one root tag)
- NEVER put multiple HTML elements in a single "block" field
- If you want multiple elements, use separate blocks in the "blocks" array
- Each list item should be a separate block: <ul><li>item</li></ul>
- Properly escape quotes in HTML attributes: use \\" for quotes inside JSON strings
- Block IDs must be preserved exactly (including trailing $)

VALID BLOCK EXAMPLES:
- "<p>This is one paragraph</p>"
- "<h1>This is a heading</h1>"
- "<ul><li>This is one list item</li></ul>"

INVALID BLOCK EXAMPLES (DO NOT DO THIS):
- "<h1>Title</h1><p>Paragraph</p>" (multiple elements in one block)
- "<p>Text with "quotes" inside</p>" (unescaped quotes)

COMPLETE EXAMPLE - COPY THIS EXACT STRUCTURE:
{"operations":[{"type":"update","id":"block-id$","block":"<h1>Democracy: A Comprehensive Overview</h1>"},{"type":"add","referenceId":"block-id$","position":"after","blocks":["<p>Democracy is a form of government in which power is vested in the people, who rule either directly or through freely elected representatives.</p>","<p>The fundamental principles of democracy include popular sovereignty, political equality, and majority rule with minority rights.</p>","<h2>Key Characteristics of Democratic Systems</h2>","<ul><li>Free and fair elections held at regular intervals</li></ul>","<ul><li>Universal suffrage and equal voting rights</li></ul>","<ul><li>Protection of fundamental human rights and civil liberties</li></ul>"]}]}

RESPOND WITH ONLY COMPLETE, VALID JSON MATCHING THE EXACT STRUCTURE ABOVE:"""
    
    def _process_blocknote_response(self, response_text: str, json_tool: Tool) -> str:
        """Process and validate BlockNote response.
        
        Args:
            response_text: Raw response from the AI
            json_tool: The JSON function tool definition
            
        Returns:
            Validated JSON string for function arguments
        """
        try:
            # Clean the response text more aggressively
            cleaned_response = response_text.strip()
            
            # Remove any markdown code blocks
            cleaned_response = re.sub(r'```json\s*', '', cleaned_response)
            cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
            
            # Try to extract JSON if there's extra text
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                cleaned_response = json_match.group(0)
            
            # Parse and validate JSON
            parsed_json = json.loads(cleaned_response)
            
            # Fix common AI mistakes and validate structure
            parsed_json = self._fix_blocknote_json(parsed_json)
            
            # Validate the final structure
            self._validate_blocknote_structure(parsed_json)
            
            logger.info(f"Successfully validated BlockNote response with {len(parsed_json['operations'])} operations")
            return json.dumps(parsed_json, separators=(',', ':'))
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse BlockNote JSON response: {e}")
            logger.error(f"Raw response: {response_text}")
            
            # Try to fix common JSON issues
            try:
                fixed_json = self._attempt_json_repair(response_text)
                if fixed_json:
                    logger.info("Successfully repaired malformed JSON")
                    return fixed_json
            except Exception as repair_error:
                logger.error(f"JSON repair also failed: {repair_error}")
            
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
    
    def _fix_blocknote_json(self, parsed_json: dict) -> dict:
        """Fix common AI mistakes in BlockNote JSON.
        
        Args:
            parsed_json: Parsed JSON object
            
        Returns:
            Fixed JSON object
        """
        if not isinstance(parsed_json, dict):
            raise ValueError("Response is not a JSON object")
        
        # Ensure operations field exists
        if "operations" not in parsed_json:
            raise ValueError("Response missing 'operations' field")
        
        if not isinstance(parsed_json["operations"], list):
            raise ValueError("'operations' field is not a list")
        
        # Fix each operation
        fixed_operations = []
        for i, operation in enumerate(parsed_json["operations"]):
            if not isinstance(operation, dict):
                logger.warning(f"Skipping non-object operation {i}")
                continue
            
            fixed_op = self._fix_single_operation(operation, i)
            if fixed_op:
                fixed_operations.append(fixed_op)
        
        if not fixed_operations:
            raise ValueError("No valid operations found after fixing")
        
        return {"operations": fixed_operations}
    
    def _fix_single_operation(self, operation: dict, index: int) -> dict:
        """Fix a single operation.
        
        Args:
            operation: Operation to fix
            index: Operation index for error messages
            
        Returns:
            Fixed operation or None if unfixable
        """
        if "type" not in operation:
            logger.warning(f"Operation {index} missing 'type' field, skipping")
            return None
        
        op_type = operation["type"]
        if op_type not in ["update", "add", "delete"]:
            logger.warning(f"Operation {index} has invalid type: {op_type}, skipping")
            return None
        
        # Fix update operations
        if op_type == "update":
            if "id" not in operation or "block" not in operation:
                logger.warning(f"Update operation {index} missing required fields, skipping")
                return None
            
            # Fix the block content - handle multi-element blocks
            block_content = str(operation["block"])
            fixed_block = self._fix_block_content(block_content, index)
            
            return {
                "type": "update",
                "id": str(operation["id"]),
                "block": fixed_block
            }
        
        # Fix add operations
        elif op_type == "add":
            if not all(field in operation for field in ["referenceId", "position", "blocks"]):
                logger.warning(f"Add operation {index} missing required fields, skipping")
                return None
            
            # Fix blocks field - ensure it's an array of strings
            blocks = operation["blocks"]
            if not isinstance(blocks, list):
                logger.warning(f"Add operation {index} blocks field is not a list, skipping")
                return None
            
            fixed_blocks = []
            for j, block in enumerate(blocks):
                if isinstance(block, dict):
                    # AI sometimes creates objects instead of strings
                    if "block" in block:
                        block_content = str(block["block"])
                    elif "content" in block:
                        block_content = str(block["content"])
                    else:
                        logger.warning(f"Skipping malformed block object in operation {index}, block {j}")
                        continue
                elif isinstance(block, str):
                    block_content = block
                else:
                    logger.warning(f"Skipping non-string block in operation {index}, block {j}")
                    continue
                
                # Fix each block content
                fixed_block = self._fix_block_content(block_content, f"{index}.{j}")
                if fixed_block:
                    fixed_blocks.append(fixed_block)
            
            if not fixed_blocks:
                logger.warning(f"Add operation {index} has no valid blocks, skipping")
                return None
            
            return {
                "type": "add",
                "referenceId": str(operation["referenceId"]),
                "position": str(operation["position"]),
                "blocks": fixed_blocks
            }
        
        # Fix delete operations
        elif op_type == "delete":
            if "id" not in operation:
                logger.warning(f"Delete operation {index} missing 'id' field, skipping")
                return None
            return {
                "type": "delete",
                "id": str(operation["id"])
            }
        
        return None
    
    def _fix_block_content(self, block_content: str, block_id: str) -> str:
        """Fix block content to ensure it contains only one HTML element.
        
        Args:
            block_content: The block content to fix
            block_id: Block identifier for logging
            
        Returns:
            Fixed block content with single HTML element
        """
        if not block_content or not block_content.strip():
            logger.warning(f"Block {block_id} is empty")
            return "<p></p>"
        
        block_content = block_content.strip()
        
        # Check if this looks like multiple HTML elements concatenated
        # Simple heuristic: count opening tags
        import re
        opening_tags = re.findall(r'<[^/][^>]*>', block_content)
        
        if len(opening_tags) > 1:
            logger.warning(f"Block {block_id} contains multiple HTML elements, taking first element")
            
            # Try to extract the first complete HTML element
            first_tag_match = re.match(r'<([^>\s]+)[^>]*>', block_content)
            if first_tag_match:
                tag_name = first_tag_match.group(1)
                
                # Find the closing tag for this element
                if tag_name.lower() in ['br', 'hr', 'img', 'input', 'meta', 'link']:
                    # Self-closing tags
                    end_pos = first_tag_match.end()
                    return block_content[:end_pos]
                else:
                    # Find matching closing tag
                    closing_tag = f"</{tag_name}>"
                    closing_pos = block_content.find(closing_tag)
                    if closing_pos != -1:
                        return block_content[:closing_pos + len(closing_tag)]
                    else:
                        # No closing tag found, wrap in paragraph
                        logger.warning(f"Block {block_id} has unclosed tag, wrapping in paragraph")
                        return f"<p>{block_content}</p>"
            
            # Fallback: wrap everything in a paragraph
            logger.warning(f"Block {block_id} could not be parsed, wrapping in paragraph")
            return f"<p>{block_content}</p>"
        
        # Single element or plain text - ensure it's wrapped properly
        if not block_content.startswith('<'):
            # Plain text, wrap in paragraph
            return f"<p>{block_content}</p>"
        
        return block_content
    
    def _validate_blocknote_structure(self, parsed_json: dict) -> None:
        """Validate the final BlockNote structure.
        
        Args:
            parsed_json: JSON to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(parsed_json, dict):
            raise ValueError("Response is not a JSON object")
        
        if "operations" not in parsed_json:
            raise ValueError("Response missing 'operations' field")
        
        if not isinstance(parsed_json["operations"], list):
            raise ValueError("'operations' field is not a list")
        
        if len(parsed_json["operations"]) == 0:
            raise ValueError("Operations array is empty")
        
        # Validate each operation
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
                if not isinstance(operation["block"], str):
                    raise ValueError(f"Update operation {i} block must be a string")
            elif op_type == "add":
                if not all(field in operation for field in ["referenceId", "position", "blocks"]):
                    raise ValueError(f"Add operation {i} missing required fields")
                if not isinstance(operation["blocks"], list):
                    raise ValueError(f"Add operation {i} blocks must be a list")
                if len(operation["blocks"]) == 0:
                    raise ValueError(f"Add operation {i} blocks array is empty")
                for j, block in enumerate(operation["blocks"]):
                    if not isinstance(block, str):
                        raise ValueError(f"Add operation {i} block {j} must be a string")
            elif op_type == "delete":
                if "id" not in operation:
                    raise ValueError(f"Delete operation {i} missing 'id' field")
    
    def _attempt_json_repair(self, response_text: str) -> str:
        """Attempt to repair malformed JSON.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Repaired JSON string or None if repair failed
        """
        try:
            # First, try to detect and convert completely wrong formats
            converted = self._convert_wrong_json_formats(response_text)
            if converted:
                logger.info("Successfully converted wrong JSON format to correct BlockNote format")
                return converted
            
            # Common fixes for AI-generated JSON
            cleaned = response_text.strip()
            
            # Remove markdown
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            
            # Fix common issues
            cleaned = re.sub(r',\s*}', '}', cleaned)  # Remove trailing commas
            cleaned = re.sub(r',\s*]', ']', cleaned)  # Remove trailing commas in arrays
            
            # Try to extract just the JSON part
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(0)
            
            # Try parsing again
            parsed = json.loads(cleaned)
            fixed = self._fix_blocknote_json(parsed)
            self._validate_blocknote_structure(fixed)
            
            return json.dumps(fixed, separators=(',', ':'))
            
        except Exception as e:
            logger.error(f"JSON repair failed: {e}")
            return None
    
    def _convert_wrong_json_formats(self, response_text: str) -> str:
        """Convert completely wrong JSON formats to correct BlockNote format.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Corrected JSON string or None if conversion failed
        """
        try:
            cleaned = response_text.strip()
            
            # Remove markdown
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            
            # Try to parse as JSON first
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                # Try to fix basic JSON syntax issues first
                cleaned = re.sub(r',\s*}', '}', cleaned)
                cleaned = re.sub(r',\s*]', ']', cleaned)
                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError:
                    return None
            
            # Detect and convert wrong format #1: name/value structure
            if self._is_name_value_format(parsed):
                logger.info("Detected name/value format, converting...")
                return self._convert_name_value_format(parsed)
            
            # Detect and convert wrong format #2: array at root level
            if isinstance(parsed, list):
                logger.info("Detected array at root level, converting...")
                return self._convert_array_root_format(parsed)
            
            # Detect and convert wrong format #3: missing operations wrapper
            if isinstance(parsed, dict) and "operations" not in parsed and "type" in parsed:
                logger.info("Detected single operation without wrapper, converting...")
                return json.dumps({"operations": [parsed]}, separators=(',', ':'))
            
            return None
            
        except Exception as e:
            logger.error(f"Format conversion failed: {e}")
            return None
    
    def _is_name_value_format(self, parsed: any) -> bool:
        """Check if this is the wrong name/value format.
        
        Args:
            parsed: Parsed JSON object
            
        Returns:
            True if this is name/value format
        """
        if isinstance(parsed, list) and len(parsed) > 0:
            first_item = parsed[0]
            if isinstance(first_item, dict) and "name" in first_item and "array" in first_item:
                return True
        return False
    
    def _convert_name_value_format(self, parsed: any) -> str:
        """Convert name/value format to correct BlockNote format.
        
        Args:
            parsed: Parsed JSON in wrong format
            
        Returns:
            Corrected JSON string
        """
        try:
            operations = []
            
            # Extract operations from the wrong format
            if isinstance(parsed, list) and len(parsed) > 0:
                operations_data = parsed[0].get("array", [])
                
                current_op = {}
                for item in operations_data:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        name = item["name"]
                        value = item["value"]
                        
                        if name == "type":
                            # Start new operation
                            if current_op:
                                operations.append(current_op)
                            current_op = {"type": value}
                        elif name in ["id", "referenceId", "position", "block"]:
                            current_op[name] = value
                        elif name == "blocks":
                            # Handle blocks array
                            current_op["blocks"] = [value] if isinstance(value, str) else value
                
                # Add the last operation
                if current_op:
                    operations.append(current_op)
            
            if operations:
                result = {"operations": operations}
                # Validate and fix the result
                fixed = self._fix_blocknote_json(result)
                return json.dumps(fixed, separators=(',', ':'))
            
            return None
            
        except Exception as e:
            logger.error(f"Name/value format conversion failed: {e}")
            return None
    
    def _convert_array_root_format(self, parsed: list) -> str:
        """Convert array at root level to correct BlockNote format.
        
        Args:
            parsed: Parsed JSON array
            
        Returns:
            Corrected JSON string
        """
        try:
            # Wrap the array in the correct operations structure
            result = {"operations": parsed}
            
            # Validate and fix the result
            fixed = self._fix_blocknote_json(result)
            return json.dumps(fixed, separators=(',', ':'))
            
        except Exception as e:
            logger.error(f"Array root format conversion failed: {e}")
            return None
    
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
