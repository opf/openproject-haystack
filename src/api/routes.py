"""API routes for the Haystack application."""

from fastapi import APIRouter, HTTPException
from src.models.schemas import GenerationRequest, GenerationResponse, HealthResponse
from src.pipelines.generation import generation_pipeline

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
