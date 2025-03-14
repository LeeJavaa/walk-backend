import re
import logging
from typing import Optional, Dict, List, Any

from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.code_artifact import CodeArtifact
from src.domain.ports.llm_provider import LLMProvider
from src.application.services.rag_service import RAGService
from src.infrastructure.adapters.prompt_utils import create_review_prompt


class ReviewStage(PipelineStage):
    """Pipeline stage for reviewing the implementation."""

    def __init__(self, id: str, name: str, llm_provider: LLMProvider,
                 rag_service: RAGService):
        """
        Initialize the review stage.

        Args:
            id: Unique identifier for the stage
            name: Name of the stage
            llm_provider: Provider for LLM interactions
            rag_service: Service for RAG capabilities
        """
        super().__init__(id, name)
        self.llm_provider = llm_provider
        self.rag_service = rag_service
        self.use_rag = False  # Flag to determine whether to use RAG or direct LLM
        self.logger = logging.getLogger(__name__)

    def execute(self, task: Task,
                state: Optional[PipelineState] = None) -> PipelineStageResult:
        """
        Execute the review stage.

        This stage reviews the generated code artifacts for correctness, completeness,
        quality, and security issues.

        Args:
            task: Task to process
            state: Current pipeline state (optional)

        Returns:
            Stage execution result with code review analysis
        """
        try:
            self.logger.info(f"Executing review for task {task.id}")

            # Get requirements, constraints, and code artifacts
            requirements, constraints, code_artifacts = self._get_inputs_from_state(
                task, state)

            # Ensure we have code artifacts to review
            if not code_artifacts:
                error_message = "No code artifacts found to review"
                self.logger.error(error_message)
                return PipelineStageResult(
                    stage_id=self.id,
                    status=PipelineStageStatus.FAILED,
                    output={"error": error_message},
                    error=error_message
                )

            # Combine all code for the review
            combined_code = "\n\n".join(
                artifact.content for artifact in code_artifacts)
            self.logger.debug(
                f"Reviewing {len(code_artifacts)} code artifacts with a total of {len(combined_code)} characters")

            # Generate the review
            review_text = ""
            if self.use_rag:
                # Use RAG for review generation
                prompt = create_review_prompt(combined_code, requirements,
                                              constraints)
                self.logger.debug("Using RAG service for code review")
                review_text = self.rag_service.generate_with_context(prompt)
            else:
                # Use direct LLM call
                prompt = create_review_prompt(combined_code, requirements,
                                              constraints)
                self.logger.debug("Using direct LLM call for code review")
                review_text = self.llm_provider.generate_text(prompt)

            # Parse the review text into structured categories
            review_data = self._parse_review(review_text)

            # Combine the full text and structured data
            result_data = {
                "review_text": review_text,
                **review_data
            }

            self.logger.info(
                f"Completed code review with {len(result_data['recommendations'])} recommendations")

            # Return the result
            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.COMPLETED,
                output=result_data
            )

        except Exception as e:
            error_message = f"Error in review stage: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.FAILED,
                output={"error": error_message},
                error=str(e)
            )

    def _get_inputs_from_state(self, task: Task,
                               state: Optional[PipelineState] = None) -> tuple:
        """
        Get required inputs from the pipeline state or task.

        Args:
            task: The task being processed
            state: The current pipeline state

        Returns:
            Tuple of (requirements, constraints, code_artifacts)
        """
        # Default to task attributes
        requirements = task.requirements
        constraints = task.constraints
        code_artifacts = []

        # Get requirements and constraints from requirements gathering stage if available
        if state and "requirements_gathering" in state.artifacts:
            req_artifacts = state.artifacts["requirements_gathering"]
            requirements = req_artifacts.get("requirements", task.requirements)
            constraints = req_artifacts.get("constraints", task.constraints)

        # Get code artifacts from implementation writing stage if available
        if state and "implementation_writing" in state.artifacts:
            implementation_artifacts = state.artifacts["implementation_writing"]
            code_artifacts_dicts = implementation_artifacts.get(
                "code_artifacts", [])
            code_artifacts = [CodeArtifact.from_dict(artifact_dict) for
                              artifact_dict in code_artifacts_dicts]

        return requirements, constraints, code_artifacts

    def _parse_review(self, review_text: str) -> Dict[str, Any]:
        """
        Parse the review text into structured categories.

        Extracts information about correctness, code quality, security issues,
        and recommendations from the review text.

        Args:
            review_text: The review text from the LLM

        Returns:
            Dictionary of structured review data
        """
        # Initialize the review data structure
        review_data = {
            "correctness": {"strengths": [], "weaknesses": []},
            "completeness": {"strengths": [], "weaknesses": []},
            "code_quality": {"strengths": [], "weaknesses": []},
            "performance": {"strengths": [], "weaknesses": []},
            "security": {"strengths": [], "weaknesses": []},
            "best_practices": {"strengths": [], "weaknesses": []},
            "general": {"strengths": [], "weaknesses": []},
            "recommendations": []
        }

        # Common section markers
        section_patterns = {
            "correctness": [r"(?i)^\s*#+\s*correct(ness)?",
                            r"(?i)^\s*correct(ness)?:"],
            "completeness": [r"(?i)^\s*#+\s*complete(ness)?",
                             r"(?i)^\s*complete(ness)?:"],
            "code_quality": [r"(?i)^\s*#+\s*code\s*quality",
                             r"(?i)^\s*code\s*quality:"],
            "performance": [r"(?i)^\s*#+\s*performance",
                            r"(?i)^\s*performance:"],
            "security": [r"(?i)^\s*#+\s*security", r"(?i)^\s*security:"],
            "best_practices": [r"(?i)^\s*#+\s*best\s*practices",
                               r"(?i)^\s*best\s*practices:"],
            "recommendations": [r"(?i)^\s*#+\s*recommend", r"(?i)^\s*recommend",
                                r"(?i)^\s*#+\s*key\s*recommend",
                                r"(?i)^\s*what\s*to\s*improve",
                                r"(?i)^\s*improvements"]
        }

        # General categories for strengths and weaknesses
        strength_weakness_patterns = {
            "strengths": [r"(?i)^\s*#+\s*strengths", r"(?i)^\s*strengths:",
                          r"(?i)\bstrengths\b"],
            "weaknesses": [r"(?i)^\s*#+\s*weaknesses", r"(?i)^\s*weaknesses:",
                           r"(?i)\bweaknesses\b"]
        }

        # Split review into lines for processing
        lines = review_text.split('\n')

        # Parse the sections
        current_section = "general"  # Default section
        current_subsection = None  # Strengths or weaknesses

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            section_found = False
            for section, patterns in section_patterns.items():
                if any(re.match(pattern, line) for pattern in patterns):
                    current_section = section
                    current_subsection = None  # Reset subsection
                    section_found = True
                    break

            if section_found:
                continue  # Skip to next line after setting section

            # Check for strength/weakness markers
            for subsection, patterns in strength_weakness_patterns.items():
                if any(re.match(pattern, line) for pattern in patterns):
                    current_subsection = subsection
                    break

            # Process recommendations section specifically
            if current_section == "recommendations":
                # Look for numbered or bulleted items
                if (line.startswith('-') or line.startswith('*') or
                        re.match(r'^\d+[\.\)]', line) or re.match(
                            r'^[a-zA-Z][\.\)]', line)):
                    # Clean the item text
                    item = re.sub(r'^[-*]\s+', '', line)
                    item = re.sub(r'^\d+[\.\)]\s+', '', item)
                    item = re.sub(r'^[a-zA-Z][\.\)]\s+', '', item)
                    review_data["recommendations"].append(item.strip())
                    continue

            # Process other sections with strength/weakness categorization
            if current_section != "recommendations" and current_subsection:
                # Skip headers
                if any(re.search(r'(?i)^what|^here|^list', line)):
                    continue

                # Process items
                if (line.startswith('-') or line.startswith('*') or
                        re.match(r'^\d+[\.\)]', line) or re.match(
                            r'^[a-zA-Z][\.\)]', line) or
                        line.startswith('✓') or line.startswith('✗')):
                    # Clean the item text
                    item = re.sub(r'^[-*]\s+', '', line)
                    item = re.sub(r'^\d+[\.\)]\s+', '', item)
                    item = re.sub(r'^[a-zA-Z][\.\)]\s+', '', item)
                    item = re.sub(r'^[✓✗]\s+', '', item)
                    item = item.strip()

                    # Add to appropriate section
                    if item:
                        if current_section in review_data and current_subsection in \
                                review_data[current_section]:
                            review_data[current_section][
                                current_subsection].append(item)
                        elif current_section in review_data:
                            # If no explicit subsection, try to determine by content
                            if line.startswith('✓') or re.search(
                                    r'(?i)\bgood\b|\bstrong\b|\bpositive\b|\bstrength\b|\bwell\b',
                                    line):
                                review_data[current_section][
                                    "strengths"].append(item)
                            elif line.startswith('✗') or re.search(
                                    r'(?i)\bbad\b|\bweak\b|\bnegative\b|\bweakness\b|\bmissing\b|\bpoor\b',
                                    line):
                                review_data[current_section][
                                    "weaknesses"].append(item)
                            else:
                                # Default to weaknesses as they're usually more important for improvement
                                review_data[current_section][
                                    "weaknesses"].append(item)

        # If no recommendations were found, try to extract them differently
        if not review_data["recommendations"]:
            for line in lines:
                line = line.strip()
                # Look for recommendation-like statements
                if (re.search(r'(?i)should (add|implement|include|fix|improve)',
                              line) or
                        re.search(
                            r'(?i)needs? to (add|implement|include|fix|improve)',
                            line)):
                    review_data["recommendations"].append(line)

        # If we didn't find any content in some sections, remove them
        sections_to_keep = {}
        for section, data in review_data.items():
            if section == "recommendations":
                if data:  # If recommendations list is not empty
                    sections_to_keep[section] = data
            elif data["strengths"] or data[
                "weaknesses"]:  # If either list has content
                sections_to_keep[section] = data

        # At minimum, keep general section and recommendations
        if "general" not in sections_to_keep:
            sections_to_keep["general"] = review_data["general"]
        if "recommendations" not in sections_to_keep:
            sections_to_keep["recommendations"] = review_data["recommendations"]

        return sections_to_keep

    def validate_transition_from(self, previous_stage: Optional[
        PipelineStage]) -> bool:
        """
        Validate if this stage can be executed after the given previous stage.

        Args:
            previous_stage: The previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the implementation writing stage
        return (previous_stage is not None and
                previous_stage.__class__.__name__ == "ImplementationWritingStage")

    def validate_transition_from_name(self, previous_stage_name: Optional[
        str]) -> bool:
        """
        Validate if this stage can be executed after a stage with the given name.

        Args:
            previous_stage_name: The name of the previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the implementation writing stage
        return previous_stage_name == "implementation_writing"

    def get_next_stage_name(self) -> str:
        """
        Get the name of the next stage in the pipeline.

        Returns:
            Name of the next stage
        """
        # This is the last stage in the pipeline
        return ""