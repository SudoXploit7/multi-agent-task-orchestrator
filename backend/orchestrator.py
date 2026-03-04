"""
Orchestrator - coordinates the agent pipeline.

Manages the execution flow:
    Planner -> Researcher -> Writer -> Reviewer -> (optional revision loop) -> Done

Key responsibilities:
- Run agents in sequence, piping outputs forward
- Handle the reviewer feedback loop (max MAX_REVISIONS cycles)
- Update TaskState at each step
- Push SSE events via an asyncio.Queue for real-time frontend updates
- Catch and record errors without crashing the pipeline
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Optional

from agents import BaseAgent, PlannerAgent, ResearcherAgent, ReviewerAgent, WriterAgent
from models import AgentOutput, TaskState, TaskStatus

MAX_REVISIONS = 2  # cap revision loops to prevent infinite cycles


class Orchestrator:
    """Coordinates the multi-agent pipeline for a single task."""

    def __init__(self, task: TaskState, event_queue: asyncio.Queue):
        self.task = task
        self.event_queue = event_queue

        # Instantiate agents
        self.planner: BaseAgent = PlannerAgent()
        self.researcher: BaseAgent = ResearcherAgent()
        self.writer: BaseAgent = WriterAgent()
        self.reviewer: BaseAgent = ReviewerAgent()

    # ── public entry point ────────────────────────────────────

    async def run(self) -> TaskState:
        """Execute the full pipeline. Returns the final TaskState."""
        try:
            # 1. Planning
            plan_output = await self._run_agent(
                agent=self.planner,
                input_data=self.task.query,
                status=TaskStatus.PLANNING,
            )

            # 2. Researching
            research_output = await self._run_agent(
                agent=self.researcher,
                input_data=plan_output.output,
                status=TaskStatus.RESEARCHING,
                original_query=self.task.query,
            )

            # 3. Writing (initial draft)
            draft_output = await self._run_agent(
                agent=self.writer,
                input_data=research_output.output,
                status=TaskStatus.WRITING,
                original_query=self.task.query,
            )

            # 4. Review -> possible revision loop
            current_draft = draft_output
            while self.task.revision_count < MAX_REVISIONS:
                review_output = await self._run_agent(
                    agent=self.reviewer,
                    input_data=current_draft.output,
                    status=TaskStatus.REVIEWING,
                    revision_count=self.task.revision_count,
                )

                if review_output.status == "approved":
                    break

                # Reviewer requested revision
                self.task.revision_count += 1
                current_draft = await self._run_agent(
                    agent=self.writer,
                    input_data=research_output.output,
                    status=TaskStatus.REVISING,
                    original_query=self.task.query,
                    revision_feedback=review_output.output,
                )

            # Done
            self.task.final_report = current_draft.output
            self._update_status(TaskStatus.DONE)
            await self._emit_event("pipeline_complete", {
                "final_report": current_draft.output,
            })

        except Exception as exc:
            self.task.status = TaskStatus.FAILED
            self.task.error = str(exc)
            await self._emit_event("error", {"message": str(exc)})

        return self.task

    # ── internal helpers ──────────────────────────────────────

    async def _run_agent(
        self,
        agent: BaseAgent,
        input_data: str,
        status: TaskStatus,
        **kwargs,
    ) -> AgentOutput:
        """Run a single agent with retries, update state, and emit events."""

        self._update_status(status, current_agent=agent.name)
        await self._emit_event("agent_start", {
            "agent": agent.name,
            "status": status.value,
        })

        last_error: Optional[Exception] = None
        for attempt in range(1, 4):  # up to 3 retries
            try:
                output = await agent.execute(input_data, **kwargs)
                self.task.agent_outputs.append(output)
                await self._emit_event("agent_complete", {
                    "agent": agent.name,
                    "status": output.status,
                    "output": output.output,
                    "metadata": output.metadata,
                })
                return output
            except Exception as exc:
                last_error = exc
                await self._emit_event("agent_retry", {
                    "agent": agent.name,
                    "attempt": attempt,
                    "error": str(exc),
                })
                await asyncio.sleep(0.5 * attempt)

        # All retries exhausted
        raise RuntimeError(
            f"Agent '{agent.name}' failed after 3 attempts: {last_error}"
        )

    def _update_status(
        self,
        status: TaskStatus,
        current_agent: Optional[str] = None,
    ) -> None:
        self.task.status = status
        self.task.current_agent = current_agent
        self.task.updated_at = datetime.utcnow()

    async def _emit_event(self, event_type: str, data: dict) -> None:
        """Push an SSE-compatible event dict onto the queue."""
        event = {
            "event": event_type,
            "task_id": self.task.task_id,
            "status": self.task.status.value,
            "current_agent": self.task.current_agent,
            "revision_count": self.task.revision_count,
            **data,
        }
        await self.event_queue.put(event)
