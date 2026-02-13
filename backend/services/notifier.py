"""Mock notifier service: persists and logs events."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import NotificationEvent


def emit_alert(db: Session, ticket_id: int, message: str) -> None:
    """Record mock alert on email and sms channels."""
    for channel in ["email", "sms"]:
        print(f"[NOTIFIER] {channel.upper()} ticket={ticket_id}: {message}")
        db.add(NotificationEvent(ticket_id=ticket_id, channel=channel, message=message))
