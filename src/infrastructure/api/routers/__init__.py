"""
Router package for the Walk API.
"""
from src.infrastructure.api.routers.context_router import router as context_router
from src.infrastructure.api.routers.task_router import router as task_router
from src.infrastructure.api.routers.pipeline_router import router as pipeline_router
from src.infrastructure.api.routers.feedback_router import router as feedback_router

__all__ = [
    "context_router",
    "task_router",
    "pipeline_router",
    "feedback_router"
]