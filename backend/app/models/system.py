"""Event, AgentLog, MemorySnapshot, and DemoSetting models."""
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class WorkflowEvent(Base):
    """Every state transition emits an event — the backbone of observability."""
    __tablename__ = "workflow_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True, index=True)
    source_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    broadcast_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    workflow: Mapped["Workflow | None"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return f"<Event {self.event_type}>"


class AgentLog(Base):
    """Fine-grained log entry from any agent during execution."""
    __tablename__ = "agent_logs"

    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True, index=True)
    step_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflow_steps.id"), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    log_level: Mapped[str] = mapped_column(String(20), default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    workflow: Mapped["Workflow | None"] = relationship(back_populates="agent_logs")

    def __repr__(self) -> str:
        return f"<AgentLog {self.agent_name} {self.action}>"


class MemorySnapshot(Base):
    """Persisted memory for workflow context, outputs, and conversation."""
    __tablename__ = "memory_snapshots"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: "workflow_context" | "agent_output" | "conversation" | "execution_trace"
    step_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="memory_snapshots")


class AgentRegistryEntry(Base):
    """DB-backed snapshot of the agent registry (for dashboard display)."""
    __tablename__ = "agent_registry"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    tools_json: Mapped[str] = mapped_column(Text, default="[]")
    permissions_json: Mapped[str] = mapped_column(Text, default="[]")
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="idle")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Live metrics
    avg_response_ms: Mapped[float] = mapped_column(Float, default=0.0)
    success_rate: Mapped[float] = mapped_column(Float, default=100.0)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PromptRegistryEntry(Base):
    """Database-backed prompt library — update prompts without code changes."""
    __tablename__ = "prompt_registry"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AuditLog(Base):
    """Immutable audit trail for every mutating action."""
    __tablename__ = "audit_logs"

    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentMetrics(Base):
    """Aggregated per-agent observability metrics."""
    __tablename__ = "agent_metrics"

    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    period_date: Mapped[str] = mapped_column(String(20), nullable=False)  # YYYY-MM-DD

    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    token_input: Mapped[int] = mapped_column(Integer, default=0)
    token_output: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cache_hits: Mapped[int] = mapped_column(Integer, default=0)
    sla_breaches: Mapped[int] = mapped_column(Integer, default=0)


class DemoSetting(Base):
    """Per-tenant Demo Mode toggle (live API vs synthetic data)."""
    __tablename__ = "demo_settings"

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), unique=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="synthetic")  # live | synthetic
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="demo_setting")

    def __repr__(self) -> str:
        return f"<DemoSetting tenant={self.tenant_id} mode={self.mode}>"
