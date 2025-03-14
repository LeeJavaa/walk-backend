import re
import logging
from typing import Optional, Tuple, List, Dict

from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.context_item import ContextItem
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.context_repository import ContextRepository
from src.application.services.rag_service import RAGService
from src.infrastructure.adapters.prompt_utils import \
    create_implementation_planning_prompt


class ImplementationPlanningStage(PipelineStage):
    """Pipeline stage for planning the implementation."""

    def __init__(self, id: str, name: str, llm_provider: LLMProvider,
                 context_repository: ContextRepository,
                 rag_service: RAGService):
        """
        Initialize the implementation planning stage.

        Args:
            id: Unique identifier for the stage
            name: Name of the stage
            llm_provider: Provider for LLM interactions
            context_repository: Repository for context items
            rag_service: Service for RAG capabilities
        """
        super().__init__(id, name)
        self.llm_provider = llm_provider
        self.context_repository = context_repository
        self.rag_service = rag_service
        self.use_rag = False  # Flag to determine whether to use RAG or direct LLM
        self.logger = logging.getLogger(__name__)

    def execute(self, task: Task,
                state: Optional[PipelineState] = None) -> PipelineStageResult:
        """
        Execute the implementation planning stage.

        This stage creates a detailed implementation plan for the task based on
        the requirements and gathered knowledge from previous stages.

        Args:
            task: Task to process
            state: Current pipeline state (optional)

        Returns:
            Stage execution result with implementation plan
        """
        try:
            self.logger.info(
                f"Executing implementation planning for task {task.id}")

            # Get requirements, constraints, and knowledge from previous stages
            requirements, constraints, context_items = self._get_inputs_from_state(
                task, state)

            # Create formatted context items for the prompt
            formatted_context = [
                {"content": item.content, "source": item.source} for item in
                context_items]
            self.logger.debug(
                f"Using {len(formatted_context)} context items for planning")

            # Generate the implementation plan
            plan_text = ""
            if self.use_rag:
                # Use RAG for plan generation (leverages context more effectively)
                prompt = create_implementation_planning_prompt(
                    task.description, requirements, constraints,
                    formatted_context
                )
                self.logger.debug(
                    f"Using RAG service for implementation planning")
                plan_text = self.rag_service.generate_with_context(prompt,
                                                                   context_items)
            else:
                # Use direct LLM call with context included in the prompt
                prompt = create_implementation_planning_prompt(
                    task.description, requirements, constraints,
                    formatted_context
                )
                self.logger.debug(
                    f"Using direct LLM call for implementation planning")
                plan_text = self.llm_provider.generate_text(prompt)

            # Parse the implementation plan into structured components
            components, steps = self._parse_implementation_plan(plan_text)

            self.logger.info(
                f"Generated implementation plan with {len(components)} components and {len(steps)} steps")

            # Return the result
            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.COMPLETED,
                output={
                    "plan": plan_text,
                    "components": components,
                    "steps": steps
                }
            )

        except Exception as e:
            error_message = f"Error in implementation planning stage: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.FAILED,
                output={"error": error_message},
                error=str(e)
            )

    def _get_inputs_from_state(self, task: Task,
                               state: Optional[PipelineState] = None) -> Tuple[
        List[str], List[str], List[ContextItem]]:
        """
        Get required inputs from the pipeline state or task.

        Args:
            task: The task being processed
            state: The current pipeline state

        Returns:
            Tuple of (requirements, constraints, context_items)
        """
        # Default to task attributes
        requirements = task.requirements
        constraints = task.constraints
        context_items = []

        # Get requirements and constraints from requirements gathering stage if available
        if state and "requirements_gathering" in state.artifacts:
            req_artifacts = state.artifacts["requirements_gathering"]
            requirements = req_artifacts.get("requirements", task.requirements)
            constraints = req_artifacts.get("constraints", task.constraints)

        # Get context items from knowledge gathering stage if available
        if state and "knowledge_gathering" in state.artifacts:
            knowledge_artifacts = state.artifacts["knowledge_gathering"]
            context_item_ids = knowledge_artifacts.get("context_items", [])

            # Retrieve the actual context items
            for context_id in context_item_ids:
                context_item = self.context_repository.get_by_id(context_id)
                if context_item:
                    context_items.append(context_item)
        elif task.context_ids:
            # If no context from knowledge stage, try using task's context IDs
            for context_id in task.context_ids:
                context_item = self.context_repository.get_by_id(context_id)
                if context_item:
                    context_items.append(context_item)

        return requirements, constraints, context_items

    def _parse_implementation_plan(self, plan_text: str) -> Tuple[
        List[str], List[str]]:
        """
        Parse the implementation plan into structured components.

        Extracts components and steps from the plan text.

        Args:
            plan_text: The implementation plan text from the LLM

        Returns:
            Tuple of (components, steps) lists
        """
        components = []
        steps = []

        # Handle various section markers
        component_headers = [
            r"(?i)^\s*#+\s*components\s*$",
            r"(?i)^\s*components\s*:",
            r"(?i)^\s*components\s*"
        ]

        step_headers = [
            r"(?i)^\s*#+\s*steps\s*$",
            r"(?i)^\s*steps\s*:",
            r"(?i)^\s*detailed\s*steps\s*$",
            r"(?i)^\s*implementation\s*steps\s*$",
            r"(?i)^\s*implementation\s*order\s*$",
            r"(?i)^\s*sequential\s*steps\s*"
        ]

        # Normalized plan text for easier processing
        lines = plan_text.split('\n')

        # Find components and steps sections
        current_section = None
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check for component section headers
            if any(re.match(pattern, line) for pattern in component_headers):
                current_section = "components"
                continue

            # Check for step section headers
            if any(re.match(pattern, line) for pattern in step_headers):
                current_section = "steps"
                continue

            # If we're in a section, extract items
            if current_section == "components":
                # Look for list items or numbered items
                if (line.startswith('-') or line.startswith('*') or
                        re.match(r'^\d+[\.\)]', line) or
                        re.match(r'^[A-Za-z][\.\)]', line)):
                    # Clean the item text
                    item = re.sub(r'^[-*]\s+', '', line)
                    item = re.sub(r'^\d+[\.\)]\s+', '', item)
                    item = re.sub(r'^[A-Za-z][\.\)]\s+', '', item)
                    components.append(item.strip())

            elif current_section == "steps":
                # Same pattern for steps
                if (line.startswith('-') or line.startswith('*') or
                        re.match(r'^\d+[\.\)]', line) or
                        re.match(r'^[A-Za-z][\.\)]', line)):
                    item = re.sub(r'^[-*]\s+', '', line)
                    item = re.sub(r'^\d+[\.\)]\s+', '', item)
                    item = re.sub(r'^[A-Za-z][\.\)]\s+', '', item)
                    steps.append(item.strip())

        # If no components or steps were found using section headers,
        # try to extract them more broadly from the text
        if not components:
            # Look for numbered or bulleted items in the plan
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check for component-like items (usually at the beginning)
                if (re.match(r'^\d+\.\s+[A-Z]', line) or
                        line.startswith('- ') and len(line) < 50 and any(
                            word in line.lower() for word in
                            ['module', 'component', 'system', 'service'])):
                    item = re.sub(r'^[-*]\s+', '', line)
                    item = re.sub(r'^\d+[\.\)]\s+', '', item)
                    components.append(item.strip())

        if not steps:
            # Look for step-like items
            step_found = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Once we find a clear step indicator, start collecting steps
                if not step_found and re.search(
                        r'(?i)step|first|begin|start|initialize', line):
                    step_found = True

                if step_found and (
                        line.startswith('- ') or re.match(r'^\d+\.', line)):
                    item = re.sub(r'^[-*]\s+', '', line)
                    item = re.sub(r'^\d+[\.\)]\s+', '', item)
                    steps.append(item.strip())

        return components, steps

    def validate_transition_from(self, previous_stage: Optional[
        PipelineStage]) -> bool:
        """
        Validate if this stage can be executed after the given previous stage.

        Args:
            previous_stage: The previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the knowledge gathering stage
        return (previous_stage is not None and
                previous_stage.__class__.__name__ == "KnowledgeGatheringStage")

    def validate_transition_from_name(self, previous_stage_name: Optional[
        str]) -> bool:
        """
        Validate if this stage can be executed after a stage with the given name.

        Args:
            previous_stage_name: The name of the previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the knowledge gathering stage
        return previous_stage_name == "knowledge_gathering"

    def get_next_stage_name(self) -> str:
        """
        Get the name of the next stage in the pipeline.

        Returns:
            Name of the next stage
        """
        return "implementation_writing"