from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import settings

CATALOG_PATH = settings.data_dir / "catalog.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS textbooks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    source_url TEXT,
    ingest_status TEXT NOT NULL DEFAULT 'pending',
    is_fixture INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS exercises (
    id TEXT PRIMARY KEY,
    textbook_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    stem_md TEXT NOT NULL,
    answer_md TEXT,
    section TEXT,
    source_url TEXT,
    chunk_id TEXT,
    FOREIGN KEY (textbook_id) REFERENCES textbooks(id)
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(CATALOG_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_textbook(
    textbook_id: str,
    title: str,
    subject: str,
    source_url: str | None,
    is_fixture: bool,
    ingest_status: str | None = None,
) -> None:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT ingest_status FROM textbooks WHERE id = ?", (textbook_id,)
        ).fetchone()
        status = ingest_status
        if status is None:
            status = existing["ingest_status"] if existing else "pending"
        conn.execute(
            """
            INSERT INTO textbooks (id, title, subject, source_url, ingest_status, is_fixture)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                subject = excluded.subject,
                source_url = excluded.source_url,
                is_fixture = excluded.is_fixture,
                ingest_status = excluded.ingest_status
            """,
            (textbook_id, title, subject, source_url, status, int(is_fixture)),
        )


def set_ingest_status(textbook_id: str, status: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE textbooks SET ingest_status = ? WHERE id = ?",
            (status, textbook_id),
        )


def list_textbooks(subject: str | None = None) -> list[dict[str, Any]]:
    with get_db() as conn:
        if subject:
            rows = conn.execute(
                "SELECT * FROM textbooks WHERE subject = ? ORDER BY title",
                (subject,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM textbooks ORDER BY title").fetchall()
        return [dict(r) for r in rows]


def get_textbook(textbook_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM textbooks WHERE id = ?", (textbook_id,)
        ).fetchone()
        return dict(row) if row else None


def list_subjects() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT subject FROM textbooks ORDER BY subject"
        ).fetchall()
        return [r["subject"] for r in rows]


def delete_exercises_for_textbook(textbook_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM exercises WHERE textbook_id = ?", (textbook_id,))


def insert_exercise(
    exercise_id: str,
    textbook_id: str,
    subject: str,
    stem_md: str,
    answer_md: str | None,
    section: str | None,
    source_url: str | None,
    chunk_id: str | None,
) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO exercises
            (id, textbook_id, subject, stem_md, answer_md, section, source_url, chunk_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exercise_id,
                textbook_id,
                subject,
                stem_md,
                answer_md,
                section,
                source_url,
                chunk_id,
            ),
        )


def count_exercises(textbook_id: str | None = None, subject: str | None = None) -> int:
    with get_db() as conn:
        query = "SELECT COUNT(*) AS n FROM exercises WHERE 1=1"
        params: list[Any] = []
        if textbook_id:
            query += " AND textbook_id = ?"
            params.append(textbook_id)
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        return int(conn.execute(query, params).fetchone()["n"])


def next_exercise(
    exclude_ids: list[str],
    textbook_id: str | None = None,
    subject: str | None = None,
) -> dict[str, Any] | None:
    with get_db() as conn:
        query = "SELECT * FROM exercises WHERE 1=1"
        params: list[Any] = []
        if textbook_id:
            query += " AND textbook_id = ?"
            params.append(textbook_id)
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if exclude_ids:
            placeholders = ",".join("?" * len(exclude_ids))
            query += f" AND id NOT IN ({placeholders})"
            params.extend(exclude_ids)
        query += " ORDER BY id LIMIT 1"
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def get_exercise(exercise_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM exercises WHERE id = ?", (exercise_id,)
        ).fetchone()
        return dict(row) if row else None
