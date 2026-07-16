"""
Event type definitions for the entire system.
Every state transition emits one of these events.
"""
from enum import Enum


class EventType(str, Enum):
    # ── Workflow lifecycle ─────────────────────────────────────────────
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_ESCALATED = "workflow.escalated"
    WORKFLOW_PAUSED = "workflow.paused"         # waiting for human approval
    WORKFLOW_RESUMED = "workflow.resumed"       # approval granted
    WORKFLOW_CANCELLED = "workflow.cancelled"
    WORKFLOW_RETRIED = "workflow.retried"

    # ── Step lifecycle ─────────────────────────────────────────────────
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    STEP_RETRIED = "step.retried"
    STEP_SKIPPED = "step.skipped"

    # ── Agent lifecycle ────────────────────────────────────────────────
    AGENT_ASSIGNED = "agent.assigned"
    AGENT_THINKING = "agent.thinking"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_STATUS_CHANGED = "agent.status_changed"

    # ── Tool calls ────────────────────────────────────────────────────
    TOOL_CALLED = "tool.called"
    TOOL_RETURNED = "tool.returned"
    TOOL_FAILED = "tool.failed"

    # ── Approval ──────────────────────────────────────────────────────
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_REJECTED = "approval.rejected"
    APPROVAL_EXPIRED = "approval.expired"

    # ── Notifications ─────────────────────────────────────────────────
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"

    # ── SLA ───────────────────────────────────────────────────────────
    SLA_WARNING = "sla.warning"
    SLA_BREACHED = "sla.breached"

    # ── System ────────────────────────────────────────────────────────
    DEMO_MODE_CHANGED = "system.demo_mode_changed"
    AGENT_REGISTERED = "system.agent_registered"
