"""
Pipeline execution router for the Walk API.

This module defines the API endpoints for pipeline execution and management.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends

from src.infrastructure.api.models.request import ExecutePipelineRequest, \
    ExecuteStageRequest, RollbackRequest
from src.infrastructure.api.models.response import (
    APIResponse, PipelineState as PipelineStateResponse,
    PipelineProgress, Checkpoint, CheckpointList
)
from src.infrastructure.api.utils.dependency_injection import (
    get_pipeline_orchestrator,
    get_execute_pipeline_stage_use_case,
    get_rollback_pipeline_use_case,
    get_get_pipeline_state_use_case,
    get_pipeline_stage,
    get_state_manager, get_pipeline_repository
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/execute", response_model=APIResponse)
def execute_pipeline(request: ExecutePipelineRequest,
                     background_tasks: BackgroundTasks):
    """
    Execute the complete pipeline for a task asynchronously.
    Returns immediately with pipeline state ID and executes in the background.
    """
    try:
        orchestrator = get_pipeline_orchestrator()

        # Get the task
        pipeline_repository = get_pipeline_repository()
        task = pipeline_repository.get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404,
                                detail=f"Task with ID {request.task_id} not found")

        # Get or create initial pipeline state
        if request.continue_from_current:
            state_manager = get_state_manager()
            state = state_manager.get_latest_pipeline_state(request.task_id)
            if not state:
                state = state_manager.create_initial_state(task)
        else:
            state_manager = get_state_manager()
            state = state_manager.create_initial_state(task)

        # Add execution to background tasks
        background_tasks.add_task(
            orchestrator.execute_pipeline,
            task_id=request.task_id,
            continue_from_current=True, # Has to be hard coded to use the same state as defined above, can fix in future
            create_checkpoints=request.create_checkpoints,
            wait_for_feedback=request.wait_for_feedback,
            use_transactions=request.use_transactions
        )

        return APIResponse(
            success=True,
            message="Pipeline execution started",
            data={
                "pipeline_state_id": state.id,
                "task_id": state.task_id,
                "current_stage": state.current_stage,
                "status": "executing"
            }
        )

    except KeyError as e:
        logger.error(f"Task not found: {str(e)}")
        raise HTTPException(status_code=404,
                            detail=f"Task with ID {request.task_id} not found")

    except Exception as e:
        logger.error(f"Error executing pipeline: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to execute pipeline",
            errors=[str(e)]
        )


@router.get("/{pipeline_id}/progress",
            response_model=APIResponse[PipelineProgress])
def get_pipeline_progress(pipeline_id: str):
    """
    Get the progress of a pipeline.
    """
    try:
        state_manager = get_state_manager()

        # Get the current state
        pipeline_state = state_manager.get_pipeline_state(pipeline_id)

        # Get the progress
        progress = state_manager.get_pipeline_progress(pipeline_id)

        # Determine execution status (you might need to add a status field to your state)
        status = "completed" if progress["current_stage"] == \
                                pipeline_state.PIPELINE_STAGES[
                                    -1] and pipeline_state.current_stage in pipeline_state.stages_completed else "executing"

        return APIResponse(
            success=True,
            data=PipelineProgress(
                current_stage=progress["current_stage"],
                completed_stages=progress["completed_stages"],
                total_stages=progress["total_stages"],
                percentage=progress["percentage"],
                status=status
            )
        )

    except KeyError as e:
        logger.error(f"Pipeline state not found: {str(e)}")
        raise HTTPException(status_code=404,
                            detail=f"Pipeline state with ID {pipeline_id} not found")

    except Exception as e:
        logger.error(f"Error getting pipeline progress: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to get pipeline progress",
            errors=[str(e)]
        )


@router.get("/{pipeline_id}/checkpoints",
            response_model=APIResponse[CheckpointList])
def list_checkpoints(pipeline_id: str):
    """
    List all checkpoints in a pipeline state.
    """
    try:
        state_manager = get_state_manager()

        # Get the checkpoints
        checkpoints = state_manager.list_checkpoints(pipeline_id)

        # Convert to response model
        response_checkpoints = [
            Checkpoint(
                id=checkpoint["id"],
                stage=checkpoint["stage"],
                timestamp=checkpoint["timestamp"]
            ) for checkpoint in checkpoints
        ]

        return APIResponse(
            success=True,
            data=CheckpointList(items=response_checkpoints)
        )

    except KeyError as e:
        logger.error(f"Pipeline state not found: {str(e)}")
        raise HTTPException(status_code=404,
                            detail=f"Pipeline state with ID {pipeline_id} not found")

    except Exception as e:
        logger.error(f"Error listing checkpoints: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to list checkpoints",
            errors=[str(e)]
        )


@router.post("/{pipeline_id}/rollback", response_model=APIResponse)
def rollback_pipeline(pipeline_id: str, request: RollbackRequest):
    """
    Roll back a pipeline to a previous checkpoint.
    """
    try:
        use_case = get_rollback_pipeline_use_case()

        # Rollback to the checkpoint
        updated_state = use_case.execute(pipeline_id, request.checkpoint_id)

        return APIResponse(
            success=True,
            message=f"Successfully rolled back to checkpoint {request.checkpoint_id}",
            data={
                "pipeline_state_id": updated_state.id,
                "current_stage": updated_state.current_stage,
                "completed_stages": updated_state.stages_completed
            }
        )

    except KeyError as e:
        logger.error(f"Pipeline state or checkpoint not found: {str(e)}")
        if "not found" in str(e) and "checkpoint" in str(e).lower():
            return APIResponse(
                success=False,
                message=f"Checkpoint {request.checkpoint_id} not found",
                errors=[str(e)]
            )
        else:
            raise HTTPException(status_code=404,
                                detail=f"Pipeline state with ID {pipeline_id} not found")

    except Exception as e:
        logger.error(f"Error rolling back pipeline: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to roll back pipeline",
            errors=[str(e)]
        )


def _convert_pipeline_state(pipeline_state):
    """
    Convert a domain PipelineState entity to a response model.
    """
    # In a full implementation, this would create a complete PipelineStateResponse object
    # For simplicity, we're just returning a dict with the key information
    return {
        "id": pipeline_state.id,
        "task_id": pipeline_state.task_id,
        "current_stage": pipeline_state.current_stage,
        "stages_completed": pipeline_state.stages_completed,
        "created_at": pipeline_state.created_at,
        "updated_at": pipeline_state.updated_at
    }


@router.get("/{pipeline_id}", response_model=APIResponse)
def get_pipeline_state(pipeline_id: str):
    """
    Get the current state of a pipeline.
    """
    try:
        use_case = get_get_pipeline_state_use_case()
        pipeline_state = use_case.execute(pipeline_id)

        if not pipeline_state:
            raise HTTPException(status_code=404,
                                detail=f"Pipeline state with ID {pipeline_id} not found")

        # Convert the pipeline state to a response model
        response_state = _convert_pipeline_state(pipeline_state)

        return APIResponse(
            success=True,
            data=response_state
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting pipeline state: {str(e)}")
        return APIResponse(
            success=False,
            message=f"Failed to get pipeline state {pipeline_id}",
            errors=[str(e)]
        )


@router.post("/{pipeline_id}/execute", response_model=APIResponse)
def execute_pipeline_stage(pipeline_id: str, request: ExecuteStageRequest):
    """
    Execute a specific stage in the pipeline.
    """
    try:
        # Get the use case
        use_case = get_execute_pipeline_stage_use_case()

        # Create the stage
        stage = get_pipeline_stage(request.stage_name)
        if not stage:
            return APIResponse(
                success=False,
                message=f"Invalid stage name: {request.stage_name}",
                errors=[f"Stage {request.stage_name} not found"]
            )

        # Execute the stage
        updated_state = use_case.execute(
            pipeline_state_id=pipeline_id,
            stage=stage,
            next_stage_name=None
        )

        return APIResponse(
            success=True,
            message=f"Successfully executed stage {request.stage_name}",
            data={
                "pipeline_state_id": updated_state.id,
                "current_stage": updated_state.current_stage,
                "completed_stages": updated_state.stages_completed
            }
        )

    except KeyError as e:
        logger.error(f"Pipeline state not found: {str(e)}")
        raise HTTPException(status_code=404,
                            detail=f"Pipeline state with ID {pipeline_id} not found")

    except ValueError as e:
        logger.error(f"Invalid stage transition: {str(e)}")
        return APIResponse(
            success=False,
            message="Invalid stage transition",
            errors=[str(e)]
        )

    except Exception as e:
        logger.error(f"Error executing pipeline stage: {str(e)}")
        return APIResponse(
            success=False,
            message=f"Failed to execute stage {request.stage_name}",
            errors=[str(e)]
        )