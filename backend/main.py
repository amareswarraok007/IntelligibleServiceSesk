"""FastAPI app for Smart Helpdesk Ticketing Solution MVP."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.agents.orchestrator import TicketGraph
from backend.db import Base, engine, get_db, serialized_write
from backend.models import Team, Ticket

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Helpdesk MVP")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class TicketCreate(BaseModel):
    title: str
    description: str
    source: str = "web"


class GLPIMockPayload(BaseModel):
    name: str
    content: str
    requester: str | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.post("/tickets")
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    with serialized_write():
        t = Ticket(
            title=payload.title,
            description=payload.description,
            source=payload.source,
            status="New",
            sla_deadline=datetime.utcnow() + timedelta(hours=8),
            trace_json=[{"agent": "api", "action": "ticket_created", "source": payload.source}],
        )
        db.add(t)
        db.commit()
        db.refresh(t)
    return _ticket_dict(t)


@app.post("/ingest/glpi-mock")
def ingest_glpi(payload: GLPIMockPayload, db: Session = Depends(get_db)) -> dict[str, Any]:
    with serialized_write():
        t = Ticket(
            title=payload.name,
            description=payload.content,
            source="glpi",
            status="New",
            sla_deadline=datetime.utcnow() + timedelta(hours=4),
            trace_json=[{"agent": "api", "action": "glpi_ingest", "requester": payload.requester}],
        )
        db.add(t)
        db.commit()
        db.refresh(t)
    return _ticket_dict(t)


@app.post("/process/{ticket_id}")
def process_ticket(ticket_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    graph = TicketGraph(db)
    state = graph.run(
        {
            "ticket_id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "source": ticket.source,
            "status": ticket.status,
            "trace": list(ticket.trace_json or []),
            "created_at": ticket.created_at,
            "sla_deadline": ticket.sla_deadline,
        }
    )

    with serialized_write():
        ticket.category = state.get("category")
        ticket.priority = state.get("priority")
        ticket.confidence = state.get("confidence")
        ticket.assigned_team = state.get("assigned_team")
        ticket.status = state.get("status", ticket.status)
        ticket.trace_json = state.get("trace", [])
        db.commit()
        db.refresh(ticket)

    result = _ticket_dict(ticket)
    result["kb_article"] = state.get("kb_article")
    result["resolved_steps"] = state.get("resolved_steps")
    result["escalate"] = state.get("escalate", False)
    return result


@app.get("/tickets")
def list_tickets(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    return [_ticket_dict(t) for t in tickets]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_dict(t)


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> dict[str, Any]:
    tickets = db.query(Ticket).all()
    total = len(tickets)
    resolved = [t for t in tickets if t.status == "Resolved"]
    escalated = [t for t in tickets if t.status == "Escalated"]

    auto_resolved_rate = round((len(resolved) / total), 3) if total else 0.0
    escalation_rate = round((len(escalated) / total), 3) if total else 0.0

    resolution_minutes = [
        (t.updated_at - t.created_at).total_seconds() / 60.0
        for t in resolved
        if t.updated_at and t.created_at
    ]
    avg_resolution_minutes = round(sum(resolution_minutes) / len(resolution_minutes), 2) if resolution_minutes else 0.0

    teams = {team.name: set(team.skills or []) for team in db.query(Team).all()}
    routed = [t for t in tickets if t.category and t.assigned_team]
    accurate = sum(1 for t in routed if t.category in teams.get(t.assigned_team, set()))
    routing_accuracy_proxy = round((accurate / len(routed)), 3) if routed else 0.0

    return {
        "total_tickets": total,
        "auto_resolved_rate": auto_resolved_rate,
        "escalation_rate": escalation_rate,
        "avg_resolution_minutes": avg_resolution_minutes,
        "routing_accuracy_proxy": routing_accuracy_proxy,
    }


def _ticket_dict(t: Ticket) -> dict[str, Any]:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "source": t.source,
        "category": t.category,
        "priority": t.priority,
        "confidence": t.confidence,
        "assigned_team": t.assigned_team,
        "status": t.status,
        "sla_deadline": t.sla_deadline.isoformat() if t.sla_deadline else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "trace_json": t.trace_json or [],
    }
