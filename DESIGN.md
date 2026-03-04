# Design Document - Multi-Agent Task Orchestration System

## 1. Problem Decomposition

The system breaks down "research and report" workflows into four specialised agents, each with a single responsibility:

| Agent | Responsibility | Input | Output |
|-------|---------------|-------|--------|
| **Planner** | Decomposes user query into sub-tasks | Raw query | Ordered sub-task list |
| **Researcher** | Gathers information per sub-task | Plan | Research findings |
| **Writer** | Synthesises findings into a report | Research | Draft report |
| **Reviewer** | Evaluates & approves or requests revision | Draft | Feedback / approval |

An **Orchestrator** coordinates the pipeline, manages data flow between agents, and handles the reviewer feedback loop (max 2 revision cycles to prevent infinite loops).

---

## 2. Architectural Decisions

### Backend: FastAPI over Flask / Django

**Why FastAPI:**
- **Async-native** - the agent pipeline uses `asyncio`, and FastAPI's async handlers mean no thread-pool overhead.
- **Pydantic integration** - request/response models are validated automatically, reducing boilerplate.
- **SSE support** - `StreamingResponse` handles server-sent events without additional libraries.
- **Minimal footprint** - the entire backend is ~4 files with 3 dependencies.

### SSE over WebSockets

| Factor | SSE | WebSockets |
|--------|-----|------------|
| Direction | Server -> Client [Yes] | Bidirectional |
| Complexity | Simple, HTTP-based | Custom protocol |
| Reconnection | Built-in | Manual |
| Browser support | Native `EventSource` | Native `WebSocket` |

**Decision:** We only need server -> client updates. SSE is simpler, auto-reconnects, and requires no extra library. WebSockets would be warranted if we needed bidirectional communication (e.g., user cancelling mid-pipeline).

### In-Memory State (no database)

For this demo, task state lives in a Python `dict`. This is sufficient because:
- Tasks are processed in seconds, not hours
- There's no multi-server deployment or persistence requirement
- It eliminates setup friction (no database to install)

**Trade-off:** State is lost on server restart. With more time, I'd add SQLite or Redis for persistence and task history.

### Background Task Execution

The `POST /api/tasks` endpoint returns immediately with a `task_id`, and the pipeline runs as an `asyncio.create_task()` coroutine. This means:
- The client gets an instant response
- Progress is streamed via SSE
- The client can also poll `GET /api/tasks/{id}` as a fallback

### Agent Abstraction

All agents extend a `BaseAgent` abstract class with a single `execute(input_data, **kwargs) -> AgentOutput` interface. This makes it trivial to:
- Add new agents (e.g., a Fact Checker)
- Swap implementations (e.g., connect to a real LLM)
- Test agents independently

---

## 3. Data Flow & Failure Modes

```
User Query -> Planner -> Researcher -> Writer -> Reviewer
                                       ^         |
                                       |_________|
                                    (revision loop, max 2x)
```

**Retry logic:** Each agent retries up to 3 times with exponential backoff (0.5s, 1.0s, 1.5s). If all retries fail, the task is marked `FAILED` and the error is propagated to the frontend.

**Reviewer loop:** The Reviewer always requests one revision on the first pass (to demonstrate the feedback loop), then approves on the second pass. The max is capped at 2 revisions to prevent infinite loops.

---

## 4. Frontend Design

- **Pipeline visualization**: Five stages (Planner -> Researcher -> Writer -> Reviewer -> Done) with animated transitions between pending/active/completed states
- **Activity log**: Expandable cards for each agent output, colour-coded by agent type
- **Report view**: Lightweight markdown rendering with support for headings, tables, lists, bold/italic
- **SSE subscription**: The page subscribes to SSE events immediately after task creation, updating the UI in real-time

---
## 5. Industrial Visual Protocol

The user interface prioritises data density and a mission-critical "Command Center" aesthetic:
- **Precision Dimensions**: The main container is expanded to `1400px` (`max-w-7xl`) to provide a high-fidelity workspace for intelligence orchestration.
- **Sharp Edges**: Rounded corners have been intentionally removed (set to `2px` or `0`) across glass panels, inputs, and status tiles to achieve an industrial, precision-engineered look.
- **High-Contrast Glassmorphism**: Uses Zinc-based transparency with strict borders to ensure clarity and depth in a dark-mode environment.
- **Dynamic Rhythm**: Spacing is calculated to ensure that synthesized reports and agent logs scale perfectly within the expanded mission grid.

---

## 6. Assumptions

1. No real LLM is required - agents return templated responses with simulated delays.
2. Single-user, single-server deployment (in-memory state is acceptable).
3. The reviewer's first review always requests revision to demonstrate the feedback loop.
4. The frontend runs on `localhost:3001` (dev default) and the backend on `localhost:8001`.

---

## 7. What I Would Do with More Time

- **Persistent state** with SQLite - task history, user sessions, revisit past results
- **Parallel research** - run sub-tasks concurrently in the Researcher agent
- **Agent configuration UI** - let users add/remove/reorder agents in the pipeline
- **Real LLM integration** - swap simulated responses with an OpenAI or local model
- **Unit tests** - pytest for backend agents/orchestrator, Jest + React Testing Library for frontend
- **Cancellation** - let users cancel a running pipeline via a WebSocket "cancel" message
- **Docker Compose** - one-command startup for both services