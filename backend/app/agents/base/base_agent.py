"""
BaseAgent — abstract class every agent inherits.
Enforces: name, capabilities, tools, retry logic, lifecycle events, metrics.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from app.config.constants import AgentLifecycle
from app.core.agent_registry import agent_registry
from app.core.event_bus import event_bus
from app.core.event_types import EventType
from app.core.llm_client import llm_client
from app.core.prompt_registry import prompt_registry
from app.core.tool_executor import ToolExecutor

if TYPE_CHECKING:
    from app.core.context import WorkflowContext


@dataclass
class AgentResult:
    """Typed result returned by every agent execution."""
    status: str           # success | failure | pending | escalated | waiting
    output: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 1.0
    duration_ms: float = 0.0
    next_action: str = "continue"   # continue | wait | escalate | abort
    tokens_used: int = 0
    error: str | None = None
    agent_name: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "output": self.output,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "next_action": self.next_action,
            "tokens_used": self.tokens_used,
            "error": self.error,
            "agent_name": self.agent_name,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Subclasses must define:
        name, capabilities, description
    And implement:
        execute(context) → AgentResult
    """

    # ── Agent identity (override in subclass) ─────────────────────────
    name: str = "BaseAgent"
    description: str = "Base agent"
    capabilities: list[str] = []
    permissions: list[str] = []
    version: str = "1.0.0"
    owner: str = "system"
    retry_limit: int = 3

    def __init__(self) -> None:
        self.tool_executor = ToolExecutor()
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Override in subclasses to register tools."""
        pass

    @property
    def tool_names(self) -> list[str]:
        return list(self.tool_executor._tools.keys())

    def register(self) -> None:
        """Self-register into the global agent registry."""
        agent_registry.register(self)

    # ── Core execution ────────────────────────────────────────────────
    @abstractmethod
    async def execute(self, context: "WorkflowContext") -> AgentResult:
        """
        Business logic. LLM should only be used for REASONING, not deterministic actions.
        Call tools for actual work, then optionally call LLM to reason over results.
        """
        ...

    async def run(self, context: "WorkflowContext") -> AgentResult:
        """
        Called by WorkflowEngine. Handles lifecycle, events, timing, metrics.
        """
        start = time.monotonic()

        # Set agent lifecycle to RUNNING
        agent_registry.set_agent_status(self.name, AgentLifecycle.RUNNING)
        await event_bus.publish(
            EventType.AGENT_ASSIGNED,
            workflow_id=context.workflow_id,
            source_agent=self.name,
            payload={"agent": self.name, "step": context.current_step},
            tenant_id=context.tenant_id,
        )
        await event_bus.publish(
            EventType.AGENT_THINKING,
            workflow_id=context.workflow_id,
            source_agent=self.name,
            payload={"agent": self.name, "message": f"{self.name} is analyzing the request..."},
            tenant_id=context.tenant_id,
        )

        try:
            result = await self.execute(context)
            result.agent_name = self.name
            result.duration_ms = round((time.monotonic() - start) * 1000, 2)

            # Record metrics
            success = result.status == "success"
            agent_registry.record_call(self.name, success, result.duration_ms)
            agent_registry.set_agent_status(
                self.name,
                AgentLifecycle.COMPLETED if success else AgentLifecycle.FAILED,
            )

            await event_bus.publish(
                EventType.AGENT_COMPLETED if success else EventType.AGENT_FAILED,
                workflow_id=context.workflow_id,
                source_agent=self.name,
                payload={
                    "agent": self.name,
                    "status": result.status,
                    "confidence": result.confidence,
                    "duration_ms": result.duration_ms,
                    "reasoning": result.reasoning,
                },
                tenant_id=context.tenant_id,
            )
            return result

        except Exception as e:
            duration = round((time.monotonic() - start) * 1000, 2)
            agent_registry.record_call(self.name, False, duration)
            agent_registry.set_agent_status(self.name, AgentLifecycle.FAILED)
            await event_bus.publish(
                EventType.AGENT_FAILED,
                workflow_id=context.workflow_id,
                source_agent=self.name,
                payload={"agent": self.name, "error": str(e)},
                tenant_id=context.tenant_id,
            )
            return AgentResult(
                status="failure",
                error=str(e),
                duration_ms=duration,
                next_action="escalate",
                agent_name=self.name,
            )
        finally:
            # Reset to IDLE after any terminal state
            agent_registry.set_agent_status(self.name, AgentLifecycle.IDLE)

    # ── LLM helper ───────────────────────────────────────────────────
    async def llm_reason(self, prompt_name: str, **kwargs) -> dict:
        """Convenience: get prompt, call LLM, return parsed JSON."""
        prompt = prompt_registry.get(prompt_name, **kwargs)
        response = await llm_client.complete(prompt)
        return response.as_json()

    async def llm_text(self, prompt_name: str, **kwargs) -> str:
        """Convenience: get prompt, call LLM, return raw text."""
        prompt = prompt_registry.get(prompt_name, **kwargs)
        response = await llm_client.complete(prompt)
        return response.text

    # ── Logging helper ─────────────────────────────────────────────────
    async def log(
        self,
        session,
        workflow_id: str,
        action: str,
        message: str,
        level: str = "INFO",
        metadata: dict | None = None,
    ) -> None:
        """Write to agent_logs table."""
        from app.models.system import AgentLog
        import json
        log_entry = AgentLog(
            workflow_id=workflow_id,
            agent_name=self.name,
            action=action,
            log_level=level,
            message=message,
            metadata_json=json.dumps(metadata or {}),
        )
        session.add(log_entry)
