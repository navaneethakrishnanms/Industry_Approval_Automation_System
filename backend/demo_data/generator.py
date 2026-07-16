"""
Synthetic Data Generator — creates realistic enterprise data.

Generates:
- 2 tenants
- 10 departments
- 500 employees (with managers, passports, budgets)
- 300 travel requests
- 100 hotels
- 100 visa requests
- 200 leave requests
- 500 invoices
- Default prompts
- Demo agent registry entries
"""
from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import UserRole
from app.database.base import AsyncSessionLocal, create_all_tables
from app.models import *  # noqa: imports all models for SQLAlchemy

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

# ── Constants ─────────────────────────────────────────────────────────
DEPARTMENTS = [
    ("Engineering", "ENG"), ("Finance", "FIN"), ("Human Resources", "HR"),
    ("Marketing", "MKT"), ("Operations", "OPS"), ("Sales", "SLS"),
    ("Legal", "LEG"), ("IT", "IT"), ("Administration", "ADM"), ("Product", "PRD"),
]

DESIGNATIONS = {
    "employee": ["Software Engineer", "Analyst", "Associate", "Executive", "Specialist"],
    "manager": ["Senior Manager", "Manager", "Team Lead", "Principal Engineer", "Director"],
    "hr_admin": ["HR Manager", "HR Business Partner", "Talent Manager"],
    "finance_admin": ["Finance Manager", "Senior Accountant", "CFO", "Financial Analyst"],
    "system_admin": ["CTO", "CEO", "COO", "VP Engineering"],
}

GRADES = ["L1", "L2", "L3", "L4", "L5", "L6"]

AIRLINES = ["Air India", "Emirates", "IndiGo", "Vistara", "SpiceJet", "GoFirst", "Flydubai"]
CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Dubai", "Singapore", "London", "New York", "Tokyo"]
LEAVE_TYPES = ["annual", "sick", "emergency", "maternity", "unpaid"]
VISA_TYPES = ["business", "tourist", "transit"]
COUNTRIES = ["UAE", "USA", "UK", "Singapore", "Japan", "Germany", "France", "Australia"]

TENANT_1_ID = "tenant-globaltech-001"
TENANT_2_ID = "tenant-acme-001"


async def generate_all():
    """Master generator — runs all seeding steps."""
    print("[..] Creating database tables...")
    await create_all_tables()

    async with AsyncSessionLocal() as session:
        print("[..] Seeding tenants...")
        tenants = await seed_tenants(session)

        print("[..] Seeding departments...")
        departments = await seed_departments(session, tenants)

        print("[..] Seeding employees (500)...")
        employees = await seed_employees(session, tenants, departments)

        print("[..] Seeding travel requests (300)...")
        await seed_travel_requests(session, employees, tenants)

        print("[..] Seeding hotels (100)...")
        await seed_hotels(session, tenants)

        print("[..] Seeding visa requests (100)...")
        await seed_visa_requests(session, employees, tenants)

        print("[..] Seeding leave requests (200)...")
        await seed_leave_requests(session, employees, tenants)

        print("[..] Seeding invoices (500)...")
        await seed_invoices(session, employees, tenants)

        print("[..] Seeding prompt registry...")
        await seed_prompts(session)

        print("[..] Seeding agent registry snapshots...")
        await seed_agent_registry(session, tenants)

        print("[..] Seeding demo settings...")
        await seed_demo_settings(session, tenants)

        await session.commit()

    print("\n[OK] Synthetic data generation complete!")
    print(f"   Tenants: 2 | Departments: 10 | Employees: 500")
    print(f"   Travel: 300 | Hotels: 100 | Visas: 100 | Leave: 200 | Invoices: 500")


async def seed_tenants(session: AsyncSession) -> list:
    from app.models.tenant import Tenant
    tenants = [
        Tenant(id=TENANT_1_ID, name="GlobalTech Corp", domain="globaltech.com", plan="enterprise", is_active=True),
        Tenant(id=TENANT_2_ID, name="Acme Industries", domain="acme.com", plan="enterprise", is_active=True),
    ]
    session.add_all(tenants)
    await session.flush()
    return tenants


async def seed_departments(session: AsyncSession, tenants: list) -> list:
    from app.models.employee import Department
    all_depts = []
    for tenant in tenants:
        for name, code in DEPARTMENTS:
            dept = Department(
                id=str(uuid.uuid4()),
                name=name, code=f"{code}-{tenant.id[:4].upper()}",
                budget=Decimal(random.randint(500000, 5000000)),
                tenant_id=tenant.id,
            )
            session.add(dept)
            all_depts.append((dept, tenant))
    await session.flush()
    return all_depts


async def seed_employees(session: AsyncSession, tenants: list, departments: list) -> list:
    from app.models.employee import Employee
    from app.auth.jwt_handler import hash_password

    all_employees = []
    emp_counter = 1

    for tenant in tenants:
        tenant_depts = [d for d, t in departments if t.id == tenant.id]
        managers = []

        # Create 10 managers first
        for i, dept in enumerate(tenant_depts):
            mgr = Employee(
                id=str(uuid.uuid4()),
                employee_id=f"EMP-{emp_counter:04d}",
                name=fake.name(),
                email=f"mgr{emp_counter}@{tenant.domain}",
                phone=fake.phone_number()[:15],
                designation=random.choice(DESIGNATIONS["manager"]),
                grade=random.choice(["L4", "L5", "L6"]),
                role=UserRole.MANAGER,
                department_id=dept.id,
                tenant_id=tenant.id,
                salary=Decimal(random.randint(150000, 300000)),
                budget_limit=Decimal(random.randint(50000, 150000)),
                leave_balance=random.randint(15, 25),
                passport_number=f"P{random.randint(1000000, 9999999)}",
                passport_expiry=(datetime.now() + timedelta(days=random.randint(365, 1825))).strftime("%Y-%m-%d"),
                hashed_password=hash_password("demo123"),
                is_active=True,
            )
            session.add(mgr)
            managers.append(mgr)
            emp_counter += 1

        # Create 240 regular employees per tenant
        for i in range(240):
            dept = random.choice(tenant_depts)
            mgr = random.choice(managers)
            role = random.choice(["employee", "employee", "employee", "hr_admin", "finance_admin"])
            desig_list = DESIGNATIONS.get(role, DESIGNATIONS["employee"])
            emp = Employee(
                id=str(uuid.uuid4()),
                employee_id=f"EMP-{emp_counter:04d}",
                name=fake.name(),
                email=f"emp{emp_counter}@{tenant.domain}",
                phone=fake.phone_number()[:15],
                designation=random.choice(desig_list),
                grade=random.choice(GRADES),
                role=role,
                department_id=dept.id,
                manager_id=mgr.id,
                tenant_id=tenant.id,
                salary=Decimal(random.randint(50000, 150000)),
                budget_limit=Decimal(random.randint(20000, 60000)),
                leave_balance=random.randint(5, 25),
                passport_number=f"P{random.randint(1000000, 9999999)}" if random.random() > 0.1 else None,
                passport_expiry=(datetime.now() + timedelta(days=random.randint(-30, 1825))).strftime("%Y-%m-%d") if random.random() > 0.05 else None,
                hashed_password=hash_password("demo123"),
                is_active=True,
            )
            session.add(emp)
            all_employees.append((emp, tenant, mgr))
            emp_counter += 1

        # Add admin user for each tenant
        admin = Employee(
            id=str(uuid.uuid4()),
            employee_id=f"EMP-ADMIN-{tenant.id[:4].upper()}",
            name=f"Admin {tenant.name}",
            email=f"admin@{tenant.domain}",
            designation="System Administrator",
            grade="L6",
            role=UserRole.SYSTEM_ADMIN,
            department_id=tenant_depts[0].id,
            tenant_id=tenant.id,
            salary=Decimal(500000),
            budget_limit=Decimal(500000),
            leave_balance=21,
            hashed_password=hash_password("admin123"),
            is_active=True,
        )
        session.add(admin)

    await session.flush()
    return all_employees


async def seed_travel_requests(session: AsyncSession, employees: list, tenants: list):
    from app.models.domain import TravelRequest
    statuses = ["pending", "approved", "completed", "rejected", "cancelled"]
    class_types = ["economy", "economy", "economy", "business"]

    for _ in range(300):
        emp, tenant, mgr = random.choice(employees)
        origin = random.choice(["MAA", "BOM", "DEL", "BLR"])
        dest = random.choice(CITIES)
        travel_date = datetime.now() + timedelta(days=random.randint(-90, 90))
        airline = random.choice(AIRLINES)

        tr = TravelRequest(
            id=str(uuid.uuid4()),
            employee_id=emp.id,
            tenant_id=tenant.id,
            origin=origin,
            destination=dest,
            travel_date=travel_date.strftime("%Y-%m-%d"),
            return_date=(travel_date + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d"),
            purpose=random.choice(["Client Meeting", "Conference", "Training", "Site Visit", "Business Development"]),
            flight_number=f"{airline[:2].upper()}{random.randint(100, 999)}",
            airline=airline,
            price=Decimal(random.randint(8000, 45000)),
            currency="INR",
            booking_ref=f"BK{str(uuid.uuid4())[:8].upper()}" if random.random() > 0.3 else None,
            status=random.choice(statuses),
            class_type=random.choice(class_types),
            departure_time=f"{random.randint(5, 22):02d}:{random.choice(['00', '15', '30', '45'])}",
            arrival_time=f"{random.randint(5, 23):02d}:{random.choice(['00', '15', '30', '45'])}",
        )
        session.add(tr)
    await session.flush()


async def seed_hotels(session: AsyncSession, tenants: list):
    from app.models.domain import Hotel
    hotel_brands = ["Marriott", "Hilton", "Hyatt", "ITC", "Taj", "Radisson", "Le Méridien", "Sheraton", "Westin", "Four Seasons"]

    for city in CITIES:
        for _ in range(10):
            stars = random.randint(3, 5)
            hotel = Hotel(
                id=str(uuid.uuid4()),
                name=f"{random.choice(hotel_brands)} {city}",
                city=city,
                country=random.choice(COUNTRIES),
                rating=round(random.uniform(3.5, 4.9), 1),
                stars=stars,
                price_per_night=Decimal(random.randint(3000, 20000)),
                currency="INR",
                available_rooms=random.randint(5, 50),
                amenities_json=json.dumps(random.sample(
                    ["WiFi", "Pool", "Gym", "Spa", "Restaurant", "Bar", "Parking", "Business Centre", "Breakfast"], k=4
                )),
            )
            session.add(hotel)
    await session.flush()


async def seed_visa_requests(session: AsyncSession, employees: list, tenants: list):
    from app.models.domain import VisaRequest
    statuses = ["pending", "approved", "rejected", "in_progress"]
    for _ in range(100):
        emp, tenant, mgr = random.choice(employees)
        vr = VisaRequest(
            id=str(uuid.uuid4()),
            employee_id=emp.id,
            tenant_id=tenant.id,
            destination_country=random.choice(COUNTRIES),
            visa_type=random.choice(VISA_TYPES),
            purpose=random.choice(["Business Meeting", "Conference", "Training", "Client Visit"]),
            travel_date=(datetime.now() + timedelta(days=random.randint(15, 120))).strftime("%Y-%m-%d"),
            duration_days=random.randint(3, 30),
            status=random.choice(statuses),
            submitted_at=(datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).isoformat(),
            documents_verified=random.random() > 0.2,
            passport_valid=random.random() > 0.05,
            tracking_number=f"VIS-{str(uuid.uuid4())[:8].upper()}",
        )
        session.add(vr)
    await session.flush()


async def seed_leave_requests(session: AsyncSession, employees: list, tenants: list):
    from app.models.domain import LeaveRequest
    statuses = ["pending", "approved", "rejected", "cancelled"]
    for _ in range(200):
        emp, tenant, mgr = random.choice(employees)
        start = datetime.now() + timedelta(days=random.randint(-60, 60))
        days = random.randint(1, 14)
        lr = LeaveRequest(
            id=str(uuid.uuid4()),
            employee_id=emp.id,
            tenant_id=tenant.id,
            leave_type=random.choice(LEAVE_TYPES),
            start_date=start.strftime("%Y-%m-%d"),
            end_date=(start + timedelta(days=days)).strftime("%Y-%m-%d"),
            days_count=days,
            reason=random.choice(["Family function", "Medical", "Personal", "Vacation", "Emergency"]),
            status=random.choice(statuses),
            approved_by=mgr.id if random.random() > 0.3 else None,
        )
        session.add(lr)
    await session.flush()


async def seed_invoices(session: AsyncSession, employees: list, tenants: list):
    from app.models.domain import Invoice
    categories = ["travel", "hotel", "visa", "training", "equipment", "meals", "conference"]
    statuses = ["draft", "submitted", "approved", "paid", "rejected"]
    for i in range(500):
        emp, tenant, mgr = random.choice(employees)
        inv = Invoice(
            id=str(uuid.uuid4()),
            employee_id=emp.id,
            tenant_id=tenant.id,
            invoice_number=f"INV-2026-{i+1:05d}",
            amount=Decimal(random.randint(500, 100000)),
            currency="INR",
            category=random.choice(categories),
            description=fake.sentence(nb_words=6),
            status=random.choice(statuses),
            due_date=(datetime.now() + timedelta(days=random.randint(-30, 60))).strftime("%Y-%m-%d"),
        )
        session.add(inv)
    await session.flush()


async def seed_prompts(session: AsyncSession):
    from app.core.prompt_registry import prompt_registry
    await prompt_registry.seed_defaults_to_db(session)


async def seed_agent_registry(session: AsyncSession, tenants: list):
    from app.models.system import AgentRegistryEntry
    agent_names = [
        ("SupervisorAgent", ["orchestrate", "parse_intent"], ["workflow_engine"], "platform"),
        ("ValidationAgent", ["validate_employee", "validate_passport"], ["db_query"], "hr"),
        ("PolicyAgent", ["check_policy", "retrieve_policy"], ["chroma_search"], "compliance"),
        ("TravelAgent", ["search_flights", "book_flight"], ["search_flights", "book_flight"], "travel_desk"),
        ("HotelAgent", ["search_hotels", "book_hotel"], ["search_hotels"], "travel_desk"),
        ("LeaveAgent", ["check_leave_balance", "process_leave"], ["check_balance"], "hr"),
        ("FinanceAgent", ["check_budget", "create_invoice"], ["check_budget", "create_invoice"], "finance"),
        ("HRAgent", ["update_leave_record", "update_calendar"], ["hr_system_api"], "hr"),
        ("ApprovalAgent", ["request_approval", "check_approval_status"], ["approval_db"], "platform"),
        ("NotificationAgent", ["send_email", "send_sms", "send_slack"], ["email_mock", "sms_mock", "slack_mock"], "platform"),
        ("AuditAgent", ["create_audit_log", "summarize_workflow"], ["audit_db"], "compliance"),
        ("DocumentAgent", ["verify_passport", "verify_documents"], ["doc_store"], "hr"),
        ("VisaAgent", ["process_visa", "track_visa_status"], ["visa_portal_api"], "travel_desk"),
        ("ReportingAgent", ["generate_report"], ["report_engine"], "analytics"),
        ("AnalyticsAgent", ["analyze_sla", "forecast"], ["metrics_db"], "analytics"),
    ]
    for name, caps, tools, owner in agent_names:
        entry = AgentRegistryEntry(
            id=str(uuid.uuid4()),
            name=name,
            version="1.0.0",
            capabilities_json=json.dumps(caps),
            tools_json=json.dumps(tools),
            permissions_json=json.dumps(["read:*"]),
            owner=owner,
            status="idle",
            description=f"{name} — enterprise AI agent",
            avg_response_ms=round(random.uniform(200, 1500), 2),
            success_rate=round(random.uniform(94, 99.9), 1),
            call_count=random.randint(50, 2000),
        )
        session.add(entry)
    await session.flush()


async def seed_demo_settings(session: AsyncSession, tenants: list):
    from app.models.system import DemoSetting
    for tenant in tenants:
        setting = DemoSetting(id=str(uuid.uuid4()), tenant_id=tenant.id, mode="synthetic")
        session.add(setting)
    await session.flush()


if __name__ == "__main__":
    asyncio.run(generate_all())
