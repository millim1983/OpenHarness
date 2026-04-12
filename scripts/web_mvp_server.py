"""Minimal browser UI server for the OpenHarness MVP."""

from __future__ import annotations

import base64
import json
import os
import sys
from hashlib import sha1
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from openharness.config.paths import get_project_config_dir
from openharness.config.settings import load_settings
from openharness.services.document_processing import extract_text_from_document
from openharness.services.rag_embeddings import (
    create_embedding_backend_for_profile,
    select_embedding_profile,
)
from openharness.services.rag_indexing import index_document
from openharness.services.rag_metadata import build_rag_document_metadata
from openharness.services.rag_retrieval import build_retrieval_context, retrieve_relevant_chunks
from openharness.services.rag_store import RagStore
from openharness.services.rag_types import ChunkRecord, RagRetrievalFilters
from openharness.services.web_runtime import run_single_prompt_sync
from openharness.services.workflows import (
    AnnouncementAgentRequest,
    DocumentWorkflowRequest,
    ProposalOpsRequest,
    build_proposal_ops_preview,
    run_announcement_agent,
    run_announcement_analysis,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "frontend" / "web"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8008
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
DEFAULT_RAG_TOP_K = 5
DEFAULT_PROJECT_CONTEXT = {
    "system_prompt": (
        "You are an internal business-analysis agent. Separate source facts from "
        "recommendations, keep dates and eligibility rules evidence-based, and flag missing information."
    ),
    "instruction": "Focus on deadlines, eligibility, required documents, risks, and next actions.",
    "team_context": "",
}


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def _profile_payload() -> dict[str, Any]:
    settings = load_settings()
    profiles = settings.merged_profiles()
    payload = []
    for name, profile in profiles.items():
        payload.append(
            {
                "name": name,
                "label": profile.label,
                "model": profile.last_model or profile.default_model,
                "active": name == settings.active_profile,
            }
        )
    return {"profiles": payload}


def _project_context_path() -> Path:
    return get_project_config_dir(REPO_ROOT) / "web_mvp_context.json"


def _load_project_context() -> dict[str, str]:
    path = _project_context_path()
    if not path.exists():
        return dict(DEFAULT_PROJECT_CONTEXT)
    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(DEFAULT_PROJECT_CONTEXT)
    payload = dict(DEFAULT_PROJECT_CONTEXT)
    if isinstance(raw_payload, dict):
        for key in ("system_prompt", "instruction", "team_context"):
            value = raw_payload.get(key, "")
            if isinstance(value, str):
                payload[key] = value
    return payload


def _save_project_context(payload: dict[str, Any]) -> dict[str, str]:
    current = _load_project_context()
    for key in ("system_prompt", "instruction", "team_context"):
        value = payload.get(key, current[key])
        current[key] = value.strip() if isinstance(value, str) else ""
    path = _project_context_path()
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return current


def _select_embedding_profile(
    settings: Any, chat_profile_name: str, requested_profile_name: str = ""
) -> str:
    env_profile = os.environ.get("OPENHARNESS_RAG_EMBEDDING_PROFILE", "").strip()
    return select_embedding_profile(
        settings,
        chat_profile_name=chat_profile_name,
        requested_profile_name=requested_profile_name or env_profile,
    )


def _document_rag_status(store: RagStore) -> dict[str, Any]:
    documents = store.list_documents()
    payload_documents: list[dict[str, Any]] = []
    for document in documents:
        metadata = store.get_document_metadata(document.id)
        payload_documents.append(
            {
                "id": document.id,
                "file_name": document.file_name,
                "chunk_count": document.chunk_count,
                "embedding_profile": str(metadata.get("embedding_profile", "")),
                "chat_profile": str(metadata.get("chat_profile", "")),
                "source": str(metadata.get("source", "")),
                "document_type": str(metadata.get("document_type", "unknown")),
                "title": str(metadata.get("title", "")),
                "ministry": str(metadata.get("ministry", "")),
                "agency": str(metadata.get("agency", "")),
                "business_type": str(metadata.get("business_type", "")),
                "rd_or_non_rd": str(metadata.get("rd_or_non_rd", "")),
                "submission_deadline": str(metadata.get("submission_deadline", "")),
            }
        )
    return {
        "indexed_document_count": len(documents),
        "indexed_chunk_count": sum(document.chunk_count for document in documents),
        "documents": payload_documents,
    }


def _index_document_for_rag(
    *,
    chat_profile_name: str,
    file_name: str,
    extracted_text: str,
    instruction: str,
    team_context: str,
    structured_analysis: dict[str, Any] | None = None,
    system_prompt: str = "",
) -> dict[str, Any]:
    settings = load_settings()
    embedding_profile_name = _select_embedding_profile(settings, chat_profile_name)
    embedding_backend = create_embedding_backend_for_profile(
        embedding_profile_name, settings=settings
    )
    store = RagStore.for_project(REPO_ROOT)
    content_hash = sha1(extracted_text.encode("utf-8")).hexdigest()
    document_id = index_document(
        cwd=str(REPO_ROOT),
        file_name=file_name,
        extracted_text=extracted_text,
        embedding_backend=embedding_backend,
        store=store,
        metadata=build_rag_document_metadata(
            file_name=file_name,
            extracted_text=extracted_text,
            embedding_profile=embedding_profile_name,
            chat_profile=chat_profile_name,
            instruction=instruction,
            has_team_context=bool(team_context.strip()),
            source_kind="web_mvp_upload",
            structured_analysis=structured_analysis,
        ),
    )
    source_id = store.upsert_ingestion_source(
        source_type="upload",
        name="Web MVP uploads",
        location="web_mvp_uploads",
        schedule="manual",
        scope={"accepted_file": file_name},
    )
    review_item_id = store.upsert_ingestion_review_item(
        source_id=source_id,
        document_id=document_id,
        source_uri=f"upload://{file_name}",
        file_name=file_name,
        content_hash=content_hash,
        review_status="needs_review",
        notes="Created from Web MVP document upload.",
    )
    return {
        "enabled": True,
        "embedding_profile": embedding_profile_name,
        "indexed_document_id": document_id,
        "ingestion_source_id": source_id,
        "ingestion_review_item_id": review_item_id,
        **_document_rag_status(store),
    }


def _chat_rag_context(
    profile_name: str, message: str, filters: RagRetrievalFilters | None = None
) -> tuple[str, dict[str, Any]]:
    store = RagStore.for_project(REPO_ROOT)
    document_status = _document_rag_status(store)
    if document_status["indexed_chunk_count"] == 0:
        return "", {
            "enabled": False,
            "reason": "No indexed document chunks yet.",
            **document_status,
        }

    settings = load_settings()
    embedding_profile_name = _select_embedding_profile(settings, profile_name)
    embedding_backend = create_embedding_backend_for_profile(
        embedding_profile_name, settings=settings
    )
    chunks = retrieve_relevant_chunks(
        cwd=str(REPO_ROOT),
        query=message,
        embedding_backend=embedding_backend,
        store=store,
        top_k=DEFAULT_RAG_TOP_K,
        filters=filters,
    )
    context = build_retrieval_context(chunks)
    applied_filters = filters.as_dict() if filters is not None and filters.has_values() else {}
    return context, {
        "enabled": bool(context),
        "embedding_profile": embedding_profile_name,
        "retrieved_chunk_count": len(chunks),
        "applied_filters": applied_filters,
        "reason": ""
        if context
        else "No retrieved chunks matched the question and active RAG filters.",
        "sources": [
            {
                "file_name": chunk.file_name,
                "chunk_index": chunk.chunk_index,
                "score": round(chunk.score, 4),
                "title": chunk.title,
                "document_type": chunk.document_type,
                "ministry": chunk.ministry,
                "agency": chunk.agency,
                "rd_or_non_rd": chunk.rd_or_non_rd,
                "business_type": chunk.business_type,
            }
            for chunk in chunks
        ],
        **document_status,
    }


def _message_with_rag_context(message: str, context: str) -> str:
    if not context:
        return message
    return (
        "Use the retrieved document context below when it is relevant. "
        "If the context does not answer the question, say what is missing.\n\n"
        f"{context}\n\n"
        "User question:\n"
        f"{message}"
    )


def _run_chat(
    profile_name: str,
    message: str,
    rag_filters: RagRetrievalFilters | None = None,
    system_prompt: str = "",
) -> dict[str, Any]:
    settings = load_settings()
    profiles = settings.merged_profiles()
    if profile_name not in profiles:
        raise ValueError(f"Unknown profile: {profile_name}")

    rag_context, rag_status = _chat_rag_context(profile_name, message, rag_filters)

    result = run_single_prompt_sync(
        profile_name=profile_name,
        message=_message_with_rag_context(message, rag_context),
        cwd=str(REPO_ROOT),
        system_prompt=system_prompt,
    )
    result["rag"] = rag_status
    return result


def _run_document_summary(
    profile_name: str,
    filename: str,
    file_data_b64: str,
    instruction: str,
    team_context: str,
    system_prompt: str = "",
) -> dict[str, Any]:
    try:
        file_bytes = base64.b64decode(file_data_b64.encode("utf-8"), validate=True)
    except ValueError as exc:
        raise ValueError("Invalid uploaded file payload.") from exc

    if not filename.strip():
        raise ValueError("`file_name` is required.")
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file is too large for the MVP limit (2 MB).")

    extracted_text = extract_text_from_document(filename, file_bytes)
    workflow_result = run_announcement_analysis(
        DocumentWorkflowRequest(
            profile_name=profile_name,
            file_name=filename,
            extracted_text=extracted_text,
            system_prompt=system_prompt,
            instruction=instruction,
            team_context=team_context,
        ),
        cwd=str(REPO_ROOT),
    )
    rag_status = _index_document_for_rag(
        chat_profile_name=profile_name,
        file_name=filename,
        extracted_text=extracted_text,
        instruction=instruction,
        team_context=team_context,
        structured_analysis=workflow_result.structured,
        system_prompt=system_prompt,
    )
    store = RagStore.for_project(REPO_ROOT)
    document_id = int(rag_status["indexed_document_id"])
    store.upsert_document_artifact(
        document_id,
        extracted_text=extracted_text,
        summary=workflow_result.summary,
        structured=workflow_result.structured,
        workflow_name=workflow_result.workflow_name,
        prompt_source_truncated=workflow_result.prompt_source_truncated,
    )
    proposal_ops = build_proposal_ops_preview(
        ProposalOpsRequest(
            file_name=filename,
            structured_analysis=workflow_result.structured,
            instruction=instruction,
            team_context=team_context,
        )
    )
    announcement_agent = run_announcement_agent(
        AnnouncementAgentRequest(
            file_name=filename,
            file_bytes=file_bytes,
            structured_analysis=workflow_result.structured,
            instruction=instruction,
            team_context=team_context,
        )
    )
    return {
        "profile": profile_name,
        "file_name": filename,
        "extracted_text": extracted_text,
        "extracted_char_count": len(extracted_text),
        "workflow": workflow_result.workflow_name,
        "summary": workflow_result.summary,
        "structured": workflow_result.structured,
        "proposal_ops": proposal_ops,
        "announcement_agent": announcement_agent,
        "summary_source_truncated": workflow_result.prompt_source_truncated,
        "rag": rag_status,
    }


def _list_rag_documents() -> dict[str, Any]:
    store = RagStore.for_project(REPO_ROOT)
    return {
        "db_path": str(store.db_path),
        **_document_rag_status(store),
    }


def _ingestion_source_payload(source: Any) -> dict[str, Any]:
    return {
        "id": source.id,
        "source_type": source.source_type,
        "name": source.name,
        "location": source.location,
        "enabled": source.enabled,
        "schedule": source.schedule,
        "scope": source.scope_json,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }


def _ingestion_plan_payload(plan: Any) -> dict[str, Any]:
    return {
        "id": plan.id,
        "source_id": plan.source_id,
        "name": plan.name,
        "status": plan.status,
        "batch_size": plan.batch_size,
        "schedule": plan.schedule,
        "scope": plan.scope_json,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


def _ingestion_job_payload(job: Any) -> dict[str, Any]:
    return {
        "id": job.id,
        "plan_id": job.plan_id,
        "status": job.status,
        "requested_limit": job.requested_limit,
        "processed_count": job.processed_count,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _ingestion_review_item_payload(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_id": item.source_id,
        "document_id": item.document_id,
        "source_uri": item.source_uri,
        "file_name": item.file_name,
        "content_hash": item.content_hash,
        "review_status": item.review_status,
        "quality_score": item.quality_score,
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _ingestion_state() -> dict[str, Any]:
    store = RagStore.for_project(REPO_ROOT)
    sources = store.list_ingestion_sources()
    plans = store.list_ingestion_plans()
    jobs = store.list_ingestion_jobs()
    review_items = store.list_ingestion_review_items()
    return {
        "sources": [_ingestion_source_payload(source) for source in sources],
        "plans": [_ingestion_plan_payload(plan) for plan in plans],
        "jobs": [_ingestion_job_payload(job) for job in jobs],
        "review_items": [_ingestion_review_item_payload(item) for item in review_items],
        "summary": {
            "source_count": len(sources),
            "plan_count": len(plans),
            "job_count": len(jobs),
            "review_item_count": len(review_items),
            "needs_review_count": sum(
                1 for item in review_items if item.review_status == "needs_review"
            ),
            "approved_count": sum(1 for item in review_items if item.review_status == "approved"),
        },
    }


def _update_ingestion_review_item(payload: dict[str, Any]) -> dict[str, Any]:
    review_item_id = int(payload.get("review_item_id", 0))
    review_status = str(payload.get("review_status", "")).strip()
    notes = str(payload.get("notes", "")).strip()
    allowed_statuses = {"needs_review", "approved", "rejected", "failed", "stale"}
    if review_item_id <= 0:
        raise ValueError("`review_item_id` is required.")
    if review_status not in allowed_statuses:
        raise ValueError(f"`review_status` must be one of: {', '.join(sorted(allowed_statuses))}")
    store = RagStore.for_project(REPO_ROOT)
    store.update_ingestion_review_status(review_item_id, review_status=review_status, notes=notes)
    return _ingestion_state()


def _get_rag_document_detail(document_id: int) -> dict[str, Any]:
    store = RagStore.for_project(REPO_ROOT)
    metadata = store.get_document_metadata(document_id)
    chunks = store.load_chunks_for_document(document_id)
    artifact = store.get_document_artifact(document_id)
    fallback_text = "\n\n".join(chunk.text for chunk in chunks)
    return {
        "id": document_id,
        "file_name": store.get_file_name(document_id),
        "metadata": metadata,
        "chunks": [
            {
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
            }
            for chunk in chunks
        ],
        "artifact_available": bool(artifact),
        "extracted_text": str(artifact.get("extracted_text", fallback_text)),
        "summary": str(artifact.get("summary", "")),
        "structured": artifact.get("structured", {}),
        "workflow": str(artifact.get("workflow", "")),
        "summary_source_truncated": bool(artifact.get("summary_source_truncated", False)),
        "artifact_updated_at": str(artifact.get("artifact_updated_at", "")),
    }


def _delete_rag_document(document_id: int) -> dict[str, Any]:
    store = RagStore.for_project(REPO_ROOT)
    store.delete_document(document_id)
    return {
        "deleted_document_id": document_id,
        **_list_rag_documents(),
    }


def _reindex_rag_document(document_id: int, profile_name: str) -> dict[str, Any]:
    settings = load_settings()
    embedding_profile_name = _select_embedding_profile(settings, profile_name)
    embedding_backend = create_embedding_backend_for_profile(
        embedding_profile_name, settings=settings
    )
    store = RagStore.for_project(REPO_ROOT)
    chunks = store.load_chunks_for_document(document_id)
    if not chunks:
        raise ValueError(f"Document has no chunks to reindex: {document_id}")
    vectors = embedding_backend.embed_texts([chunk.text for chunk in chunks])
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding backend returned an unexpected number of vectors.")
    store.update_chunk_embeddings(
        [
            ChunkRecord(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                embedding=vector,
            )
            for chunk, vector in zip(chunks, vectors)
        ]
    )
    return {
        "reindexed_document_id": document_id,
        "embedding_profile": embedding_profile_name,
        **_list_rag_documents(),
    }


class WebMvpHandler(SimpleHTTPRequestHandler):
    """Serve static files and a tiny chat API."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/api/profiles":
            payload = _profile_payload()
            self._send_json(HTTPStatus.OK, payload)
            return
        if parsed_path.path == "/api/project-context":
            self._send_json(HTTPStatus.OK, _load_project_context())
            return
        if parsed_path.path == "/api/rag/documents":
            self._send_json(HTTPStatus.OK, _list_rag_documents())
            return
        if parsed_path.path == "/api/ingestion/state":
            self._send_json(HTTPStatus.OK, _ingestion_state())
            return
        if parsed_path.path == "/api/ingestion/sources":
            self._send_json(HTTPStatus.OK, {"sources": _ingestion_state()["sources"]})
            return
        if parsed_path.path == "/api/ingestion/plans":
            self._send_json(HTTPStatus.OK, {"plans": _ingestion_state()["plans"]})
            return
        if parsed_path.path == "/api/ingestion/jobs":
            self._send_json(HTTPStatus.OK, {"jobs": _ingestion_state()["jobs"]})
            return
        if parsed_path.path == "/api/ingestion/review-items":
            self._send_json(HTTPStatus.OK, {"review_items": _ingestion_state()["review_items"]})
            return
        if parsed_path.path == "/api/rag/document":
            query = parse_qs(parsed_path.query)
            try:
                document_id = int(query.get("document_id", ["0"])[0])
                if document_id <= 0:
                    raise ValueError("`document_id` is required.")
                self._send_json(HTTPStatus.OK, _get_rag_document_detail(document_id))
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:  # pragma: no cover - defensive endpoint guard
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path in {"/", "/index.html"}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/chat":
            self._handle_chat_request()
            return
        if self.path == "/api/process-document":
            self._handle_document_request()
            return
        if self.path == "/api/project-context":
            self._handle_project_context_request()
            return
        if self.path == "/api/rag/delete":
            self._handle_rag_delete_request()
            return
        if self.path == "/api/rag/reindex":
            self._handle_rag_reindex_request()
            return
        if self.path == "/api/ingestion/review":
            self._handle_ingestion_review_request()
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})

    def _handle_chat_request(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            message = str(payload.get("message", "")).strip()
            profile_name = str(payload.get("profile", "")).strip()
            if not message:
                raise ValueError("`message` is required.")
            if not profile_name:
                raise ValueError("`profile` is required.")
            system_prompt = str(payload.get("system_prompt", "")).strip()
            result = _run_chat(
                profile_name,
                message,
                _rag_filters_from_payload(payload),
                system_prompt,
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except RuntimeError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive endpoint guard
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, result)

    def _handle_document_request(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            profile_name = str(payload.get("profile", "")).strip()
            file_name = str(payload.get("file_name", "")).strip()
            file_data_b64 = str(payload.get("file_data_base64", "")).strip()
            instruction = str(payload.get("instruction", "")).strip()
            team_context = str(payload.get("team_context", "")).strip()
            system_prompt = str(payload.get("system_prompt", "")).strip()
            if not profile_name:
                raise ValueError("`profile` is required.")
            if not file_data_b64:
                raise ValueError("`file_data_base64` is required.")
            result = _run_document_summary(
                profile_name,
                file_name,
                file_data_b64,
                instruction,
                team_context,
                system_prompt,
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except RuntimeError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive endpoint guard
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, result)

    def _handle_project_context_request(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            result = _save_project_context(payload)
        except Exception as exc:  # pragma: no cover - defensive endpoint guard
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, result)

    def _handle_rag_delete_request(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            document_id = int(payload.get("document_id", 0))
            if document_id <= 0:
                raise ValueError("`document_id` is required.")
            result = _delete_rag_document(document_id)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive endpoint guard
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, result)

    def _handle_rag_reindex_request(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            document_id = int(payload.get("document_id", 0))
            profile_name = str(payload.get("profile", "")).strip()
            if document_id <= 0:
                raise ValueError("`document_id` is required.")
            if not profile_name:
                raise ValueError("`profile` is required.")
            result = _reindex_rag_document(document_id, profile_name)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except RuntimeError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive endpoint guard
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, result)

    def _handle_ingestion_review_request(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            result = _update_ingestion_review_item(payload)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive endpoint guard
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, result)

    def _read_json_body(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Request body is required."})
            return None
        raw_body = self.rfile.read(content_length)

        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON body: {exc}"})
            return None

    def log_message(self, format: str, *args: Any) -> None:
        message = format % args
        sys.stdout.write(f"[web-mvp] {self.address_string()} {message}\n")

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        response = _json_bytes(payload)
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def _rag_filters_from_payload(payload: dict[str, Any]) -> RagRetrievalFilters:
    raw_filters = payload.get("rag_filters", {})
    if not isinstance(raw_filters, dict):
        raise ValueError("`rag_filters` must be an object when provided.")
    return RagRetrievalFilters(
        document_type=str(raw_filters.get("document_type", "")).strip(),
        ministry=str(raw_filters.get("ministry", "")).strip(),
        agency=str(raw_filters.get("agency", "")).strip(),
        rd_or_non_rd=str(raw_filters.get("rd_or_non_rd", "")).strip(),
        business_type=str(raw_filters.get("business_type", "")).strip(),
    )


def main() -> None:
    host = os.environ.get("OPENHARNESS_WEB_HOST", DEFAULT_HOST)
    port = int(os.environ.get("OPENHARNESS_WEB_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer((host, port), WebMvpHandler)
    print(f"OpenHarness Web MVP running at http://{host}:{port}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web MVP server.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
