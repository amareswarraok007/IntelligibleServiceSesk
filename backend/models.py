"""ORM models for tickets, teams, and events."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False)
    skills = Column(JSON, nullable=False, default=list)


class RoutingScore(Base):
    __tablename__ = "routing_scores"

    id = Column(Integer, primary_key=True)
    category = Column(String(40), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    score = Column(Float, nullable=False, default=0.0)

    team = relationship("Team")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String(30), nullable=False, default="web")
    category = Column(String(30), nullable=True)
    priority = Column(String(20), nullable=True)
    confidence = Column(Float, nullable=True)
    assigned_team = Column(String(80), nullable=True)
    status = Column(String(30), nullable=False, default="New")
    sla_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    trace_json = Column(JSON, nullable=False, default=list)


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    channel = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("Ticket")
