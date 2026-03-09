"""FastAPI web server for the Code Verification System.

Provides:
- Static file serving for the web UI
- POST /api/verify endpoint to start verification (returns SSE stream)
- Progress updates streamed to the UI via Server-Sent Events
- Accepts either a local directory path or a Git HTTPS URL
"""

import asyncio
import json
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.agents.orchestrator import run_verification_pipeline
from backend.git_utils import is_git_url, clone_repo, cleanup_clone

app = FastAPI(title="Code Verification System")

_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/verify")
async def verify_codebase(request: Request):
    """Start the code verification pipeline.

    Expects JSON body with one of:
      {"directory_path": "/absolute/path/to/codebase"}
      {"git_url": "https://github.com/user/repo"}
    Returns a Server-Sent Events stream with progress updates and the final report.
    """
    body = await request.json()
    directory_path: str = body.get("directory_path", "")
    git_url: str = body.get("git_url", "")

    if not directory_path and not git_url:
        return StreamingResponse(
            _error_stream("Provide either directory_path or git_url"),
            media_type="text/event-stream",
        )

    # --- Git URL mode: clone into a temp directory ---
    if git_url:
        if not is_git_url(git_url):
            return StreamingResponse(
                _error_stream(
                    "Invalid Git URL. Only HTTPS URLs are supported "
                    "(e.g. https://github.com/user/repo)"
                ),
                media_type="text/event-stream",
            )
        return StreamingResponse(
            _git_verification_stream(git_url),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # --- Local directory mode ---
    if not os.path.isabs(directory_path):
        return StreamingResponse(
            _error_stream("directory_path must be an absolute path"),
            media_type="text/event-stream",
        )

    real_path = os.path.realpath(directory_path)
    if not os.path.isdir(real_path):
        return StreamingResponse(
            _error_stream("The specified directory was not found."),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _verification_stream(real_path),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _error_stream(message: str):
    data = json.dumps({"type": "error", "message": message})
    yield f"data: {data}\n\n"


async def _git_verification_stream(git_url: str):
    """Clone a Git repo, run verification, then clean up."""
    clone_dir: str | None = None
    try:
        clone_dir = await asyncio.to_thread(clone_repo, git_url)
    except (ValueError, RuntimeError) as exc:
        data = json.dumps({"type": "error", "message": str(exc)})
        yield f"data: {data}\n\n"
        return

    try:
        async for chunk in _verification_stream(clone_dir):
            yield chunk
    finally:
        if clone_dir:
            await asyncio.to_thread(cleanup_clone, clone_dir)


async def _verification_stream(directory_path: str):
    """Run the pipeline and yield SSE events for progress and the final report."""
    progress_queue: asyncio.Queue[dict] = asyncio.Queue()

    async def on_progress(stage: str, message: str) -> None:
        await progress_queue.put({"type": "progress", "stage": stage, "message": message})

    async def run_pipeline() -> str:
        try:
            result = await run_verification_pipeline(directory_path, on_progress=on_progress)
            await progress_queue.put({"type": "complete", "report": result})
            return result
        except Exception as exc:
            await progress_queue.put({"type": "error", "message": str(exc)})
            return ""

    task = asyncio.create_task(run_pipeline())

    while True:
        try:
            event = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            if task.done():
                break
            # Send keepalive
            yield ": keepalive\n\n"
            continue

        data = json.dumps(event)
        yield f"data: {data}\n\n"

        if event["type"] in ("complete", "error"):
            break

    # Ensure the task is awaited
    await task
