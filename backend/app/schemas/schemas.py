"""
Pydantic v2 schemas — request/response contracts for all API endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ── Workflow Schemas ──────────────────────────────────────────────────
class StartWorkflowRequest(BaseModel):
    message: str = Field(..., description="Natural language request from the employee", min_length=5)
    employee_id: str = Field(..., description="UUID of the requesting employee")
    demo_mode: bool = Field(True, description="Use synthetic data if True")


class WorkflowStepOut(BaseModel):
    id: str
    step_index: int
    step_name: str
    agent_name: str
    status: str
    confidence_score: float | None
    duration_ms: int | None
    reasoning: str | None
    started_at: str | None
    completed_at: str | None
    output: dict | None = None

    class Config:
        from_attributes = True


class WorkflowOut(BaseModel):
    id: str
    workflow_type: str
    status: str
    definition_name: str
    definition_version: str
    employee_id: str | None
    tenant_id: str
    current_step: int
    total_steps: int
    retry_count: int
    raw_request: str | None
    sla_deadline: str | None
    started_at: str | None
    completed_at: str | None
    duration_ms: int | None
    error_message: str | None
    created_at: datetime
    steps: list[WorkflowStepOut] = []

    class Config:
        from_attributes = True


class WorkflowListItem(BaseModel):
    id: str
    workflow_type: str
    status: str
    employee_id: str | None
    current_step: int
    total_steps: int
    sla_deadline: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class StartWorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str
    workflow_type: str
    intent: dict


# ── Agent Schemas ─────────────────────────────────────────────────────
class AgentCardOut(BaseModel):
    name: str
    description: str
    status: str
    capabilities: list[str]
    tools: list[str]
    version: str
    owner: str
    call_count: int
    success_rate: float
    avg_response_ms: float
    last_active: str | None


class AgentHealthOut(BaseModel):
    total_agents: int
    idle: int
    running: int
    failed: int
    agents: list[AgentCardOut]


# ── Approval Schemas ──────────────────────────────────────────────────
class ApprovalOut(BaseModel):
    id: str
    workflow_id: str
    level: int
    requested_from_role: str
    status: str
    summary: str | None
    requested_at: str | None
    expires_at: str | None
    approver_name: str | None
    decided_at: str | None
    tenant_id: str

    class Config:
        from_attributes = True


class ApprovalDecisionRequest(BaseModel):
    reason: str | None = None
    approver_name: str = "Manager"
    approver_email: str | None = None


# ── Employee Schemas ──────────────────────────────────────────────────
class EmployeeOut(BaseModel):
    id: str
    employee_id: str
    name: str
    email: str
    designation: str
    grade: str
    role: str
    department_id: str | None
    budget_limit: float
    leave_balance: int
    is_active: bool

    class Config:
        from_attributes = True


# ── Analytics / Dashboard Schemas ─────────────────────────────────────
class DashboardKPIOut(BaseModel):
    total_workflows_today: int
    active_workflows: int
    completed_today: int
    failed_today: int
    escalated_today: int
    sla_compliance_pct: float
    avg_workflow_duration_ms: float
    pending_approvals: int
    running_agents: int


class AgentMetricsOut(BaseModel):
    agent_name: str
    total_calls: int
    success_count: int
    failure_count: int
    avg_latency_ms: float
    success_rate: float
    token_input: int
    token_output: int
    cost_usd: float


class CostSummaryOut(BaseModel):
    today_tokens_in: int
    today_tokens_out: int
    today_cost_usd: float
    is_mock: bool
    by_agent: list[dict]


# ── Event / Log Schemas ───────────────────────────────────────────────
class EventOut(BaseModel):
    id: str
    event_type: str
    workflow_id: str | None
    source_agent: str | None
    payload: dict
    tenant_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationTurnOut(BaseModel):
    role: str
    agent: str
    message: str
    created_at: str | None = None


# ── Demo Mode Schemas ─────────────────────────────────────────────────
class DemoModeOut(BaseModel):
    mode: str
    is_live: bool
    description: str


class DemoModeSetRequest(BaseModel):
    mode: str = Field(..., pattern="^(live|synthetic)$")


# ── Workflow Definition Schemas ───────────────────────────────────────
class WorkflowDefinitionOut(BaseModel):
    name: str
    version: str
    description: str
    sla_hours: int
    steps: list[dict]


# ── Pagination ────────────────────────────────────────────────────────
class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ── Standard Response ─────────────────────────────────────────────────
class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ── Auth Schemas ──────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee_id: str
    role: str
    name: str
    tenant_id: str


class TokenData(BaseModel):
    employee_id: str | None = None
    tenant_id: str | None = None
    role: str | None = None
