"""Workflow, WorkflowStep, WorkflowDefinition ORM models."""
import json

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class WorkflowDefinition(Base):
    """Versioned JSON workflow definitions — loaded by the engine at runtime."""
    __tablename__ = "workflow_definitions"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    definition_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True)

    @property
    def definition(self) -> dict:
        return json.loads(self.definition_json)

    def __repr__(self) -> str:
        return f"<WorkflowDefinition {self.name} {self.version}>"


class Workflow(Base):
    """A single execution instance of a workflow."""
    __tablename__ = "workflows"

    workflow_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    definition_name: Mapped[str] = mapped_column(String(100), nullable=False)
    definition_version: Mapped[str] = mapped_column(String(20), default="v1")

    # Relations
    employee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    initiated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)

    # Execution state
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Context & data
    raw_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_intent: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON
    context_json: Mapped[str | None] = mapped_column(Text, nullable=True)    # Full WorkflowContext JSON

    # SLA
    sla_deadline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Audit
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="workflows")
    employee: Mapped["Employee | None"] = relationship(back_populates="workflows", foreign_keys=[employee_id])
    steps: Mapped[list["WorkflowStep"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    events: Mapped[list["WorkflowEvent"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    agent_logs: Mapped[list["AgentLog"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    memory_snapshots: Mapped[list["MemorySnapshot"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Workflow {self.id[:8]} {self.workflow_type} {self.status}>"


class WorkflowStep(Base):
    """Individual step execution record within a workflow."""
    __tablename__ = "workflow_steps"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # IO
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Quality
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="steps")

    def __repr__(self) -> str:
        return f"<WorkflowStep {self.step_name} {self.status}>"
