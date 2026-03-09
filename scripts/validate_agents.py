"""Validation script — tests agent tools and formatting logic without live Azure services.

Run: python scripts/validate_agents.py
"""

import os
import sys
import tempfile

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy env vars so config.py loads without a real .env
os.environ.setdefault("AZURE_AI_PROJECT_ENDPOINT", "https://test.openai.azure.com/")
os.environ.setdefault("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
os.environ.setdefault("COSMOS_ENDPOINT", "https://test.documents.azure.com:443/")
os.environ.setdefault("COSMOS_KEY", "test-key")
os.environ.setdefault("COSMOS_DATABASE_NAME", "code-examples")
os.environ.setdefault("COSMOS_CONTAINER_NAME", "examples")

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    if not condition:
        failed += 1
    else:
        passed += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


# ---------------------------------------------------------------------------
# 1. Module imports
# ---------------------------------------------------------------------------
print("\n=== 1. Module imports ===")

try:
    from backend.cosmos_client import format_examples_for_context
    check("cosmos_client import", True)
except Exception as e:
    check("cosmos_client import", False, str(e))

try:
    from backend.agents.code_example_retrieval import (
        CODE_EXAMPLE_RETRIEVAL_INSTRUCTIONS,
        CODE_EXAMPLE_RETRIEVAL_TOOLS,
    )
    check("code_example_retrieval import", True, f"{len(CODE_EXAMPLE_RETRIEVAL_TOOLS)} tools")
except Exception as e:
    check("code_example_retrieval import", False, str(e))

try:
    from backend.agents.codebase_import import (
        CODEBASE_IMPORT_INSTRUCTIONS,
        CODEBASE_IMPORT_TOOLS,
        import_codebase,
        list_python_files,
    )
    check("codebase_import import", True, f"{len(CODEBASE_IMPORT_TOOLS)} tools")
except Exception as e:
    check("codebase_import import", False, str(e))

try:
    from backend.agents.verification.code_quality import CODE_QUALITY_INSTRUCTIONS
    from backend.agents.verification.functional_correctness import FUNCTIONAL_CORRECTNESS_INSTRUCTIONS
    from backend.agents.verification.known_errors import KNOWN_ERRORS_INSTRUCTIONS
    from backend.agents.verification.unknown_errors import UNKNOWN_ERRORS_INSTRUCTIONS
    check("verification agents import (4)", True)
except Exception as e:
    check("verification agents import", False, str(e))

try:
    from backend.agents.report_generation import REPORT_GENERATION_INSTRUCTIONS
    check("report_generation import", True)
except Exception as e:
    check("report_generation import", False, str(e))

try:
    from backend.agents.orchestrator import run_verification_pipeline
    check("orchestrator import", True)
except Exception as e:
    check("orchestrator import", False, str(e))

try:
    from backend.app import app
    check("FastAPI app import", True)
except Exception as e:
    check("FastAPI app import", False, str(e))

# ---------------------------------------------------------------------------
# 2. format_examples_for_context
# ---------------------------------------------------------------------------
print("\n=== 2. format_examples_for_context ===")

examples = [
    {"type": "good", "severity": "low", "description": "Good naming", "code": "x = 1"},
    {"type": "bad", "severity": "high", "description": "Bad naming", "code": "a = 1"},
]
result = format_examples_for_context(examples)
check("returns string", isinstance(result, str))
check("contains 'Example 1'", "Example 1" in result)
check("contains 'Example 2'", "Example 2" in result)
check("contains severity", "low" in result and "high" in result)
check("contains code", "x = 1" in result and "a = 1" in result)

empty_result = format_examples_for_context([])
check("empty list returns empty string", empty_result == "")

# ---------------------------------------------------------------------------
# 3. Codebase import tool (local filesystem — no Azure needed)
# ---------------------------------------------------------------------------
print("\n=== 3. Codebase import tool (local fs) ===")

with tempfile.TemporaryDirectory() as tmpdir:
    # Create test Python files
    with open(os.path.join(tmpdir, "main.py"), "w") as f:
        f.write("print('hello')\n")
    subdir = os.path.join(tmpdir, "pkg")
    os.makedirs(subdir)
    with open(os.path.join(subdir, "utils.py"), "w") as f:
        f.write("def add(a, b):\n    return a + b\n")
    # Create a non-Python file that should be ignored
    with open(os.path.join(tmpdir, "data.txt"), "w") as f:
        f.write("not python")
    # Create a __pycache__ dir that should be skipped
    os.makedirs(os.path.join(tmpdir, "__pycache__"))
    with open(os.path.join(tmpdir, "__pycache__", "cached.pyc"), "w") as f:
        f.write("bytecode")

    import_result = import_codebase.func(directory_path=tmpdir)
    check("imports 2 files", "Imported 2 Python file(s)" in import_result)
    check("contains main.py", "main.py" in import_result)
    check("contains utils.py", "utils.py" in import_result)
    check("contains file content", "print('hello')" in import_result)
    check("skipped __pycache__", "__pycache__" not in import_result)
    check("excluded .txt files", "data.txt" not in import_result)

    list_result = list_python_files.func(directory_path=tmpdir)
    check("lists 2 files", "Found 2 Python file(s)" in list_result)

    # Test empty directory
    with tempfile.TemporaryDirectory() as empty:
        empty_import = import_codebase.func(directory_path=empty)
        check("empty dir message", "No Python files found" in empty_import)

# ---------------------------------------------------------------------------
# 4. Path traversal protection
# ---------------------------------------------------------------------------
print("\n=== 4. Path traversal protection ===")

with tempfile.TemporaryDirectory() as tmpdir:
    # Create a symlink pointing outside the base directory
    outside_dir = tempfile.mkdtemp()
    with open(os.path.join(outside_dir, "secret.py"), "w") as f:
        f.write("SECRET = 'leaked'")

    link_path = os.path.join(tmpdir, "escape")
    try:
        os.symlink(outside_dir, link_path)
        result = import_codebase.func(directory_path=tmpdir)
        check("symlink outside base is blocked", "SECRET" not in result)
    except OSError:
        # Symlinks may require elevated privileges on Windows
        check("symlink test skipped (insufficient privileges)", True, "os.symlink not available")
    finally:
        import shutil
        shutil.rmtree(outside_dir, ignore_errors=True)

# ---------------------------------------------------------------------------
# 5. Instruction content validation
# ---------------------------------------------------------------------------
print("\n=== 5. Agent instruction content ===")

check("retrieval instructions reference Cosmos DB", "Cosmos DB" in CODE_EXAMPLE_RETRIEVAL_INSTRUCTIONS)
check("retrieval instructions reference Python", "Python" in CODE_EXAMPLE_RETRIEVAL_INSTRUCTIONS)
check("quality instructions contain rubric", "0:" in CODE_QUALITY_INSTRUCTIONS and "5:" in CODE_QUALITY_INSTRUCTIONS)
check("functional instructions contain rubric", "0:" in FUNCTIONAL_CORRECTNESS_INSTRUCTIONS and "5:" in FUNCTIONAL_CORRECTNESS_INSTRUCTIONS)
check("known errors instructions contain rubric", "0:" in KNOWN_ERRORS_INSTRUCTIONS and "5:" in KNOWN_ERRORS_INSTRUCTIONS)
check("unknown errors instructions contain rubric", "0:" in UNKNOWN_ERRORS_INSTRUCTIONS and "5:" in UNKNOWN_ERRORS_INSTRUCTIONS)
check("report instructions mention HTML", "HTML" in REPORT_GENERATION_INSTRUCTIONS)
check("report instructions mention error table", "table" in REPORT_GENERATION_INSTRUCTIONS.lower())

# ---------------------------------------------------------------------------
# 6. FastAPI routes
# ---------------------------------------------------------------------------
print("\n=== 6. FastAPI routes ===")

routes = [r.path for r in app.routes]
check("GET / route exists", "/" in routes)
check("POST /api/verify route exists", "/api/verify" in routes)
check("/static mount exists", "/static" in routes or any("/static" in r for r in routes))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print(f"{'='*50}")

sys.exit(1 if failed > 0 else 0)
