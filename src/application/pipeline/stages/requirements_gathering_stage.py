import re
import logging
from typing import Optional, Tuple, List

from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.ports.llm_provider import LLMProvider
from src.infrastructure.adapters.prompt_utils import \
    create_requirements_gathering_prompt


class RequirementsGatheringStage(PipelineStage):
    """Pipeline stage for gathering and refining requirements."""

    def __init__(self, id: str, name: str, llm_provider: LLMProvider):
        """
        Initialize the requirements gathering stage.

        Args:
            id: Unique identifier for the stage
            name: Name of the stage
            llm_provider: Provider for LLM interactions
        """
        super().__init__(id, name)
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(__name__)

    def execute(self, task: Task,
                state: Optional[PipelineState] = None) -> PipelineStageResult:
        """
        Execute the requirements gathering stage.

        This stage takes the task description and any existing requirements/constraints
        and uses the LLM to refine and expand them into a comprehensive set.

        Args:
            task: Task to process
            state: Current pipeline state (optional)

        Returns:
            Stage execution result with refined requirements, constraints, and clarifications
        """
        try:
            self.logger.info(
                f"Executing requirements gathering for task {task.id}")

            # Create the prompt for the LLM
            user_input = self._format_task_input(task)
            prompt = create_requirements_gathering_prompt(task.description,
                                                          user_input)

            # Generate refined requirements using the LLM
            self.logger.debug(f"Sending prompt to LLM: {prompt[:100]}...")
            llm_response = self.llm_provider.generate_text(prompt)
            self.logger.debug(
                f"Received response from LLM: {llm_response[:100]}...")

            # Parse the LLM response
            requirements, constraints, clarifications = self._parse_llm_response(
                llm_response)

            # Combine with existing requirements and constraints, removing duplicates
            requirements = list(set(requirements))
            constraints = list(set(constraints))

            self.logger.info(
                f"Gathered {len(requirements)} requirements, {len(constraints)} constraints")

            # Return the result
            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.COMPLETED,
                output={
                    "requirements": requirements,
                    "constraints": constraints,
                    "clarifications": clarifications
                }
            )

        except Exception as e:
            error_message = f"Error in requirements gathering stage: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.FAILED,
                output={"error": error_message},
                error=str(e)
            )

    def _format_task_input(self, task: Task) -> str:
        """
        Format the task input for the LLM prompt.

        Args:
            task: The task containing requirements and constraints

        Returns:
            Formatted input string
        """
        input_str = ""

        # Add existing requirements if any
        if task.requirements:
            input_str += "Existing Requirements:\n"
            for req in task.requirements:
                input_str += f"- {req}\n"
            input_str += "\n"

        # Add existing constraints if any
        if task.constraints:
            input_str += "Existing Constraints:\n"
            for constraint in task.constraints:
                input_str += f"- {constraint}\n"
            input_str += "\n"

        return input_str

    def _parse_llm_response(self, response: str) -> Tuple[
        List[str], List[str], List[str]]:
        """
        Parse the LLM response into requirements, constraints, and clarifications.

        Args:
            response: The response from the LLM

        Returns:
            Tuple of (requirements, constraints, clarifications) lists
        """
        requirements = []
        constraints = []
        clarifications = []

        # Split response into sections
        sections = {
            "requirements": [],
            "constraints": [],
            "clarifications": []
        }

        current_section = None
        lines = response.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers with various formats
            lower_line = line.lower()
            if "requirement" in lower_line and (
                    ":" in line or line.endswith("s")):
                current_section = "requirements"
                continue
            elif "constraint" in lower_line and (
                    ":" in line or line.endswith("s")):
                current_section = "constraints"
                continue
            elif any(x in lower_line for x in ["clarification", "assumption",
                                               "clarifications/assumptions"]) and (
                    ":" in line or line.endswith("s")):
                current_section = "clarifications"
                continue

            # If we're in a section and the line starts with a list marker or number, add it to the section
            if current_section and (
                    line.startswith("-") or line.startswith("*") or re.match(
                    r"^\d+\.", line)):
                # Remove list markers and leading/trailing whitespace
                clean_line = re.sub(r"^[-*]\s+", "", line)
                clean_line = re.sub(r"^\d+\.\s+", "", clean_line)
                sections[current_section].append(clean_line.strip())
            elif current_section:
                # If not a list item but in a section, it might be a continuation or unlisted item
                sections[current_section].append(line)

        # Extract the items from each section
        requirements = sections["requirements"]
        constraints = sections["constraints"]
        clarifications = sections["clarifications"]

        return requirements, constraints, clarifications

    def validate_transition_from(self, previous_stage: Optional[
        PipelineStage]) -> bool:
        """
        Validate if this stage can be executed after the given previous stage.

        Args:
            previous_stage: The previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This is the first stage, so it can only be executed if there is no previous stage
        return previous_stage is None

    def validate_transition_from_name(self, previous_stage_name: Optional[
        str]) -> bool:
        """
        Validate if this stage can be executed after a stage with the given name.

        Args:
            previous_stage_name: The name of the previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed at the start
        return previous_stage_name == ""

    def get_next_stage_name(self) -> str:
        """
        Get the name of the next stage in the pipeline.

        Returns:
            Name of the next stage
        """
        return "knowledge_gathering"