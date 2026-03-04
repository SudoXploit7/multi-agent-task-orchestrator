"""
Pydantic models and enums for the Multi-Agent Task Orchestration System.

Defines the data structures used throughout the backend:
- TaskStatus: The lifecycle states of a task
- AgentOutput: The result produced by each agent
- TaskState: Full state of a task including all agent outputs
- Request/Response models for API endpoints
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, enum.Enum):
    """Lifecycle states of a task through the agent pipeline."""

    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    WRITING = "writing"
    REVIEWING = "reviewing"
    REVISING = "revising"
    DONE = "done"
    FAILED = "failed"


class AgentOutput(BaseModel):
    """Output produced by a single agent execution."""

    agent_name: str
    status: str = "success"  # "success" | "error"
    output: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)


class TaskState(BaseModel):
    """Full state of a task, including all agent outputs and progress info."""

    task_id: str
    query: str
    status: TaskStatus = TaskStatus.PENDING
    current_agent: Optional[str] = None
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    final_report: Optional[str] = None
    revision_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None


# --------------- API Request / Response Models ---------------


class TaskRequest(BaseModel):
    """Request body for POST /api/tasks."""

    query: str = Field(..., min_length=1, max_length=2000)


class TaskResponse(BaseModel):
    """Minimal response returned when a new task is created."""

    task_id: str
    status: TaskStatus


class TaskDetailResponse(BaseModel):
    """Full response returned by GET /api/tasks/{task_id}."""

    task_id: str
    query: str
    status: TaskStatus
    current_agent: Optional[str] = None
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    final_report: Optional[str] = None
    revision_count: int = 0
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None
