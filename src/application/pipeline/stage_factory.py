"""
Factory functions for creating pipeline stages.

This module creates the appropriate pipeline stage instances based on stage names.
"""
import logging
from typing import Optional, Dict, Type
from uuid import uuid4

from src.domain.entities.pipeline_stage import PipelineStage
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.context_repository import ContextRepository
from src.application.services.rag_service import RAGService
from src.application.pipeline.stages.requirements_gathering_stage import RequirementsGatheringStage
from src.application.pipeline.stages.knowledge_gathering_stage import KnowledgeGatheringStage
from src.application.pipeline.stages.implementation_planning_stage import ImplementationPlanningStage
from src.application.pipeline.stages.implementation_writing_stage import ImplementationWritingStage
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


def create_pipeline_stage(
    stage_name: str,
    llm_provider: Optional[LLMProvider] = None,
    context_repository: Optional[ContextRepository] = None,
    rag_service: Optional[RAGService] = None,
) -> Optional[PipelineStage]:
    """
    Create a pipeline stage instance based on the stage name.

    Args:
        stage_name: Name of the stage to create
        llm_provider: LLM provider instance for stages that require it
        context_repository: Context repository instance for stages that require it
        rag_service: RAG service instance for stages that require it

    Returns:
        A pipeline stage instance or None if the stage name is invalid
    """
    stage_class = STAGE_REGISTRY.get(stage_name)

    if not stage_class:
        logger.error(f"Invalid pipeline stage: {stage_name}")
        return None

    stage_id = str(uuid4())

    # Create stage instance based on stage requirements
    if stage_name == "requirements_gathering":
        if not llm_provider:
            logger.error(f"LLM provider required for stage: {stage_name}")
            return None
        return RequirementsGatheringStage(
            id=stage_id,
            name=stage_name,
            llm_provider=llm_provider
        )

    elif stage_name in ["knowledge_gathering", "implementation_planning", "implementation_writing"]:
        if not all([llm_provider, context_repository, rag_service]):
            logger.error(f"Missing dependencies for stage: {stage_name}")
            return None

        return STAGE_REGISTRY[stage_name](
            id=stage_id,
            name=stage_name,
            llm_provider=llm_provider,
            context_repository=context_repository,
            rag_service=rag_service
        )

    elif stage_name == "review":
        if not all([llm_provider, rag_service]):
            logger.error(f"Missing dependencies for stage: {stage_name}")
            return None

        return ReviewStage(
            id=stage_id,
            name=stage_name,
            llm_provider=llm_provider,
            rag_service=rag_service
        )

    # Default case (should not be reached with proper registry)
    return stage_class(id=stage_id, name=stage_name)