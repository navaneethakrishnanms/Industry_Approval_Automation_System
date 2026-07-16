"""
Workflow Engine — the core execution loop.

Loads versioned JSON definitions, executes steps via AgentRegistry,
handles retries, escalations, human approvals, and emits events at every transition.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import (
    AgentLifecycle, FailureStrategy, SLA_DEFAULTS, WorkflowStatus, StepStatus, WorkflowType
)
from app.core.agent_registry import agent_registry
from app.core.context import WorkflowContext
from app.core.event_bus import event_bus
from app.core.event_types import EventType
from app.core.memory_manager import memory_manager


DEFINITIONS_DIR = os.path.join(os.path.dirname(__file__), "definitions")


class WorkflowStep:
    """Runtime representation of a workflow step from JSON definition."""

    def __init__(self, data: dict) -> None:
        self.name: str = data["name"]
        self.agent_name: str = data["agent"]
        self.description: str = data.get("description", "")
        self.retry_limit: int = data.get("retry_limit", 2)
        self.on_failure: str = data.get("on_failure", "escalate")
        self.timeout_seconds: int | None = data.get("timeout_seconds")
        self.human_approval: bool = data.get("human_approval", False)
        self.approval_level: int = data.get("approval_level", 1)
        self.approval_role: str = data.get("approval_role", "manager")
        self.timeout_hours: int = data.get("timeout_hours", 48)
        self.skip: bool = False


class WorkflowDefinitionLoader:
    """Loads and caches versioned JSON workflow definitions."""

    _cache: dict[str, dict] = {}

    @classmethod
    def load(cls, workflow_type: str, version: str = "v1") -> list[WorkflowStep]:
        key = f"{workflow_type}_{version}"
        if key not in cls._cache:
            path = os.path.join(DEFINITIONS_DIR, f"{workflow_type}_workflow_{version}.json")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Workflow definition not found: {path}")
            with open(path) as f:
                definition = json.load(f)
            cls._cache[key] = definition
        return [WorkflowStep(s) for s in cls._cache[key]["steps"]]

    @classmethod
    def load_definition(cls, workflow_type: str, version: str = "v1") -> dict:
        key = f"{workflow_type}_{version}"
        if key not in cls._cache:
            path = os.path.join(DEFINITIONS_DIR, f"{workflow_type}_workflow_{version}.json")
            with open(path) as f:
                cls._cache[key] = json.load(f)
        return cls._cache[key]

    @classmethod
    def list_available(cls) -> list[dict]:
        result = []
        for fname in os.listdir(DEFINITIONS_DIR):
            if fname.endswith(".json"):
                with open(os.path.join(DEFINITIONS_DIR, fname)) as f:
                    d = json.load(f)
                result.append({"name": d["name"], "version": d["version"], "description": d.get("description", "")})
        return result


class WorkflowEngine:
    """
    Core execution engine. Called by the Supervisor Agent.

    Flow:
        load definition → iterate steps → run agent → handle result
        → retry/escalate/abort/skip → persist state → emit events → continue
    """

    async def execute(
        self,
        context: WorkflowContext,
        session: AsyncSession,
        start_from_step: int = 0,
    ) -> WorkflowContext:
        """
        Execute the full workflow for the given context.
        Returns the final context with all step outputs populated.
        """
        from app.models.workflow import Workflow, WorkflowStep as WorkflowStepModel
        from sqlalchemy import select

        steps = WorkflowDefinitionLoader.load(context.workflow_type, context.workflow_version)
        context.total_steps = len(steps)

        # ── Load DB workflow record ───────────────────────────────────
        result = await session.execute(
            select(Workflow).where(Workflow.id == context.workflow_id)
        )
        wf_record = result.scalar_one_or_none()
        if not wf_record:
            raise ValueError(f"Workflow {context.workflow_id} not found in DB")

        await event_bus.publish(
            EventType.WORKFLOW_STARTED,
            workflow_id=context.workflow_id,
            source_agent="WorkflowEngine",
            payload={
                "workflow_type": context.workflow_type,
                "total_steps": context.total_steps,
                "employee": context.employee.name if context.employee else "Unknown",
                "steps": [s.name for s in steps],
            },
            tenant_id=context.tenant_id,
        )

        # Update DB record
        wf_record.status = WorkflowStatus.RUNNING
        wf_record.total_steps = len(steps)
        wf_record.started_at = datetime.now(timezone.utc).isoformat()
        await session.flush()

        # ── Step execution loop ───────────────────────────────────────
        for idx, step in enumerate(steps):
            if idx < start_from_step:
                continue

            context.current_step = idx + 1
            step_start = time.monotonic()

            # Persist step record
            step_record = WorkflowStepModel(
                workflow_id=context.workflow_id,
                step_index=idx,
                step_name=step.name,
                agent_name=step.agent_name,
                status=StepStatus.RUNNING,
                started_at=datetime.now(timezone.utc).isoformat(),
                input_json=context.to_json(),
            )
            session.add(step_record)
            await session.flush()

            await event_bus.publish(
                EventType.STEP_STARTED,
                workflow_id=context.workflow_id,
                source_agent="WorkflowEngine",
                payload={
                    "step_name": step.name,
                    "agent_name": step.agent_name,
                    "step_index": idx + 1,
                    "total_steps": len(steps),
                    "description": step.description,
                },
                tenant_id=context.tenant_id,
            )

            # Update DB workflow step
            wf_record.current_step = idx + 1
            await session.flush()

            # ── Human approval gate ───────────────────────────────────
            if step.human_approval:
                context, approved = await self._handle_human_approval(
                    context, session, step, wf_record
                )
                if not approved:
                    # Workflow stays paused in DB; resume via API
                    return context

            # ── Agent execution with retry ────────────────────────────
            result = None
            for attempt in range(step.retry_limit + 1):
                try:
                    agent = agent_registry.get(step.agent_name)
                    if attempt > 0:
                        agent_registry.set_agent_status(step.agent_name, AgentLifecycle.RETRYING)
                        await event_bus.publish(
                            EventType.STEP_RETRIED,
                            workflow_id=context.workflow_id,
                            source_agent="WorkflowEngine",
                            payload={"step": step.name, "attempt": attempt + 1},
                            tenant_id=context.tenant_id,
                        )
                        await asyncio.sleep(min(2 ** attempt, 8))  # exponential backoff

                    result = await agent.run(context)

                    if result.status == "success":
                        break

                except KeyError as e:
                    result = None
                    print(f"[WorkflowEngine] Agent not found: {e}")
                    break

            # ── Handle step result ────────────────────────────────────
            duration = round((time.monotonic() - step_start) * 1000, 2)

            if result and result.status == "success":
                # Merge agent output into context
                context.set_step_output(step.name, result.output)

                step_record.status = StepStatus.COMPLETED
                step_record.output_json = json.dumps(result.to_dict(), default=str)
                step_record.completed_at = datetime.now(timezone.utc).isoformat()
                step_record.duration_ms = int(duration)
                step_record.confidence_score = result.confidence
                step_record.reasoning = result.reasoning

                await memory_manager.save_agent_output(
                    session, context.workflow_id, step.agent_name, step.name, result.to_dict()
                )
                await memory_manager.save_context(session, context, step.name)
                await session.flush()

                await event_bus.publish(
                    EventType.STEP_COMPLETED,
                    workflow_id=context.workflow_id,
                    source_agent="WorkflowEngine",
                    payload={
                        "step_name": step.name,
                        "agent_name": step.agent_name,
                        "duration_ms": duration,
                        "confidence": result.confidence,
                        "reasoning": result.reasoning,
                    },
                    tenant_id=context.tenant_id,
                )

            else:
                # Step failed after all retries
                error_msg = result.error if result else "Agent not found"
                step_record.status = StepStatus.FAILED
                step_record.error_message = error_msg
                step_record.completed_at = datetime.now(timezone.utc).isoformat()
                step_record.duration_ms = int(duration)
                await session.flush()

                context.add_error(f"Step '{step.name}' failed: {error_msg}")

                await event_bus.publish(
                    EventType.STEP_FAILED,
                    workflow_id=context.workflow_id,
                    source_agent="WorkflowEngine",
                    payload={"step_name": step.name, "error": error_msg},
                    tenant_id=context.tenant_id,
                )

                # Apply failure strategy
                strategy = step.on_failure
                if strategy == FailureStrategy.ABORT:
                    wf_record.status = WorkflowStatus.FAILED
                    wf_record.error_message = error_msg
                    await self._complete_workflow(context, session, wf_record, success=False)
                    return context
                elif strategy == FailureStrategy.ESCALATE:
                    wf_record.status = WorkflowStatus.ESCALATED
                    await event_bus.publish(
                        EventType.WORKFLOW_ESCALATED,
                        workflow_id=context.workflow_id,
                        source_agent="WorkflowEngine",
                        payload={"reason": error_msg, "step": step.name},
                        tenant_id=context.tenant_id,
                    )
                    await self._complete_workflow(context, session, wf_record, success=False)
                    return context
                elif strategy == FailureStrategy.SKIP:
                    step_record.status = StepStatus.SKIPPED
                    await session.flush()
                    continue
                # "log" strategy: log and continue
                elif strategy == FailureStrategy.LOG:
                    continue

        # ── All steps complete ────────────────────────────────────────
        await self._complete_workflow(context, session, wf_record, success=True)
        return context

    async def _handle_human_approval(
        self,
        context: WorkflowContext,
        session: AsyncSession,
        step: WorkflowStep,
        wf_record,
    ) -> tuple[WorkflowContext, bool]:
        """Create approval record, pause workflow, return (context, already_decided)."""
        from app.models.domain import Approval
        from sqlalchemy import select as sa_select

        # Check if approval already exists and is decided
        existing = await session.execute(
            sa_select(Approval).where(
                Approval.workflow_id == context.workflow_id,
                Approval.level == step.approval_level,
            )
        )
        existing_approval = existing.scalar_one_or_none()

        if existing_approval and existing_approval.status == "approved":
            context.approval_status = "approved"
            return context, True
        if existing_approval and existing_approval.status == "rejected":
            context.approval_status = "rejected"
            return context, False

        # Create new approval request
        expires_at = datetime.now(timezone.utc) + timedelta(hours=step.timeout_hours)
        approval = Approval(
            workflow_id=context.workflow_id,
            level=step.approval_level,
            requested_from_role=step.approval_role,
            status="pending",
            requested_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at.isoformat(),
            tenant_id=context.tenant_id,
            summary=f"Approval required for {context.workflow_type} workflow — {context.employee.name if context.employee else 'Employee'} → {context.destination or 'N/A'}",
        )
        session.add(approval)
        await session.flush()
        context.approval_id = approval.id

        wf_record.status = WorkflowStatus.PAUSED
        await session.flush()

        await event_bus.publish(
            EventType.WORKFLOW_PAUSED,
            workflow_id=context.workflow_id,
            source_agent="WorkflowEngine",
            payload={
                "approval_id": approval.id,
                "approval_level": step.approval_level,
                "approval_role": step.approval_role,
                "step": step.name,
            },
            tenant_id=context.tenant_id,
        )
        await event_bus.publish(
            EventType.APPROVAL_REQUESTED,
            workflow_id=context.workflow_id,
            source_agent="ApprovalAgent",
            payload={
                "approval_id": approval.id,
                "level": step.approval_level,
                "role": step.approval_role,
                "summary": approval.summary,
            },
            tenant_id=context.tenant_id,
        )

        await memory_manager.save_context(session, context, step.name)
        return context, False  # Workflow is now paused

    async def _complete_workflow(
        self,
        context: WorkflowContext,
        session: AsyncSession,
        wf_record,
        success: bool,
    ) -> None:
        wf_record.completed_at = datetime.now(timezone.utc).isoformat()
        if success:
            wf_record.status = WorkflowStatus.COMPLETED
        await session.flush()

        await event_bus.publish(
            EventType.WORKFLOW_COMPLETED if success else EventType.WORKFLOW_FAILED,
            workflow_id=context.workflow_id,
            source_agent="WorkflowEngine",
            payload={
                "status": "completed" if success else "failed",
                "workflow_type": context.workflow_type,
            },
            tenant_id=context.tenant_id,
        )
