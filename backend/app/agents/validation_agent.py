"""Validation Agent — first step in every workflow."""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents.base.base_agent import AgentResult, BaseAgent
from app.core.context import WorkflowContext


class ValidationAgent(BaseAgent):
    name = "ValidationAgent"
    description = "Validates employee identity, passport, and request completeness"
    capabilities = ["validate_employee", "validate_passport", "validate_request"]
    permissions = ["read:employees"]
    version = "1.0.0"
    owner = "hr"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        issues = []

        # 1. Employee check
        if not context.employee:
            return AgentResult(
                status="failure", error="Employee not found in system",
                next_action="abort", agent_name=self.name
            )

        employee = context.employee

        # 2. Passport validation (for travel/visa)
        if context.workflow_type in ("travel", "visa"):
            if not employee.passport_number:
                issues.append("No passport on file")
            elif employee.passport_expiry:
                try:
                    expiry = datetime.strptime(employee.passport_expiry, "%Y-%m-%d")
                    days_to_expiry = (expiry - datetime.now()).days
                    if days_to_expiry < 0:
                        return AgentResult(
                            status="failure",
                            error=f"Passport expired on {employee.passport_expiry}",
                            next_action="escalate",
                            reasoning="Passport is expired. Cannot proceed with travel/visa workflow.",
                            agent_name=self.name,
                        )
                    elif days_to_expiry < 180:
                        issues.append(f"Passport expires in {days_to_expiry} days (< 6 months warning)")
                except ValueError:
                    pass

        # 3. Request completeness check
        if context.workflow_type == "travel" and not context.destination:
            issues.append("Travel destination not specified")
        if context.workflow_type == "leave" and context.leave_days <= 0:
            issues.append("Leave duration not specified")

        # 4. LLM validation summary
        llm_result = await self.llm_reason(
            "validation_agent.check",
            employee_id=employee.employee_id,
            grade=employee.grade,
            passport_expiry=employee.passport_expiry or "N/A",
            workflow_type=context.workflow_type,
            destination=context.destination or "N/A",
        )

        context.employee_validated = True
        context.passport_valid = not any("passport" in i.lower() and "expir" in i.lower() for i in issues)

        return AgentResult(
            status="success" if not any("No passport" in i for i in issues) else "failure",
            output={
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                "validation_passed": len(issues) == 0,
                "issues": issues,
                "passport_valid": context.passport_valid,
                "llm_assessment": llm_result,
            },
            reasoning=f"Employee {employee.name} validated. Issues: {issues if issues else 'None'}",
            confidence=0.98 if not issues else 0.75,
            next_action="continue",
            agent_name=self.name,
        )
