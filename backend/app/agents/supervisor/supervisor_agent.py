"""
Supervisor Agent — the brain of the platform.

Responsibilities:
1. Parse natural language → structured intent (LLM)
2. Select and load the correct workflow definition
3. Build WorkflowContext with employee data
4. Execute workflow via WorkflowEngine
5. Stream live updates via EventBus
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base.base_agent import AgentResult, BaseAgent
from app.config.constants import SLA_DEFAULTS, WorkflowType, WorkflowStatus
from app.core.context import EmployeeRecord, WorkflowContext
from app.core.event_bus import event_bus
from app.core.event_types import EventType
from app.core.llm_client import llm_client
from app.core.memory_manager import memory_manager
from app.core.prompt_registry import prompt_registry
from app.workflow_engine.engine import WorkflowEngine, WorkflowDefinitionLoader


class SupervisorAgent(BaseAgent):
    name = "SupervisorAgent"
    description = "Orchestrates all enterprise workflows by parsing intent and delegating to department agents"
    capabilities = ["orchestrate", "parse_intent", "route_workflow", "escalate", "resume"]
    permissions = ["*"]  # Supervisor has full access
    version = "1.0.0"
    owner = "platform"

    def __init__(self) -> None:
        super().__init__()
        self.engine = WorkflowEngine()

    async def execute(self, context: WorkflowContext) -> AgentResult:
        """Not called directly — Supervisor uses start_workflow instead."""
        return AgentResult(status="success", output={"message": "Supervisor is ready"})

    async def start_workflow(
        self,
        raw_request: str,
        employee_id: str,
        session: AsyncSession,
        tenant_id: str,
        demo_mode: bool = True,
    ) -> WorkflowContext:
        """
        Full workflow orchestration entry point.
        Called by the /workflow/start API endpoint.
        """
        # ── Step 1: Parse intent ──────────────────────────────────────
        intent = await self._parse_intent(raw_request)
        workflow_type = intent.get("workflow_type", "travel")

        # Validate workflow type
        if workflow_type not in [wt.value for wt in WorkflowType]:
            workflow_type = "travel"

        # ── Step 2: Load employee ─────────────────────────────────────
        employee = await self._load_employee(employee_id, session)

        # ── Step 3: Build WorkflowContext ─────────────────────────────
        sla_hours = SLA_DEFAULTS.get(WorkflowType(workflow_type), 24)
        sla_deadline = (datetime.now(timezone.utc) + timedelta(hours=sla_hours)).isoformat()

        context = WorkflowContext(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            workflow_version="v1",
            employee=employee,
            raw_request=raw_request,
            parsed_intent=intent,
            destination=intent.get("destination", ""),
            travel_date=intent.get("travel_date", ""),
            return_date=intent.get("return_date", ""),
            purpose=intent.get("purpose", "Business"),
            leave_days=intent.get("days", 0),
            budget_limit=employee.budget_limit if employee else 50000,
            currency=employee.currency if employee else "INR",
            sla_deadline=sla_deadline,
            demo_mode=demo_mode,
        )

        # ── Step 4: Persist workflow record in DB ─────────────────────
        from app.models.workflow import Workflow
        wf_record = Workflow(
            id=context.workflow_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.PENDING,
            definition_name=f"{workflow_type}_workflow",
            definition_version="v1",
            employee_id=employee_id,
            tenant_id=tenant_id,
            raw_request=raw_request,
            parsed_intent=json.dumps(intent),
            context_json=context.to_json(),
            sla_deadline=sla_deadline,
        )
        session.add(wf_record)
        await session.flush()

        # ── Step 5: Save initial conversation turn ────────────────────
        await memory_manager.save_conversation_turn(
            session, context.workflow_id, "employee", "Employee", raw_request, tenant_id
        )
        supervisor_response = (
            f"Supervisor Agent: {workflow_type.capitalize()} request detected. "
            f"Confidence: {intent.get('confidence', 0.95):.0%}. "
            f"Loading {workflow_type}_workflow_v1 and initiating agent pipeline..."
        )
        await memory_manager.save_conversation_turn(
            session, context.workflow_id, "agent", self.name, supervisor_response, tenant_id
        )

        await event_bus.publish(
            EventType.AGENT_THINKING,
            workflow_id=context.workflow_id,
            source_agent=self.name,
            payload={"message": supervisor_response, "agent": self.name},
            tenant_id=tenant_id,
        )

        # ── Step 6: Execute via WorkflowEngine ────────────────────────
        final_context = await self.engine.execute(context, session)
        return final_context

    async def resume_workflow(
        self,
        workflow_id: str,
        approval_id: str,
        session: AsyncSession,
        tenant_id: str,
    ) -> WorkflowContext:
        """
        Resume a paused workflow after human approval.
        Called by /approvals/{id}/approve endpoint.
        """
        from sqlalchemy import select
        from app.models.workflow import Workflow, WorkflowStep as WFStep
        from app.models.domain import Approval

        # Load workflow
        result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
        wf_record = result.scalar_one_or_none()
        if not wf_record:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Restore context from memory
        context = await memory_manager.get_context(session, workflow_id)
        if not context:
            raise ValueError(f"No context found for workflow {workflow_id}")

        context.approval_status = "approved"
        context.demo_mode = wf_record.status != WorkflowStatus.COMPLETED

        # Find which step to resume from (the one after last completed)
        steps_result = await session.execute(
            select(WFStep)
            .where(WFStep.workflow_id == workflow_id)
            .order_by(WFStep.step_index)
        )
        completed_steps = [s for s in steps_result.scalars().all() if s.status == "completed"]
        resume_from = len(completed_steps)

        wf_record.status = WorkflowStatus.RUNNING
        await session.flush()

        await event_bus.publish(
            EventType.WORKFLOW_RESUMED,
            workflow_id=workflow_id,
            source_agent=self.name,
            payload={"resume_from_step": resume_from, "approval_id": approval_id},
            tenant_id=tenant_id,
        )

        final_context = await self.engine.execute(context, session, start_from_step=resume_from)
        return final_context

    async def _parse_intent(self, request: str) -> dict:
        """Use LLM to extract structured intent from natural language."""
        prompt = prompt_registry.get("supervisor.intent_parser", request=request)
        response = await llm_client.complete(prompt)
        result = response.as_json()

        # Ensure required fields
        if "workflow_type" not in result:
            result["workflow_type"] = "travel"
        if "confidence" not in result:
            result["confidence"] = 0.85
        return result

    async def _load_employee(self, employee_id: str, session: AsyncSession) -> EmployeeRecord | None:
        """Load employee from DB and map to EmployeeRecord."""
        from sqlalchemy import select
        from app.models.employee import Employee, Department

        result = await session.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return None

        # Load manager name
        manager_name = None
        manager_email = None
        if emp.manager_id:
            m_result = await session.execute(
                select(Employee).where(Employee.id == emp.manager_id)
            )
            mgr = m_result.scalar_one_or_none()
            if mgr:
                manager_name = mgr.name
                manager_email = mgr.email

        # Load department name
        dept_name = ""
        dept_id = ""
        if emp.department_id:
            d_result = await session.execute(
                select(Department).where(Department.id == emp.department_id)
            )
            dept = d_result.scalar_one_or_none()
            if dept:
                dept_name = dept.name
                dept_id = dept.id

        return EmployeeRecord(
            id=emp.id,
            employee_id=emp.employee_id,
            name=emp.name,
            email=emp.email,
            designation=emp.designation,
            department=dept_name,
            department_id=dept_id,
            grade=emp.grade,
            role=emp.role,
            budget_limit=float(emp.budget_limit),
            leave_balance=emp.leave_balance,
            passport_number=emp.passport_number,
            passport_expiry=emp.passport_expiry,
            manager_id=emp.manager_id,
            manager_name=manager_name,
            manager_email=manager_email,
            phone=emp.phone,
            currency=emp.currency,
        )


# ── Global singleton ──────────────────────────────────────────────────
supervisor_agent = SupervisorAgent()
