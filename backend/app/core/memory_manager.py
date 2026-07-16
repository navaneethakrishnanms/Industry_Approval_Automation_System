"""
Memory Manager — persists workflow context, agent outputs,
conversation history, and execution traces across steps.
Ensures no context is lost between agent invocations.
"""
from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.context import WorkflowContext


class MemoryManager:
    """
    Coordinates all memory operations.
    All memory is stored in memory_snapshots table.
    """

    WORKFLOW_CONTEXT = "workflow_context"
    AGENT_OUTPUT = "agent_output"
    CONVERSATION = "conversation"
    EXECUTION_TRACE = "execution_trace"

    async def save_context(
        self,
        session: "AsyncSession",
        context: "WorkflowContext",
        step_name: str | None = None,
    ) -> None:
        """Snapshot the full WorkflowContext after each step."""
        from app.models.system import MemorySnapshot
        snapshot = MemorySnapshot(
            workflow_id=context.workflow_id,
            agent_name="system",
            memory_type=self.WORKFLOW_CONTEXT,
            step_name=step_name,
            content_json=context.to_json(),
            tenant_id=context.tenant_id,
        )
        session.add(snapshot)
        await session.flush()

    async def save_agent_output(
        self,
        session: "AsyncSession",
        workflow_id: str,
        agent_name: str,
        step_name: str,
        output: dict,
        tenant_id: str | None = None,
    ) -> None:
        """Store an agent's output for this step."""
        from app.models.system import MemorySnapshot
        snapshot = MemorySnapshot(
            workflow_id=workflow_id,
            agent_name=agent_name,
            memory_type=self.AGENT_OUTPUT,
            step_name=step_name,
            content_json=json.dumps(output, default=str),
            tenant_id=tenant_id,
        )
        session.add(snapshot)
        await session.flush()

    async def save_conversation_turn(
        self,
        session: "AsyncSession",
        workflow_id: str,
        role: str,
        agent_name: str,
        message: str,
        tenant_id: str | None = None,
    ) -> None:
        """Save a chat message turn (employee or agent)."""
        from app.models.system import MemorySnapshot
        turn = {
            "role": role,       # "employee" | "agent" | "supervisor"
            "agent": agent_name,
            "message": message,
        }
        snapshot = MemorySnapshot(
            workflow_id=workflow_id,
            agent_name=agent_name,
            memory_type=self.CONVERSATION,
            content_json=json.dumps(turn),
            tenant_id=tenant_id,
        )
        session.add(snapshot)
        await session.flush()

    async def get_context(
        self,
        session: "AsyncSession",
        workflow_id: str,
    ) -> "WorkflowContext | None":
        """Restore the latest WorkflowContext for a workflow."""
        from sqlalchemy import select, desc
        from app.models.system import MemorySnapshot
        from app.core.context import WorkflowContext

        result = await session.execute(
            select(MemorySnapshot)
            .where(
                MemorySnapshot.workflow_id == workflow_id,
                MemorySnapshot.memory_type == self.WORKFLOW_CONTEXT,
            )
            .order_by(desc(MemorySnapshot.created_at))
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            return None
        return WorkflowContext.from_json(snapshot.content_json)

    async def get_conversation_history(
        self,
        session: "AsyncSession",
        workflow_id: str,
    ) -> list[dict]:
        """Retrieve full conversation history for a workflow."""
        from sqlalchemy import select
        from app.models.system import MemorySnapshot

        result = await session.execute(
            select(MemorySnapshot)
            .where(
                MemorySnapshot.workflow_id == workflow_id,
                MemorySnapshot.memory_type == self.CONVERSATION,
            )
            .order_by(MemorySnapshot.created_at)
        )
        snapshots = result.scalars().all()
        return [json.loads(s.content_json) for s in snapshots]

    async def get_execution_trace(
        self,
        session: "AsyncSession",
        workflow_id: str,
    ) -> list[dict]:
        """Full step-by-step execution trace."""
        from sqlalchemy import select
        from app.models.system import MemorySnapshot

        result = await session.execute(
            select(MemorySnapshot)
            .where(
                MemorySnapshot.workflow_id == workflow_id,
                MemorySnapshot.memory_type == self.AGENT_OUTPUT,
            )
            .order_by(MemorySnapshot.created_at)
        )
        snapshots = result.scalars().all()
        return [
            {
                "step_name": s.step_name,
                "agent_name": s.agent_name,
                "output": json.loads(s.content_json),
            }
            for s in snapshots
        ]


# ── Global singleton ──────────────────────────────────────────────────
memory_manager = MemoryManager()
