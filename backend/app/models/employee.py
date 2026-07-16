"""Employee and Department ORM models."""
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Department(Base):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    head_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # FK to employee set after
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="departments")
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")

    def __repr__(self) -> str:
        return f"<Department {self.name}>"


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # EMP-XXXX
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    grade: Mapped[str] = mapped_column(String(20), default="L3")
    role: Mapped[str] = mapped_column(String(50), default="employee")  # UserRole enum value

    department_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("departments.id"), nullable=True)
    manager_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)

    # Financials
    salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    budget_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=50000)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Leave
    leave_balance: Mapped[int] = mapped_column(Integer, default=21)

    # Travel
    passport_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    passport_expiry: Mapped[str | None] = mapped_column(String(20), nullable=True)  # YYYY-MM-DD

    # Auth
    hashed_password: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Audit
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="employees")
    department: Mapped["Department | None"] = relationship(back_populates="employees")
    manager: Mapped["Employee | None"] = relationship(remote_side="Employee.id", foreign_keys=[manager_id])
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="employee", foreign_keys="Workflow.employee_id")
    travel_requests: Mapped[list["TravelRequest"]] = relationship(back_populates="employee", foreign_keys="TravelRequest.employee_id")
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(back_populates="employee", foreign_keys="LeaveRequest.employee_id")
    visa_requests: Mapped[list["VisaRequest"]] = relationship(back_populates="employee", foreign_keys="VisaRequest.employee_id")

    def __repr__(self) -> str:
        return f"<Employee {self.employee_id} {self.name}>"
