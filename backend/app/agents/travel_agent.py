"""Travel Agent — searches flights via tool, selects best via LLM reasoning."""
from __future__ import annotations

import random
from datetime import datetime

from app.agents.base.base_agent import AgentResult, BaseAgent
from app.core.context import WorkflowContext
from app.core.tool_executor import BaseTool, ToolResult


class SearchFlightsTool(BaseTool):
    name = "search_flights"
    description = "Search available flights between origin and destination"

    async def execute(self, context: WorkflowContext, params: dict) -> ToolResult:
        if not context.demo_mode:
            return await self._live(context, params)
        return await self._synthetic(context, params)

    async def _synthetic(self, context: WorkflowContext, params: dict) -> ToolResult:
        """Generate realistic flight options."""
        airlines = [
            ("Air India", "AI", 0.85),
            ("Emirates", "EK", 0.92),
            ("IndiGo", "6E", 0.78),
            ("Vistara", "UK", 0.88),
            ("SpiceJet", "SG", 0.72),
        ]
        destination = params.get("destination", context.destination or "Dubai")
        travel_date = params.get("travel_date", context.travel_date or "2026-08-01")

        flights = []
        for i, (airline, code, rating) in enumerate(random.sample(airlines, k=min(4, len(airlines)))):
            dep_hour = random.choice([6, 8, 10, 13, 16, 20])
            arr_hour = dep_hour + random.randint(3, 8)
            base_price = random.uniform(12000, 45000)
            flights.append({
                "flight_number": f"{code}{random.randint(100, 999)}",
                "airline": airline,
                "origin": context.origin or "MAA",
                "destination": destination,
                "date": travel_date,
                "departure": f"{dep_hour:02d}:00",
                "arrival": f"{arr_hour % 24:02d}:{random.randint(0,5)*10:02d}",
                "price": round(base_price, 2),
                "currency": context.currency,
                "class": "economy",
                "stops": 0 if i < 2 else 1,
                "seats_available": random.randint(2, 15),
                "rating": rating,
                "duration_minutes": (arr_hour - dep_hour) * 60 + random.randint(0, 30),
            })
        return ToolResult("search_flights", True, {"flights": flights, "total": len(flights)})

    async def _live(self, context: WorkflowContext, params: dict) -> ToolResult:
        """Real Aviationstack API integration."""
        import aiohttp
        from app.config.settings import get_settings
        settings = get_settings()
        api_key = settings.aviationstack_api_key
        if not api_key:
            return await self._synthetic(context, params)
        try:
            async with aiohttp.ClientSession() as http:
                url = "http://api.aviationstack.com/v1/flights"
                params_req = {
                    "access_key": api_key,
                    "dep_iata": params.get("origin", "MAA"),
                    "arr_iata": params.get("dest_code", "DXB"),
                    "flight_status": "scheduled",
                    "limit": 5,
                }
                async with http.get(url, params=params_req) as resp:
                    data = await resp.json()
                    flights_raw = data.get("data", [])
                    flights = [
                        {
                            "flight_number": f.get("flight", {}).get("iata", "N/A"),
                            "airline": f.get("airline", {}).get("name", "Unknown"),
                            "departure": f.get("departure", {}).get("scheduled", ""),
                            "arrival": f.get("arrival", {}).get("scheduled", ""),
                            "status": f.get("flight_status", "scheduled"),
                            "price": round(random.uniform(15000, 40000), 2),
                            "currency": context.currency,
                        }
                        for f in flights_raw[:5]
                    ]
                    return ToolResult("search_flights", True, {"flights": flights})
        except Exception as e:
            return await self._synthetic(context, params)


class BookFlightTool(BaseTool):
    name = "book_flight"
    description = "Book a selected flight (mock booking in prototype)"

    async def execute(self, context: WorkflowContext, params: dict) -> ToolResult:
        """Mock booking — returns a realistic booking reference."""
        flight = params.get("flight", {})
        import uuid
        booking_ref = f"BK{str(uuid.uuid4())[:8].upper()}"
        return ToolResult("book_flight", True, {
            "booking_ref": booking_ref,
            "status": "confirmed",
            "flight": flight,
            "is_mock": True,
        })


class TravelAgent(BaseAgent):
    name = "TravelAgent"
    description = "Searches and selects flights based on policy; uses LLM to reason about best option"
    capabilities = ["search_flights", "book_flight", "check_travel_policy"]
    permissions = ["read:travel", "write:travel"]
    version = "1.0.0"
    owner = "travel_desk"

    def _setup_tools(self) -> None:
        self.tool_executor.register(SearchFlightsTool())
        self.tool_executor.register(BookFlightTool())

    async def execute(self, context: WorkflowContext) -> AgentResult:
        # 1. TOOL: Search flights (deterministic)
        search_result = await self.tool_executor.run(
            "search_flights", context,
            {"destination": context.destination, "travel_date": context.travel_date}
        )
        if not search_result.success:
            return AgentResult(
                status="failure", error="Flight search failed",
                next_action="retry", agent_name=self.name
            )

        flights = search_result.data.get("flights", [])
        context.flight_options = flights

        # 2. LLM: Reason over results (non-deterministic — the AI part)
        policy = context.policy_snapshot
        llm_result = await self.llm_reason(
            "travel_agent.reason",
            employee_name=context.employee.name if context.employee else "Employee",
            destination=context.destination,
            travel_date=context.travel_date,
            budget_limit=context.budget_limit,
            currency=context.currency,
            policy_summary=policy.get("policy_summary", "Standard policy"),
            flights_json=str(flights[:4]),
        )

        selected = llm_result.get("selected_flight") or (flights[0] if flights else {})
        context.selected_flight = selected

        # 3. TOOL: Book the selected flight
        if selected:
            book_result = await self.tool_executor.run(
                "book_flight", context, {"flight": selected}
            )
            if book_result.success:
                selected["booking_ref"] = book_result.data.get("booking_ref")
                context.estimated_cost = float(selected.get("price", 0))

        return AgentResult(
            status="success",
            output={
                "flights_found": len(flights),
                "selected_flight": selected,
                "policy_compliant": llm_result.get("policy_compliant", True),
                "booking_ref": selected.get("booking_ref") if selected else None,
                "estimated_cost": context.estimated_cost,
            },
            reasoning=llm_result.get("reasoning", "Best flight selected based on policy and budget."),
            confidence=0.92,
            next_action="continue",
            agent_name=self.name,
        )
