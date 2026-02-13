"""Database configuration for Smart Helpdesk MVP."""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/helpdesk.db")
IS_SQLITE = DB_URL.startswith("sqlite")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if IS_SQLITE else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
WRITE_LOCK = threading.RLock()


if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_context() -> Generator[Session, None, None]:
    """Context manager helper for scripts."""
    db = SessionLocal()
    try:
        with WRITE_LOCK:
            db.execute(text("SELECT 1"))
            yield db
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def serialized_write() -> Generator[None, None, None]:
    """Cross-thread write lock for SQLite safety in this MVP."""
    with WRITE_LOCK:
        yield
