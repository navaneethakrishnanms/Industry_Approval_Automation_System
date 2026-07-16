"""Travel, Hotel, Visa, Leave, Finance, Approval, Notification models."""
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


# ── Travel ────────────────────────────────────────────────────────────
class TravelRequest(Base):
    __tablename__ = "travel_requests"

    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)

    origin: Mapped[str] = mapped_column(String(100), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    travel_date: Mapped[str] = mapped_column(String(20), nullable=False)
    return_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Flight details (post-booking)
    flight_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    airline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    booking_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    class_type: Mapped[str] = mapped_column(String(20), default="economy")
    departure_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    arrival_time: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    employee: Mapped["Employee | None"] = relationship(back_populates="travel_requests")


# ── Hotel ─────────────────────────────────────────────────────────────
class Hotel(Base):
    __tablename__ = "hotels"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=3.0)
    stars: Mapped[int] = mapped_column(Integer, default=3)
    price_per_night: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    available_rooms: Mapped[int] = mapped_column(Integer, default=10)
    amenities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    bookings: Mapped[list["HotelBooking"]] = relationship(back_populates="hotel")


class HotelBooking(Base):
    __tablename__ = "hotel_bookings"

    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True)
    hotel_id: Mapped[str] = mapped_column(String(36), ForeignKey("hotels.id"), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    check_in: Mapped[str] = mapped_column(String(20), nullable=False)
    check_out: Mapped[str] = mapped_column(String(20), nullable=False)
    nights: Mapped[int] = mapped_column(Integer, default=1)
    price_total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    booking_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Relationships
    hotel: Mapped["Hotel"] = relationship(back_populates="bookings")


# ── Visa ──────────────────────────────────────────────────────────────
class VisaRequest(Base):
    __tablename__ = "visa_requests"

    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    destination_country: Mapped[str] = mapped_column(String(100), nullable=False)
    visa_type: Mapped[str] = mapped_column(String(50), default="business")
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    travel_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, default=7)

    status: Mapped[str] = mapped_column(String(50), default="pending")
    submitted_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    documents_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    passport_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    employee: Mapped["Employee | None"] = relationship(back_populates="visa_requests")


# ── Leave ─────────────────────────────────────────────────────────────
class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    leave_type: Mapped[str] = mapped_column(String(50), default="annual")
    start_date: Mapped[str] = mapped_column(String(20), nullable=False)
    end_date: Mapped[str] = mapped_column(String(20), nullable=False)
    days_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    hr_updated: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    employee: Mapped["Employee | None"] = relationship(back_populates="leave_requests")


# ── Finance ───────────────────────────────────────────────────────────
class Invoice(Base):
    __tablename__ = "invoices"

    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # travel, hotel, visa, etc.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    paid_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    budget_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ── Approval ──────────────────────────────────────────────────────────
class Approval(Base):
    __tablename__ = "approvals"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)
    step_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflow_steps.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    level: Mapped[int] = mapped_column(Integer, default=1)  # 1=manager, 2=finance, 3=exec
    requested_from_role: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(36), nullable=True)  # Agent or employee
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approver_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approver_email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="pending")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI-generated summary

    requested_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decided_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="approvals")


# ── Notification ──────────────────────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # email|sms|slack|in_app
    recipient_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    sent_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)  # Always mock for prototype
