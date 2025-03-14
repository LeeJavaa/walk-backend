import re
import logging
from typing import Optional, List, Dict
from uuid import uuid4

from src.domain.entities.pipeline_stage import PipelineStage, \
    PipelineStageResult, PipelineStageStatus
from src.domain.entities.task import Task
from src.domain.entities.pipeline_state import PipelineState
from src.domain.entities.context_item import ContextItem
from src.domain.entities.code_artifact import CodeArtifact, CodeArtifactType
from src.domain.ports.llm_provider import LLMProvider
from src.domain.ports.context_repository import ContextRepository
from src.application.services.rag_service import RAGService
from src.infrastructure.adapters.prompt_utils import \
    create_implementation_writing_prompt


class ImplementationWritingStage(PipelineStage):
    """Pipeline stage for writing the actual implementation code."""

    def __init__(self, id: str, name: str, llm_provider: LLMProvider,
                 context_repository: ContextRepository,
                 rag_service: RAGService):
        """
        Initialize the implementation writing stage.

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
        Execute the implementation writing stage.

        This stage generates the actual implementation code based on the plan
        from the previous stage and the requirements.

        Args:
            task: Task to process
            state: Current pipeline state (optional)

        Returns:
            Stage execution result with generated code artifacts
        """
        try:
            self.logger.info(
                f"Executing implementation writing for task {task.id}")

            # Get requirements, constraints, plan, and context
            requirements, constraints, plan, context_items = self._get_inputs_from_state(
                task, state)

            # Create formatted context items for the prompt
            formatted_context = [
                {"content": item.content, "source": item.source} for item in
                context_items]
            self.logger.debug(
                f"Using {len(formatted_context)} context items for implementation")

            # Generate the implementation code
            implementation_text = ""
            if self.use_rag:
                # Use RAG for implementation generation
                prompt = create_implementation_writing_prompt(
                    task.description, requirements, plan, formatted_context
                )
                self.logger.debug(
                    f"Using RAG service for implementation writing")
                implementation_text = self.rag_service.generate_with_context(
                    prompt, context_items)
            else:
                # Use direct LLM call with context included in the prompt
                prompt = create_implementation_writing_prompt(
                    task.description, requirements, plan, formatted_context
                )
                self.logger.debug(
                    f"Using direct LLM call for implementation writing")
                implementation_text = self.llm_provider.generate_text(prompt)

            # Extract code blocks from the response
            self.logger.debug(f"Extracting code blocks from LLM response")
            code_blocks = self._extract_code_blocks(implementation_text)

            # Create code artifacts from the code blocks
            code_artifacts = self._create_code_artifacts(code_blocks, task.id)

            self.logger.info(f"Generated {len(code_artifacts)} code artifacts")

            # Return the result
            return PipelineStageResult(
                stage_id=self.id,
                status=PipelineStageStatus.COMPLETED,
                output={
                    "code_artifacts": [artifact.to_dict() for artifact in
                                       code_artifacts],
                    "full_response": implementation_text
                }
            )

        except Exception as e:
            error_message = f"Error in implementation writing stage: {str(e)}"
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
            Tuple of (requirements, constraints, plan, context_items)
        """
        # Default to task attributes
        requirements = task.requirements
        constraints = task.constraints
        plan = ""
        context_items = []

        # Get requirements and constraints from requirements gathering stage if available
        if state and "requirements_gathering" in state.artifacts:
            req_artifacts = state.artifacts["requirements_gathering"]
            requirements = req_artifacts.get("requirements", task.requirements)
            constraints = req_artifacts.get("constraints", task.constraints)

        # Get plan from implementation planning stage if available
        if state and "implementation_planning" in state.artifacts:
            planning_artifacts = state.artifacts["implementation_planning"]
            plan = planning_artifacts.get("plan", "")

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

        return requirements, constraints, plan, context_items

    def _extract_code_blocks(self, text: str) -> List[str]:
        """
        Extract code blocks from the LLM response.

        Args:
            text: The LLM response text

        Returns:
            List of extracted code blocks
        """
        # Look for code blocks marked with triple backticks
        code_blocks = []

        # Match code blocks with language specifier (like ```python)
        pattern = r"```(?:python|java|javascript|typescript|html|css|json|yaml|sql|bash|sh|shell|cmd|powershell|xml|rust|go|c|cpp|csharp|)?\n(.*?)```"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            code_block = match.group(1).strip()
            if code_block:
                code_blocks.append(code_block)

        # If no code blocks found with backticks, try to extract any code-like sections
        if not code_blocks:
            self.logger.warning(
                "No code blocks with backticks found, attempting to extract code directly")

            # Look for indented blocks or sections that look like code
            lines = text.split('\n')
            current_block = []
            in_code_block = False

            for line in lines:
                # If line has common code patterns, we might be in a code block
                if (re.match(
                        r'^\s*(def|class|import|from|#|//|\/\*|\*\/|function|var|let|const|package|public|private|if|for|while)\b',
                        line) or
                        re.match(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*[=:]\s*',
                                 line)):

                    if not in_code_block:
                        # Start a new code block
                        in_code_block = True

                    current_block.append(line)

                elif in_code_block:
                    # If line is part of the current code block
                    if line.strip() or re.match(r'^\s+',
                                                line):  # Non-empty line or indented line
                        current_block.append(line)
                    else:
                        # Empty line might end a code block
                        # But only end if the next non-empty line isn't indented
                        if current_block:
                            code_blocks.append('\n'.join(current_block))
                            current_block = []
                            in_code_block = False

            # Add the last block if there is one
            if current_block:
                code_blocks.append('\n'.join(current_block))

        # If still no code blocks found, use the entire text as a single code block
        if not code_blocks and text.strip():
            self.logger.warning("No code blocks identified, using entire text")
            code_blocks = [text.strip()]

        return code_blocks

    def _create_code_artifacts(self, code_blocks: List[str], task_id: str) -> \
    List[CodeArtifact]:
        """
        Create code artifacts from extracted code blocks.

        Args:
            code_blocks: List of code blocks
            task_id: ID of the task

        Returns:
            List of code artifacts
        """
        code_artifacts = []

        for i, code_block in enumerate(code_blocks):
            # Determine the language based on content
            language = self._determine_language(code_block)

            # Create a unique ID for the artifact
            artifact_id = str(uuid4())

            # Create the code artifact
            artifact = CodeArtifact(
                id=artifact_id,
                task_id=task_id,
                content=code_block,
                artifact_type=CodeArtifactType.IMPLEMENTATION,
                language=language
            )

            code_artifacts.append(artifact)

        return code_artifacts

    def _determine_language(self, code_block: str) -> str:
        """
        Determine the programming language of a code block.

        Args:
            code_block: The code block to analyze

        Returns:
            Detected language name
        """
        # Simple language detection based on common patterns
        if re.search(r'^(import|from|def|class|print|if __name__)', code_block,
                     re.MULTILINE):
            return "python"
        elif re.search(
                r'^(package|import java|public class|private|protected|@Override)',
                code_block, re.MULTILINE):
            return "java"
        elif re.search(
                r'^(import React|function|const|let|var|export default|component)',
                code_block, re.MULTILINE):
            return "javascript"
        elif re.search(r'^(interface|class|enum|import|export|type)',
                       code_block, re.MULTILINE):
            return "typescript"
        elif re.search(r'^(<!DOCTYPE html>|<html>|<head>|<body>|<div>|<span>)',
                       code_block, re.MULTILINE):
            return "html"
        elif re.search(r'^(body|margin|padding|div|\.class|#id)', code_block,
                       re.MULTILINE):
            return "css"
        elif re.search(r'^(\{|\[).*(\}|\])', code_block, re.DOTALL):
            return "json"
        else:
            # Default to Python as it's the most common for this project
            return "python"


    def validate_transition_from(self,
                                 previous_stage: Optional[PipelineStage]) -> bool:
        """
        Validate if this stage can be executed after the given previous stage.

        Args:
            previous_stage: The previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the implementation planning stage
        return (previous_stage is not None and
                previous_stage.__class__.__name__ == "ImplementationPlanningStage")


    def validate_transition_from_name(self,
                                      previous_stage_name: Optional[str]) -> bool:
        """
        Validate if this stage can be executed after a stage with the given name.

        Args:
            previous_stage_name: The name of the previous stage in the pipeline

        Returns:
            True if the transition is valid, False otherwise
        """
        # This stage can only be executed after the implementation planning stage
        return previous_stage_name == "implementation_planning"


    def get_next_stage_name(self) -> str:
        """
        Get the name of the next stage in the pipeline.

        Returns:
            Name of the next stage
        """
        return "review"