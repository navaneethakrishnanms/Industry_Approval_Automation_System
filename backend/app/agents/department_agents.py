"""Hotel, Leave, Finance, HR, Notification, Audit, Approval, Document Agents."""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from app.agents.base.base_agent import AgentResult, BaseAgent
from app.core.context import WorkflowContext
from app.core.tool_executor import BaseTool, ToolResult


# ── Hotel Agent ───────────────────────────────────────────────────────
class SearchHotelsTool(BaseTool):
    name = "search_hotels"
    async def execute(self, context: WorkflowContext, params: dict) -> ToolResult:
        city = params.get("city", context.destination)
        star_max = context.policy_snapshot.get("hotel_stars_max", 4)
        budget_max = float(context.policy_snapshot.get("budget_per_night", 10000) or 10000)
        hotel_names = ["Marriott", "Hilton", "Hyatt", "ITC Hotels", "Taj", "Le Méridien", "Radisson"]
        hotels = [
            {
                "name": f"{random.choice(hotel_names)} {city}",
                "city": city, "stars": random.randint(3, star_max),
                "price_per_night": round(random.uniform(4000, budget_max), 2),
                "currency": context.currency,
                "rating": round(random.uniform(3.8, 4.8), 1),
                "amenities": random.sample(["WiFi", "Pool", "Gym", "Breakfast", "Parking", "Business Centre"], k=3),
                "available_rooms": random.randint(5, 20),
            }
            for _ in range(3)
        ]
        return ToolResult("search_hotels", True, {"hotels": hotels})


class HotelAgent(BaseAgent):
    name = "HotelAgent"
    description = "Searches and books hotel accommodation at travel destination"
    capabilities = ["search_hotels", "book_hotel"]
    permissions = ["read:hotels", "write:hotel_bookings"]
    version = "1.0.0"
    owner = "travel_desk"

    def _setup_tools(self) -> None:
        self.tool_executor.register(SearchHotelsTool())

    async def execute(self, context: WorkflowContext) -> AgentResult:
        result = await self.tool_executor.run("search_hotels", context, {"city": context.destination})
        hotels = result.data.get("hotels", [])
        context.hotel_options = hotels

        llm_result = await self.llm_reason(
            "hotel_agent.reason",
            employee_name=context.employee.name if context.employee else "Employee",
            destination=context.destination,
            check_in=context.travel_date,
            check_out=context.return_date or context.travel_date,
            budget_per_night=context.policy_snapshot.get("hotel_stars_max", 10000),
            currency=context.currency,
            policy_summary=context.policy_snapshot.get("policy_summary", "Standard policy"),
            hotels_json=str(hotels),
        )
        selected = llm_result.get("selected_hotel") or (hotels[0] if hotels else {})
        context.selected_hotel = selected

        return AgentResult(
            status="success",
            output={"hotels_found": len(hotels), "selected_hotel": selected},
            reasoning=llm_result.get("reasoning", "Hotel selected per policy."),
            confidence=0.90, next_action="continue", agent_name=self.name,
        )


# ── Leave Agent ───────────────────────────────────────────────────────
class LeaveAgent(BaseAgent):
    name = "LeaveAgent"
    description = "Processes leave requests: checks balance, validates dates, prepares approval"
    capabilities = ["check_leave_balance", "process_leave", "update_calendar"]
    permissions = ["read:leave", "write:leave"]
    version = "1.0.0"
    owner = "hr"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        employee = context.employee
        balance = employee.leave_balance if employee else 21
        days = context.leave_days or 1
        context.leave_balance = balance
        sufficient = balance >= days

        llm_result = await self.llm_reason(
            "leave_agent.reason",
            employee_name=employee.name if employee else "Employee",
            leave_type=context.parsed_intent.get("leave_type", "annual"),
            days=days,
            start_date=context.travel_date or "2026-08-01",
            end_date=context.return_date or "2026-08-05",
            leave_balance=balance,
            reason=context.purpose or "Personal",
        )

        return AgentResult(
            status="success" if sufficient else "failure",
            output={
                "leave_approved": sufficient,
                "requested_days": days,
                "current_balance": balance,
                "remaining_balance": balance - days if sufficient else balance,
                "llm_assessment": llm_result,
            },
            reasoning=llm_result.get("reasoning", "Leave balance checked."),
            confidence=0.95, next_action="continue" if sufficient else "abort",
            agent_name=self.name,
            error=None if sufficient else f"Insufficient leave balance ({balance} days available, {days} requested)",
        )


# ── Finance Agent ─────────────────────────────────────────────────────
class FinanceAgent(BaseAgent):
    name = "FinanceAgent"
    description = "Creates invoices, checks budget availability, processes payments"
    capabilities = ["check_budget", "create_invoice", "process_payment"]
    permissions = ["read:finance", "write:finance"]
    version = "1.0.0"
    owner = "finance"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        amount = context.estimated_cost or (context.budget_limit * 0.6)
        budget_limit = context.budget_limit
        within_budget = amount <= budget_limit
        invoice_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-{random.randint(1000, 9999)}"

        llm_result = await self.llm_reason(
            "finance_agent.reason",
            employee_name=context.employee.name if context.employee else "Employee",
            category=context.workflow_type,
            amount=amount,
            currency=context.currency,
            budget_limit=budget_limit,
            purpose=context.purpose or "Business travel",
        )

        context.invoice_number = invoice_number
        budget_code = llm_result.get("budget_code", f"CORP-{context.workflow_type.upper()[:3]}-001")

        return AgentResult(
            status="success",
            output={
                "budget_approved": within_budget,
                "invoice_number": invoice_number,
                "amount": amount,
                "currency": context.currency,
                "budget_code": budget_code,
                "within_budget": within_budget,
                "llm_reasoning": llm_result.get("reasoning", "Budget allocated."),
            },
            reasoning=f"Invoice {invoice_number} created. Amount {amount:.2f} {'within' if within_budget else 'exceeds'} budget limit {budget_limit:.2f}.",
            confidence=0.97, next_action="continue", agent_name=self.name,
        )


# ── HR Agent ──────────────────────────────────────────────────────────
class HRAgent(BaseAgent):
    name = "HRAgent"
    description = "Updates HR systems: leave records, employee data, team calendar"
    capabilities = ["update_leave_record", "update_employee_record", "update_calendar"]
    permissions = ["write:employees", "write:leave"]
    version = "1.0.0"
    owner = "hr"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        # Mock HR system update
        return AgentResult(
            status="success",
            output={
                "hr_updated": True,
                "leave_deducted": context.leave_days,
                "new_balance": max(0, context.leave_balance - context.leave_days),
                "calendar_updated": True,
                "record_id": f"HR-{str(uuid.uuid4())[:8].upper()}",
            },
            reasoning="HR records updated. Leave balance deducted. Team calendar notified.",
            confidence=0.99, next_action="continue", agent_name=self.name,
        )


# ── Approval Agent ────────────────────────────────────────────────────
class ApprovalAgent(BaseAgent):
    name = "ApprovalAgent"
    description = "Creates approval requests and manages the human approval workflow"
    capabilities = ["request_approval", "check_approval_status", "escalate_approval"]
    permissions = ["read:approvals", "write:approvals"]
    version = "1.0.0"
    owner = "platform"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        """Prepare the approval request summary for the manager."""
        flight_info = ""
        if context.selected_flight:
            f = context.selected_flight
            flight_info = f"Flight: {f.get('airline')} {f.get('flight_number')} at {f.get('price', 0):.0f} {context.currency}"

        llm_result = await self.llm_reason(
            "approval_agent.summarize",
            workflow_type=context.workflow_type,
            employee_name=context.employee.name if context.employee else "Employee",
            details=f"{context.destination} | {context.travel_date} | {flight_info} | {context.selected_hotel or ''}",
            estimated_cost=context.estimated_cost,
            currency=context.currency,
        )

        summary = llm_result.get("summary", "Approval requested for workflow.")

        return AgentResult(
            status="waiting",
            output={"approval_summary": summary, "approval_status": "pending"},
            reasoning=summary,
            confidence=1.0, next_action="wait", agent_name=self.name,
        )


# ── Notification Agent ────────────────────────────────────────────────
class NotificationAgent(BaseAgent):
    name = "NotificationAgent"
    description = "Sends notifications via email, SMS, Slack (all mocked in prototype)"
    capabilities = ["send_email", "send_sms", "send_slack"]
    permissions = ["write:notifications"]
    version = "1.0.0"
    owner = "platform"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        employee = context.employee
        notifications_sent = []

        # Email notification (mock)
        if employee and employee.email:
            msg = await self.llm_text(
                "notification_agent.compose",
                notification_type="workflow_complete",
                recipient_name=employee.name,
                workflow_type=context.workflow_type,
                status="completed",
                details=f"Destination: {context.destination}, Date: {context.travel_date}",
                channel="email",
            )
            notifications_sent.append({
                "channel": "email",
                "recipient": employee.email,
                "subject": f"[AI Workforce OS] {context.workflow_type.capitalize()} Request Processed",
                "status": "sent (mock)",
            })

        # Manager notification
        if employee and employee.manager_email:
            notifications_sent.append({
                "channel": "email",
                "recipient": employee.manager_email,
                "subject": f"[Action] {employee.name}'s {context.workflow_type} request completed",
                "status": "sent (mock)",
            })

        # Slack (mock)
        notifications_sent.append({
            "channel": "slack",
            "recipient": "#travel-desk",
            "message": f"✅ {context.workflow_type.capitalize()} workflow completed for {employee.name if employee else 'Employee'}",
            "status": "sent (mock)",
        })

        context.notifications_sent = [n["channel"] for n in notifications_sent]

        return AgentResult(
            status="success",
            output={"notifications_sent": len(notifications_sent), "details": notifications_sent},
            reasoning=f"{len(notifications_sent)} notifications dispatched via email and Slack.",
            confidence=0.99, next_action="continue", agent_name=self.name,
        )


# ── Audit Agent ───────────────────────────────────────────────────────
class AuditAgent(BaseAgent):
    name = "AuditAgent"
    description = "Creates immutable audit trail for completed workflows"
    capabilities = ["create_audit_log", "summarize_workflow"]
    permissions = ["write:audit"]
    version = "1.0.0"
    owner = "compliance"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        llm_result = await self.llm_reason(
            "audit_agent.summarize",
            workflow_id=context.workflow_id[:8],
            workflow_type=context.workflow_type,
            employee_name=context.employee.name if context.employee else "Employee",
            outcome="completed",
            steps_completed=context.current_step,
            duration_ms=0,
            total_cost=context.estimated_cost,
            currency=context.currency,
        )

        audit_ref = f"AUD-{str(uuid.uuid4())[:8].upper()}"
        return AgentResult(
            status="success",
            output={
                "audit_ref": audit_ref,
                "workflow_id": context.workflow_id,
                "summary": llm_result.get("summary", "Workflow completed. Audit trail created."),
                "immutable": True,
            },
            reasoning="Audit trail created with full execution trace.",
            confidence=1.0, next_action="continue", agent_name=self.name,
        )


# ── Document Agent ────────────────────────────────────────────────────
class DocumentAgent(BaseAgent):
    name = "DocumentAgent"
    description = "Verifies documents required for visa and travel applications"
    capabilities = ["verify_passport", "verify_documents", "check_document_completeness"]
    permissions = ["read:employees"]
    version = "1.0.0"
    owner = "hr"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        employee = context.employee
        missing_docs = []
        if not employee or not employee.passport_number:
            missing_docs.append("Passport")

        documents_complete = len(missing_docs) == 0

        return AgentResult(
            status="success" if documents_complete else "failure",
            output={
                "documents_verified": documents_complete,
                "passport_number": employee.passport_number if employee else None,
                "passport_expiry": employee.passport_expiry if employee else None,
                "missing_documents": missing_docs,
            },
            reasoning="All required documents verified." if documents_complete else f"Missing: {missing_docs}",
            confidence=0.97, next_action="continue" if documents_complete else "escalate",
            agent_name=self.name,
        )


# ── Visa Agent ────────────────────────────────────────────────────────
class VisaAgent(BaseAgent):
    name = "VisaAgent"
    description = "Processes visa applications, verifies documents, tracks status"
    capabilities = ["process_visa", "verify_visa_documents", "track_visa_status"]
    permissions = ["read:employees", "write:visa"]
    version = "1.0.0"
    owner = "travel_desk"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        employee = context.employee
        llm_result = await self.llm_reason(
            "visa_agent.reason",
            employee_name=employee.name if employee else "Employee",
            passport_expiry=employee.passport_expiry if employee else "N/A",
            destination_country=context.destination or "UAE",
            travel_date=context.travel_date or "N/A",
            documents="Passport, Employment Letter, Bank Statement",
        )

        tracking_number = f"VIS-{str(uuid.uuid4())[:8].upper()}"
        context.visa_required = llm_result.get("visa_required", True)
        context.visa_status = llm_result.get("status", "approved")

        return AgentResult(
            status="success",
            output={
                "visa_required": context.visa_required,
                "visa_status": context.visa_status,
                "tracking_number": tracking_number,
                "documents_complete": llm_result.get("documents_complete", True),
                "estimated_processing_days": llm_result.get("estimated_processing_days", 5),
                "reasoning": llm_result.get("reasoning", "Visa application processed."),
            },
            reasoning=llm_result.get("reasoning", "Visa application submitted for processing."),
            confidence=0.88, next_action="continue", agent_name=self.name,
        )


# ── Reporting Agent ───────────────────────────────────────────────────
class ReportingAgent(BaseAgent):
    name = "ReportingAgent"
    description = "Generates workflow and analytics reports"
    capabilities = ["generate_report", "summarize_analytics"]
    permissions = ["read:*"]
    version = "1.0.0"
    owner = "analytics"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        return AgentResult(
            status="success",
            output={"report_generated": True, "report_id": f"RPT-{str(uuid.uuid4())[:8].upper()}"},
            reasoning="Report generated successfully.",
            confidence=0.95, next_action="continue", agent_name=self.name,
        )


# ── Analytics Agent ───────────────────────────────────────────────────
class AnalyticsAgent(BaseAgent):
    name = "AnalyticsAgent"
    description = "Analyzes workflow patterns, SLA compliance, and agent performance"
    capabilities = ["analyze_sla", "analyze_agent_performance", "forecast"]
    permissions = ["read:metrics"]
    version = "1.0.0"
    owner = "analytics"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        return AgentResult(
            status="success",
            output={"analysis_complete": True},
            reasoning="Analytics computed.", confidence=0.95,
            next_action="continue", agent_name=self.name,
        )
