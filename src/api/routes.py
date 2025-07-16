"""API routes for the Haystack application."""

from fastapi import APIRouter, HTTPException, Header
from src.api.schemas import (
    GenerationRequest, GenerationResponse, HealthResponse,
    ChatCompletionRequest, ChatCompletionResponse, ChatMessage, ChatChoice,
    Usage, ModelsResponse, ModelInfo, ErrorResponse, ErrorDetail,
    ProjectStatusReportRequest, ProjectStatusReportResponse,
    SuggestRequest, SuggestResponse
)
from src.pipelines.generation import generation_pipeline
from src.services.openproject_client import OpenProjectClient, OpenProjectAPIError
import uuid
import logging
from typing import Optional
from src.pipelines.suggestion import pipeline

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

@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion (OpenAI-compatible endpoint).

    Args:
        request: Chat completion request with messages and parameters

    Returns:
        Chat completion response in OpenAI format
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


# Project Status Report endpoint

@router.post("/generate-project-status-report", response_model=ProjectStatusReportResponse)
async def generate_project_status_report(
    request: ProjectStatusReportRequest,
    authorization: Optional[str] = Header(None)
):
    """Generate a project status report from OpenProject work packages.

    Args:
        request: Project status report request with project ID and base URL
        authorization: Bearer token for OpenProject API authentication

    Returns:
        Generated project status report
    """
    try:
        # Validate authorization header
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "Authorization header is required",
                        "type": "authentication_error",
                        "code": "missing_authorization"
                    }
                }
            )

        # Extract API key from Bearer token
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "Authorization header must be in format 'Bearer <token>'",
                        "type": "authentication_error",
                        "code": "invalid_authorization_format"
                    }
                }
            )

        api_key = authorization[7:]  # Remove "Bearer " prefix

        if not api_key:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "API key cannot be empty",
                        "type": "authentication_error",
                        "code": "empty_api_key"
                    }
                }
            )

        # Initialize OpenProject client
        openproject_client = OpenProjectClient(
            base_url=request.openproject_base_url,
            api_key=api_key
        )

        logger.info(f"Generating project status report for project {request.project_id}")

        # Fetch work packages from OpenProject
        try:
            work_packages = await openproject_client.get_work_packages(request.project_id)
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
                project_id=request.project_id,
                openproject_base_url=request.openproject_base_url,
                work_packages=work_packages
            )

            logger.info(f"Successfully generated project status report for project {request.project_id}")

            return ProjectStatusReportResponse(
                project_id=request.project_id,
                report=report_text,
                work_packages_analyzed=len(work_packages),
                openproject_base_url=request.openproject_base_url
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

@router.post("/evaluate-projects-similarities", response_model=SuggestResponse)
def suggest_endpoint(request: SuggestRequest):
    try:
        result = pipeline.suggest(request.project_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
