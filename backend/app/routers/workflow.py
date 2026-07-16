"""
Workflow Router — start, monitor, retry, and manage workflows.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import get_current_user, get_tenant_id
from app.database.base import get_db
from app.models.workflow import Workflow, WorkflowStep
from app.schemas.schemas import (
    StartWorkflowRequest, StartWorkflowResponse,
    WorkflowOut, WorkflowListItem, WorkflowStepOut, MessageResponse, PaginatedResponse
)

router = APIRouter(prefix="/api/v1/workflow", tags=["Workflow"])


@router.post("/start", response_model=StartWorkflowResponse)
async def start_workflow(
    request: StartWorkflowRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Start a new workflow from a natural language request.
    The Supervisor Agent parses intent and begins orchestration.
    """
    from app.agents.supervisor.supervisor_agent import supervisor_agent

    # Parse intent first for immediate response
    intent = await supervisor_agent._parse_intent(request.message)
    workflow_type = intent.get("workflow_type", "travel")

    # Build initial workflow record ID for immediate response
    import uuid
    workflow_id = str(uuid.uuid4())

    # Run the full workflow in the background so WebSocket can stream updates
    async def run_in_background():
        from app.database.base import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_session:
            try:
                # Override the workflow_id
                from app.core.context import WorkflowContext
                ctx = await supervisor_agent.start_workflow(
                    raw_request=request.message,
                    employee_id=request.employee_id,
                    session=bg_session,
                    tenant_id=tenant_id,
                    demo_mode=request.demo_mode,
                )
            except Exception as e:
                print(f"[WorkflowRouter] Background execution error: {e}")

    background_tasks.add_task(run_in_background)

    return StartWorkflowResponse(
        workflow_id=workflow_id,
        status="started",
        message=f"Supervisor Agent activated. Processing {workflow_type} request...",
        workflow_type=workflow_type,
        intent=intent,
    )


@router.post("/start/sync", response_model=dict)
async def start_workflow_sync(
    request: StartWorkflowRequest,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Synchronous workflow start — waits for completion.
    Use for demo scenarios where you want to see full output.
    """
    from app.agents.supervisor.supervisor_agent import supervisor_agent
    ctx = await supervisor_agent.start_workflow(
        raw_request=request.message,
        employee_id=request.employee_id,
        session=session,
        tenant_id=tenant_id,
        demo_mode=request.demo_mode,
    )
    return {
        "workflow_id": ctx.workflow_id,
        "status": "completed",
        "workflow_type": ctx.workflow_type,
        "step_outputs": ctx.step_outputs,
        "selected_flight": ctx.selected_flight,
        "selected_hotel": ctx.selected_hotel,
        "invoice_number": ctx.invoice_number,
    }


@router.get("/", response_model=PaginatedResponse)
async def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    workflow_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """List all workflows with pagination and filtering."""
    query = select(Workflow).where(Workflow.tenant_id == tenant_id)
    if status:
        query = query.where(Workflow.status == status)
    if workflow_type:
        query = query.where(Workflow.workflow_type == workflow_type)

    count_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.order_by(desc(Workflow.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    workflows = result.scalars().all()

    items = [WorkflowListItem.model_validate(w) for w in workflows]
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/{workflow_id}", response_model=dict)
async def get_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get full workflow status with steps."""
    result = await session.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps_result = await session.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.step_index)
    )
    steps = steps_result.scalars().all()

    return {
        "id": wf.id,
        "workflow_type": wf.workflow_type,
        "status": wf.status,
        "current_step": wf.current_step,
        "total_steps": wf.total_steps,
        "raw_request": wf.raw_request,
        "sla_deadline": wf.sla_deadline,
        "started_at": wf.started_at,
        "completed_at": wf.completed_at,
        "created_at": wf.created_at.isoformat(),
        "steps": [
            {
                "step_name": s.step_name,
                "agent_name": s.agent_name,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "confidence_score": s.confidence_score,
                "reasoning": s.reasoning,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
            }
            for s in steps
        ],
    }


@router.get("/{workflow_id}/events")
async def get_workflow_events(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get all events for a specific workflow."""
    from app.models.system import WorkflowEvent
    result = await session.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.workflow_id == workflow_id)
        .order_by(WorkflowEvent.created_at)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "source_agent": e.source_agent,
            "payload": json.loads(e.payload_json or "{}"),
            "timestamp": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/{workflow_id}/conversation")
async def get_conversation(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get full agent conversation history for this workflow."""
    from app.core.memory_manager import memory_manager
    turns = await memory_manager.get_conversation_history(session, workflow_id)
    return {"workflow_id": workflow_id, "turns": turns}


@router.post("/{workflow_id}/retry")
async def retry_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Retry a failed workflow."""
    result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status not in ("failed", "escalated"):
        raise HTTPException(status_code=400, detail=f"Cannot retry workflow in status: {wf.status}")

    from app.core.event_bus import event_bus
    from app.core.event_types import EventType
    await event_bus.publish(EventType.WORKFLOW_RETRIED, workflow_id=workflow_id,
                            source_agent="API", tenant_id=tenant_id)
    return {"message": "Workflow retry initiated", "workflow_id": workflow_id}


@router.delete("/{workflow_id}", response_model=MessageResponse)
async def cancel_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Cancel a running or paused workflow."""
    result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    wf.status = "cancelled"
    await session.flush()
    return MessageResponse(message=f"Workflow {workflow_id[:8]} cancelled")
