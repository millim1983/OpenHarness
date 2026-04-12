from __future__ import annotations

from pathlib import Path

from openharness.services.rag_store import RagStore


def test_ingestion_store_records_source_plan_job_and_review_item(tmp_path: Path) -> None:
    store = RagStore(tmp_path / "rag.sqlite3")

    source_id = store.upsert_ingestion_source(
        source_type="folder",
        name="Company docs",
        location="/data/company",
        schedule="0 2 * * *",
        scope={"include": ["*.pdf"], "batch_size": 5},
    )
    duplicate_source_id = store.upsert_ingestion_source(
        source_type="folder",
        name="Company documents",
        location="/data/company",
        schedule="0 3 * * *",
        scope={"include": ["*.pdf", "*.docx"], "batch_size": 10},
    )
    plan_id = store.create_ingestion_plan(
        source_id=source_id,
        name="Nightly small batch",
        status="draft",
        batch_size=10,
        schedule="0 3 * * *",
        scope={"folder": "/data/company"},
    )
    job_id = store.create_ingestion_job(
        plan_id=plan_id,
        status="queued",
        requested_limit=10,
    )
    review_item_id = store.upsert_ingestion_review_item(
        source_id=source_id,
        source_uri="file:///data/company/notice.pdf",
        file_name="notice.pdf",
        content_hash="abc123",
        review_status="needs_review",
        quality_score=0.82,
    )

    assert duplicate_source_id == source_id
    assert store.list_ingestion_sources()[0].name == "Company documents"
    assert store.list_ingestion_sources()[0].scope_json["include"] == ["*.pdf", "*.docx"]
    assert store.list_ingestion_plans()[0].id == plan_id
    assert store.list_ingestion_jobs()[0].id == job_id
    assert store.list_ingestion_review_items()[0].id == review_item_id
    assert store.list_ingestion_review_items()[0].review_status == "needs_review"

    store.update_ingestion_review_status(
        review_item_id,
        review_status="approved",
        notes="Looks usable.",
    )

    updated = store.list_ingestion_review_items()[0]
    assert updated.review_status == "approved"
    assert updated.notes == "Looks usable."
