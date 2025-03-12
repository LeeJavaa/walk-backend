"""
Factory functions for creating pipeline stages.

This module creates the appropriate pipeline stage instances based on stage names.
"""
import logging
from typing import Optional, Dict, Type
from uuid import uuid4

from src.domain.entities.pipeline_stage import PipelineStage
from src.application.pipeline.stages.requirements_gathering_stage import \
    RequirementsGatheringStage
from src.application.pipeline.stages.knowledge_gathering_stage import \
    KnowledgeGatheringStage
from src.application.pipeline.stages.implementation_planning_stage import \
    ImplementationPlanningStage
from src.application.pipeline.stages.implementation_writing_stage import \
    ImplementationWritingStage
from src.application.pipeline.stages.review_stage import ReviewStage

logger = logging.getLogger(__name__)

# Registry of available pipeline stages
STAGE_REGISTRY: Dict[str, Type[PipelineStage]] = {
    "requirements_gathering": RequirementsGatheringStage,
    "knowledge_gathering": KnowledgeGatheringStage,
    "implementation_planning": ImplementationPlanningStage,
    "implementation_writing": ImplementationWritingStage,
    "review": ReviewStage
}


def create_pipeline_stage(stage_name: str) -> Optional[PipelineStage]:
    """
    Create a pipeline stage instance based on the stage name.

    Args:
        stage_name: Name of the stage to create

    Returns:
        A pipeline stage instance or None if the stage name is invalid
    """
    stage_class = STAGE_REGISTRY.get(stage_name)

    if not stage_class:
        logger.error(f"Invalid pipeline stage: {stage_name}")
        return None

    stage_id = str(uuid4())
    return stage_class(id=stage_id, name=stage_name)