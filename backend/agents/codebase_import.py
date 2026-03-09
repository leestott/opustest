"""Codebase Import Agent.

Imports and reads the user's Python codebase from a specified directory.
Collects all Python files and their contents for analysis by the
verification agents.
"""

import os
from typing import Annotated

from pydantic import Field

from agent_framework import tool


@tool(approval_mode="never_require")
def import_codebase(
    directory_path: Annotated[str, Field(description="Absolute path to the directory containing the Python codebase")]
) -> str:
    """Import and read all Python files from the specified directory.

    Recursively scans the directory for .py files and returns their contents.
    Skips virtual environments, __pycache__, .git, and node_modules directories.

    Args:
        directory_path: The absolute path to the codebase directory.

    Returns:
        A formatted string containing all Python file paths and their contents.
    """
    skip_dirs = {"__pycache__", ".git", "node_modules", "venv", ".venv", "env", ".env", ".tox", ".mypy_cache"}
    files_content: list[str] = []
    file_count = 0

    real_base = os.path.realpath(directory_path)

    for root, dirs, files in os.walk(directory_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        real_root = os.path.realpath(root)
        if not real_root.startswith(real_base):
            continue

        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(root, filename)
            real_filepath = os.path.realpath(filepath)
            if not real_filepath.startswith(real_base):
                continue

            rel_path = os.path.relpath(filepath, directory_path)
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                files_content.append(
                    f"===== FILE: {rel_path} =====\n{content}\n"
                )
                file_count += 1
            except OSError:
                files_content.append(
                    f"===== FILE: {rel_path} =====\n[Error: Could not read file]\n"
                )

    if not files_content:
        return f"No Python files found in directory: {directory_path}"

    header = f"Imported {file_count} Python file(s) from: {directory_path}\n\n"
    return header + "\n".join(files_content)


@tool(approval_mode="never_require")
def list_python_files(
    directory_path: Annotated[str, Field(description="Absolute path to the directory containing the Python codebase")]
) -> str:
    """List all Python files in the specified directory without reading contents.

    Args:
        directory_path: The absolute path to the codebase directory.

    Returns:
        A newline-separated list of Python file paths relative to the directory.
    """
    skip_dirs = {"__pycache__", ".git", "node_modules", "venv", ".venv", "env", ".env", ".tox", ".mypy_cache"}
    py_files: list[str] = []

    real_base = os.path.realpath(directory_path)

    for root, dirs, files in os.walk(directory_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        real_root = os.path.realpath(root)
        if not real_root.startswith(real_base):
            continue

        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(root, filename)
            real_filepath = os.path.realpath(filepath)
            if not real_filepath.startswith(real_base):
                continue

            py_files.append(os.path.relpath(filepath, directory_path))

    if not py_files:
        return f"No Python files found in directory: {directory_path}"

    return f"Found {len(py_files)} Python file(s):\n" + "\n".join(py_files)


CODEBASE_IMPORT_INSTRUCTIONS = (
    "You are the Codebase Import Agent. Your role is to import and read all Python files "
    "from the user's specified directory. Use the import_codebase tool to recursively "
    "collect all .py files and their contents. Return the complete codebase contents "
    "so they can be analyzed by the verification agents."
)

CODEBASE_IMPORT_TOOLS = [import_codebase, list_python_files]
