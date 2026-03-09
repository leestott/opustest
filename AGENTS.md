# AGENTS.md — Opustest Agent Architecture

This document describes the AI agents in the opustest code verification system, their roles, orchestration, and conventions.

## Overview

Opustest uses **Microsoft Agent Framework** with **Azure OpenAI** to run a multi-agent pipeline that analyzes Python codebases. All agents are orchestrated sequentially by the `run_verification_pipeline` function in `backend/agents/orchestrator.py`.

## Agent Pipeline

The pipeline runs in four stages:

### Stage 1: Code Example Retrieval Agent

- **File:** `backend/agents/code_example_retrieval.py`
- **Purpose:** Retrieves Python code examples (good and bad) from Azure Cosmos DB via RAG. These examples serve as the coding standards reference for all downstream verification.
- **Tools:**
  - `retrieve_all_python_examples` — Fetches all examples from the database
  - `retrieve_good_examples` — Fetches only "good" practice examples
  - `retrieve_bad_examples` — Fetches only "bad" practice examples
  - `retrieve_examples_by_severity` — Filters examples by severity level (low/medium/high)

### Stage 2: Codebase Import Agent

- **File:** `backend/agents/codebase_import.py`
- **Purpose:** Reads the user's Python codebase from a directory path. Recursively collects all `.py` files and their contents, skipping `__pycache__`, `.git`, `venv`, etc.
- **Tools:**
  - `import_codebase` — Reads all Python files from a directory and returns their contents
  - `list_python_files` — Lists Python file paths without reading contents

### Stage 3: Verification Agents (4 parallel areas)

Four agents each score the codebase from 0–5 in their respective area and return errors as structured JSON.

#### Code Quality Agent
- **File:** `backend/agents/verification/code_quality.py`
- **Scoring area:** Static Code Quality and Coding Standards
- **Rubric:** 0 (syntax errors) → 5 (fully compliant, idiomatic, optimized for readability)

#### Functional Correctness Agent
- **File:** `backend/agents/verification/functional_correctness.py`
- **Scoring area:** Functional Correctness
- **Rubric:** 0 (core functionality broken) → 5 (fully correct and robust across all scenarios)

#### Known Errors Agent
- **File:** `backend/agents/verification/known_errors.py`
- **Scoring area:** Handling of Known Errors
- **Rubric:** 0 (known errors cause crashes) → 5 (comprehensive handling with graceful recovery)

#### Unknown Errors Agent
- **File:** `backend/agents/verification/unknown_errors.py`
- **Scoring area:** Handling of Unknown Errors
- **Rubric:** 0 (unexpected errors cause crashes) → 5 (resilient via defensive programming and logging)

### Stage 4: Report Generation Agent

- **File:** `backend/agents/report_generation.py`
- **Purpose:** Compiles all verification results into a single HTML report with score cards, a total score out of 20, and an errors table with fix prompts.

## Conventions

- **Framework:** All agents are created via `AzureOpenAIResponsesClient.as_agent()` from the Microsoft Agent Framework.
- **Authentication:** Uses `DefaultAzureCredential` for Azure OpenAI and Cosmos DB access.
- **Model config:** Deployment name and project endpoint are read from environment variables (`AZURE_AI_MODEL_DEPLOYMENT_NAME`, `AZURE_AI_PROJECT_ENDPOINT`) in `backend/config.py`.
- **Tool approval:** All tools use `approval_mode="never_require"` (no human-in-the-loop confirmation).
- **Output format:** Verification agents return JSON with `{"score": <0-5>, "errors": [...]}`. The report agent returns raw HTML.
- **Progress reporting:** The orchestrator accepts an async `on_progress` callback, used to stream status updates to the web UI via Server-Sent Events.

## Infrastructure

- **Backend:** FastAPI server (`backend/app.py`) serving the web UI and the `/api/verify` SSE endpoint.
- **Database:** Azure Cosmos DB stores curated Python code examples for RAG retrieval.
- **Hosting:** Azure Container Apps via `azd` (Azure Developer CLI). Infrastructure defined in `infra/` using Bicep.
