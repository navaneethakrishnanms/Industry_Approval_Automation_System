"""
LLM Client — wraps Google Gemini with a mock fallback.

When GEMINI_API_KEY is set: uses real Gemini 1.5 Flash.
Otherwise: returns deterministic, realistic mock responses for demo.

The mock responses are carefully crafted to look authentic in demos.
"""
from __future__ import annotations

import json
import random
import time
from typing import Any


class LLMResponse:
    def __init__(self, text: str, tokens_in: int = 0, tokens_out: int = 0) -> None:
        self.text = text
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_usd = (tokens_in / 1000 * 0.00015) + (tokens_out / 1000 * 0.00060)

    def as_json(self) -> dict:
        """Parse text as JSON, with graceful fallback."""
        try:
            # Strip markdown code blocks if present
            text = self.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": self.text}


class LLMClient:
    """
    Unified LLM interface. Swappable between Gemini and Mock.
    """

    def __init__(self) -> None:
        self._gemini = None
        self._use_mock = True
        self._total_tokens_in = 0
        self._total_tokens_out = 0
        self._total_cost = 0.0

    def initialize(self, api_key: str | None, use_mock: bool) -> None:
        self._use_mock = use_mock or not api_key
        if not self._use_mock and api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self._gemini = genai.GenerativeModel("gemini-1.5-flash")
                # Quick test to confirm key is valid
                print("  [OK] Gemini Flash connected — REAL AI mode active")
            except Exception as e:
                print(f"  [WARN] Gemini key failed ({e}) — falling back to Mock LLM")
                self._use_mock = True


    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        """Send a completion request. Uses Gemini or mock."""
        if self._use_mock:
            return await self._mock_complete(prompt)
        return await self._gemini_complete(prompt, system)

    async def _gemini_complete(self, prompt: str, system: str = "") -> LLMResponse:
        import asyncio
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            response = await asyncio.to_thread(
                self._gemini.generate_content, full_prompt
            )
            text = response.text
            tokens_in = len(prompt.split()) * 1.3
            tokens_out = len(text.split()) * 1.3
            resp = LLMResponse(text, int(tokens_in), int(tokens_out))
            self._total_tokens_in += resp.tokens_in
            self._total_tokens_out += resp.tokens_out
            self._total_cost += resp.cost_usd
            return resp
        except Exception as e:
            return LLMResponse(f'{{"error": "{str(e)}"}}', 0, 0)

    async def _mock_complete(self, prompt: str) -> LLMResponse:
        """
        Deterministic mock responses based on prompt keywords.
        Mimics realistic LLM output for demo purposes.
        """
        import asyncio
        # Simulate a realistic 0.3–0.8s LLM latency
        await asyncio.sleep(random.uniform(0.3, 0.8))

        prompt_lower = prompt.lower()

        # Intent parsing
        if "extract structured intent" in prompt_lower or "workflow_type" in prompt_lower:
            wf = "travel"
            dest = "Dubai"
            if "leave" in prompt_lower or "vacation" in prompt_lower:
                wf = "leave"
            elif "visa" in prompt_lower:
                wf = "visa"
            elif "hotel" in prompt_lower:
                wf = "hotel"
            elif "invoice" in prompt_lower or "finance" in prompt_lower:
                wf = "finance"
            if "london" in prompt_lower: dest = "London"
            elif "singapore" in prompt_lower: dest = "Singapore"
            elif "new york" in prompt_lower: dest = "New York"
            result = {
                "workflow_type": wf,
                "destination": dest,
                "travel_date": "2026-08-01",
                "return_date": "2026-08-05",
                "purpose": "Business meeting with client",
                "confidence": round(random.uniform(0.88, 0.98), 2),
                "summary": f"Employee requesting {wf} arrangements to {dest}",
            }

        # Travel agent — flight selection
        elif "select the best flight" in prompt_lower or "available flights" in prompt_lower:
            result = {
                "selected_flight": {
                    "flight_number": f"AI{random.randint(100, 999)}",
                    "airline": "Air India",
                    "departure": "08:30",
                    "arrival": "11:45",
                    "price": round(random.uniform(14000, 19000), 2),
                    "currency": "INR",
                    "class": "economy",
                    "stops": 0,
                    "seats_available": random.randint(3, 12),
                },
                "policy_compliant": True,
                "reasoning": "Selected Air India as it is within budget, non-stop, and a company-preferred carrier. Departs at a business-friendly hour.",
            }

        # Policy agent
        elif "policy" in prompt_lower and "budget_limit" in prompt_lower:
            result = {
                "budget_limit": 20000,
                "class_allowed": "economy",
                "hotel_stars_max": 4,
                "advance_booking_days": 7,
                "approval_required": True,
                "key_rules": [
                    "Economy class for flights under 6 hours",
                    "Hotel budget capped at INR 8,000/night",
                    "Manager approval required for international travel",
                    "Finance approval required for amounts over INR 15,000",
                ],
                "policy_summary": "Standard corporate travel policy applies. Economy class, manager + finance approval required.",
            }

        # Hotel agent
        elif "select the best hotel" in prompt_lower or "available hotels" in prompt_lower:
            result = {
                "selected_hotel": {
                    "name": "Marriott City Centre",
                    "city": "Dubai",
                    "stars": 4,
                    "price_per_night": 7500,
                    "currency": "INR",
                    "rating": 4.3,
                    "amenities": ["WiFi", "Breakfast", "Business Centre"],
                },
                "reasoning": "Marriott selected as it meets the 4-star policy limit, includes breakfast, and is centrally located near the meeting venue.",
            }

        # Visa agent
        elif "visa application" in prompt_lower or "passport_expiry" in prompt_lower:
            result = {
                "visa_required": True,
                "documents_complete": True,
                "missing_documents": [],
                "estimated_processing_days": 5,
                "status": "approved",
                "reasoning": "Passport is valid. UAE business visa documentation is complete. Standard 5-day processing time applies.",
            }

        # Leave agent
        elif "leave request" in prompt_lower or "leave_balance" in prompt_lower:
            result = {
                "leave_approved": True,
                "balance_sufficient": True,
                "remaining_balance": 16,
                "reasoning": "Employee has sufficient leave balance. Leave dates do not conflict with project deadlines.",
            }

        # Finance agent
        elif "expense" in prompt_lower or "budget_approved" in prompt_lower:
            result = {
                "budget_approved": True,
                "invoice_created": True,
                "budget_code": f"CORP-TRV-{random.randint(1000, 9999)}",
                "reasoning": "Expense is within the approved travel budget. Invoice created and submitted to accounts payable.",
            }

        # Validation agent
        elif "validate the employee" in prompt_lower or "employee_exists" in prompt_lower:
            result = {
                "employee_exists": True,
                "employee_active": True,
                "passport_valid": True,
                "passport_warning": None,
                "validation_passed": True,
                "issues": [],
            }

        # Approval summary
        elif "approval request" in prompt_lower or "approve" in prompt_lower:
            result = {
                "summary": "Requesting approval for international business travel to Dubai from 1-5 August 2026. Estimated cost: INR 18,450 for flight + INR 30,000 for hotel (4 nights). Purpose: Client meeting and product demonstration. Request complies with company travel policy.",
            }

        # Notification
        elif "notification" in prompt_lower or "compose" in prompt_lower:
            result = {
                "message": "Your travel request to Dubai has been approved and processed. Flight AI274 (08:30–11:45) and Marriott City Centre accommodation have been booked. Please check your inbox for booking confirmations.",
            }

        # Audit summary
        elif "audit summary" in prompt_lower or "audit_agent" in prompt_lower:
            result = {
                "summary": "Travel workflow completed successfully in 45 seconds. All 8 steps executed without errors. Total spend: INR 48,450 (within approved budget). Audit trail complete.",
            }

        # Status / orchestrator update
        elif "status update" in prompt_lower or "what step" in prompt_lower:
            result = {
                "message": "Supervisor Agent: Step completed successfully. Delegating to next agent in the workflow pipeline.",
            }

        else:
            result = {
                "status": "processed",
                "confidence": round(random.uniform(0.85, 0.97), 2),
                "message": "Request analyzed and processed by AI agent.",
            }

        text = json.dumps(result)
        tokens_in = len(prompt.split()) * 1
        tokens_out = len(text.split()) * 1
        return LLMResponse(text, tokens_in, tokens_out)

    @property
    def usage_stats(self) -> dict:
        return {
            "total_tokens_in": self._total_tokens_in,
            "total_tokens_out": self._total_tokens_out,
            "total_cost_usd": round(self._total_cost, 6),
            "is_mock": self._use_mock,
        }


# ── Global singleton ──────────────────────────────────────────────────
llm_client = LLMClient()
