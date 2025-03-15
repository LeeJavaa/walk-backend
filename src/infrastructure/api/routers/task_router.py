"""
Task management router for the Walk API.

This module defines the API endpoints for task management.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, \
    Query

from src.domain.entities.task import Task
from src.infrastructure.api.models.request import CreateTaskRequest, \
    QueryRequest
from src.infrastructure.api.models.response import APIResponse, TaskList, \
    Task as TaskResponse
from src.infrastructure.api.utils.dependency_injection import (
    get_pipeline_use_case,
    get_pipeline_repository,
    get_rag_service
)
from src.infrastructure.api.utils.file_handling import save_upload_file

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=APIResponse[TaskList])
def list_tasks(
        status: Optional[str] = Query(None, description="Filter by status")):
    """
    List all tasks, optionally filtered by status.
    """
    try:
        repository = get_pipeline_repository()
        tasks = repository.list_tasks(status)

        # Convert domain entities to response models
        response_items = [
            TaskResponse(
                id=task.id,
                description=task.description,
                requirements=task.requirements,
                constraints=task.constraints,
                context_ids=task.context_ids,
                status=task.status.value,
                created_at=task.created_at
            ) for task in tasks
        ]

        return APIResponse(
            success=True,
            data=TaskList(items=response_items, total=len(response_items))
        )

    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to list tasks",
            errors=[str(e)]
        )


@router.post("/", response_model=APIResponse)
def create_task(
        task_data: CreateTaskRequest,
        input_file: Optional[UploadFile] = File(None)
):
    """
    Create a new task for code generation.
    """
    try:
        # Build the task input string
        task_input = task_data.description + "\n\n"

        if task_data.requirements:
            task_input += "Requirements:\n"
            for req in task_data.requirements:
                task_input += f"- {req}\n"
            task_input += "\n"

        if task_data.constraints:
            task_input += "Constraints:\n"
            for constraint in task_data.constraints:
                task_input += f"- {constraint}\n"
            task_input += "\n"

        # Read additional input from file if provided
        if input_file:
            file_path = save_upload_file(input_file)
            with open(file_path, "r") as f:
                additional_input = f.read()
                task_input += additional_input

        # Parse task from input
        task = Task.parse_from_user_input(task_input)

        # Add context IDs if provided
        if task_data.context_ids:
            task.context_ids = task_data.context_ids

        # Create pipeline for the task
        use_case = get_pipeline_use_case()
        saved_task, pipeline_state = use_case.execute(task)

        return APIResponse(
            success=True,
            message=f"Task created successfully with ID {saved_task.id}",
            data={
                "task_id": saved_task.id,
                "pipeline_state_id": pipeline_state.id
            }
        )

    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to create task",
            errors=[str(e)]
        )


@router.post("/json", response_model=APIResponse)
def create_task_json(task_data: CreateTaskRequest):
    """
    Create a new task using JSON data.

    This endpoint accepts a JSON request body with task data.
    """
    try:
        # Build the task input string
        task_input = task_data.description + "\n\n"

        if task_data.requirements:
            task_input += "Requirements:\n"
            for req in task_data.requirements:
                task_input += f"- {req}\n"
            task_input += "\n"

        if task_data.constraints:
            task_input += "Constraints:\n"
            for constraint in task_data.constraints:
                task_input += f"- {constraint}\n"
            task_input += "\n"

        # Parse task from input
        task = Task.parse_from_user_input(task_input)

        # Add context IDs if provided
        if task_data.context_ids:
            task.context_ids = task_data.context_ids

        # Create pipeline for the task
        use_case = get_pipeline_use_case()
        saved_task, pipeline_state = use_case.execute(task)

        return APIResponse(
            success=True,
            message=f"Task created successfully with ID {saved_task.id}",
            data={
                "task_id": saved_task.id,
                "pipeline_state_id": pipeline_state.id
            }
        )

    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to create task",
            errors=[str(e)]
        )


@router.get("/{task_id}", response_model=APIResponse)
def get_task(task_id: str):
    """
    Get a specific task by ID.
    """
    try:
        repository = get_pipeline_repository()
        task = repository.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404,
                                detail=f"Task with ID {task_id} not found")

        # Get the latest pipeline state for this task
        latest_state = repository.get_latest_pipeline_state(task_id)
        pipeline_state_id = latest_state.id if latest_state else None

        # Convert domain entity to response model
        task_response = TaskResponse(
            id=task.id,
            description=task.description,
            requirements=task.requirements,
            constraints=task.constraints,
            context_ids=task.context_ids,
            status=task.status.value,
            created_at=task.created_at
        )

        return APIResponse(
            success=True,
            data={
                "task": task_response,
                "pipeline_state_id": pipeline_state_id
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting task: {str(e)}")
        return APIResponse(
            success=False,
            message=f"Failed to get task {task_id}",
            errors=[str(e)]
        )


@router.post("/query", response_model=APIResponse)
def query_system(query: QueryRequest):
    """
    Query the system using RAG to get information.
    """
    try:
        rag_service = get_rag_service()
        response = rag_service.generate_with_context(query.text)

        return APIResponse(
            success=True,
            data={
                "response": response
            }
        )

    except Exception as e:
        logger.error(f"Error querying system: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to query system",
            errors=[str(e)]
        )