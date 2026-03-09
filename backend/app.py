"""FastAPI web server for the Code Verification System.

Provides:
- Static file serving for the web UI
- POST /api/verify endpoint to start verification (returns SSE stream)
- Progress updates streamed to the UI via Server-Sent Events
"""

import asyncio
import json
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.agents.orchestrator import run_verification_pipeline

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

    Expects JSON body: {"directory_path": "/absolute/path/to/codebase"}
    Returns a Server-Sent Events stream with progress updates and the final report.
    """
    body = await request.json()
    directory_path: str = body.get("directory_path", "")

    if not directory_path:
        return StreamingResponse(
            _error_stream("directory_path is required"),
            media_type="text/event-stream",
        )

    # Validate the path exists, is a directory, and is absolute
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
