"""
Feedback management router for the Walk API.

This module defines the API endpoints for feedback management.
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from src.infrastructure.api.models.request import SubmitFeedbackRequest, \
    IncorporateFeedbackRequest
from src.infrastructure.api.models.response import APIResponse
from src.infrastructure.api.utils.dependency_injection import (
    get_submit_feedback_use_case,
    get_incorporate_feedback_use_case
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/submit", response_model=APIResponse)
def submit_feedback(request: SubmitFeedbackRequest):
    """
    Submit feedback for a pipeline stage.
    """
    try:
        use_case = get_submit_feedback_use_case()

        # Submit the feedback
        updated_state = use_case.execute(
            pipeline_state_id=request.pipeline_state_id,
            stage_name=request.stage_name,
            content=request.content,
            feedback_type=request.feedback_type
        )

        return APIResponse(
            success=True,
            message="Successfully submitted feedback",
            data={
                "pipeline_state_id": updated_state.id,
                "stage": request.stage_name,
                "type": request.feedback_type
            }
        )

    except KeyError as e:
        logger.error(f"Pipeline state not found: {str(e)}")
        raise HTTPException(status_code=404,
                            detail=f"Pipeline state with ID {request.pipeline_state_id} not found")

    except ValueError as e:
        logger.error(f"Invalid stage name: {str(e)}")
        return APIResponse(
            success=False,
            message="Invalid stage name",
            errors=[str(e)]
        )

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to submit feedback",
            errors=[str(e)]
        )


@router.post("/incorporate", response_model=APIResponse)
def incorporate_feedback(request: IncorporateFeedbackRequest):
    """
    Incorporate feedback into the pipeline.
    """
    try:
        use_case = get_incorporate_feedback_use_case()

        if request.incorporate_all:
            # Incorporate all feedback with prioritization
            updated_state = use_case.execute_prioritized(
                request.pipeline_state_id)

            return APIResponse(
                success=True,
                message="Successfully incorporated all feedback",
                data={
                    "pipeline_state_id": updated_state.id
                }
            )
        elif request.feedback_ids:
            # Incorporate specific feedback items
            updated_state = use_case.execute(request.pipeline_state_id,
                                             request.feedback_ids)

            return APIResponse(
                success=True,
                message="Successfully incorporated specified feedback",
                data={
                    "pipeline_state_id": updated_state.id,
                    "feedback_ids": request.feedback_ids
                }
            )
        else:
            return APIResponse(
                success=False,
                message="Please specify feedback_ids or set incorporate_all to true",
                errors=["No feedback specified for incorporation"]
            )

    except KeyError as e:
        logger.error(f"Pipeline state not found: {str(e)}")
        raise HTTPException(status_code=404,
                            detail=f"Pipeline state with ID {request.pipeline_state_id} not found")

    except ValueError as e:
        logger.error(f"Invalid feedback ID: {str(e)}")
        return APIResponse(
            success=False,
            message="Invalid feedback ID",
            errors=[str(e)]
        )

    except Exception as e:
        logger.error(f"Error incorporating feedback: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to incorporate feedback",
            errors=[str(e)]
        )