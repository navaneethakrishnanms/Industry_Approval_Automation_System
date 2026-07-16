"""
Prompt Registry — database-backed prompt library.
Update prompts at runtime without code changes.
Falls back to hardcoded defaults if DB entry not found.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ── Default Prompts ───────────────────────────────────────────────────
# These are the fallback prompts loaded when DB has no entry yet.
DEFAULT_PROMPTS: dict[str, str] = {
    "supervisor.intent_parser": """You are the Supervisor Agent of an enterprise AI Workforce OS.
Analyze the employee's request and extract structured intent.

Return a JSON object with these fields:
- workflow_type: one of [travel, hotel, visa, leave, finance]
- destination: destination city/country (if travel/visa)
- travel_date: date mentioned (YYYY-MM-DD format, if applicable)
- return_date: return date if mentioned
- days: number of days (if leave)
- purpose: purpose of the request
- confidence: 0.0–1.0 confidence score
- summary: one-line summary of the request

Be precise. Do not guess. If workflow type is unclear, set confidence below 0.5.
Employee request: {request}
""",

    "supervisor.orchestrator": """You are the Supervisor Agent. 
Current workflow: {workflow_type}
Current step: {step_name} ({step_index}/{total_steps})
Employee: {employee_name}
Context: {context_summary}

Provide a brief, professional status update (1-2 sentences) indicating:
- What step just completed
- What happens next
- Any important findings

Be concise and professional. Speak as the Supervisor AI.
""",

    "travel_agent.reason": """You are the Travel Agent. You have received flight search results.
Employee: {employee_name}
Destination: {destination}
Date: {travel_date}
Budget limit: {budget_limit} {currency}
Policy: {policy_summary}

Available flights:
{flights_json}

Select the BEST flight based on:
1. Budget compliance (must be under budget limit)
2. Airline preference (company-preferred carriers first)
3. Travel time (shorter is better)
4. Non-stop preferred

Return JSON: {{"selected_flight": {{...}}, "reasoning": "...", "policy_compliant": true/false}}
""",

    "hotel_agent.reason": """You are the Hotel Agent. Select the best hotel option.
Employee: {employee_name}
City: {destination}
Check-in: {check_in}
Check-out: {check_out}
Budget per night: {budget_per_night} {currency}
Policy: {policy_summary}

Available hotels:
{hotels_json}

Return JSON: {{"selected_hotel": {{...}}, "reasoning": "..."}}
""",

    "visa_agent.reason": """You are the Visa Agent. Analyze the visa application.
Employee: {employee_name}
Passport valid until: {passport_expiry}
Destination: {destination_country}
Travel date: {travel_date}
Documents provided: {documents}

Return JSON:
{{
  "visa_required": true/false,
  "documents_complete": true/false,
  "missing_documents": [],
  "estimated_processing_days": 5,
  "status": "approved/pending/rejected",
  "reasoning": "..."
}}
""",

    "leave_agent.reason": """You are the Leave Agent. Process the leave request.
Employee: {employee_name}
Leave type: {leave_type}
Duration: {days} days ({start_date} to {end_date})
Current leave balance: {leave_balance} days
Reason: {reason}

Return JSON:
{{
  "leave_approved": true/false,
  "balance_sufficient": true/false,
  "remaining_balance": 0,
  "reasoning": "..."
}}
""",

    "finance_agent.reason": """You are the Finance Agent. Review the expense for approval.
Employee: {employee_name}
Category: {category}
Amount: {amount} {currency}
Budget limit: {budget_limit} {currency}
Purpose: {purpose}

Return JSON:
{{
  "budget_approved": true/false,
  "invoice_created": true/false,
  "budget_code": "...",
  "reasoning": "..."
}}
""",

    "policy_agent.rag_query": """You are the Policy Agent. You have retrieved relevant policy sections.
Employee grade: {grade}
Request type: {workflow_type}
Policy sections retrieved:
{policy_content}

Extract the relevant rules that apply to this request. Return JSON:
{{
  "budget_limit": 0,
  "class_allowed": "economy",
  "hotel_stars_max": 3,
  "advance_booking_days": 7,
  "approval_required": true,
  "key_rules": ["rule1", "rule2"],
  "policy_summary": "..."
}}
""",

    "approval_agent.summarize": """You are the Approval Agent. Prepare a clear approval request.
Workflow: {workflow_type}
Employee: {employee_name}
Details: {details}
Estimated cost: {estimated_cost} {currency}

Write a concise approval request (3-4 sentences) for the manager.
Include: what is being requested, why, cost, and urgency.
""",

    "notification_agent.compose": """You are the Notification Agent. Compose a professional notification.
Type: {notification_type}
Recipient: {recipient_name}
Workflow: {workflow_type}
Status: {status}
Details: {details}

Write a brief, professional message (2-3 sentences) suitable for {channel} notification.
""",

    "audit_agent.summarize": """You are the Audit Agent. Create an audit summary.
Workflow ID: {workflow_id}
Type: {workflow_type}
Employee: {employee_name}
Outcome: {outcome}
Steps completed: {steps_completed}
Duration: {duration_ms}ms
Total cost: {total_cost} {currency}

Write a 2-sentence audit summary capturing what happened and the outcome.
""",

    "validation_agent.check": """You are the Validation Agent. Validate the employee request.
Employee ID: {employee_id}
Employee grade: {grade}
Passport expiry: {passport_expiry}
Request type: {workflow_type}
Destination: {destination}

Return JSON:
{{
  "employee_exists": true,
  "employee_active": true,
  "passport_valid": true,
  "passport_warning": null,
  "validation_passed": true,
  "issues": []
}}
""",
}


class PromptRegistry:
    """
    Database-backed prompt library with in-memory cache.
    Agents call registry.get("agent.prompt_name") to retrieve their system prompt.
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._loaded_from_db = False

    async def load_from_db(self, session: "AsyncSession") -> None:
        """Load all active prompts from DB into memory cache."""
        from sqlalchemy import select
        from app.models.system import PromptRegistryEntry

        result = await session.execute(
            select(PromptRegistryEntry).where(PromptRegistryEntry.is_active == True)
        )
        entries = result.scalars().all()
        for entry in entries:
            self._cache[entry.name] = entry.content
        self._loaded_from_db = True

    def get(self, name: str, **kwargs) -> str:
        """
        Get a prompt by name. Falls back to DEFAULT_PROMPTS if not in cache.
        Supports .format() kwargs for variable substitution.
        """
        template = self._cache.get(name) or DEFAULT_PROMPTS.get(name, f"[Prompt '{name}' not found]")
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                return template  # Return unformatted if keys don't match
        return template

    def set(self, name: str, content: str) -> None:
        """Update in-memory cache (call DB save separately)."""
        self._cache[name] = content

    def list_all(self) -> dict[str, str]:
        merged = dict(DEFAULT_PROMPTS)
        merged.update(self._cache)
        return merged

    async def seed_defaults_to_db(self, session: "AsyncSession") -> None:
        """Write default prompts to DB if they don't exist yet."""
        from sqlalchemy import select
        from app.models.system import PromptRegistryEntry

        for name, content in DEFAULT_PROMPTS.items():
            result = await session.execute(
                select(PromptRegistryEntry).where(PromptRegistryEntry.name == name)
            )
            existing = result.scalar_one_or_none()
            if not existing:
                entry = PromptRegistryEntry(
                    name=name,
                    version="1.0",
                    content=content,
                    description=f"Default prompt for {name}",
                    is_active=True,
                )
                session.add(entry)
        await session.commit()


# ── Global singleton ──────────────────────────────────────────────────
prompt_registry = PromptRegistry()
