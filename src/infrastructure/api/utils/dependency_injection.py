"""
Dependency injection utilities for the Walk API.

This module provides FastAPI dependency functions that wrap around
the existing dependency container from the CLI.
"""
from fastapi import Depends

from src.infrastructure.cli.utils.dependency_container import (
    # Context dependencies
    create_add_context_use_case,
    create_remove_context_use_case,
    create_list_context_use_case,
    create_search_context_use_case,

    # Task dependencies
    create_pipeline_use_case,
    create_pipeline_repository,

    # Pipeline dependencies
    create_execute_pipeline_stage_use_case,
    create_rollback_pipeline_use_case,
    create_get_pipeline_state_use_case,
    create_pipeline_stage_with_dependencies,
    create_pipeline_orchestrator,

    # RAG dependencies
    create_rag_service,

    # Feedback dependencies
    create_submit_feedback_use_case,
    create_incorporate_feedback_use_case,

    # State management dependencies
    create_state_manager,
)


# Context dependencies
def get_add_context_use_case():
    """Get the AddContextUseCase."""
    return create_add_context_use_case()


def get_remove_context_use_case():
    """Get the RemoveContextUseCase."""
    return create_remove_context_use_case()


def get_list_context_use_case():
    """Get the ListContextUseCase."""
    return create_list_context_use_case()


def get_search_context_use_case():
    """Get the SearchContextUseCase."""
    return create_search_context_use_case()


# Task dependencies
def get_pipeline_use_case():
    """Get the CreatePipelineUseCase."""
    return create_pipeline_use_case()


def get_pipeline_repository():
    """Get the PipelineRepository."""
    return create_pipeline_repository()


# Pipeline dependencies
def get_execute_pipeline_stage_use_case():
    """Get the ExecutePipelineStageUseCase."""
    return create_execute_pipeline_stage_use_case()


def get_rollback_pipeline_use_case():
    """Get the RollbackPipelineUseCase."""
    return create_rollback_pipeline_use_case()


def get_get_pipeline_state_use_case():
    """Get the GetPipelineStateUseCase."""
    return create_get_pipeline_state_use_case()


def get_pipeline_stage(stage_name: str):
    """Get a pipeline stage instance."""
    return create_pipeline_stage_with_dependencies(stage_name)


def get_pipeline_orchestrator():
    """Get the PipelineOrchestrator."""
    return create_pipeline_orchestrator()


# RAG dependencies
def get_rag_service():
    """Get the RAGService."""
    return create_rag_service()


# Feedback dependencies
def get_submit_feedback_use_case():
    """Get the SubmitFeedbackUseCase."""
    return create_submit_feedback_use_case()


def get_incorporate_feedback_use_case():
    """Get the IncorporateFeedbackUseCase."""
    return create_incorporate_feedback_use_case()


# State management dependencies
def get_state_manager():
    """Get the StateManager."""
    return create_state_manager()