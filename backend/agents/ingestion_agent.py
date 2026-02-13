"""Ingestion node for normalizing ticket payload."""
from __future__ import annotations

from backend.agents.state import AgentState


def run(state: AgentState) -> AgentState:
    trace = state.get("trace", [])
    trace.append({"agent": "ingestion", "action": "normalized_input", "source": state.get("source", "web")})
    state["trace"] = trace
    return state
