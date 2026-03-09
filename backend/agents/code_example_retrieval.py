"""Code Example Retrieval Agent.

Uses RAG to retrieve Python code examples from the Cosmos DB database.
These examples serve as the coding standards reference for verification.
The agent retrieves both 'good' and 'bad' examples and formats them
for downstream consumption by the verification agents.
"""

from typing import Annotated

from pydantic import Field

from agent_framework import tool

from backend.cosmos_client import (
    retrieve_python_examples,
    retrieve_examples_by_type,
    format_examples_for_context,
)


@tool(approval_mode="never_require")
def retrieve_all_python_examples() -> str:
    """Retrieve all Python code examples (good and bad) from the Cosmos DB database.

    Returns a formatted text block containing all Python code examples
    used as the coding standards reference for verification.
    """
    examples = retrieve_python_examples()
    if not examples:
        return "No Python code examples found in the database."
    return format_examples_for_context(examples)


@tool(approval_mode="never_require")
def retrieve_good_examples() -> str:
    """Retrieve Python code examples marked as 'good' from the Cosmos DB database.

    Returns formatted examples of good coding practices.
    """
    examples = retrieve_examples_by_type("good")
    if not examples:
        return "No good Python code examples found in the database."
    return format_examples_for_context(examples)


@tool(approval_mode="never_require")
def retrieve_bad_examples() -> str:
    """Retrieve Python code examples marked as 'bad' from the Cosmos DB database.

    Returns formatted examples of bad coding practices with severity levels.
    """
    examples = retrieve_examples_by_type("bad")
    if not examples:
        return "No bad Python code examples found in the database."
    return format_examples_for_context(examples)


@tool(approval_mode="never_require")
def retrieve_examples_by_severity(
    severity: Annotated[str, Field(description="Severity level: 'low', 'medium', or 'high'")]
) -> str:
    """Retrieve Python code examples filtered by severity level from the Cosmos DB database.

    Args:
        severity: The severity level to filter by.

    Returns formatted examples matching the specified severity.
    """
    all_examples = retrieve_python_examples()
    filtered = [ex for ex in all_examples if ex.get("severity") == severity]
    if not filtered:
        return f"No Python code examples with severity '{severity}' found."
    return format_examples_for_context(filtered)


CODE_EXAMPLE_RETRIEVAL_INSTRUCTIONS = (
    "You are the Code Example Retrieval Agent. Your role is to retrieve Python code "
    "examples from the Cosmos DB database that serve as coding standards for verification. "
    "Use your tools to retrieve all Python examples (both 'good' and 'bad'). "
    "Each example has a type ('good' or 'bad'), severity ('low', 'medium', 'high'), "
    "a description of what is good or bad, and the actual code snippet. "
    "Return ALL retrieved examples in a structured format so the verification agents "
    "can use them as the reference standards for code quality assessment."
)

CODE_EXAMPLE_RETRIEVAL_TOOLS = [
    retrieve_all_python_examples,
    retrieve_good_examples,
    retrieve_bad_examples,
    retrieve_examples_by_severity,
]
