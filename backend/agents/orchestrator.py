"""Orchestrator Agent.

Manages the overall workflow as specified:
1. Triggers the Code Example Retrieval agent (RAG from Cosmos DB)
2. Triggers the Codebase Import agent and Verification agents
3. Triggers the Report Generation agent

Uses Microsoft Agent Framework's SequentialBuilder for the pipeline
and ConcurrentBuilder for running verification agents in parallel.
Progress callbacks report status to the web UI via SSE.
"""

import asyncio
import json
from typing import Any, Callable, Awaitable, cast

from agent_framework import Agent, Message
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import SequentialBuilder
from azure.identity import DefaultAzureCredential

from backend.config import (
    AZURE_AI_PROJECT_ENDPOINT,
    AZURE_AI_MODEL_DEPLOYMENT_NAME,
)
from backend.agents.code_example_retrieval import (
    CODE_EXAMPLE_RETRIEVAL_INSTRUCTIONS,
    CODE_EXAMPLE_RETRIEVAL_TOOLS,
)
from backend.agents.codebase_import import (
    CODEBASE_IMPORT_INSTRUCTIONS,
    CODEBASE_IMPORT_TOOLS,
)
from backend.agents.verification.code_quality import CODE_QUALITY_INSTRUCTIONS
from backend.agents.verification.functional_correctness import FUNCTIONAL_CORRECTNESS_INSTRUCTIONS
from backend.agents.verification.known_errors import KNOWN_ERRORS_INSTRUCTIONS
from backend.agents.verification.unknown_errors import UNKNOWN_ERRORS_INSTRUCTIONS
from backend.agents.report_generation import REPORT_GENERATION_INSTRUCTIONS

# Type alias for the progress callback
ProgressCallback = Callable[[str, str], Awaitable[None]]


def _create_client() -> AzureOpenAIResponsesClient:
    return AzureOpenAIResponsesClient(
        project_endpoint=AZURE_AI_PROJECT_ENDPOINT,
        deployment_name=AZURE_AI_MODEL_DEPLOYMENT_NAME,
        credential=DefaultAzureCredential(),
    )


async def run_verification_pipeline(
    directory_path: str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """Run the full code verification pipeline.

    Workflow (as specified):
    1. Code Example Retrieval agent retrieves Python examples from Cosmos DB
    2. Codebase Import agent reads the user's codebase
    3. Four Verification agents analyze the codebase (one per scoring area)
    4. Report Generation agent produces the HTML report

    Args:
        directory_path: Absolute path to the Python codebase to verify.
        on_progress: Optional async callback for progress updates.
            Called with (stage: str, message: str).

    Returns:
        The generated HTML report as a string.
    """

    async def _progress(stage: str, message: str) -> None:
        if on_progress:
            await on_progress(stage, message)

    client = _create_client()

    # --- Stage 1: Code Example Retrieval ---
    await _progress("retrieval", "Retrieving Python code examples from Cosmos DB...")

    retrieval_agent = client.as_agent(
        name="code_example_retrieval",
        instructions=CODE_EXAMPLE_RETRIEVAL_INSTRUCTIONS,
        tools=CODE_EXAMPLE_RETRIEVAL_TOOLS,
    )

    retrieval_result = await retrieval_agent.run(
        "Retrieve all Python code examples from the database. "
        "Return both good and bad examples with their type, severity, "
        "description, and code."
    )
    code_examples_context = str(retrieval_result)

    await _progress("retrieval", "Code examples retrieved successfully.")

    # --- Stage 2: Codebase Import ---
    await _progress("import", "Importing codebase from directory...")

    import_agent = client.as_agent(
        name="codebase_import",
        instructions=CODEBASE_IMPORT_INSTRUCTIONS,
        tools=CODEBASE_IMPORT_TOOLS,
    )

    import_result = await import_agent.run(
        f"Import all Python files from this directory: {directory_path}"
    )
    codebase_context = str(import_result)

    await _progress("import", "Codebase imported successfully.")

    # --- Stage 3: Verification (four agents, one per area) ---
    await _progress("verification", "Starting code verification across all four areas...")

    verification_context = (
        f"CODE EXAMPLES FROM DATABASE (use as coding standards reference):\n"
        f"{code_examples_context}\n\n"
        f"CODEBASE TO VERIFY:\n"
        f"{codebase_context}"
    )

    verification_agents_config = [
        ("code_quality", CODE_QUALITY_INSTRUCTIONS, "Code Quality and Coding Standards"),
        ("functional_correctness", FUNCTIONAL_CORRECTNESS_INSTRUCTIONS, "Functional Correctness"),
        ("known_errors", KNOWN_ERRORS_INSTRUCTIONS, "Handling of Known Errors"),
        ("unknown_errors", UNKNOWN_ERRORS_INSTRUCTIONS, "Handling of Unknown Errors"),
    ]

    verification_results: dict[str, str] = {}

    for agent_name, instructions, area_label in verification_agents_config:
        await _progress("verification", f"Verifying: {area_label}...")

        verification_agent = client.as_agent(
            name=agent_name,
            instructions=instructions,
        )

        result = await verification_agent.run(
            f"Analyze the following codebase against the provided code examples.\n\n"
            f"{verification_context}"
        )
        verification_results[agent_name] = str(result)

        await _progress("verification", f"Completed: {area_label}")

    await _progress("verification", "All verification areas completed.")

    # --- Stage 4: Report Generation ---
    await _progress("report", "Generating HTML report...")

    report_agent = client.as_agent(
        name="report_generation",
        instructions=REPORT_GENERATION_INSTRUCTIONS,
    )

    report_input = (
        "Generate a complete HTML report from the following verification results.\n\n"
    )
    for agent_name, result in verification_results.items():
        report_input += f"=== {agent_name} ===\n{result}\n\n"

    report_result = await report_agent.run(report_input)
    html_report = str(report_result)

    await _progress("report", "Report generated successfully.")

    return html_report
