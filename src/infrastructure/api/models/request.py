"""
Request models for the Walk API.

This module defines Pydantic models for validating API request data.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

# Context Models
class SearchQuery(BaseModel):
    """Request model for context search."""
    query: str = Field(..., description="Natural language query for semantic search")
    limit: int = Field(10, description="Maximum number of results to return")

# Task Models
class CreateTaskRequest(BaseModel):
    """Request model for creating a task."""
    description: str = Field(..., description="Task description")
    requirements: List[str] = Field(default_factory=list, description="List of requirements")
    constraints: List[str] = Field(default_factory=list, description="List of constraints")
    context_ids: List[str] = Field(default_factory=list, description="List of context IDs to associate with the task")

class QueryRequest(BaseModel):
    """Request model for RAG queries."""
    text: str = Field(..., description="Query text")

# Pipeline Models
class ExecutePipelineRequest(BaseModel):
    """Request model for executing a pipeline."""
    task_id: str = Field(..., description="ID of the task to execute")
    continue_from_current: bool = Field(False, description="Whether to continue from current state")
    create_checkpoints: bool = Field(False, description="Whether to create checkpoints before each stage")
    wait_for_feedback: bool = Field(False, description="Whether to pause for feedback after each stage")
    use_transactions: bool = Field(False, description="Whether to use transactions for state updates")

class ExecuteStageRequest(BaseModel):
    """Request model for executing a specific pipeline stage."""
    stage_name: str = Field(..., description="Name of the stage to execute")
    create_checkpoint: bool = Field(True, description="Whether to create a checkpoint before execution")

class RollbackRequest(BaseModel):
    """Request model for rolling back to a checkpoint."""
    checkpoint_id: str = Field(..., description="ID of the checkpoint to roll back to")

# Feedback Models
class SubmitFeedbackRequest(BaseModel):
    """Request model for submitting feedback."""
    pipeline_state_id: str = Field(..., description="ID of the pipeline state")
    stage_name: str = Field(..., description="Name of the stage to provide feedback for")
    content: str = Field(..., description="Feedback content")
    feedback_type: str = Field("suggestion", description="Type of feedback (suggestion, correction, enhancement)")

class IncorporateFeedbackRequest(BaseModel):
    """Request model for incorporating feedback."""
    pipeline_state_id: str = Field(..., description="ID of the pipeline state")
    feedback_ids: List[str] = Field(default_factory=list, description="List of feedback IDs to incorporate")
    incorporate_all: bool = Field(False, description="Whether to incorporate all available feedback")