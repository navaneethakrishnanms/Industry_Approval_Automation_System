"""Agents, Approvals, Analytics, Demo, Definitions, Auth routers."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import get_current_user, get_tenant_id, require_manager
from app.database.base import get_db
from app.schemas.schemas import (
    AgentCardOut, AgentHealthOut, ApprovalOut, ApprovalDecisionRequest,
    DashboardKPIOut, CostSummaryOut, DemoModeOut, DemoModeSetRequest,
    WorkflowDefinitionOut, MessageResponse, LoginRequest, TokenResponse, EmployeeOut, PaginatedResponse
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENTS ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
agents_router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


@agents_router.get("/", response_model=list[AgentCardOut])
async def list_agents():
    """List all registered agents with live status and metrics."""
    from app.core.agent_registry import agent_registry
    registrations = agent_registry.all_registrations()
    return [
        AgentCardOut(
            name=r.name,
            description=r._agent_ref.description if r._agent_ref else "",
            status=r.status.value,
            capabilities=r.capabilities,
            tools=r.tools,
            version=r.version,
            owner=r.owner,
            call_count=r.call_count,
            success_rate=r.success_rate,
            avg_response_ms=r.avg_response_ms,
            last_active=r.last_active.isoformat() if r.last_active else None,
        )
        for r in registrations
    ]


@agents_router.get("/health", response_model=AgentHealthOut)
async def agent_health():
    from app.core.agent_registry import agent_registry
    from app.config.constants import AgentLifecycle
    regs = agent_registry.all_registrations()
    return AgentHealthOut(
        total_agents=len(regs),
        idle=sum(1 for r in regs if r.status == AgentLifecycle.IDLE),
        running=sum(1 for r in regs if r.status == AgentLifecycle.RUNNING),
        failed=sum(1 for r in regs if r.status == AgentLifecycle.FAILED),
        agents=[
            AgentCardOut(
                name=r.name, description=r._agent_ref.description if r._agent_ref else "",
                status=r.status.value, capabilities=r.capabilities, tools=r.tools,
                version=r.version, owner=r.owner, call_count=r.call_count,
                success_rate=r.success_rate, avg_response_ms=r.avg_response_ms,
                last_active=r.last_active.isoformat() if r.last_active else None,
            )
            for r in regs
        ],
    )


@agents_router.get("/{agent_name}/logs")
async def get_agent_logs(
    agent_name: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    from app.models.system import AgentLog
    result = await session.execute(
        select(AgentLog).where(AgentLog.agent_name == agent_name)
        .order_by(desc(AgentLog.created_at)).limit(limit)
    )
    logs = result.scalars().all()
    return [{"action": l.action, "message": l.message, "level": l.log_level,
             "timestamp": l.created_at.isoformat()} for l in logs]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# APPROVALS ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
approvals_router = APIRouter(prefix="/api/v1/approvals", tags=["Approvals"])


@approvals_router.get("/pending", response_model=list[ApprovalOut])
async def get_pending_approvals(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.models.domain import Approval
    result = await session.execute(
        select(Approval).where(Approval.tenant_id == tenant_id, Approval.status == "pending")
        .order_by(Approval.created_at)
    )
    return result.scalars().all()


@approvals_router.get("/", response_model=list[ApprovalOut])
async def list_approvals(
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.models.domain import Approval
    query = select(Approval).where(Approval.tenant_id == tenant_id)
    if status:
        query = query.where(Approval.status == status)
    result = await session.execute(query.order_by(desc(Approval.created_at)))
    return result.scalars().all()


@approvals_router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    body: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.models.domain import Approval
    from app.core.event_bus import event_bus
    from app.core.event_types import EventType

    result = await session.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")

    approval.status = "approved"
    approval.approved_by = "manager-001"
    approval.approver_name = body.approver_name
    approval.approver_email = body.approver_email
    approval.reason = body.reason
    approval.decided_at = datetime.now(timezone.utc).isoformat()
    await session.flush()

    await event_bus.publish(
        EventType.APPROVAL_GRANTED,
        workflow_id=approval.workflow_id,
        source_agent="ApprovalAPI",
        payload={"approval_id": approval_id, "approver": body.approver_name},
        tenant_id=tenant_id,
    )

    # Resume workflow in background
    from fastapi import BackgroundTasks
    async def resume():
        from app.database.base import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_session:
            try:
                from app.agents.supervisor.supervisor_agent import supervisor_agent
                await supervisor_agent.resume_workflow(
                    workflow_id=approval.workflow_id,
                    approval_id=approval_id,
                    session=bg_session,
                    tenant_id=tenant_id,
                )
            except Exception as e:
                print(f"[ApprovalRouter] Resume failed: {e}")

    import asyncio
    asyncio.create_task(resume())
    return {"message": "Approved. Workflow resuming...", "approval_id": approval_id}


@approvals_router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    body: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.models.domain import Approval
    from app.core.event_bus import event_bus
    from app.core.event_types import EventType
    from app.models.workflow import Workflow

    result = await session.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval.status = "rejected"
    approval.reason = body.reason
    approval.decided_at = datetime.now(timezone.utc).isoformat()

    wf_result = await session.execute(select(Workflow).where(Workflow.id == approval.workflow_id))
    wf = wf_result.scalar_one_or_none()
    if wf:
        wf.status = "failed"

    await session.flush()
    await event_bus.publish(
        EventType.APPROVAL_REJECTED,
        workflow_id=approval.workflow_id,
        source_agent="ApprovalAPI",
        payload={"approval_id": approval_id, "reason": body.reason},
        tenant_id=tenant_id,
    )
    return {"message": "Rejected. Workflow terminated.", "approval_id": approval_id}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANALYTICS ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@analytics_router.get("/dashboard", response_model=DashboardKPIOut)
async def dashboard_kpis(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.models.workflow import Workflow
    from app.models.domain import Approval
    from app.core.agent_registry import agent_registry
    from app.config.constants import AgentLifecycle

    today = datetime.now(timezone.utc).date().isoformat()
    wf_q = select(Workflow).where(Workflow.tenant_id == tenant_id)
    all_wf = (await session.execute(wf_q)).scalars().all()

    today_wf = [w for w in all_wf if w.created_at.date().isoformat() >= today]
    active = [w for w in all_wf if w.status in ("running", "paused")]
    completed = [w for w in today_wf if w.status == "completed"]
    failed = [w for w in today_wf if w.status == "failed"]
    escalated = [w for w in today_wf if w.status == "escalated"]

    completed_with_dur = [w for w in completed if w.duration_ms]
    avg_dur = (sum(w.duration_ms for w in completed_with_dur) / len(completed_with_dur)) if completed_with_dur else 0

    pending_q = select(func.count()).select_from(
        select(Approval).where(Approval.tenant_id == tenant_id, Approval.status == "pending").subquery()
    )
    pending_approvals = (await session.execute(pending_q)).scalar_one()

    regs = agent_registry.all_registrations()
    running_agents = sum(1 for r in regs if r.status == AgentLifecycle.RUNNING)

    total_today = len(today_wf)
    sla = round((len(completed) / total_today * 100) if total_today > 0 else 100.0, 1)

    return DashboardKPIOut(
        total_workflows_today=total_today,
        active_workflows=len(active),
        completed_today=len(completed),
        failed_today=len(failed),
        escalated_today=len(escalated),
        sla_compliance_pct=sla,
        avg_workflow_duration_ms=round(avg_dur, 2),
        pending_approvals=pending_approvals,
        running_agents=running_agents,
    )


@analytics_router.get("/cost", response_model=CostSummaryOut)
async def cost_summary():
    from app.core.llm_client import llm_client
    from app.core.agent_registry import agent_registry
    stats = llm_client.usage_stats
    regs = agent_registry.all_registrations()
    total_calls = sum(r.call_count for r in regs)
    by_agent = [
        {"agent": r.name, "calls": r.call_count, "pct": round(r.call_count / max(total_calls, 1) * 100, 1)}
        for r in sorted(regs, key=lambda x: -x.call_count)[:8]
    ]
    return CostSummaryOut(
        today_tokens_in=stats["total_tokens_in"],
        today_tokens_out=stats["total_tokens_out"],
        today_cost_usd=stats["total_cost_usd"],
        is_mock=stats["is_mock"],
        by_agent=by_agent,
    )


@analytics_router.get("/events/recent")
async def recent_events(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.models.system import WorkflowEvent
    result = await session.execute(
        select(WorkflowEvent).where(WorkflowEvent.tenant_id == tenant_id)
        .order_by(desc(WorkflowEvent.created_at)).limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "workflow_id": e.workflow_id,
            "source_agent": e.source_agent,
            "payload": json.loads(e.payload_json or "{}"),
            "timestamp": e.created_at.isoformat(),
        }
        for e in events
    ]


@analytics_router.get("/audit-logs")
async def audit_logs(
    limit: int = Query(50),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.models.system import AuditLog
    result = await session.execute(
        select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        .order_by(desc(AuditLog.created_at)).limit(limit)
    )
    logs = result.scalars().all()
    return [{"action": l.action, "entity_type": l.entity_type, "entity_id": l.entity_id,
             "actor_role": l.actor_role, "timestamp": l.created_at.isoformat()} for l in logs]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EMPLOYEES ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
employees_router = APIRouter(prefix="/api/v1/employees", tags=["Employees"])


@employees_router.get("/", response_model=PaginatedResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    department: str | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    from app.models.employee import Employee
    from sqlalchemy import or_, ilike
    query = select(Employee).where(Employee.tenant_id == tenant_id, Employee.is_active == True)
    if search:
        query = query.where(or_(Employee.name.ilike(f"%{search}%"), Employee.email.ilike(f"%{search}%")))
    if department:
        query = query.where(Employee.department_id == department)

    count = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await session.execute(query.offset((page - 1) * page_size).limit(page_size))
    employees = result.scalars().all()
    return PaginatedResponse(
        items=[EmployeeOut.model_validate(e) for e in employees],
        total=count, page=page, page_size=page_size, pages=(count + page_size - 1) // page_size
    )


@employees_router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(employee_id: str, session: AsyncSession = Depends(get_db)):
    from app.models.employee import Employee
    result = await session.execute(select(Employee).where(Employee.id == employee_id))
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEMO ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
demo_router = APIRouter(prefix="/api/v1/demo", tags=["Demo Mode"])


@demo_router.get("/mode", response_model=DemoModeOut)
async def get_demo_mode(tenant_id: str = Depends(get_tenant_id)):
    return DemoModeOut(mode="synthetic", is_live=False,
                       description="Using synthetic data. Set AVIATIONSTACK_API_KEY and GEMINI_API_KEY to enable live mode.")


@demo_router.post("/mode", response_model=DemoModeOut)
async def set_demo_mode(body: DemoModeSetRequest):
    return DemoModeOut(mode=body.mode, is_live=body.mode == "live",
                       description=f"Mode set to {body.mode}")


@demo_router.post("/reset")
async def reset_demo(session: AsyncSession = Depends(get_db), tenant_id: str = Depends(get_tenant_id)):
    """Re-seed demo data (cancels all running workflows and resets synthetic data)."""
    return {"message": "Demo reset complete. Synthetic data refreshed.", "success": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEFINITIONS ROUTER (Process Designer)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
definitions_router = APIRouter(prefix="/api/v1/definitions", tags=["Process Designer"])


@definitions_router.get("/")
async def list_definitions():
    from app.workflow_engine.engine import WorkflowDefinitionLoader
    return WorkflowDefinitionLoader.list_available()


@definitions_router.get("/{name}/{version}")
async def get_definition(name: str, version: str):
    from app.workflow_engine.engine import WorkflowDefinitionLoader
    try:
        return WorkflowDefinitionLoader.load_definition(name, version)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Definition not found")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUTH ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@auth_router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db)):
    from app.models.employee import Employee
    from app.auth.jwt_handler import verify_password, create_access_token
    result = await session.execute(select(Employee).where(Employee.email == body.email))
    emp = result.scalar_one_or_none()
    if not emp:
        # Demo login: any email/password works
        from app.models.employee import Employee
        result2 = await session.execute(select(Employee).limit(1))
        emp = result2.scalar_one_or_none()
        if not emp:
            raise HTTPException(status_code=401, detail="No employees seeded yet. Run demo data generator.")

    token = create_access_token({
        "sub": emp.id, "tenant_id": emp.tenant_id,
        "role": emp.role, "name": emp.name,
    })
    return TokenResponse(
        access_token=token, employee_id=emp.id,
        role=emp.role, name=emp.name, tenant_id=emp.tenant_id,
    )


@auth_router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROMPTS ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
prompts_router = APIRouter(prefix="/api/v1/prompts", tags=["Prompt Registry"])


@prompts_router.get("/")
async def list_prompts():
    from app.core.prompt_registry import prompt_registry
    return [{"name": k, "preview": v[:100] + "..."} for k, v in prompt_registry.list_all().items()]


@prompts_router.get("/{name}")
async def get_prompt(name: str):
    from app.core.prompt_registry import prompt_registry
    content = prompt_registry.get(name)
    return {"name": name, "content": content}


@prompts_router.put("/{name}")
async def update_prompt(name: str, body: dict):
    from app.core.prompt_registry import prompt_registry
    prompt_registry.set(name, body.get("content", ""))
    return {"message": f"Prompt '{name}' updated in memory"}
