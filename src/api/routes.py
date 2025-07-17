"""API routes for the Haystack application."""

from fastapi import APIRouter, HTTPException
from src.models.schemas import (
    GenerationRequest, GenerationResponse, HealthResponse,
    ChatCompletionRequest, ChatCompletionResponse, ChatMessage, ChatChoice,
    Usage, ModelsResponse, ModelInfo, ErrorResponse, ErrorDetail,
    ProjectStatusReportRequest, ProjectStatusReportResponse,
    ProjectManagementHintsRequest, ProjectManagementHintsResponse,
    FunctionCall, ToolCall, ToolCallFunction, ChatCompletionStreamingResponse,
    ChatChoiceStreaming, DeltaMessage
)
from src.pipelines.generation import generation_pipeline
from src.services.openproject_client import OpenProjectClient, OpenProjectAPIError
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.post("/generate", response_model=GenerationResponse)
def generate_text(request: GenerationRequest):
    """Generate text from a prompt.
    
    Args:
        request: The generation request containing the prompt
        
    Returns:
        Generated text response
    """
    try:
        response = generation_pipeline.generate(request.prompt)
        return GenerationResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# OpenAI-compatible endpoints

@router.post("/v1/chat/completions")
def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion (OpenAI-compatible endpoint).
    
    Args:
        request: Chat completion request with messages and parameters
        
    Returns:
        Chat completion response in OpenAI format (streaming or non-streaming)
    """
    try:
        # Validate that we have at least one message
        if not request.messages:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "message": "At least one message is required",
                        "type": "invalid_request_error",
                        "param": "messages",
                        "code": "missing_required_parameter"
                    }
                }
            )
        
        # Check if this is a BlockNote tool calling request
        is_blocknote_request = (request.tools and 
                               request.tool_choice and 
                               request.tool_choice.type == "function" and
                               request.tool_choice.function.get("name") == "json")
        
        if is_blocknote_request and request.stream:
            # Handle BlockNote streaming tool calls
            return _create_blocknote_streaming_response(request)
        elif is_blocknote_request:
            # Handle BlockNote non-streaming tool calls
            return _create_blocknote_response(request)
        elif request.stream:
            # Handle regular streaming
            return _create_streaming_response(request)
        else:
            # Handle regular non-streaming
            return _create_regular_response(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat completion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "code": "internal_error"
                }
            }
        )


def _create_blocknote_streaming_response(request: ChatCompletionRequest):
    """Create a streaming response for BlockNote tool calls."""
    from fastapi.responses import StreamingResponse
    import json
    import time
    
    def generate_blocknote_stream():
        try:
            # Generate response using the pipeline
            response_text, usage_info = generation_pipeline.chat_completion(request)
            
            # Create completion ID
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
            created_time = int(time.time())
            
            # Create tool call ID
            tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
            
            # First chunk - start tool call
            first_chunk = ChatCompletionStreamingResponse(
                id=completion_id,
                model=request.model,
                created=created_time,
                choices=[
                    ChatChoiceStreaming(
                        index=0,
                        delta=DeltaMessage(
                            role="assistant",
                            content=None,
                            tool_calls=[
                                ToolCall(
                                    id=tool_call_id,
                                    type="function",
                                    function=ToolCallFunction(
                                        name="json",
                                        arguments=""
                                    )
                                )
                            ]
                        ),
                        finish_reason=None
                    )
                ],
                system_fingerprint="fp_local_ollama",
                service_tier="default"
            )
            
            yield f"data: {first_chunk.model_dump_json()}\n\n"
            
            # Stream the JSON arguments character by character
            for i, char in enumerate(response_text):
                chunk = ChatCompletionStreamingResponse(
                    id=completion_id,
                    model=request.model,
                    created=created_time,
                    choices=[
                        ChatChoiceStreaming(
                            index=0,
                            delta=DeltaMessage(
                                tool_calls=[
                                    ToolCall(
                                        id=tool_call_id,
                                        type="function",
                                        function=ToolCallFunction(
                                            name="json",
                                            arguments=char
                                        )
                                    )
                                ]
                            ),
                            finish_reason=None
                        )
                    ],
                    system_fingerprint="fp_local_ollama",
                    service_tier="default"
                )
                
                yield f"data: {chunk.model_dump_json()}\n\n"
            
            # Final chunk - end stream
            final_chunk = ChatCompletionStreamingResponse(
                id=completion_id,
                model=request.model,
                created=created_time,
                choices=[
                    ChatChoiceStreaming(
                        index=0,
                        delta=DeltaMessage(),
                        finish_reason="tool_calls"
                    )
                ],
                system_fingerprint="fp_local_ollama",
                service_tier="default"
            )
            
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in BlockNote streaming: {str(e)}")
            error_chunk = {
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "code": "internal_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_blocknote_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )


def _create_blocknote_response(request: ChatCompletionRequest):
    """Create a non-streaming response for BlockNote tool calls."""
    # Generate response using the pipeline
    response_text, usage_info = generation_pipeline.chat_completion(request)
    
    # Create response in modern tool_calls format
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
    tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
    
    response = ChatCompletionResponse(
        id=completion_id,
        model=request.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id=tool_call_id,
                            type="function",
                            function=ToolCallFunction(
                                name="json",
                                arguments=response_text
                            )
                        )
                    ]
                ),
                finish_reason="tool_calls"
            )
        ],
        usage=Usage(**usage_info)
    )
    
    return response


def _create_streaming_response(request: ChatCompletionRequest):
    """Create a streaming response for regular chat."""
    from fastapi.responses import StreamingResponse
    import json
    import time
    
    def generate_stream():
        try:
            # Generate response using the pipeline
            response_text, usage_info = generation_pipeline.chat_completion(request)
            
            # Create completion ID
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
            created_time = int(time.time())
            
            # First chunk with role
            first_chunk = ChatCompletionStreamingResponse(
                id=completion_id,
                model=request.model,
                created=created_time,
                choices=[
                    ChatChoiceStreaming(
                        index=0,
                        delta=DeltaMessage(role="assistant"),
                        finish_reason=None
                    )
                ]
            )
            
            yield f"data: {first_chunk.model_dump_json()}\n\n"
            
            # Stream content word by word
            words = response_text.split()
            for i, word in enumerate(words):
                content = word + (" " if i < len(words) - 1 else "")
                
                chunk = ChatCompletionStreamingResponse(
                    id=completion_id,
                    model=request.model,
                    created=created_time,
                    choices=[
                        ChatChoiceStreaming(
                            index=0,
                            delta=DeltaMessage(content=content),
                            finish_reason=None
                        )
                    ]
                )
                
                yield f"data: {chunk.model_dump_json()}\n\n"
            
            # Final chunk
            final_chunk = ChatCompletionStreamingResponse(
                id=completion_id,
                model=request.model,
                created=created_time,
                choices=[
                    ChatChoiceStreaming(
                        index=0,
                        delta=DeltaMessage(),
                        finish_reason="stop"
                    )
                ]
            )
            
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}")
            error_chunk = {
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "code": "internal_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )


def _create_regular_response(request: ChatCompletionRequest):
    """Create a regular non-streaming response."""
    # Generate response using the pipeline
    response_text, usage_info = generation_pipeline.chat_completion(request)
    
    # Create response in OpenAI format
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
    
    response = ChatCompletionResponse(
        id=completion_id,
        model=request.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(
                    role="assistant",
                    content=response_text
                ),
                finish_reason="stop"
            )
        ],
        usage=Usage(**usage_info)
    )
    
    return response


# RAG Management endpoints

@router.post("/rag/initialize")
def initialize_rag_system():
    """Initialize the RAG system by loading PMFlex documents.
    
    Returns:
        Initialization status and results
    """
    try:
        from src.pipelines.rag_pipeline import rag_pipeline
        result = rag_pipeline.initialize()
        
        return {
            "status": "success",
            "message": "RAG system initialization completed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error initializing RAG system: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to initialize RAG system: {str(e)}",
                    "type": "rag_initialization_error",
                    "code": "rag_init_failed"
                }
            }
        )


@router.get("/rag/status")
def get_rag_status():
    """Get the current status of the RAG system.
    
    Returns:
        RAG system status and statistics
    """
    try:
        from src.pipelines.rag_pipeline import rag_pipeline
        stats = rag_pipeline.get_pipeline_stats()
        validation = rag_pipeline.validate_setup()
        
        return {
            "status": "success",
            "pipeline_stats": stats,
            "validation": validation
        }
        
    except Exception as e:
        logger.error(f"Error getting RAG status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to get RAG status: {str(e)}",
                    "type": "rag_status_error",
                    "code": "rag_status_failed"
                }
            }
        )


@router.post("/rag/refresh")
def refresh_rag_documents():
    """Refresh the RAG document index.
    
    Returns:
        Refresh operation results
    """
    try:
        from src.pipelines.rag_pipeline import rag_pipeline
        result = rag_pipeline.refresh_documents()
        
        return {
            "status": "success",
            "message": "Document refresh completed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error refreshing RAG documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to refresh documents: {str(e)}",
                    "type": "rag_refresh_error",
                    "code": "rag_refresh_failed"
                }
            }
        )


@router.post("/rag/search")
def search_rag_documents(query: str, max_results: int = 5):
    """Search RAG documents for specific information.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        Search results from RAG system
    """
    try:
        from src.pipelines.rag_pipeline import rag_pipeline
        results = rag_pipeline.search_documents(query, max_results)
        
        return {
            "status": "success",
            "query": query,
            "results": results,
            "total_results": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error searching RAG documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to search documents: {str(e)}",
                    "type": "rag_search_error",
                    "code": "rag_search_failed"
                }
            }
        )


# Project Status Report endpoint

@router.post("/generate-project-status-report", response_model=ProjectStatusReportResponse)
async def generate_project_status_report(
    request: ProjectStatusReportRequest
):
    """Generate a project status report from OpenProject work packages.
    
    Args:
        request: Project status report request with project info and OpenProject instance info
        
    Returns:
        Generated project status report
    """
    try:
        # Extract values from the new request structure
        project_id = request.project.id
        project_type = request.project.type
        base_url = request.openproject.base_url
        user_token = request.openproject.user_token
        debug = request.debug
        
        # Validate user token
        if not user_token:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "OpenProject user token is required",
                        "type": "authentication_error",
                        "code": "missing_user_token"
                    }
                }
            )
        
        # Initialize OpenProject client with debug parameter
        openproject_client = OpenProjectClient(
            base_url=base_url,
            api_key=user_token,
            debug=debug
        )
        
        logger.info(f"Generating project status report for project {project_id} (type: {project_type})")
        
        # Fetch work packages from OpenProject
        try:
            work_packages = await openproject_client.get_work_packages(str(project_id))
            logger.info(f"Fetched {len(work_packages)} work packages")
        except OpenProjectAPIError as e:
            logger.error(f"OpenProject API error: {e.message}")
            
            # Map OpenProject API errors to appropriate HTTP status codes
            if e.status_code == 401:
                raise HTTPException(status_code=401, detail={
                    "error": {
                        "message": e.message,
                        "type": "authentication_error",
                        "code": "invalid_api_key"
                    }
                })
            elif e.status_code == 403:
                raise HTTPException(status_code=403, detail={
                    "error": {
                        "message": e.message,
                        "type": "permission_error",
                        "code": "insufficient_permissions"
                    }
                })
            elif e.status_code == 404:
                raise HTTPException(status_code=404, detail={
                    "error": {
                        "message": e.message,
                        "type": "not_found_error",
                        "code": "project_not_found"
                    }
                })
            elif e.status_code == 503:
                raise HTTPException(status_code=503, detail={
                    "error": {
                        "message": e.message,
                        "type": "service_unavailable_error",
                        "code": "openproject_unavailable"
                    }
                })
            else:
                raise HTTPException(status_code=500, detail={
                    "error": {
                        "message": f"OpenProject API error: {e.message}",
                        "type": "external_api_error",
                        "code": "openproject_api_error"
                    }
                })
        
        # Generate project status report using LLM
        try:
            report_text, analysis = generation_pipeline.generate_project_status_report(
                project_id=str(project_id),
                project_type=project_type,
                openproject_base_url=base_url,
                work_packages=work_packages
            )
            
            logger.info(f"Successfully generated project status report for project {project_id}")
            
            return ProjectStatusReportResponse(
                project_id=project_id,
                project_type=project_type,
                report=report_text,
                work_packages_analyzed=len(work_packages),
                openproject_base_url=base_url
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "message": f"Failed to generate report: {str(e)}",
                        "type": "report_generation_error",
                        "code": "llm_generation_failed"
                    }
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in project status report generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "code": "internal_error"
                }
            }
        )


# Project Management Hints endpoint

@router.post("/project-management-hints", response_model=ProjectManagementHintsResponse)
async def generate_project_management_hints(
    request: ProjectManagementHintsRequest
):
    """Generate German project management hints based on automated checks.
    
    Args:
        request: Project management hints request with project info and OpenProject instance info
        
    Returns:
        Generated project management hints in German
    """
    try:
        # Extract values from the request structure
        project_id = request.project.id
        project_type = request.project.type
        base_url = request.openproject.base_url
        user_token = request.openproject.user_token
        debug = request.debug
        
        # Validate user token
        if not user_token:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "OpenProject user token is required",
                        "type": "authentication_error",
                        "code": "missing_user_token"
                    }
                }
            )
        
        # Initialize OpenProject client with debug parameter
        openproject_client = OpenProjectClient(
            base_url=base_url,
            api_key=user_token,
            debug=debug
        )
        
        logger.info(f"Generating project management hints for project {project_id} (type: {project_type})")
        
        # Fetch comprehensive project data from OpenProject
        try:
            # Fetch work packages
            work_packages = await openproject_client.get_work_packages(str(project_id))
            logger.info(f"Fetched {len(work_packages)} work packages")
            
            # Fetch additional data for the 10 checks
            relations = await openproject_client.get_work_package_relations(str(project_id))
            time_entries = await openproject_client.get_time_entries(str(project_id))
            users = await openproject_client.get_users()
            
            # Fetch journals and attachments for each work package
            journals_data = {}
            attachments_data = {}
            
            for wp in work_packages:
                try:
                    journals_data[wp.id] = await openproject_client.get_work_package_journals(wp.id)
                    attachments_data[wp.id] = await openproject_client.get_work_package_attachments(wp.id)
                except Exception as e:
                    logger.warning(f"Failed to fetch additional data for work package {wp.id}: {e}")
                    journals_data[wp.id] = []
                    attachments_data[wp.id] = []
            
            logger.info(f"Fetched additional data: {len(relations)} relations, {len(time_entries)} time entries, {len(users)} users")
            
        except OpenProjectAPIError as e:
            logger.error(f"OpenProject API error: {e.message}")
            
            # Map OpenProject API errors to appropriate HTTP status codes
            if e.status_code == 401:
                raise HTTPException(status_code=401, detail={
                    "error": {
                        "message": e.message,
                        "type": "authentication_error",
                        "code": "invalid_api_key"
                    }
                })
            elif e.status_code == 403:
                raise HTTPException(status_code=403, detail={
                    "error": {
                        "message": e.message,
                        "type": "permission_error",
                        "code": "insufficient_permissions"
                    }
                })
            elif e.status_code == 404:
                raise HTTPException(status_code=404, detail={
                    "error": {
                        "message": e.message,
                        "type": "not_found_error",
                        "code": "project_not_found"
                    }
                })
            elif e.status_code == 503:
                raise HTTPException(status_code=503, detail={
                    "error": {
                        "message": e.message,
                        "type": "service_unavailable_error",
                        "code": "openproject_unavailable"
                    }
                })
            else:
                raise HTTPException(status_code=500, detail={
                    "error": {
                        "message": f"OpenProject API error: {e.message}",
                        "type": "external_api_error",
                        "code": "openproject_api_error"
                    }
                })
        
        # Perform the 10 automated project management checks
        try:
            from src.templates.report_templates import ProjectManagementAnalyzer
            
            analyzer = ProjectManagementAnalyzer()
            checks_results = await analyzer.perform_all_checks(
                work_packages=work_packages,
                relations=relations,
                time_entries=time_entries,
                users=users,
                journals_data=journals_data,
                attachments_data=attachments_data
            )
            
            logger.info(f"Completed {analyzer.checks_performed} automated checks")
            
        except Exception as e:
            logger.error(f"Error performing automated checks: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "message": f"Failed to perform automated checks: {str(e)}",
                        "type": "analysis_error",
                        "code": "checks_failed"
                    }
                }
            )
        
        # Get PMFlex context from RAG system
        try:
            from src.pipelines.rag_pipeline import rag_pipeline
            
            # Build query for PMFlex context
            query_parts = [
                f"PMFlex {project_type} project management",
                "German federal government project standards",
                "project management best practices",
                "risk management guidelines"
            ]
            
            # Add specific terms based on check results
            if checks_results.get("deadline_health", {}).get("severity") == "critical":
                query_parts.append("deadline management project delays")
            
            if checks_results.get("resource_balance", {}).get("severity") == "warning":
                query_parts.append("resource allocation team management")
            
            query = " ".join(query_parts)
            pmflex_context = rag_pipeline.retriever.retrieve_context(
                query=query,
                max_chunks=5,
                score_threshold=0.1
            )
            
            logger.info("Retrieved PMFlex context from RAG system")
            
        except Exception as e:
            logger.warning(f"Could not retrieve PMFlex context: {e}")
            pmflex_context = ""
        
        # Generate German hints using LLM with enhanced monitoring
        try:
            # Track generation attempt
            from src.utils.hint_optimizer import hint_optimizer
            
            # Generate hints - now returns a list of dictionaries
            hints_list = generation_pipeline.generate_project_management_hints(
                project_id=str(project_id),
                project_type=project_type,
                openproject_base_url=base_url,
                checks_results=checks_results,
                pmflex_context=pmflex_context
            )
            
            # Convert to Pydantic models
            from src.models.schemas import ProjectManagementHint
            hints = []
            
            for i, hint_data in enumerate(hints_list):
                try:
                    if not isinstance(hint_data, dict):
                        logger.warning(f"Hint {i} is not a dictionary, skipping")
                        continue
                    
                    # Ensure required fields exist
                    if "title" not in hint_data or "description" not in hint_data:
                        logger.warning(f"Hint {i} missing required fields, skipping")
                        continue
                    
                    hint = ProjectManagementHint(
                        checked=hint_data.get("checked", False),
                        title=str(hint_data["title"])[:60],  # Truncate to max length
                        description=str(hint_data["description"])
                    )
                    hints.append(hint)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse hint {i}: {e}")
                    continue
            
            # Track generation metrics
            success = len(hints) > 0
            hint_optimizer.track_generation_attempt(
                success=success,
                used_fallback=False,  # The generation pipeline handles fallback internally
                json_parse_failed=False,  # No JSON parsing needed with new approach
                retry_succeeded=False
            )
            
            logger.info(f"Successfully generated {len(hints)} project management hints")
            
            # Summary is no longer part of the response format
            return ProjectManagementHintsResponse(
                hints=hints,
                summary=None,
                project_id=project_id,
                checks_performed=analyzer.checks_performed,
                openproject_base_url=base_url
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating hints: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "message": f"Failed to generate hints: {str(e)}",
                        "type": "hint_generation_error",
                        "code": "llm_generation_failed"
                    }
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in project management hints generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "code": "internal_error"
                }
            }
        )


@router.get("/v1/models", response_model=ModelsResponse)
def list_models():
    """List available models (OpenAI-compatible endpoint).
    
    Returns:
        List of available models in OpenAI format
    """
    try:
        available_models = generation_pipeline.get_available_models()
        
        models = [
            ModelInfo(id=model_id)
            for model_id in available_models
        ]
        
        return ModelsResponse(data=models)
        
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "code": "internal_error"
                }
            }
        )


# Additional OpenAI-compatible endpoints for completeness

@router.get("/v1/models/{model_id}")
def get_model(model_id: str):
    """Get specific model information (OpenAI-compatible endpoint).
    
    Args:
        model_id: The model ID to retrieve
        
    Returns:
        Model information
    """
    try:
        available_models = generation_pipeline.get_available_models()
        
        if model_id not in available_models:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"Model '{model_id}' not found",
                        "type": "invalid_request_error",
                        "param": "model",
                        "code": "model_not_found"
                    }
                }
            )
        
        return ModelInfo(id=model_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "code": "internal_error"
                }
            }
        )


# Hint Generation Monitoring endpoints

@router.get("/hint-generation/metrics")
def get_hint_generation_metrics():
    """Get hint generation performance metrics.
    
    Returns:
        Current hint generation metrics and success rates
    """
    try:
        from src.utils.hint_optimizer import hint_optimizer
        metrics = hint_optimizer.get_generation_metrics()
        
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": "2025-01-17T22:54:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting hint generation metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to get metrics: {str(e)}",
                    "type": "metrics_error",
                    "code": "metrics_failed"
                }
            }
        )


@router.post("/hint-generation/metrics/reset")
def reset_hint_generation_metrics():
    """Reset hint generation metrics.
    
    Returns:
        Reset confirmation
    """
    try:
        from src.utils.hint_optimizer import hint_optimizer
        hint_optimizer.reset_metrics()
        
        return {
            "status": "success",
            "message": "Hint generation metrics have been reset",
            "timestamp": "2025-01-17T22:54:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error resetting hint generation metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to reset metrics: {str(e)}",
                    "type": "metrics_error",
                    "code": "metrics_reset_failed"
                }
            }
        )


@router.post("/hint-generation/test-fallback")
async def test_hint_fallback_generation(checks_results: dict):
    """Test the enhanced fallback hint generation system.
    
    Args:
        checks_results: Mock check results to test fallback generation
        
    Returns:
        Generated fallback hints and quality analysis
    """
    try:
        from src.utils.hint_optimizer import hint_optimizer
        
        # Generate enhanced fallback hints
        fallback_json = hint_optimizer.generate_enhanced_fallback_hints(checks_results)
        
        # Analyze the quality of generated hints
        quality_analysis = hint_optimizer.analyze_hint_quality(fallback_json)
        
        # Parse the JSON to return structured data
        import json
        hints_data = json.loads(fallback_json)
        
        return {
            "status": "success",
            "fallback_hints": hints_data,
            "quality_analysis": quality_analysis,
            "generation_method": "enhanced_fallback",
            "timestamp": "2025-01-17T22:54:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error testing fallback hint generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to test fallback generation: {str(e)}",
                    "type": "fallback_test_error",
                    "code": "fallback_test_failed"
                }
            }
        )
