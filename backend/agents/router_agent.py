"""Routing node based on team skills and routing history scores."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.models import RoutingScore, Team


def run(state: AgentState, db: Session) -> AgentState:
    category = state.get("category", "Other")
    teams = db.query(Team).all()
    score_rows = db.query(RoutingScore).filter(RoutingScore.category == category).all()
    hist = {row.team_id: row.score for row in score_rows}

    best_team = "Service Desk"
    best_score = -1.0
    for team in teams:
        skill_match = 1.0 if category in (team.skills or []) else 0.0
        combined = 0.7 * skill_match + 0.3 * hist.get(team.id, 0.0)
        if combined > best_score:
            best_score = combined
            best_team = team.name

    state["assigned_team"] = best_team
    state.setdefault("trace", []).append(
        {"agent": "router", "category": category, "assigned_team": best_team, "routing_score": round(best_score, 3)}
    )
    return state
