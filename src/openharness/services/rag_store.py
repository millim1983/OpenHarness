"""SQLite-backed storage for project-local document RAG."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from openharness.config.paths import get_project_rag_db_path
from openharness.services.rag_types import ChunkRecord, IndexedDocument


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_name, content_hash)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    embedding_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS document_artifacts (
    document_id INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    extracted_text TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    structured_json TEXT NOT NULL DEFAULT '{}',
    workflow_name TEXT NOT NULL DEFAULT '',
    prompt_source_truncated INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class RagStore:
    """Persistent project-local storage for documents and embeddings."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @classmethod
    def for_project(cls, cwd: str | Path) -> "RagStore":
        """Return the project-local RAG store."""
        return cls(get_project_rag_db_path(cwd))

    @property
    def db_path(self) -> Path:
        """Return the backing SQLite file path."""
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def upsert_document(
        self, file_name: str, content_hash: str, metadata: dict[str, object] | None = None
    ) -> int:
        """Insert or refresh one document row and clear stale chunks when needed."""
        payload = json.dumps(metadata or {}, ensure_ascii=True, sort_keys=True)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM documents WHERE file_name = ? AND content_hash = ?",
                (file_name, content_hash),
            ).fetchone()
            if row is not None:
                document_id = int(row["id"])
                connection.execute(
                    "UPDATE documents SET metadata_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (payload, document_id),
                )
                connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                return document_id

            row = connection.execute(
                "SELECT id FROM documents WHERE file_name = ?",
                (file_name,),
            ).fetchone()
            if row is not None:
                document_id = int(row["id"])
                connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                connection.execute(
                    """
                    UPDATE documents
                    SET content_hash = ?, metadata_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (content_hash, payload, document_id),
                )
                return document_id

            cursor = connection.execute(
                "INSERT INTO documents (file_name, content_hash, metadata_json) VALUES (?, ?, ?)",
                (file_name, content_hash, payload),
            )
            return int(cursor.lastrowid)

    def insert_chunks(self, document_id: int, chunks: list[ChunkRecord]) -> None:
        """Store chunk rows for one document."""
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO chunks (document_id, chunk_index, text, start_char, end_char, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        document_id,
                        chunk.chunk_index,
                        chunk.text,
                        chunk.start_char,
                        chunk.end_char,
                        json.dumps(chunk.embedding, ensure_ascii=True),
                    )
                    for chunk in chunks
                ],
            )

    def list_documents(self) -> list[IndexedDocument]:
        """Return indexed document metadata."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.file_name, d.content_hash, COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                GROUP BY d.id
                ORDER BY d.updated_at DESC
                """
            ).fetchall()
        return [
            IndexedDocument(
                id=int(row["id"]),
                file_name=str(row["file_name"]),
                content_hash=str(row["content_hash"]),
                chunk_count=int(row["chunk_count"]),
            )
            for row in rows
        ]

    def load_all_chunks(self) -> list[ChunkRecord]:
        """Return every stored chunk for similarity search."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, document_id, chunk_index, text, start_char, end_char, embedding_json
                FROM chunks
                ORDER BY document_id, chunk_index
                """
            ).fetchall()
        return [
            ChunkRecord(
                id=int(row["id"]),
                document_id=int(row["document_id"]),
                chunk_index=int(row["chunk_index"]),
                text=str(row["text"]),
                start_char=int(row["start_char"]),
                end_char=int(row["end_char"]),
                embedding=json.loads(str(row["embedding_json"])),
            )
            for row in rows
        ]

    def get_document_metadata(self, document_id: int) -> dict[str, object]:
        """Return metadata JSON for one document."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT metadata_json FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Unknown document id: {document_id}")
        return json.loads(str(row["metadata_json"]))

    def upsert_document_artifact(
        self,
        document_id: int,
        *,
        extracted_text: str,
        summary: str,
        structured: dict[str, object],
        workflow_name: str,
        prompt_source_truncated: bool,
    ) -> None:
        """Store reusable document analysis artifacts for dashboard detail views."""
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            if exists is None:
                raise ValueError(f"Unknown document id: {document_id}")
            connection.execute(
                """
                INSERT INTO document_artifacts (
                    document_id,
                    extracted_text,
                    summary,
                    structured_json,
                    workflow_name,
                    prompt_source_truncated,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(document_id) DO UPDATE SET
                    extracted_text = excluded.extracted_text,
                    summary = excluded.summary,
                    structured_json = excluded.structured_json,
                    workflow_name = excluded.workflow_name,
                    prompt_source_truncated = excluded.prompt_source_truncated,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    document_id,
                    extracted_text,
                    summary,
                    json.dumps(structured, ensure_ascii=True, sort_keys=True),
                    workflow_name,
                    1 if prompt_source_truncated else 0,
                ),
            )

    def get_document_artifact(self, document_id: int) -> dict[str, object]:
        """Return stored analysis artifacts for one document, if available."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT extracted_text, summary, structured_json, workflow_name,
                       prompt_source_truncated, updated_at
                FROM document_artifacts
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            return {}
        return {
            "extracted_text": str(row["extracted_text"]),
            "summary": str(row["summary"]),
            "structured": json.loads(str(row["structured_json"])),
            "workflow": str(row["workflow_name"]),
            "summary_source_truncated": bool(row["prompt_source_truncated"]),
            "artifact_updated_at": str(row["updated_at"]),
        }

    def delete_document(self, document_id: int) -> None:
        """Delete one document and its chunks."""
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            if cursor.rowcount == 0:
                raise ValueError(f"Unknown document id: {document_id}")

    def load_chunks_for_document(self, document_id: int) -> list[ChunkRecord]:
        """Return stored chunks for one document."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, document_id, chunk_index, text, start_char, end_char, embedding_json
                FROM chunks
                WHERE document_id = ?
                ORDER BY chunk_index
                """,
                (document_id,),
            ).fetchall()
        if not rows:
            with self._connect() as connection:
                exists = connection.execute(
                    "SELECT 1 FROM documents WHERE id = ?",
                    (document_id,),
                ).fetchone()
            if exists is None:
                raise ValueError(f"Unknown document id: {document_id}")
        return [
            ChunkRecord(
                id=int(row["id"]),
                document_id=int(row["document_id"]),
                chunk_index=int(row["chunk_index"]),
                text=str(row["text"]),
                start_char=int(row["start_char"]),
                end_char=int(row["end_char"]),
                embedding=json.loads(str(row["embedding_json"])),
            )
            for row in rows
        ]

    def update_chunk_embeddings(self, chunks: list[ChunkRecord]) -> None:
        """Replace embeddings for existing chunks."""
        with self._connect() as connection:
            connection.executemany(
                "UPDATE chunks SET embedding_json = ? WHERE id = ?",
                [(json.dumps(chunk.embedding, ensure_ascii=True), chunk.id) for chunk in chunks],
            )

    def get_file_name(self, document_id: int) -> str:
        """Return the file name for one document id."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT file_name FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Unknown document id: {document_id}")
        return str(row["file_name"])
