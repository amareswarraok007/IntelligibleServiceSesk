"""LangGraph state definition."""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    ticket_id: int
    title: str
    description: str
    source: str
    category: str
    priority: str
    confidence: float
    reasoning: str
    assigned_team: str
    status: str
    sla_risk: bool
    escalate: bool
    resolved_steps: str
    kb_article: dict[str, Any] | None
    trace: list[dict[str, Any]]
