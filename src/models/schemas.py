"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import time


class GenerationRequest(BaseModel):
    """Request model for text generation."""
    prompt: str


class GenerationResponse(BaseModel):
    """Response model for text generation."""
    response: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str


# OpenAI Chat Completion Compatible Models

class ChatMessage(BaseModel):
    """A chat message with role and content."""
    role: Literal["system", "user", "assistant"]
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
    finish_reason: Literal["stop", "length", "content_filter"] = "stop"


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatChoice]
    usage: Usage


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "local"


class ModelsResponse(BaseModel):
    """Response for models endpoint."""
    object: str = "list"
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


# Project Status Report Models

class ProjectInfo(BaseModel):
    """Project information model."""
    id: int = Field(..., description="OpenProject project ID")
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
    id: int
    subject: str
    status: Dict[str, Any]
    priority: Optional[Dict[str, Any]] = None
    assignee: Optional[Dict[str, Any]] = None
    due_date: Optional[str] = None
    done_ratio: Optional[int] = None
    created_at: str
    updated_at: str
    description: Optional[Dict[str, Any]] = None


class ProjectStatusReportResponse(BaseModel):
    """Response model for project status report."""
    project_id: int
    project_type: str
    report: str
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    work_packages_analyzed: int
    openproject_base_url: str


# Project Management Hints Models

class ProjectManagementHint(BaseModel):
    """Model for a single project management hint."""
    checked: bool = False
    title: str = Field(..., description="German title of the hint")
    description: str = Field(..., description="German description of the hint")


class ProjectManagementHintsRequest(BaseModel):
    """Request model for project management hints generation."""
    project: ProjectInfo = Field(..., description="Project information")
    openproject: OpenProjectInfo = Field(..., description="OpenProject instance information")


class ProjectManagementHintsResponse(BaseModel):
    """Response model for project management hints."""
    hints: List[ProjectManagementHint] = Field(..., description="List of project management hints")
    summary: Optional[str] = Field(None, description="Optional summary text in German")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    project_id: int
    checks_performed: int
    openproject_base_url: str
