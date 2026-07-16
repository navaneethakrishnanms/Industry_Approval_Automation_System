"""Tenant model — multi-tenant SaaS isolation."""
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="enterprise")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    employees: Mapped[list["Employee"]] = relationship(back_populates="tenant")
    departments: Mapped[list["Department"]] = relationship(back_populates="tenant")
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="tenant")
    demo_setting: Mapped["DemoSetting"] = relationship(back_populates="tenant", uselist=False)

    def __repr__(self) -> str:
        return f"<Tenant {self.name}>"
