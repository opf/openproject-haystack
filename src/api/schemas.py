from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

# Suggestion schemas
class CandidateSuggestion(BaseModel):
    name: Optional[str] = None
    score: Optional[float] = None
    project_id: Optional[int] = None
    reason: str

class SuggestRequest(BaseModel):
    project_id: int

class SuggestResponse(BaseModel):
    portfolio: Optional[str] = None
    candidates: List[CandidateSuggestion]
    text: str

# Generation schemas
class GenerationRequest(BaseModel):
    prompt: str

class GenerationResponse(BaseModel):
    response: str

# Health check
class HealthResponse(BaseModel):
    status: str

# OpenAI-compatible schemas
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    stop: Optional[List[str]] = None

class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    choices: List[ChatChoice]
    usage: Usage

class ModelInfo(BaseModel):
    id: str

class ModelsResponse(BaseModel):
    data: List[ModelInfo]

class ErrorDetail(BaseModel):
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail

# Project Status Report schemas
class ProjectStatusReportRequest(BaseModel):
    project_id: str
    openproject_base_url: str

class ProjectStatusReportResponse(BaseModel):
    project_id: str
    report: str
    work_packages_analyzed: int
    openproject_base_url: str

class WorkPackage(BaseModel):
    id: str
    subject: str
    status: Optional[Dict[str, Any]] = None
    priority: Optional[Dict[str, Any]] = None
    assignee: Optional[Dict[str, Any]] = None
    due_date: Optional[str] = None
    done_ratio: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: Optional[Dict[str, Any]] = None
