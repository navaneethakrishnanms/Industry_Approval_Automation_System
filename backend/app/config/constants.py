"""
Application-wide constants. Never use magic strings in business logic.
"""
from enum import Enum


# ── Workflow Types ────────────────────────────────────────────────────
class WorkflowType(str, Enum):
    TRAVEL = "travel"
    HOTEL = "hotel"
    VISA = "visa"
    LEAVE = "leave"
    FINANCE = "finance"


# ── Workflow Status ───────────────────────────────────────────────────
class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"          # waiting for human approval
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


# ── Agent Lifecycle States ────────────────────────────────────────────
class AgentLifecycle(str, Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    RUNNING = "running"
    WAITING = "waiting"        # human approval pause
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    ESCALATED = "escalated"


# ── Step Status ───────────────────────────────────────────────────────
class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


# ── Approval Status ───────────────────────────────────────────────────
class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ── Approval Level ────────────────────────────────────────────────────
class ApprovalLevel(int, Enum):
    MANAGER = 1
    FINANCE = 2
    EXECUTIVE = 3


# ── User Roles ────────────────────────────────────────────────────────
class UserRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR_ADMIN = "hr_admin"
    FINANCE_ADMIN = "finance_admin"
    SYSTEM_ADMIN = "system_admin"


# ── Notification Channels ─────────────────────────────────────────────
class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    IN_APP = "in_app"


# ── Leave Types ───────────────────────────────────────────────────────
class LeaveType(str, Enum):
    ANNUAL = "annual"
    SICK = "sick"
    EMERGENCY = "emergency"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    UNPAID = "unpaid"


# ── Visa Types ────────────────────────────────────────────────────────
class VisaType(str, Enum):
    BUSINESS = "business"
    TOURIST = "tourist"
    TRANSIT = "transit"
    WORK = "work"


# ── Invoice Status ────────────────────────────────────────────────────
class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"


# ── Demo Mode ─────────────────────────────────────────────────────────
class DemoMode(str, Enum):
    LIVE = "live"
    SYNTHETIC = "synthetic"


# ── On-Failure Strategies ─────────────────────────────────────────────
class FailureStrategy(str, Enum):
    RETRY = "retry"
    ESCALATE = "escalate"
    ABORT = "abort"
    SKIP = "skip"
    LOG = "log"


# ── Known Agent Names ─────────────────────────────────────────────────
class AgentName(str, Enum):
    SUPERVISOR = "SupervisorAgent"
    VALIDATION = "ValidationAgent"
    POLICY = "PolicyAgent"
    TRAVEL = "TravelAgent"
    HOTEL = "HotelAgent"
    VISA = "VisaAgent"
    LEAVE = "LeaveAgent"
    FINANCE = "FinanceAgent"
    HR = "HRAgent"
    NOTIFICATION = "NotificationAgent"
    AUDIT = "AuditAgent"
    APPROVAL = "ApprovalAgent"
    REPORTING = "ReportingAgent"
    DOCUMENT = "DocumentAgent"
    ANALYTICS = "AnalyticsAgent"


# ── SLA Defaults (hours) ─────────────────────────────────────────────
SLA_DEFAULTS = {
    WorkflowType.TRAVEL: 24,
    WorkflowType.HOTEL: 12,
    WorkflowType.VISA: 72,
    WorkflowType.LEAVE: 48,
    WorkflowType.FINANCE: 24,
}

# ── System Settings ───────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_RETRY_LIMIT = 3
DEFAULT_APPROVAL_TIMEOUT_HOURS = 48
TOKEN_COST_PER_1K_INPUT = 0.00015   # Gemini Flash pricing
TOKEN_COST_PER_1K_OUTPUT = 0.00060
