"""
Utility functions for constructing prompts for different stages of the code generation pipeline.
"""
from typing import List, Dict, Any


def format_context_items_for_prompt(context_items: List[Dict[str, str]]) -> str:
    """
    Format context items for inclusion in prompts.

    Args:
        context_items: List of dictionaries with 'content' and 'source' keys

    Returns:
        Formatted string with context items
    """
    if not context_items:
        return ""

    formatted_items = []
    for item in context_items:
        # Format each item with its source and content
        formatted_item = f"--- {item['source']} ---\n{item['content']}\n"
        formatted_items.append(formatted_item)

    # Join all formatted items with a separator
    return "\n".join(formatted_items)


def create_requirements_gathering_prompt(task_description: str,
                                         user_input: str) -> str:
    """
    Create a prompt for gathering requirements from the task description and user input.

    Args:
        task_description: Description of the task
        user_input: Additional input from the user

    Returns:
        Prompt for requirements gathering
    """
    prompt = f"""
I need to extract clear requirements and constraints for the following coding task:

Task Description: {task_description}

Additional Information: {user_input}

Please analyze the task and provide:

1. A list of specific, actionable requirements that the solution must satisfy
2. A list of constraints or limitations that apply to the implementation
3. Any clarifications or assumptions that need to be made

Format your response as follows:
Requirements:
- [Requirement 1]
- [Requirement 2]
...

Constraints:
- [Constraint 1]
- [Constraint 2]
...

Clarifications/Assumptions:
- [Clarification 1]
- [Clarification 2]
...
"""
    return prompt


def create_knowledge_gathering_prompt(
        task_description: str,
        requirements: List[str],
        constraints: List[str]
) -> str:
    """
    Create a prompt for gathering relevant knowledge for the given task.

    Args:
        task_description: Description of the task
        requirements: List of requirements
        constraints: List of constraints

    Returns:
        Prompt for knowledge gathering
    """
    requirements_str = "\n".join([f"- {req}" for req in requirements])
    constraints_str = "\n".join(
        [f"- {constraint}" for constraint in constraints])

    prompt = f"""
I need to identify the key knowledge and information needed to implement the following coding task:

Task Description: {task_description}

Requirements:
{requirements_str}

Constraints:
{constraints_str}

Please provide:

1. Key concepts and domain knowledge required to understand this task
2. Relevant libraries, frameworks, or tools that should be used
3. Best practices or design patterns that would be appropriate for this implementation
4. Any potential challenges or edge cases to be aware of

Format your response in a structured way with clear sections for each category.
"""
    return prompt


def create_implementation_planning_prompt(
        task_description: str,
        requirements: List[str],
        constraints: List[str],
        context_items: List[Dict[str, str]]
) -> str:
    """
    Create a prompt for planning the implementation of the task.

    Args:
        task_description: Description of the task
        requirements: List of requirements
        constraints: List of constraints
        context_items: List of context items with relevant information

    Returns:
        Prompt for implementation planning
    """
    requirements_str = "\n".join([f"- {req}" for req in requirements])
    constraints_str = "\n".join(
        [f"- {constraint}" for constraint in constraints])
    context_str = format_context_items_for_prompt(context_items)

    prompt = f"""
I need to create a detailed implementation plan for the following coding task:

Task Description: {task_description}

Requirements:
{requirements_str}

Constraints:
{constraints_str}

Relevant Context Information:
{context_str}

Please provide a step-by-step implementation plan that:
1. Breaks down the task into manageable components or functions
2. Specifies the inputs, outputs, and behavior of each component
3. Describes the data structures and algorithms to be used
4. Outlines the control flow and interactions between components
5. Addresses all requirements while respecting the constraints

Format your response as a structured implementation plan with clear steps, components, and explanations.
"""
    return prompt


def create_implementation_writing_prompt(
        task_description: str,
        requirements: List[str],
        plan: str,
        context_items: List[Dict[str, str]]
) -> str:
    """
    Create a prompt for writing the implementation code.

    Args:
        task_description: Description of the task
        requirements: List of requirements
        plan: Implementation plan
        context_items: List of context items with relevant information

    Returns:
        Prompt for implementation writing
    """
    requirements_str = "\n".join([f"- {req}" for req in requirements])
    context_str = format_context_items_for_prompt(context_items)

    prompt = f"""
I need to write high-quality, production-ready code for the following task:

Task Description: {task_description}

Requirements:
{requirements_str}

Implementation Plan:
{plan}

Relevant Context Information:
{context_str}

Please write the complete implementation code that:
1. Follows the implementation plan
2. Satisfies all requirements
3. Is clean, efficient, and well-structured
4. Includes appropriate error handling
5. Is well-documented with clear comments and docstrings

Provide the full implementation without abbreviations or placeholders. The code should be ready to use without further modifications.
"""
    return prompt


def create_review_prompt(
        code: str,
        requirements: List[str],
        constraints: List[str]
) -> str:
    """
    Create a prompt for reviewing the implementation code.

    Args:
        code: The implementation code to review
        requirements: List of requirements
        constraints: List of constraints

    Returns:
        Prompt for code review
    """
    requirements_str = "\n".join([f"- {req}" for req in requirements])
    constraints_str = "\n".join(
        [f"- {constraint}" for constraint in constraints])

    prompt = f"""
I need a thorough code review of the following implementation:

```
{code}
```

The code should satisfy these requirements:
{requirements_str}

And adhere to these constraints:
{constraints_str}

Please provide a comprehensive review that evaluates:
1. Correctness: Does the code correctly fulfill all requirements?
2. Completeness: Are there any missing features or edge cases?
3. Code quality: Is the code clean, well-structured, and maintainable?
4. Performance: Are there any potential performance issues?
5. Security: Are there any security concerns?
6. Best practices: Does the code follow industry best practices?

For each issue identified, please provide:
- A description of the issue
- Its impact or severity
- A specific recommendation for improvement

Additionally, provide an overall assessment of the code quality and recommendations for the most important improvements.
"""
    return prompt