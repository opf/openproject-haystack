"""API routes for the Haystack application."""

from fastapi import APIRouter, HTTPException
from src.models.schemas import (
    GenerationRequest, GenerationResponse, HealthResponse,
    ChatCompletionRequest, ChatCompletionResponse, ChatMessage, ChatChoice,
    Usage, ModelsResponse, ModelInfo, ErrorResponse, ErrorDetail
)
from src.pipelines.generation import generation_pipeline
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
