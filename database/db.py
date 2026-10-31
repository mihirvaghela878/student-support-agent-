"""SQLite persistence for synthetic student records, tickets, and memory."""
from __future__ import annotations
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("STUDENT_AGENT_DB", "student_support.sqlite3"))

@contextmanager
def connect(path: str | Path | None = None):
    db = sqlite3.connect(str(path or DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db(path: str | Path | None = None) -> None:
    with connect(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS students(
          student_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, programme TEXT NOT NULL,
          semester INTEGER NOT NULL, fee_amount REAL NOT NULL, amount_paid REAL NOT NULL,
          payment_status TEXT NOT NULL, scholarship_status TEXT NOT NULL,
          scholarship_eligibility TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tickets(
          ticket_id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(student_id),
          category TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories(
          memory_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL REFERENCES students(student_id),
          fact TEXT NOT NULL, category TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(student_id, fact));
        CREATE TABLE IF NOT EXISTS conversation_messages(
          id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL, session_id TEXT NOT NULL,
          role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        """)
