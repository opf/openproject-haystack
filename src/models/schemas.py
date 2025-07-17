"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime
import time

# --- Suggestion Schemas ---
class CandidateSuggestion(BaseModel):
    name: Optional[str] = None
    score: Optional[float] = None
    project_id: Optional[Union[int, str]] = None
    reason: str

class SuggestRequest(BaseModel):
    project_id: Union[int, str]

class SuggestResponse(BaseModel):
    portfolio: Optional[str] = None
    candidates: List[CandidateSuggestion]
    text: str

# --- Generation Schemas ---
class GenerationRequest(BaseModel):
    """Request model for text generation."""
    prompt: str

class GenerationResponse(BaseModel):
    """Response model for text generation."""
    response: str

# --- Health Check ---
class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str

# --- OpenAI Chat Completion Compatible Models ---
class ChatMessage(BaseModel):
    """A chat message with role and content."""
    role: str  # Accept any string for compatibility
    content: str

class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model: str = "mistral:latest"
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=1000, gt=0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    stop: Optional[List[str]] = None
    stream: Optional[bool] = False

class Usage(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatChoice(BaseModel):
    """A chat completion choice."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str
    model: str
    choices: List[ChatChoice]
    usage: Usage

class ModelInfo(BaseModel):
    """Model information."""
    id: str

class ModelsResponse(BaseModel):
    """Response for models endpoint."""
    data: List[ModelInfo]

class ErrorDetail(BaseModel):
    """Error detail information."""
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    """OpenAI-compatible error response."""
    error: ErrorDetail

# --- Project Status Report Models ---
class ProjectInfo(BaseModel):
    """Project information model."""
    id: Union[int, str] = Field(..., description="OpenProject project ID")
    type: str = Field(..., description="Project type (e.g., 'portfolio')")

class OpenProjectInfo(BaseModel):
    """OpenProject instance information model."""
    base_url: str = Field(..., description="Base URL of OpenProject instance")
    user_token: str = Field(..., description="OpenProject user API token")

class ProjectStatusReportRequest(BaseModel):
    """Request model for project status report generation."""
    project: ProjectInfo = Field(..., description="Project information")
    openproject: OpenProjectInfo = Field(..., description="OpenProject instance information")

class WorkPackage(BaseModel):
    """Model for OpenProject work package data."""
    id: Union[int, str]
    subject: str
    status: Optional[Dict[str, Any]] = None
    priority: Optional[Dict[str, Any]] = None
    assignee: Optional[Dict[str, Any]] = None
    due_date: Optional[str] = None
    done_ratio: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: Optional[Dict[str, Any]] = None

class ProjectStatusReportResponse(BaseModel):
    """Response model for project status report."""
    project_id: Union[int, str]
    project_type: str
    report: str
    work_packages_analyzed: int
    openproject_base_url: str
