"""
FastAPI application setup for the Walk API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.api.routers.context_router import router as context_router
from src.infrastructure.api.routers.task_router import router as task_router
from src.infrastructure.api.routers.pipeline_router import router as pipeline_router
from src.infrastructure.api.routers.feedback_router import router as feedback_router

# Create FastAPI application
app = FastAPI(
    title="Walk API",
    description="API for the Walk Agentic Coding System",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(context_router, prefix="/api/contexts", tags=["contexts"])
app.include_router(task_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(pipeline_router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(feedback_router, prefix="/api/feedback", tags=["feedback"])

@app.get("/")
def root():
    """Root endpoint to verify API is running."""
    return {"message": "Welcome to the Walk API", "status": "online"}