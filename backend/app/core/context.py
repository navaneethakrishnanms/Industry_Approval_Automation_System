"""
WorkflowContext — the single shared object passed to every agent.
No context is ever lost between steps.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass
class EmployeeRecord:
    id: str
    employee_id: str
    name: str
    email: str
    designation: str
    department: str
    department_id: str
    grade: str
    role: str
    budget_limit: float
    leave_balance: int
    passport_number: str | None = None
    passport_expiry: str | None = None
    manager_id: str | None = None
    manager_name: str | None = None
    manager_email: str | None = None
    phone: str | None = None
    currency: str = "INR"


@dataclass
class WorkflowContext:
    """
    The canonical shared context object.
    Every agent reads from and writes to this object.
    Serialized to JSON and stored in memory_snapshots after each step.
    """

    # ── Identity ──────────────────────────────────────────────────────
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    workflow_type: str = ""
    workflow_version: str = "v1"

    # ── Employee ──────────────────────────────────────────────────────
    employee: EmployeeRecord | None = None

    # ── Raw Request ───────────────────────────────────────────────────
    raw_request: str = ""
    parsed_intent: dict[str, Any] = field(default_factory=dict)

    # ── Travel specifics ──────────────────────────────────────────────
    origin: str = ""
    destination: str = ""
    travel_date: str = ""
    return_date: str = ""
    purpose: str = ""
    class_type: str = "economy"

    # ── Financials ────────────────────────────────────────────────────
    budget_limit: float = 0.0
    approved_budget: float = 0.0
    currency: str = "INR"
    estimated_cost: float = 0.0

    # ── Execution State ───────────────────────────────────────────────
    current_step: int = 0
    total_steps: int = 0
    retry_count: int = 0
    sla_deadline: str = ""

    # ── Accumulated Step Outputs ──────────────────────────────────────
    # step_name → output dict
    step_outputs: dict[str, Any] = field(default_factory=dict)
    previous_errors: list[str] = field(default_factory=list)

    # ── Policy Snapshot ───────────────────────────────────────────────
    policy_snapshot: dict[str, Any] = field(default_factory=dict)

    # ── Validation Results ────────────────────────────────────────────
    employee_validated: bool = False
    passport_valid: bool = True
    budget_approved: bool = False

    # ── Flight / Hotel / Visa / Leave data ────────────────────────────
    flight_options: list[dict] = field(default_factory=list)
    selected_flight: dict | None = None
    hotel_options: list[dict] = field(default_factory=list)
    selected_hotel: dict | None = None
    visa_required: bool = False
    visa_status: str = ""
    leave_days: int = 0
    leave_balance: int = 0

    # ── Approval State ────────────────────────────────────────────────
    approval_id: str | None = None
    approval_level: int = 1
    approval_status: str = "pending"
    approver_name: str = ""
    approver_email: str = ""

    # ── Invoice / Finance ─────────────────────────────────────────────
    invoice_id: str | None = None
    invoice_number: str | None = None

    # ── Notifications ─────────────────────────────────────────────────
    notifications_sent: list[str] = field(default_factory=list)

    # ── Demo Mode ─────────────────────────────────────────────────────
    demo_mode: bool = True

    # ── Metadata ──────────────────────────────────────────────────────
    initiated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict."""
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowContext":
        if data.get("employee") and isinstance(data["employee"], dict):
            data["employee"] = EmployeeRecord(**data["employee"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowContext":
        return cls.from_dict(json.loads(json_str))

    def set_step_output(self, step_name: str, output: dict) -> None:
        """Record step output — called by WorkflowEngine after each step."""
        self.step_outputs[step_name] = output

    def get_step_output(self, step_name: str) -> dict:
        return self.step_outputs.get(step_name, {})

    def add_error(self, error: str) -> None:
        self.previous_errors.append(error)
