"""
FastAPI application - entry point for the Multi-Agent Task Orchestration API.

Endpoints:
    POST /api/tasks            - Submit a new task
    GET  /api/tasks/{task_id}  - Get full task state (polling)
    GET  /api/tasks/{task_id}/stream  - SSE stream for real-time progress
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models import (
    TaskDetailResponse,
    TaskRequest,
    TaskResponse,
    TaskState,
    TaskStatus,
)
from orchestrator import Orchestrator

# ── Application ───────────────────────────────────────────────

app = FastAPI(
    title="Multi-Agent Task Orchestrator",
    description="Orchestrates Planner -> Researcher -> Writer -> Reviewer agents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state store ─────────────────────────────────────

tasks: Dict[str, TaskState] = {}
event_queues: Dict[str, asyncio.Queue] = {}


# ── Endpoints ─────────────────────────────────────────────────


@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
async def create_task(body: TaskRequest):
    """Accept a user query and kick off the agent pipeline in the background."""

    task_id = str(uuid.uuid4())
    task = TaskState(task_id=task_id, query=body.query)
    tasks[task_id] = task

    # Create an event queue for this task's SSE stream
    queue: asyncio.Queue = asyncio.Queue()
    event_queues[task_id] = queue

    # Launch the orchestrator as a background coroutine
    orchestrator = Orchestrator(task=task, event_queue=queue)
    asyncio.create_task(_run_pipeline(task_id, orchestrator))

    return TaskResponse(task_id=task_id, status=task.status)


@app.get("/api/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    """Return the full state of a task (for polling)."""

    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskDetailResponse(
        task_id=task.task_id,
        query=task.query,
        status=task.status,
        current_agent=task.current_agent,
        agent_outputs=task.agent_outputs,
        final_report=task.final_report,
        revision_count=task.revision_count,
        created_at=task.created_at,
        updated_at=task.updated_at,
        error=task.error,
    )


@app.get("/api/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    """
    SSE endpoint - streams real-time agent progress events.

    Event format:
        data: { "event": "agent_start", "agent": "Planner", ... }
    """

    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    queue = event_queues.get(task_id)
    if not queue:
        raise HTTPException(status_code=404, detail="No event stream for this task")

    return StreamingResponse(
        _event_generator(task_id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Background helpers ────────────────────────────────────────


async def _run_pipeline(task_id: str, orchestrator: Orchestrator) -> None:
    """Run the pipeline and signal completion on the event queue."""
    try:
        await orchestrator.run()
    finally:
        # Sentinel: tells the SSE generator to stop
        queue = event_queues.get(task_id)
        if queue:
            await queue.put(None)


async def _event_generator(task_id: str, queue: asyncio.Queue):
    """Yield SSE-formatted events from the queue until the pipeline finishes."""
    while True:
        event = await queue.get()
        if event is None:
            # Pipeline finished - send a final event and close
            yield f"data: {json.dumps({'event': 'stream_end'})}\n\n"
            break
        yield f"data: {json.dumps(event)}\n\n"


# ── Dev server ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
