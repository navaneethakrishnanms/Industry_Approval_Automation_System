"""
WebSocket router — real-time event streaming to the dashboard.

Channels:
  /ws/dashboard   — all system events (live event feed)
  /ws/workflow/{id}  — events for a specific workflow
  /ws/agents      — agent lifecycle state changes
"""
from __future__ import annotations

import json
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.event_bus import event_bus

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    """Stream all system events to dashboard clients."""
    await websocket.accept()
    event_bus.add_ws_client(websocket)
    try:
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "event_type": "system.connected",
            "message": "Connected to AI Workforce OS real-time feed",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }))
        # Keep alive with ping
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text(json.dumps({"event_type": "pong"}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"event_type": "heartbeat"}))
    except WebSocketDisconnect:
        event_bus.remove_ws_client(websocket)
    except Exception:
        event_bus.remove_ws_client(websocket)


@router.websocket("/ws/workflow/{workflow_id}")
async def ws_workflow(websocket: WebSocket, workflow_id: str):
    """Stream events for a specific workflow."""
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()

    async def handler(event: dict):
        if event.get("workflow_id") == workflow_id:
            await queue.put(event)

    event_bus.subscribe("*", handler)
    try:
        await websocket.send_text(json.dumps({
            "event_type": "system.connected",
            "workflow_id": workflow_id,
            "message": f"Subscribed to workflow {workflow_id[:8]}",
        }))
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
                await websocket.send_text(json.dumps(event, default=str))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"event_type": "heartbeat"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@router.websocket("/ws/agents")
async def ws_agents(websocket: WebSocket):
    """Stream agent status changes."""
    await websocket.accept()
    event_bus.add_ws_client(websocket)
    try:
        while True:
            # Send current agent status every 2 seconds
            from app.core.agent_registry import agent_registry
            status = agent_registry.health_summary()
            await websocket.send_text(json.dumps({
                "event_type": "agents.status_snapshot",
                "agents": status,
            }))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        event_bus.remove_ws_client(websocket)
    except Exception:
        event_bus.remove_ws_client(websocket)
