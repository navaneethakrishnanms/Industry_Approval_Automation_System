"""
Central model registry — import all models here so SQLAlchemy
discovers them before create_all() is called.
"""
from app.models.tenant import Tenant  # noqa: F401
from app.models.employee import Department, Employee  # noqa: F401
from app.models.workflow import Workflow, WorkflowDefinition, WorkflowStep  # noqa: F401
from app.models.system import (  # noqa: F401
    AgentLog,
    AgentMetrics,
    AgentRegistryEntry,
    AuditLog,
    DemoSetting,
    MemorySnapshot,
    PromptRegistryEntry,
    WorkflowEvent,
)
from app.models.domain import (  # noqa: F401
    Approval,
    Hotel,
    HotelBooking,
    Invoice,
    LeaveRequest,
    Notification,
    TravelRequest,
    VisaRequest,
)

__all__ = [
    "Tenant",
    "Department",
    "Employee",
    "Workflow",
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowEvent",
    "AgentLog",
    "AgentMetrics",
    "AgentRegistryEntry",
    "AuditLog",
    "DemoSetting",
    "MemorySnapshot",
    "PromptRegistryEntry",
    "Approval",
    "Hotel",
    "HotelBooking",
    "Invoice",
    "LeaveRequest",
    "Notification",
    "TravelRequest",
    "VisaRequest",
]
