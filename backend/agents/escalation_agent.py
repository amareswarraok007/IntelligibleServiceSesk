"""Escalation node for critical and SLA-risk tickets."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.services.notifier import emit_alert


def _sla_risk(created_at: datetime | None, sla_deadline: datetime | None) -> bool:
    if not created_at or not sla_deadline:
        return False
    total = (sla_deadline - created_at).total_seconds()
    remaining = (sla_deadline - datetime.utcnow()).total_seconds()
    if total <= 0:
        return True
    return (remaining / total) < 0.2


def run(state: AgentState, db: Session) -> AgentState:
    risk = _sla_risk(state.get("created_at"), state.get("sla_deadline"))
    critical = state.get("priority") == "Critical"
    escalate = bool(critical or risk)
    state["sla_risk"] = risk
    state["escalate"] = escalate
    if escalate:
        state["status"] = "Escalated"
        emit_alert(
            db,
            state["ticket_id"],
            f"Escalation triggered for ticket {state['ticket_id']} (priority={state.get('priority')}, sla_risk={risk})",
        )

    state.setdefault("trace", []).append(
        {"agent": "escalation", "escalated": escalate, "critical": critical, "sla_risk": risk}
    )
    return state
