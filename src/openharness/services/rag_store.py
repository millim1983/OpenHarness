"""SQLite-backed storage for project-local document RAG."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from openharness.config.paths import get_project_rag_db_path
from openharness.services.rag_types import (
    ChunkRecord,
    IndexedDocument,
    IngestionJob,
    IngestionPlan,
    IngestionReviewItem,
    IngestionSource,
)


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

CREATE TABLE IF NOT EXISTS ingestion_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    schedule TEXT NOT NULL DEFAULT '',
    scope_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, location)
);

CREATE TABLE IF NOT EXISTS ingestion_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES ingestion_sources(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    batch_size INTEGER NOT NULL DEFAULT 10,
    schedule TEXT NOT NULL DEFAULT '',
    scope_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES ingestion_plans(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'queued',
    requested_limit INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_review_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES ingestion_sources(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_uri TEXT NOT NULL,
    file_name TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'needs_review',
    quality_score REAL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, source_uri, content_hash)
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

    def upsert_ingestion_source(
        self,
        *,
        source_type: str,
        name: str,
        location: str,
        enabled: bool = True,
        schedule: str = "",
        scope: dict[str, object] | None = None,
    ) -> int:
        """Insert or update one ingestion source."""
        payload = json.dumps(scope or {}, ensure_ascii=True, sort_keys=True)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO ingestion_sources (
                    source_type, name, location, enabled, schedule, scope_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_type, location) DO UPDATE SET
                    name = excluded.name,
                    enabled = excluded.enabled,
                    schedule = excluded.schedule,
                    scope_json = excluded.scope_json,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (source_type, name, location, 1 if enabled else 0, schedule, payload),
            )
            return int(cursor.fetchone()["id"])

    def list_ingestion_sources(self) -> list[IngestionSource]:
        """Return configured ingestion sources."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, source_type, name, location, enabled, schedule, scope_json,
                       created_at, updated_at
                FROM ingestion_sources
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        return [
            IngestionSource(
                id=int(row["id"]),
                source_type=str(row["source_type"]),
                name=str(row["name"]),
                location=str(row["location"]),
                enabled=bool(row["enabled"]),
                schedule=str(row["schedule"]),
                scope_json=json.loads(str(row["scope_json"])),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def create_ingestion_plan(
        self,
        *,
        source_id: int,
        name: str,
        status: str = "draft",
        batch_size: int = 10,
        schedule: str = "",
        scope: dict[str, object] | None = None,
    ) -> int:
        """Create an ingestion plan shell for a source."""
        payload = json.dumps(scope or {}, ensure_ascii=True, sort_keys=True)
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM ingestion_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
            if exists is None:
                raise ValueError(f"Unknown ingestion source id: {source_id}")
            cursor = connection.execute(
                """
                INSERT INTO ingestion_plans (
                    source_id, name, status, batch_size, schedule, scope_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source_id, name, status, batch_size, schedule, payload),
            )
            return int(cursor.lastrowid)

    def list_ingestion_plans(self) -> list[IngestionPlan]:
        """Return ingestion plan shells."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, source_id, name, status, batch_size, schedule, scope_json,
                       created_at, updated_at
                FROM ingestion_plans
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        return [
            IngestionPlan(
                id=int(row["id"]),
                source_id=int(row["source_id"]),
                name=str(row["name"]),
                status=str(row["status"]),
                batch_size=int(row["batch_size"]),
                schedule=str(row["schedule"]),
                scope_json=json.loads(str(row["scope_json"])),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def create_ingestion_job(
        self,
        *,
        plan_id: int,
        status: str = "queued",
        requested_limit: int = 0,
        processed_count: int = 0,
        error_message: str = "",
    ) -> int:
        """Create one ingestion batch job record."""
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM ingestion_plans WHERE id = ?",
                (plan_id,),
            ).fetchone()
            if exists is None:
                raise ValueError(f"Unknown ingestion plan id: {plan_id}")
            cursor = connection.execute(
                """
                INSERT INTO ingestion_jobs (
                    plan_id, status, requested_limit, processed_count, error_message
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (plan_id, status, requested_limit, processed_count, error_message),
            )
            return int(cursor.lastrowid)

    def list_ingestion_jobs(self) -> list[IngestionJob]:
        """Return ingestion job records."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, plan_id, status, requested_limit, processed_count, error_message,
                       created_at, updated_at
                FROM ingestion_jobs
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        return [
            IngestionJob(
                id=int(row["id"]),
                plan_id=int(row["plan_id"]),
                status=str(row["status"]),
                requested_limit=int(row["requested_limit"]),
                processed_count=int(row["processed_count"]),
                error_message=str(row["error_message"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def upsert_ingestion_review_item(
        self,
        *,
        source_id: int,
        source_uri: str,
        file_name: str,
        content_hash: str,
        document_id: int | None = None,
        review_status: str = "needs_review",
        quality_score: float | None = None,
        notes: str = "",
    ) -> int:
        """Insert or update one review item for an ingested source item."""
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM ingestion_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
            if exists is None:
                raise ValueError(f"Unknown ingestion source id: {source_id}")
            cursor = connection.execute(
                """
                INSERT INTO ingestion_review_items (
                    source_id, document_id, source_uri, file_name, content_hash,
                    review_status, quality_score, notes, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_id, source_uri, content_hash) DO UPDATE SET
                    document_id = excluded.document_id,
                    file_name = excluded.file_name,
                    review_status = excluded.review_status,
                    quality_score = excluded.quality_score,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (
                    source_id,
                    document_id,
                    source_uri,
                    file_name,
                    content_hash,
                    review_status,
                    quality_score,
                    notes,
                ),
            )
            return int(cursor.fetchone()["id"])

    def list_ingestion_review_items(self) -> list[IngestionReviewItem]:
        """Return ingestion review records."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, source_id, document_id, source_uri, file_name, content_hash,
                       review_status, quality_score, notes, created_at, updated_at
                FROM ingestion_review_items
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        return [
            IngestionReviewItem(
                id=int(row["id"]),
                source_id=int(row["source_id"]),
                document_id=int(row["document_id"]) if row["document_id"] is not None else None,
                source_uri=str(row["source_uri"]),
                file_name=str(row["file_name"]),
                content_hash=str(row["content_hash"]),
                review_status=str(row["review_status"]),
                quality_score=(
                    float(row["quality_score"]) if row["quality_score"] is not None else None
                ),
                notes=str(row["notes"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def update_ingestion_review_status(
        self, review_item_id: int, *, review_status: str, notes: str = ""
    ) -> None:
        """Update review status for one ingestion item."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE ingestion_review_items
                SET review_status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (review_status, notes, review_item_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Unknown ingestion review item id: {review_item_id}")

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
