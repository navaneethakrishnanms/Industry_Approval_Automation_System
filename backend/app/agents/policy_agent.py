"""Policy Agent — queries ChromaDB knowledge base for applicable policy rules."""
from __future__ import annotations

from app.agents.base.base_agent import AgentResult, BaseAgent
from app.core.context import WorkflowContext


class PolicyAgent(BaseAgent):
    name = "PolicyAgent"
    description = "Retrieves and applies company policies using RAG over policy documents"
    capabilities = ["check_policy", "retrieve_policy", "apply_rules"]
    permissions = ["read:policies"]
    version = "1.0.0"
    owner = "compliance"

    async def execute(self, context: WorkflowContext) -> AgentResult:
        # Query policy via LLM (ChromaDB RAG in production; mock content for demo)
        policy_content = self._get_policy_content(context.workflow_type, context.employee)

        llm_result = await self.llm_reason(
            "policy_agent.rag_query",
            grade=context.employee.grade if context.employee else "L3",
            workflow_type=context.workflow_type,
            policy_content=policy_content,
        )

        # Merge policy into context
        context.policy_snapshot = llm_result
        context.budget_approved = True  # Policy check passed; actual budget checked by FinanceAgent

        # Update budget_limit from policy if lower than employee's default
        policy_budget = llm_result.get("budget_limit", context.budget_limit)
        if policy_budget and float(policy_budget) < context.budget_limit:
            context.budget_limit = float(policy_budget)

        return AgentResult(
            status="success",
            output={
                "policy_applied": True,
                "budget_limit": context.budget_limit,
                "currency": context.currency,
                "class_allowed": llm_result.get("class_allowed", "economy"),
                "hotel_stars_max": llm_result.get("hotel_stars_max", 4),
                "approval_required": llm_result.get("approval_required", True),
                "key_rules": llm_result.get("key_rules", []),
                "policy_summary": llm_result.get("policy_summary", "Standard corporate policy applies."),
            },
            reasoning=llm_result.get("policy_summary", "Policy applied successfully."),
            confidence=0.96,
            next_action="continue",
            agent_name=self.name,
        )

    def _get_policy_content(self, workflow_type: str, employee) -> str:
        """Return relevant policy text. In production: ChromaDB vector search."""
        grade = employee.grade if employee else "L3"
        policies = {
            "travel": f"""
Travel Policy (Grade {grade}):
- Economy class for flights under 8 hours; Business class above 8 hours only for L5+
- Maximum flight budget: INR 20,000 for domestic, INR 50,000 for international
- Hotel: Maximum 4-star for L1-L4; 5-star permitted for L5+
- Hotel budget: INR 6,000-10,000/night depending on city tier
- Booking must be made at least 7 days in advance
- Manager approval required for all international travel
- Finance approval required for amounts exceeding INR 15,000
- Per diem allowance: INR 2,500/day for international travel
""",
            "visa": """
Visa Policy:
- Passport must have minimum 6 months validity beyond travel date
- All original documents must be submitted 15 days before travel
- Company covers visa fees for business travel
- Employee responsible for tourist/personal visa fees
- Processing time: 5-15 business days depending on country
""",
            "leave": f"""
Leave Policy (Grade {grade}):
- Annual leave: 21 days per year
- Sick leave: 12 days per year (no carry forward)
- Emergency leave: Up to 5 days, manager approval same day
- Leave cannot be taken during project critical phases without HOD approval
- Minimum 3 days advance notice required (except emergency)
- Maximum 10 consecutive days without HR Director approval
""",
            "finance": """
Finance & Expense Policy:
- Expenses above INR 5,000 require receipts
- Reimbursement processed within 15 business days of approved claim
- All claims must be submitted within 30 days of expense
- Credit card statements accepted for amounts under INR 2,000
- Finance approval required for claims above INR 10,000
""",
        }
        return policies.get(workflow_type, "Standard company policy applies.")
