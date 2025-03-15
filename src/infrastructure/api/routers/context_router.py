"""
Context management router for the Walk API.

This module defines the API endpoints for context management.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Query

from src.domain.entities.context_item import ContextItem
from src.infrastructure.api.models.request import SearchQuery
from src.infrastructure.api.models.response import APIResponse, ContextList, ContextSearchResponse, ContextSearchResult, ContextItem as ContextItemResponse
from src.infrastructure.api.utils.dependency_injection import (
    get_add_context_use_case,
    get_remove_context_use_case,
    get_list_context_use_case,
    get_search_context_use_case
)
from src.infrastructure.api.utils.file_handling import save_upload_file

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=APIResponse[ContextList])
def list_contexts(content_type: Optional[str] = Query(None, description="Filter by content type")):
    """
    List all context items, optionally filtered by content type.
    """
    try:
        use_case = get_list_context_use_case()
        filters = {"content_type": content_type} if content_type else None
        context_items = use_case.execute(filters)

        # Convert domain entities to response models
        response_items = [
            ContextItemResponse(
                id=item.id,
                source=item.source,
                content_type=item.content_type.value,
                created_at=item.created_at,
                updated_at=item.updated_at,
                metadata=item.metadata
            ) for item in context_items
        ]

        return APIResponse(
            success=True,
            data=ContextList(items=response_items, total=len(response_items))
        )

    except Exception as e:
        logger.error(f"Error listing contexts: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to list contexts",
            errors=[str(e)]
        )

@router.post("/", response_model=APIResponse)
def add_context(file: UploadFile = File(...)):
    """
    Add a file to the context repository.
    """
    try:
        # Save the uploaded file
        file_path = save_upload_file(file)

        # Add to context
        use_case = get_add_context_use_case()
        context_item = use_case.execute_from_file_path(file_path)

        return APIResponse(
            success=True,
            message=f"Context added successfully from {file.filename}",
            data={
                "id": context_item.id,
                "source": context_item.source,
                "content_type": context_item.content_type.value
            }
        )

    except Exception as e:
        logger.error(f"Error adding context: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to add context",
            errors=[str(e)]
        )

@router.delete("/{context_id}", response_model=APIResponse)
def remove_context(context_id: str):
    """
    Remove a context item from the repository.
    """
    try:
        use_case = get_remove_context_use_case()
        result = use_case.execute(context_id)

        if result:
            return APIResponse(
                success=True,
                message=f"Context item {context_id} removed successfully"
            )
        else:
            return APIResponse(
                success=False,
                message=f"Failed to remove context item {context_id}",
                errors=["Operation returned false"]
            )

    except KeyError as e:
        logger.error(f"Context not found: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Context item with ID {context_id} not found")

    except Exception as e:
        logger.error(f"Error removing context: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to remove context",
            errors=[str(e)]
        )

@router.post("/search", response_model=APIResponse[ContextSearchResponse])
def search_context(query: SearchQuery):
    """
    Search for context items using semantic similarity.
    """
    try:
        use_case = get_search_context_use_case()
        results = use_case.execute(query.query, query.limit)

        # Convert domain entities to response models
        response_results = [
            ContextSearchResult(
                context=ContextItemResponse(
                    id=item.id,
                    source=item.source,
                    content_type=item.content_type.value,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    metadata=item.metadata
                ),
                similarity_score=score
            ) for item, score in results
        ]

        return APIResponse(
            success=True,
            data=ContextSearchResponse(results=response_results)
        )

    except Exception as e:
        logger.error(f"Error searching contexts: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to search contexts",
            errors=[str(e)]
        )