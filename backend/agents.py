"""
Agent definitions for the Multi-Agent Task Orchestration System.

Each agent follows a consistent interface defined by BaseAgent:
  - `name` property: human-readable agent name
  - `execute(input_data) -> AgentOutput`: process input and return output

Agents use templated/simulated responses (no real LLM required).
Async sleep simulates processing time so the frontend can visualise progress.
"""

from __future__ import annotations

import abc
import asyncio
import random
from datetime import datetime

from models import AgentOutput


class BaseAgent(abc.ABC):
    """Abstract base class that all agents must implement."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable agent name shown in the UI pipeline."""
        ...

    @abc.abstractmethod
    async def execute(self, input_data: str, **kwargs) -> AgentOutput:
        """
        Run the agent's logic on *input_data* and return an AgentOutput.

        Parameters
        ----------
        input_data : str
            Free-form text the agent processes (e.g. user query, research notes).
        **kwargs :
            Optional context such as previous agent outputs.
        """
        ...

    def _make_output(
        self,
        output: str,
        started: datetime,
        metadata: dict | None = None,
    ) -> AgentOutput:
        """Helper to build a consistent AgentOutput."""
        return AgentOutput(
            agent_name=self.name,
            status="success",
            output=output,
            started_at=started,
            completed_at=datetime.utcnow(),
            metadata=metadata or {},
        )


# ──────────────────────────────────────────────────────────────
#  Concrete Agent Implementations
# ──────────────────────────────────────────────────────────────


class PlannerAgent(BaseAgent):
    """Breaks the user's request into discrete sub-tasks."""

    @property
    def name(self) -> str:
        return "Planner"

    async def execute(self, input_data: str, **kwargs) -> AgentOutput:
        started = datetime.utcnow()
        await asyncio.sleep(random.uniform(1.0, 2.0))  # simulate thinking

        # Extract a topic from the query for templated responses
        topic = input_data.strip()

        sub_tasks = [
            f"1. Define key concepts and terminology related to: {topic}",
            f"2. Research arguments IN FAVOUR of the first perspective",
            f"3. Research arguments AGAINST / alternative perspective",
            f"4. Identify real-world case studies or examples",
            f"5. Synthesize findings into a balanced summary report",
        ]

        plan_text = (
            f"## Execution Plan\n\n"
            f"**Query:** {topic}\n\n"
            f"**Sub-tasks identified:**\n" + "\n".join(sub_tasks)
        )

        return self._make_output(
            output=plan_text,
            started=started,
            metadata={"sub_task_count": len(sub_tasks)},
        )


class ResearcherAgent(BaseAgent):
    """Gathers information for each sub-task (simulated)."""

    @property
    def name(self) -> str:
        return "Researcher"

    async def execute(self, input_data: str, **kwargs) -> AgentOutput:
        started = datetime.utcnow()
        await asyncio.sleep(random.uniform(2.0, 3.5))  # simulate research

        topic = kwargs.get("original_query", input_data)

        research = (
            f"## Research Findings\n\n"
            f"### Key Concepts\n"
            f"The topic \"{topic}\" encompasses several important dimensions that "
            f"professionals and organizations must consider.\n\n"
            f"### Perspective A - Advantages\n"
            f"- **Scalability**: Enables independent scaling of components, allowing "
            f"teams to allocate resources where they are most needed.\n"
            f"- **Flexibility**: Teams can choose the best technology for each component, "
            f"reducing lock-in to a single stack.\n"
            f"- **Fault Isolation**: Failures in one area do not cascade to the entire system.\n"
            f"- **Team Autonomy**: Smaller, focused teams can own and deploy independently.\n\n"
            f"### Perspective B - Challenges & Counter-arguments\n"
            f"- **Complexity**: Distributed systems introduce network latency, data consistency "
            f"challenges, and operational overhead.\n"
            f"- **Debugging Difficulty**: Tracing issues across multiple services requires "
            f"sophisticated observability tooling.\n"
            f"- **Deployment Overhead**: Each component needs its own CI/CD pipeline, "
            f"monitoring, and infrastructure.\n"
            f"- **Consistency Trade-offs**: Maintaining data consistency across boundaries "
            f"often requires eventual consistency patterns.\n\n"
            f"### Real-World Examples\n"
            f"- **Netflix**: Migrated from monolith to microservices to handle 200M+ subscribers.\n"
            f"- **Shopify**: Chose a modular monolith approach, proving that monoliths can "
            f"scale effectively with the right architecture.\n"
            f"- **Amazon**: Transitioned to service-oriented architecture early, enabling "
            f"rapid feature development across teams.\n"
        )

        return self._make_output(
            output=research,
            started=started,
            metadata={"sources_consulted": 5, "findings_count": 3},
        )


class WriterAgent(BaseAgent):
    """Synthesizes research into a draft report."""

    @property
    def name(self) -> str:
        return "Writer"

    async def execute(self, input_data: str, **kwargs) -> AgentOutput:
        started = datetime.utcnow()
        await asyncio.sleep(random.uniform(1.5, 2.5))  # simulate writing

        topic = kwargs.get("original_query", "the requested topic")
        revision_feedback = kwargs.get("revision_feedback", "")

        if revision_feedback:
            # This is a revision pass
            draft = (
                f"## Summary Report (Revised)\n\n"
                f"**Topic:** {topic}\n\n"
                f"*This report has been revised based on reviewer feedback.*\n\n"
                f"### Executive Summary\n"
                f"This report provides a comprehensive analysis of {topic}. "
                f"After careful examination of multiple perspectives, real-world case studies, "
                f"and industry best practices, we present a balanced assessment to guide "
                f"decision-making.\n\n"
                f"### 1. Overview\n"
                f"The landscape surrounding {topic} has evolved significantly. Modern approaches "
                f"emphasize pragmatism over ideology - the right choice depends on team size, "
                f"operational maturity, and business requirements.\n\n"
                f"### 2. Comparative Analysis\n"
                f"| Factor | Approach A | Approach B |\n"
                f"|--------|-----------|------------|\n"
                f"| Scalability | Independent scaling | Vertical scaling |\n"
                f"| Complexity | Higher operational | Lower operational |\n"
                f"| Team Size | Large distributed | Small co-located |\n"
                f"| Time to Market | Slower initially | Faster initially |\n"
                f"| Fault Isolation | Strong | Requires discipline |\n\n"
                f"### 3. Key Findings\n"
                f"- There is no universally superior approach; context matters significantly.\n"
                f"- Organizations should consider their current scale, team structure, and growth trajectory.\n"
                f"- A hybrid approach (e.g., modular monolith) can capture benefits of both paradigms.\n"
                f"- Migration between approaches is possible but costly - choose thoughtfully upfront.\n\n"
                f"### 4. Recommendations\n"
                f"1. Start with the simplest architecture that meets current needs.\n"
                f"2. Design for modularity regardless of deployment strategy.\n"
                f"3. Invest in observability and CI/CD early.\n"
                f"4. Re-evaluate architecture as the team and product scale.\n\n"
                f"### 5. Conclusion\n"
                f"The choice regarding {topic} should be driven by practical constraints rather than "
                f"industry trends. Both approaches have proven successful at scale when applied "
                f"appropriately. The key is to make an informed, deliberate decision and revisit "
                f"it as circumstances evolve.\n"
            )
        else:
            draft = (
                f"## Draft Report\n\n"
                f"**Topic:** {topic}\n\n"
                f"### Executive Summary\n"
                f"This report examines {topic} by analysing multiple perspectives and "
                f"real-world case studies.\n\n"
                f"### 1. Background\n"
                f"The debate around {topic} has been a recurring theme in technology "
                f"and business strategy discussions. Understanding the trade-offs is "
                f"essential for making informed decisions.\n\n"
                f"### 2. Analysis\n"
                f"**Arguments in favour:**\n"
                f"- Improved scalability and independent deployments\n"
                f"- Better fault isolation and technology flexibility\n"
                f"- Enhanced team autonomy and ownership\n\n"
                f"**Counter-arguments / challenges:**\n"
                f"- Increased operational complexity\n"
                f"- More difficult debugging and tracing\n"
                f"- Higher infrastructure and orchestration costs\n\n"
                f"### 3. Case Studies\n"
                f"Companies like Netflix and Amazon have successfully adopted distributed "
                f"approaches, while Shopify demonstrates that well-structured monoliths "
                f"can also scale effectively.\n\n"
                f"### 4. Conclusion\n"
                f"The optimal approach depends on organizational context. Teams should "
                f"evaluate their specific constraints before committing to a strategy.\n"
            )

        return self._make_output(
            output=draft,
            started=started,
            metadata={"word_count": len(draft.split()), "is_revision": bool(revision_feedback)},
        )


class ReviewerAgent(BaseAgent):
    """Evaluates the draft and either approves or requests revision."""

    @property
    def name(self) -> str:
        return "Reviewer"

    async def execute(self, input_data: str, **kwargs) -> AgentOutput:
        started = datetime.utcnow()
        await asyncio.sleep(random.uniform(1.0, 2.0))

        revision_count: int = kwargs.get("revision_count", 0)

        if revision_count == 0:
            # First review - send back for revision
            feedback = (
                "## Review Feedback\n\n"
                "**Decision:** [Revision Requested]\n\n"
                "The draft covers the core topic but needs improvement in the following areas:\n\n"
                "1. **Add a comparison table** - A side-by-side comparison would make the "
                "analysis more scannable and actionable.\n"
                "2. **Include concrete recommendations** - The conclusion is too generic. "
                "Add specific, actionable recommendations.\n"
                "3. **Strengthen the executive summary** - It should stand alone as a "
                "complete overview for time-pressed readers.\n"
                "4. **Add a section on hybrid approaches** - The analysis presents a false "
                "binary; discuss middle-ground options.\n"
            )
            return AgentOutput(
                agent_name=self.name,
                status="revision_requested",
                output=feedback,
                started_at=started,
                completed_at=datetime.utcnow(),
                metadata={"decision": "revision_requested", "issues_found": 4},
            )
        else:
            # Second review - approve
            approval = (
                "## Review Result\n\n"
                "**Decision:** [Approved]\n\n"
                "The revised report addresses all previous feedback:\n"
                "- Comparison table added\n"
                "- Concrete recommendations included\n"
                "- Executive summary strengthened\n"
                "- Hybrid approaches discussed\n\n"
                "The report is now comprehensive, well-structured, and ready for delivery."
            )
            return AgentOutput(
                agent_name=self.name,
                status="approved",
                output=approval,
                started_at=started,
                completed_at=datetime.utcnow(),
                metadata={"decision": "approved", "quality_score": 9.2},
            )
