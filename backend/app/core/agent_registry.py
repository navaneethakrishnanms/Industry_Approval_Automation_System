"""
Agent Registry — dynamic discovery and health tracking.

Agents self-register on startup. The Supervisor queries the registry
to discover which agents are available and what capabilities they have.
No hardcoded agent names in the Supervisor.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.config.constants import AgentLifecycle

if TYPE_CHECKING:
    from app.agents.base.base_agent import BaseAgent


class AgentRegistration:
    """Live registration record for a single agent."""

    def __init__(
        self,
        name: str,
        capabilities: list[str],
        tools: list[str],
        permissions: list[str],
        version: str = "1.0.0",
        owner: str = "system",
        description: str = "",
    ) -> None:
        self.name = name
        self.capabilities = capabilities
        self.tools = tools
        self.permissions = permissions
        self.version = version
        self.owner = owner
        self.description = description
        self.status: AgentLifecycle = AgentLifecycle.IDLE

        # Live metrics
        self.call_count: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self._latencies: list[float] = []
        self.last_active: datetime | None = None
        self._agent_ref: "BaseAgent | None" = None

    @property
    def avg_response_ms(self) -> float:
        if not self._latencies:
            return 0.0
        return round(sum(self._latencies) / len(self._latencies), 2)

    @property
    def success_rate(self) -> float:
        if self.call_count == 0:
            return 100.0
        return round((self.success_count / self.call_count) * 100, 1)

    def record_call(self, success: bool, latency_ms: float) -> None:
        self.call_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self._latencies.append(latency_ms)
        if len(self._latencies) > 1000:  # rolling window
            self._latencies = self._latencies[-1000:]
        self.last_active = datetime.now(timezone.utc)

    def set_status(self, status: AgentLifecycle) -> None:
        self.status = status

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "capabilities": self.capabilities,
            "tools": self.tools,
            "permissions": self.permissions,
            "version": self.version,
            "owner": self.owner,
            "description": self.description,
            "status": self.status.value,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_response_ms": self.avg_response_ms,
            "success_rate": self.success_rate,
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }


class AgentRegistry:
    """
    Central registry of all available agents.
    Thread-safe for concurrent async access.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentRegistration] = {}
        self._capability_index: dict[str, list[str]] = {}  # capability → agent names

    def register(self, agent: "BaseAgent") -> None:
        """Called by each agent during app startup."""
        reg = AgentRegistration(
            name=agent.name,
            capabilities=agent.capabilities,
            tools=agent.tool_names,
            permissions=agent.permissions,
            version=agent.version,
            owner=agent.owner,
            description=agent.description,
        )
        reg._agent_ref = agent
        self._agents[agent.name] = reg

        # Build capability index
        for cap in agent.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = []
            self._capability_index[cap].append(agent.name)

    def get(self, name: str) -> "BaseAgent":
        """Get agent instance by name. Raises KeyError if not found."""
        reg = self._agents.get(name)
        if not reg or not reg._agent_ref:
            raise KeyError(f"Agent '{name}' not found in registry. Registered: {list(self._agents.keys())}")
        return reg._agent_ref

    def get_registration(self, name: str) -> AgentRegistration:
        reg = self._agents.get(name)
        if not reg:
            raise KeyError(f"Agent '{name}' not found in registry.")
        return reg

    def discover(self, capability: str) -> list[str]:
        """Return agent names that have the given capability."""
        return self._capability_index.get(capability, [])

    def all_registrations(self) -> list[AgentRegistration]:
        return list(self._agents.values())

    def all_names(self) -> list[str]:
        return list(self._agents.keys())

    def health_summary(self) -> dict:
        return {
            name: {
                "status": reg.status.value,
                "call_count": reg.call_count,
                "success_rate": reg.success_rate,
                "avg_response_ms": reg.avg_response_ms,
            }
            for name, reg in self._agents.items()
        }

    def set_agent_status(self, name: str, status: AgentLifecycle) -> None:
        if name in self._agents:
            self._agents[name].set_status(status)

    def record_call(self, name: str, success: bool, latency_ms: float) -> None:
        if name in self._agents:
            self._agents[name].record_call(success, latency_ms)


# ── Global singleton ──────────────────────────────────────────────────
agent_registry = AgentRegistry()
