"""
Tool Executor — routes tool calls from agents to their implementations.
Agents never call external APIs directly; they go through here.
Every tool call is logged and respects demo_mode.
"""
from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

from app.core.event_bus import event_bus
from app.core.event_types import EventType

if TYPE_CHECKING:
    from app.core.context import WorkflowContext


class ToolResult:
    """Typed result from any tool execution."""

    def __init__(
        self,
        tool_name: str,
        success: bool,
        data: dict[str, Any],
        error: str | None = None,
        duration_ms: float = 0.0,
        is_synthetic: bool = True,
    ) -> None:
        self.tool_name = tool_name
        self.success = success
        self.data = data
        self.error = error
        self.duration_ms = duration_ms
        self.is_synthetic = is_synthetic

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "is_synthetic": self.is_synthetic,
        }


class BaseTool:
    """Abstract base for all agent tools."""

    name: str = "base_tool"
    description: str = "Base tool"

    async def execute(self, context: "WorkflowContext", params: dict) -> ToolResult:
        raise NotImplementedError

    async def _synthetic(self, context: "WorkflowContext", params: dict) -> ToolResult:
        raise NotImplementedError

    async def _live(self, context: "WorkflowContext", params: dict) -> ToolResult:
        raise NotImplementedError


class ToolExecutor:
    """
    Central tool invocation engine.
    Records every tool call as events for observability.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    async def run(
        self,
        tool_name: str,
        context: "WorkflowContext",
        params: dict | None = None,
    ) -> ToolResult:
        """Execute a tool, emit events, return result."""
        params = params or {}
        start = time.monotonic()

        await event_bus.publish(
            EventType.TOOL_CALLED,
            workflow_id=context.workflow_id,
            source_agent="ToolExecutor",
            payload={"tool": tool_name, "params": params},
            tenant_id=context.tenant_id,
        )

        tool = self._tools.get(tool_name)
        if not tool:
            result = ToolResult(
                tool_name=tool_name,
                success=False,
                data={},
                error=f"Tool '{tool_name}' not registered",
                duration_ms=0,
            )
            await event_bus.publish(
                EventType.TOOL_FAILED,
                workflow_id=context.workflow_id,
                source_agent="ToolExecutor",
                payload={"tool": tool_name, "error": result.error},
                tenant_id=context.tenant_id,
            )
            return result

        try:
            result = await tool.execute(context, params)
            result.duration_ms = round((time.monotonic() - start) * 1000, 2)

            await event_bus.publish(
                EventType.TOOL_RETURNED,
                workflow_id=context.workflow_id,
                source_agent="ToolExecutor",
                payload={"tool": tool_name, "success": result.success, "duration_ms": result.duration_ms},
                tenant_id=context.tenant_id,
            )
            return result

        except Exception as e:
            result = ToolResult(
                tool_name=tool_name,
                success=False,
                data={},
                error=str(e),
                duration_ms=round((time.monotonic() - start) * 1000, 2),
            )
            await event_bus.publish(
                EventType.TOOL_FAILED,
                workflow_id=context.workflow_id,
                source_agent="ToolExecutor",
                payload={"tool": tool_name, "error": str(e)},
                tenant_id=context.tenant_id,
            )
            return result
