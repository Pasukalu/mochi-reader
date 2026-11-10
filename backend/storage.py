"""SQLite persistence. A connection is scoped to each operation for safe threads."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .retrieval import chunk_text


class Store:
    def __init__(self, database: str):
        self.database = database
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL,
                    created_at TEXT NOT NULL, chunk_count INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL, text TEXT NOT NULL,
                    PRIMARY KEY(document_id, ordinal)
                );
            """)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.database, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def create(self, title: str, url: str, text: str) -> dict:
        paragraphs = chunk_text(text)
        doc = {
            "id": uuid.uuid4().hex, "title": title, "url": url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "chunk_count": len(paragraphs),
        }
        with self.connect() as conn:
            conn.execute("INSERT INTO documents VALUES (:id,:title,:url,:created_at,:chunk_count)", doc)
            conn.executemany("INSERT INTO chunks VALUES (?,?,?)", [
                (doc["id"], i + 1, text) for i, text in enumerate(paragraphs)
            ])
        return doc

    def list(self) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM documents ORDER BY created_at DESC")]

    def get(self, doc_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            return dict(row) if row else None

    def chunks(self, doc_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("""SELECT c.ordinal,c.text,d.title,d.url FROM chunks c
                JOIN documents d ON c.document_id=d.id WHERE d.id=? ORDER BY c.ordinal""", (doc_id,))
            return [{**dict(row), "id": f"S{row['ordinal']}"} for row in rows]

    def delete(self, doc_id: str) -> bool:
        with self.connect() as conn:
            return conn.execute("DELETE FROM documents WHERE id=?", (doc_id,)).rowcount > 0
