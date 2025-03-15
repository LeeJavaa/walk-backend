"""
Response models for the Walk API.

This module defines Pydantic models for standardizing API responses.
"""
from typing import Generic, TypeVar, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """Standard API response format."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[str]] = None

# Context Models
class ContextItem(BaseModel):
    """Context item representation in API responses."""
    id: str
    source: str
    content_type: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        orm_mode = True

class ContextList(BaseModel):
    """List of context items."""
    items: List[ContextItem]
    total: int = Field(..., description="Total number of items")

class ContextSearchResult(BaseModel):
    """Result item from context search."""
    context: ContextItem
    similarity_score: float

class ContextSearchResponse(BaseModel):
    """Response for context search."""
    results: List[ContextSearchResult]

# Task Models
class Task(BaseModel):
    """Task representation in API responses."""
    id: str
    description: str
    requirements: List[str]
    constraints: List[str]
    context_ids: List[str]
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class TaskList(BaseModel):
    """List of tasks."""
    items: List[Task]
    total: int = Field(..., description="Total number of items")

# Pipeline Models
class PipelineStateArtifact(BaseModel):
    """Artifacts produced by pipeline stages."""
    stage_name: str
    content: Dict[str, Any]

class PipelineStateFeedback(BaseModel):
    """Feedback item in pipeline state."""
    id: str
    stage_name: str
    content: str
    type: str
    timestamp: str
    incorporated: bool

class PipelineState(BaseModel):
    """Pipeline state representation in API responses."""
    id: str
    task_id: str
    current_stage: str
    stages_completed: List[str]
    artifacts: Dict[str, Any]
    feedback: List[PipelineStateFeedback]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class PipelineProgress(BaseModel):
    """Pipeline progress information."""
    current_stage: str
    completed_stages: List[str]
    total_stages: int
    percentage: float
    status: str = Field(..., description="Current execution status (executing/completed)")

class Checkpoint(BaseModel):
    """Checkpoint information."""
    id: str
    stage: str
    timestamp: str

class CheckpointList(BaseModel):
    """List of checkpoints."""
    items: List[Checkpoint]