"""LangGraph orchestrator for ticket lifecycle."""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from backend.agents import escalation_agent, ingestion_agent, resolution_agent, router_agent, triage_agent
from backend.agents.state import AgentState


class TicketGraph:
    def __init__(self, db: Session) -> None:
        self.db = db
        graph = StateGraph(AgentState)
        graph.add_node("ingest", self._ingest)
        graph.add_node("triage", self._triage)
        graph.add_node("route", self._route)
        graph.add_node("resolve", self._resolve)
        graph.add_node("escalate", self._escalate)

        graph.set_entry_point("ingest")
        graph.add_edge("ingest", "triage")
        graph.add_edge("triage", "route")
        graph.add_edge("route", "resolve")
        graph.add_conditional_edges("resolve", self._next_after_resolution, {"escalate": "escalate", "end": END})
        graph.add_edge("escalate", END)
        self.app = graph.compile()

    def _ingest(self, state: AgentState) -> AgentState:
        return ingestion_agent.run(state)

    def _triage(self, state: AgentState) -> AgentState:
        return triage_agent.run(state)

    def _route(self, state: AgentState) -> AgentState:
        return router_agent.run(state, self.db)

    def _resolve(self, state: AgentState) -> AgentState:
        return resolution_agent.run(state)

    def _escalate(self, state: AgentState) -> AgentState:
        return escalation_agent.run(state, self.db)

    def _next_after_resolution(self, state: AgentState) -> str:
        if state.get("status") != "Resolved" or state.get("priority") == "Critical":
            return "escalate"
        return "end"

    def run(self, initial_state: dict[str, Any]) -> AgentState:
        return self.app.invoke(initial_state)
