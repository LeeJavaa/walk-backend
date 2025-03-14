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
    create_knowledge_gathering_prompt


class KnowledgeGatheringStage(PipelineStage):
    """Pipeline stage for gathering relevant knowledge and context."""

    def __init__(self, id: str, name: str, llm_provider: LLMProvider,
                 context_repository: ContextRepository,
                 rag_service: RAGService):
        """
        Initialize the knowledge gathering stage.

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
        self.logger = logging.getLogger(__name__)

    def execute(self, task: Task,
                state: Optional[PipelineState] = None) -> PipelineStageResult:
        """
        Execute the knowledge gathering stage.

        This stage identifies and gathers relevant knowledge and context for the task,
        using both the task's explicit context IDs and RAG-based search.

        Args:
            task: Task to process
            state: Current pipeline state (optional)

        Returns:
            Stage execution result with gathered knowledge and context references
        """
        try:
            self.logger.info(
                f"Executing knowledge gathering for task {task.id}")

            # Get requirements and constraints from the previous stage or the task
            requirements, constraints = self._get_requirements_and_constraints(
                task, state)

            # Gather context items
            context_items = self._gather_context_items(task, requirements,
                                                       constraints)

            # Create the prompt for knowledge gathering
            prompt = create_knowledge_gathering_prompt(task.description,
                                                       requirements,
                                                       constraints)

            # Generate knowledge analysis using the LLM, enhanced with context
            formatted_context = [
                {"content": item.content, "source": item.source} for item in
                context_items]
            self.logger.debug(
                f"Sending prompt to LLM with {len(formatted_context)} context items")

            llm_response = self.rag_service.generate_with_context(prompt,
                                                                  context_items)
            self.logger.debug(
                f"Received response from LLM: {llm_response[:100]}...")

            # Parse the LLM response
            domain_knowledge, libraries_frameworks, best_practices, challenges = self._parse_llm_response(
                llm_response)

            self.logger.info(
                f"Gathered knowledge: {len(domain_knowledge)} concepts, {len(libraries_frameworks)} libraries, "
                f"{len(best_practices)} best practices, {len(challenges)} challenges")

            # Return the result
            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.COMPLETED,
                output={
                    "domain_knowledge": domain_knowledge,
                    "libraries_frameworks": libraries_frameworks,
                    "best_practices": best_practices,
                    "challenges": challenges,
                    "context_items": [item.id for item in context_items]
                }
            )

        except Exception as e:
            error_message = f"Error in knowledge gathering stage: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.FAILED,
                output={"error": error_message},
                error=str(e)
            )

    def _get_requirements_and_constraints(self, task: Task,
                                          state: Optional[PipelineState]) -> \
    Tuple[List[str], List[str]]:
        """
        Get requirements and constraints from the previous stage or the task.

        Args:
            task: The task being processed
            state: The current pipeline state

        Returns:
            Tuple of (requirements, constraints) lists
        """
        # If we have a state with artifacts from the requirements stage, use those
        if state and "requirements_gathering" in state.artifacts:
            artifacts = state.artifacts["requirements_gathering"]
            requirements = artifacts.get("requirements", task.requirements)
            constraints = artifacts.get("constraints", task.constraints)
        else:
            # Otherwise, use the task's requirements and constraints directly
            requirements = task.requirements
            constraints = task.constraints

        return requirements, constraints

    def _gather_context_items(self, task: Task, requirements: List[str],
                              constraints: List[str]) -> List[ContextItem]:
        """
        Gather relevant context items using explicit IDs and RAG search.

        Args:
            task: The task being processed
            requirements: Task requirements
            constraints: Task constraints

        Returns:
            List of relevant context items
        """
        context_items = []

        # First, gather any explicitly referenced context items
        if task.context_ids:
            self.logger.info(
                f"Gathering {len(task.context_ids)} explicit context items")
            for context_id in task.context_ids:
                item = self.context_repository.get_by_id(context_id)
                if item:
                    context_items.append(item)

        # Then, if there are fewer than 5 items, use RAG to find more related context
        if len(context_items) < 5:
            self.logger.info("Using RAG to find additional context items")

            # Create a search query from the task description and requirements
            query = f"{task.description}\n"
            query += "Requirements:\n" + "\n".join(
                [f"- {req}" for req in requirements])
            query += "\nConstraints:\n" + "\n".join(
                [f"- {constraint}" for constraint in constraints])

            # Use the RAG service to retrieve relevant context
            additional_items = self.rag_service.retrieve_context(query)

            # Add new items (avoiding duplicates)
            existing_ids = {item.id for item in context_items}
            for item in additional_items:
                if item.id not in existing_ids:
                    context_items.append(item)
                    existing_ids.add(item.id)

            self.logger.info(
                f"Added {len(additional_items)} additional context items from RAG")

        return context_items

    def _parse_llm_response(self, response: str) -> Tuple[
        List[str], List[str], List[str], List[str]]:
        """
        Parse the LLM response into knowledge categories.

        Args:
            response: The response from the LLM

        Returns:
            Tuple of (domain_knowledge, libraries_frameworks, best_practices, challenges) lists
        """
        domain_knowledge = []
        libraries_frameworks = []
        best_practices = []
        challenges = []

        # Split response into sections
        sections = {
            "domain_knowledge": [],
            "libraries_frameworks": [],
            "best_practices": [],
            "challenges": []
        }

        current_section = None
        lines = response.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers with various formats
            lower_line = line.lower()

            # Match domain knowledge section
            if any(x in lower_line for x in
                   ["domain knowledge", "key concepts", "concepts",
                    "knowledge"]):
                current_section = "domain_knowledge"
                continue

            # Match libraries and frameworks section
            elif any(x in lower_line for x in
                     ["libraries", "frameworks", "tools", "technologies"]):
                current_section = "libraries_frameworks"
                continue

            # Match best practices section
            elif any(x in lower_line for x in
                     ["best practices", "patterns", "design patterns",
                      "principles"]):
                current_section = "best_practices"
                continue

            # Match challenges section
            elif any(x in lower_line for x in
                     ["challenges", "potential challenges", "issues",
                      "concerns"]):
                current_section = "challenges"
                continue

            # If we're in a section and the line starts with a list marker or number, add it to the section
            if current_section and (
                    line.startswith("-") or line.startswith("*") or
                    re.match(r"^\d+[\.\)]", line) or re.match(
                r"^[a-zA-Z][\.\)]", line)):
                # Remove list markers and leading/trailing whitespace
                clean_line = re.sub(r"^[-*]\s+", "", line)
                clean_line = re.sub(r"^\d+[\.\)]\s+", "", clean_line)
                clean_line = re.sub(r"^[a-zA-Z][\.\)]\s+", "", clean_line)
                sections[current_section].append(clean_line.strip())
            elif current_section and line and not any(
                    x in line.lower() for x in ["section", "category"]):
                # If not a list item but in a section, it might be a continuation or unlisted item
                sections[current_section].append(line)

        # Extract the items from each section
        domain_knowledge = sections["domain_knowledge"]
        libraries_frameworks = sections["libraries_frameworks"]
        best_practices = sections["best_practices"]
        challenges = sections["challenges"]

        return domain_knowledge, libraries_frameworks, best_practices, challenges

    def validate_transition_from(self, previous_stage: Optional[
        PipelineStage]) -> bool:
        """
        Validate if this stage can be executed after the given previous stage.

        Args:
            previous_stage: The previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the requirements gathering stage
        return (previous_stage is not None and
                previous_stage.__class__.__name__ == "RequirementsGatheringStage")

    def validate_transition_from_name(self, previous_stage_name: Optional[
        str]) -> bool:
        """
        Validate if this stage can be executed after a stage with the given name.

        Args:
            previous_stage_name: The name of the previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the requirements gathering stage
        return previous_stage_name == "requirements_gathering"

    def get_next_stage_name(self) -> str:
        """
        Get the name of the next stage in the pipeline.

        Returns:
            Name of the next stage
        """
        return "implementation_planning"