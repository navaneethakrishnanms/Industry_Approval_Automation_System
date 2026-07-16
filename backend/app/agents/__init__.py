"""
Agent initialization — registers all agents into the global registry on import.
Import this module in main.py startup to activate the entire agent fleet.
"""
from app.agents.validation_agent import ValidationAgent
from app.agents.policy_agent import PolicyAgent
from app.agents.travel_agent import TravelAgent
from app.agents.department_agents import (
    HotelAgent,
    LeaveAgent,
    FinanceAgent,
    HRAgent,
    ApprovalAgent,
    NotificationAgent,
    AuditAgent,
    DocumentAgent,
    VisaAgent,
    ReportingAgent,
    AnalyticsAgent,
)
from app.agents.supervisor.supervisor_agent import supervisor_agent


def register_all_agents() -> None:
    """
    Instantiate and register all agents into the global AgentRegistry.
    Called once at application startup.
    """
    agents = [
        ValidationAgent(),
        PolicyAgent(),
        TravelAgent(),
        HotelAgent(),
        LeaveAgent(),
        FinanceAgent(),
        HRAgent(),
        ApprovalAgent(),
        NotificationAgent(),
        AuditAgent(),
        DocumentAgent(),
        VisaAgent(),
        ReportingAgent(),
        AnalyticsAgent(),
    ]
    for agent in agents:
        agent.register()

    # Register supervisor separately (it's a singleton)
    supervisor_agent.register()

    print(f"[AgentRegistry] {len(agents) + 1} agents registered successfully")
