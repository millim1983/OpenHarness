# Web MVP Progress

## Goal
Build the smallest possible browser UI on top of OpenHarness so we can:
- choose a configured model/profile
- send one message
- receive one response in the browser

This is intentionally a minimal MVP, not the final internal agent product.

## Current Status
Completed:
- WSL workspace migration finished
- Main working repo is now `~/workspace/OpenHarness`
- Python virtual environment works
- Node/npm issue in WSL fixed
- OpenHarness profiles load correctly
- `openai-compatible` profile works
- `gemini-compatible` profile works
- Gemini API call tested successfully in CLI
- Minimal browser UI works
- Browser UI successfully sent a message with Gemini and received an answer
- Browser UI can upload a document, extract text, and request a one-shot summary
- Web MVP browser requests now reuse the internal OpenHarness runtime instead of shelling out to the CLI
- PDF extraction is now a declared project dependency via `pypdf`
- Document processing now returns structured insights for action items, deadlines, risks, and owners
- Document analysis now supports announcement-specific fields plus team-context-based internal execution planning
- Announcement analysis has been separated into a reusable workflow layer so later business workflows can share the same document stack
- Local RAG core scaffolding has been added with SQLite storage, chunking, embeddings, and retrieval services
- RAG storage now resolves to a per-project SQLite database under `~/.openharness/data/rag/<project-name>-<hash>/documents.sqlite3`
- RAG core has focused unit tests covering chunking, indexing, retrieval, and prompt-context rendering
- Web document upload now attempts to index extracted text into the project-local RAG store
- Web chat now retrieves relevant indexed chunks and injects them into the runtime prompt when available
- Browser status text now reports RAG indexing/retrieval status after upload and chat requests

## Files Added For The Web MVP
- `frontend/web/index.html`
- `frontend/web/styles.css`
- `frontend/web/app.js`
- `scripts/web_mvp_server.py`

## What Each File Does
### `frontend/web/index.html`
Contains the first browser UI layout:
- profile selector
- message input
- send button
- answer panel

### `frontend/web/styles.css`
Contains the MVP styling for the browser UI.

### `frontend/web/app.js`
Handles:
- loading available profiles from the backend
- sending chat requests
- rendering the answer
- copy button behavior
- uploading one document and rendering extracted text + summary + structured insights + internal execution plan

### `scripts/web_mvp_server.py`
A very small Python server that:
- serves the web UI
- exposes `/api/profiles`
- exposes `/api/chat`
- exposes `/api/process-document`
- reuses existing OpenHarness settings and profiles
- runs one prompt through the internal OpenHarness runtime and returns the answer

### `src/openharness/services/document_processing.py`
Contains reusable document-processing helpers for the web MVP:
- extract text from `.txt`, `.md`, `.csv`, `.json`, `.yaml`, `.yml`, `.docx`
- extract from `.pdf` through `pypdf`
- build the one-shot announcement-analysis prompt with truncation guardrails
- parse structured announcement-analysis JSON from the model
- support optional team context for internal execution planning

### `src/openharness/services/workflows/announcement.py`
Contains the first domain workflow on top of the shared document layer:
- runs the announcement-analysis prompt
- parses the structured result
- returns a reusable workflow payload for the web layer

### `src/openharness/services/web_runtime.py`
Contains reusable one-shot runtime helpers for the web MVP:
- executes a browser request through the internal runtime
- avoids spawning `python -m openharness --print` for each request
- keeps web behavior aligned with the main engine path

### `src/openharness/services/rag_*.py`
Contains the first reusable RAG core:
- SQLite-backed local document store
- paragraph-aware chunking
- embedding backend interface plus OpenAI-compatible backend
- cosine-similarity retrieval helpers

RAG file split:
- `src/openharness/services/rag_types.py`
  - shared dataclasses and the embedding backend protocol
- `src/openharness/services/rag_store.py`
  - SQLite schema, document upsert, chunk insert/list, and document lookup
- `src/openharness/services/rag_indexing.py`
  - paragraph-aware chunking, content hashing, embedding, and persistence
- `src/openharness/services/rag_embeddings.py`
  - OpenAI-compatible embedding backend and profile-based backend creation
- `src/openharness/services/rag_retrieval.py`
  - cosine similarity search and prompt-friendly context rendering

### `src/openharness/config/paths.py`
Now also contains project-scoped RAG storage helpers:
- `get_project_rag_dir(cwd)`
- `get_project_rag_db_path(cwd)`

## How To Start Development Next Time
Open WSL and run:

```bash
cd ~/workspace/OpenHarness
source .venv/bin/activate
uv sync
```

If the prompt shows something like (openharness-ai), the virtual environment is active.

## How To Run The Web MVP
From ~/workspace/OpenHarness:

```bash
bash scripts/run_web_mvp.sh
```

Then open:

`http://127.0.0.1:8013`

Use `scripts/run_web_mvp.sh` instead of invoking `scripts/web_mvp_server.py` directly in Codex/snap
sessions. The script pins:

- `OPENHARNESS_CONFIG_DIR=/home/kiakiakia/.openharness`
- `OPENHARNESS_DATA_DIR=/home/kiakiakia/.openharness/data`

Without those variables, snap-based sessions may resolve `Path.home()` to
`/home/kiakiakia/snap/codex/34` and create a separate empty RAG database.

## What Has Been Verified
Verified successfully:

browser page loads
profile list loads
gemini-compatible appears in dropdown
sending a message works
Gemini returns a response in the browser
document text extraction has unit coverage for text and docx
announcement workflow has unit coverage with a mocked runtime response
RAG core has unit coverage for chunking, indexing, retrieval, and retrieval-context rendering

## Current Architecture
Temporary MVP architecture:

Browser UI
frontend/web/*
Tiny Python web server
scripts/web_mvp_server.py
OpenHarness runtime
existing OpenHarness CLI/runtime/config system

## Profile/config source
~/.openharness/settings.json
~/.openharness/credentials.json

## Important Notes
The real working repository is ~/workspace/OpenHarness
Do not continue development in E:\github\OpenHarness
The browser MVP is intentionally simple and thin
The browser MVP chat and document panels are still separate flows
The general chat box now consumes indexed uploaded-document context when retrieval succeeds
The announcement analyzer now distinguishes extracted announcement facts from recommended strategy/internal execution items
The announcement analyzer is now implemented as a workflow module, not hard-coded directly into the web server
The RAG core is now wired into the upload->chat loop in the web MVP
The current `/api/process-document` route extracts text, runs the announcement workflow, and attempts to index the upload into the RAG store
The current `/api/chat` route retrieves relevant indexed chunks and prepends them to the runtime prompt when retrieval succeeds
Embedding backend creation currently supports only OpenAI-compatible profiles
If no embedding profile or credentials are available, RAG indexing/retrieval should fail clearly instead of silently falling back or pretending to work


## RAG Embedding Requirement

RAG is not just document summarization. The intended flow is:
1. Upload a document.
2. Extract text once.
3. Split it into chunks.
4. Create embeddings for each chunk.
5. Store document/chunk/embedding rows in the project-local SQLite RAG database.
6. On later chat requests, embed the user question, retrieve relevant stored chunks, and attach those chunks as answer context.

This avoids repeatedly sending the whole uploaded document to the LLM. The LLM should see only the retrieved context needed for the current question.

Required for proper RAG:
- An OpenAI-compatible embedding profile in `~/.openharness/settings.json`.
- A matching API key in `~/.openharness/credentials.json` or `OPENAI_API_KEY`.
- Current default embedding model: `text-embedding-3-small`.

Current implementation behavior:
- The web MVP chooses `OPENHARNESS_RAG_EMBEDDING_PROFILE` when set.
- Otherwise it uses a real OpenAI provider profile when the chat profile is OpenAI.
- Otherwise it uses the `openai-compatible` profile.
- There is no fake/local embedding fallback, by design. If embeddings fail, the user should fix the embedding profile/key rather than getting a misleading partial RAG flow.

## Where To Edit For Common Changes
Change colors / styling
Edit:

frontend/web/styles.css
Change frontend behavior
Edit:

frontend/web/app.js
Change server behavior
Edit:

scripts/web_mvp_server.py
Change text extraction rules
Edit:

src/openharness/services/document_processing.py
Change RAG indexing, storage, retrieval, or embeddings
Edit:

src/openharness/services/rag_indexing.py
src/openharness/services/rag_store.py
src/openharness/services/rag_retrieval.py
src/openharness/services/rag_embeddings.py
Change model/profile definitions
Edit:

~/.openharness/settings.json
Change API keys
Edit:

~/.openharness/credentials.json

## Recommended Next Step
The most sensible next step is:
Harden the RAG web loop with explicit embedding-profile selection, document index visibility, and a real browser smoke test.

Concrete implementation order:
1. Add an embedding-profile selector or config value for RAG.
2. Add an indexed-document panel that shows file names and chunk counts.
3. Add a reset/reindex path for the project-local RAG store.
4. Run a real browser upload->chat test with an OpenAI-compatible embedding profile configured.
5. Decide whether workflow generation should also use retrieval context or remain one-shot over the uploaded text.

After that, move toward streaming responses or a multi-turn chat history.


## OpenAI Compatibility Note
During MVP verification:
- `openai-compatible` with `gpt-5.4-mini` failed
- error: `max_tokens` is not supported with this model, and `max_completion_tokens` is required
- temporary workaround:
  - changed `openai-compatible` model to `gpt-4.1`
- result:
  - `gpt-4.1` works correctly in CLI
  - browser MVP can use OpenAI after this change

This should later be fixed in the OpenAI request layer so newer GPT-5 models can be supported properly.

## 2026-04-11 RAG Web Loop Update

Developed:
- Connected web document uploads to the local RAG indexing path.
- Connected web chat to retrieval-backed prompt context when indexed chunks are available.
- Added visible browser status text for RAG indexing and retrieval outcomes.

Changed files:
- `scripts/web_mvp_server.py`: selects an OpenAI-compatible embedding profile, indexes extracted document text, retrieves relevant chunks for chat, and returns RAG status metadata.
- `frontend/web/app.js`: renders RAG indexing/retrieval status after document upload and chat responses.
- `frontend/web/index.html`: updates chat helper copy to explain upload-backed RAG behavior.
- `tests/test_services/test_web_mvp_rag.py`: adds mocked tests for RAG prompt injection and upload indexing status.
- `docs/WEB_MVP_PROGRESS.md`: records the completed RAG web-loop step and next tasks.

Verified:
- `uv run pytest tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_web_runtime.py`
- `uv run ruff check scripts/web_mvp_server.py tests/test_services/test_web_mvp_rag.py`

Next plan:
- Add explicit RAG embedding-profile selection/configuration.
- Expose indexed document status and reset/reindex controls in the UI.
- Run a real browser upload->chat smoke test with configured embeddings.


## 2026-04-11 RAG Management API Update

Developed:
- Added API support for listing indexed RAG documents.
- Added API support for deleting indexed RAG documents and their chunks.
- Added API support for reindexing an existing document's stored chunks with the configured embedding profile.

Changed files:
- `src/openharness/services/rag_store.py`: added document metadata lookup, delete, per-document chunk loading, and chunk embedding update helpers.
- `scripts/web_mvp_server.py`: added `GET /api/rag/documents`, `POST /api/rag/delete`, and `POST /api/rag/reindex` helpers/routes.
- `tests/test_services/test_web_mvp_rag.py`: added management helper coverage for list, reindex, and delete.
- `docs/WEB_MVP_PROGRESS.md`: recorded the metadata strategy decision and API work.

Metadata strategy decision:
- Do not force announcement-specific fields onto every uploaded document yet.
- Keep current generic `metadata_json` storage, then design a layered metadata model: common fields for every document plus optional typed fields for announcements, regulations, technical documents, and company/team documents.
- If a new required field is discovered later, existing documents can only receive that field reliably if the original text or enough chunk text remains available; otherwise the source document must be reprocessed. Current chunks retain text, so many metadata backfills can be done from stored chunks, but document-level extraction may be less reliable than reprocessing the original source.

Verified:
- `uv run pytest tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_web_runtime.py`
- `uv run ruff check src/openharness/services/rag_store.py scripts/web_mvp_server.py tests/test_services/test_web_mvp_rag.py`

Next plan:
- Design the layered metadata schema before adding announcement-specific metadata fields.
- Add the browser RAG document management UI after the schema decision.
- Add source chunk display under chat answers.

## 2026-04-11 RAG Development Summary

Developed:
- Built the local RAG core around project-scoped SQLite storage, document chunking, OpenAI-compatible embeddings, cosine retrieval, and retrieval-context prompt rendering.
- Connected web document upload to the RAG indexing flow: uploaded files are extracted, chunked, embedded, and stored in the project-local RAG database.
- Connected web chat to RAG retrieval: chat questions are embedded, relevant stored chunks are retrieved, and the retrieved text is attached to the LLM prompt as context.
- Added RAG status reporting to the browser response flow so upload/chat can show whether indexed chunks or retrieved chunks were used.
- Added RAG management API helpers/routes for listing indexed documents, deleting a document and its chunks, and reindexing an existing document stored chunks.

Current storage behavior:
- RAG data is stored in a project-scoped SQLite database under ~/.openharness/data/rag/<project-name>-<hash>/documents.sqlite3.
- For the current OpenHarness workspace, the observed DB path is /home/kiakiakia/.openharness/data/rag/OpenHarness-79e1287ffb53/documents.sqlite3.
- Data persists after browser refresh, server restart, and chat session end because it is stored on disk, not in memory.
- The documents table stores file name, content hash, metadata JSON, and timestamps.
- The chunks table stores chunk text, character offsets, and embedding JSON.
- Uploading the same file name with new content refreshes that document stored chunks instead of blindly accumulating duplicates.

Current answer flow:
- During upload analysis, the LLM reads the extracted document text to produce summary, structured insights, and internal execution planning.
- During later chat, the server does not reread the uploaded file from disk. It embeds the user question, retrieves relevant stored chunks from the RAG DB, and sends only those retrieved chunks as context.
- This reduces repeated full-document token usage, but the upload analysis step itself is still a full extracted-text workflow today.

Changed files:
- src/openharness/config/paths.py: added project-scoped RAG data path helpers.
- src/openharness/services/rag_types.py: added shared RAG dataclasses and embedding protocol.
- src/openharness/services/rag_store.py: added SQLite persistence, document/chunk listing, metadata lookup, delete, per-document chunk loading, and embedding update helpers.
- src/openharness/services/rag_indexing.py: added chunking, content hashing, embedding, and persistence pipeline.
- src/openharness/services/rag_embeddings.py: added OpenAI-compatible embedding backend and profile-based backend creation.
- src/openharness/services/rag_retrieval.py: added cosine retrieval and prompt-context rendering.
- scripts/web_mvp_server.py: wired upload indexing, chat retrieval, RAG status, and RAG document management APIs.
- frontend/web/app.js: added RAG status display after upload and chat responses.
- frontend/web/index.html: updated chat helper copy for uploaded-document RAG behavior.
- tests/test_services/test_rag_core.py: covers chunking, indexing, retrieval, and retrieval context rendering.
- tests/test_services/test_web_mvp_rag.py: covers web RAG prompt injection plus list/reindex/delete helpers.

Metadata strategy decision:
- Do not hard-code announcement-specific metadata fields onto every uploaded document yet.
- Use a layered metadata model next: common metadata for every document plus optional typed metadata for announcements, regulations/operating guidelines, technical documents, and company/team documents.
- Common fields should likely include document_type, title, source_file, content_hash, uploaded_at, embedding_profile, chunk_count, and optional tags.
- Announcement fields should likely include ministry, agency, business_type, rd_or_non_rd, program_name, submission_channel, deadline, contacts, and related regulation references.
- Regulation fields should likely include regulation_owner, applies_to_business_type, effective_date, article_scope, and linked announcement/business categories.
- Technical document fields should likely include technology_domain, product_or_system, version, and spec scope.
- If a new metadata field such as d becomes required later, existing documents can be backfilled from stored chunk text when the needed evidence is present in chunks. If the field requires whole-document structure or omitted source details, the original document must be reprocessed. This means the next design should decide whether to persist extracted full text or an original-file reference for reliable metadata backfills.

Next plan:
- Design and document the layered metadata schema before adding announcement-specific metadata extraction.
- Add a browser RAG document management UI that calls the list/delete/reindex APIs.
- Show indexed document list, chunk counts, embedding profile, and DB/storage status in that UI.
- Add source chunk display under chat answers, including document name, chunk index, and similarity score.
- Decide whether upload analysis should remain a full-text one-shot workflow or move toward metadata-aware/RAG-assisted analysis for very large documents.

Verified:
- uv run pytest tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_web_runtime.py
- uv run ruff check src/openharness/services/rag_store.py scripts/web_mvp_server.py tests/test_services/test_web_mvp_rag.py

## 2026-04-11 RAG Dashboard Update

Developed:
- Added a browser RAG Document Dashboard section to the Web MVP.
- The dashboard loads indexed RAG documents from `GET /api/rag/documents`.
- The dashboard displays total indexed documents, total chunks, the SQLite DB path, file names, chunk counts, embedding profile, and chat profile when available.
- Added dashboard actions for deleting a RAG document and reindexing a document's existing stored chunks.
- Added a RAG Sources panel under chat answers that shows retrieved document file name, chunk index, and similarity score.

Changed files:
- `frontend/web/index.html`: added the RAG Document Dashboard and RAG Sources areas.
- `frontend/web/app.js`: added RAG document loading, rendering, delete/reindex actions, and source display after chat responses.
- `frontend/web/styles.css`: added dashboard, document row, action button, and source panel styles.
- `scripts/web_mvp_server.py`: completed delete/reindex route handlers and enriched document list payload with embedding/chat profile metadata.
- `tests/test_services/test_web_mvp_rag.py`: updated fake store coverage for document metadata.
- `docs/WEB_MVP_PROGRESS.md`: recorded the dashboard update.

Verified:
- `node --check frontend/web/app.js`
- `uv run pytest tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_web_runtime.py`
- `uv run ruff check src/openharness/services/rag_store.py scripts/web_mvp_server.py tests/test_services/test_web_mvp_rag.py`

Next plan:
- Design the layered metadata schema before adding announcement-specific metadata extraction.
- Add metadata fields to the dashboard only after the schema is decided.
- Add a safer confirmation flow before destructive delete actions if the UI grows beyond MVP.

## Next Session Handoff: Layered RAG Metadata

Environment expectation:
- Continue from WSL Ubuntu bash, not Windows PowerShell.
- Recommended start:
  - cd ~/workspace/OpenHarness
  - codex .
- Keep all work inside /home/kiakiakia/workspace/OpenHarness.
- Do not create temporary edit scripts outside the project directory.

Current RAG status:
- Web upload extracts text, runs announcement analysis, chunks extracted text, creates OpenAI-compatible embeddings, and stores chunks in project-local SQLite.
- Chat embeds the user question, retrieves relevant stored chunks with cosine similarity, and attaches retrieved chunk text to the prompt.
- RAG DB path pattern: ~/.openharness/data/rag/<project-name>-<hash>/documents.sqlite3.
- Observed current DB path: /home/kiakiakia/.openharness/data/rag/OpenHarness-79e1287ffb53/documents.sqlite3.
- RAG management APIs exist:
  - GET /api/rag/documents
  - POST /api/rag/delete
  - POST /api/rag/reindex
- Browser dashboard exists and should show indexed document count, chunk count, DB path, documents, delete/reindex actions, and RAG source chunks under chat answers.

Important design decision:
- Do not force announcement-only metadata fields onto every uploaded document.
- Uploaded documents may be announcements, regulations/operating guidelines, technical documents, or company/team documents.
- Next work should design a layered metadata schema first, then implement extraction and dashboard display.

Proposed layered metadata schema:
- Common metadata for every document:
  - document_type
  - title
  - source_file
  - content_hash
  - uploaded_at
  - embedding_profile
  - chunk_count
  - tags
  - language
  - source_kind
- Announcement metadata:
  - ministry
  - agency
  - business_type
  - rd_or_non_rd
  - program_name
  - submission_channel
  - submission_deadline
  - contacts
  - related_regulations
  - eligibility_roles
- Regulation metadata:
  - regulation_owner
  - applies_to_business_type
  - effective_date
  - article_scope
  - related_ministry
  - related_agency
- Technical document metadata:
  - technology_domain
  - product_or_system
  - version
  - spec_scope
  - related_project_or_program
- Company/team document metadata:
  - department
  - owner
  - responsibility_area
  - related_task

Backfill concern:
- If a new metadata field is added later, existing documents can sometimes be backfilled from stored chunk text.
- If the field requires full-document structure, the original document or full extracted text may need to be reprocessed.
- Therefore the metadata design should decide whether to persist full extracted text, original file references, or both.

Next implementation sequence:
1. Draft docs/RAG_METADATA_SCHEMA.md with the layered metadata schema and backfill policy.
2. Add typed metadata dataclasses or schemas in the RAG service layer.
3. Add metadata extraction that classifies document_type first, then extracts type-specific fields.
4. Store extracted metadata in documents.metadata_json without breaking existing rows.
5. Add dashboard fields for document_type, title, agency/ministry when available, business_type, and submission_deadline.
6. Add retrieval filtering later: document_type, ministry, agency, rd_or_non_rd, business_type.
7. Keep source chunk display under chat answers and extend it with metadata once schema is stable.

Verification baseline:
- uv run pytest tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_web_runtime.py
- uv run ruff check src/openharness/services/rag_store.py scripts/web_mvp_server.py tests/test_services/test_web_mvp_rag.py

Progress update:
- Drafted docs/RAG_METADATA_SCHEMA.md with the layered metadata schema and backfill policy.
- Added typed RAG metadata dataclasses and heuristic document_type classification in src/openharness/services/rag_metadata.py.
- Upload indexing now stores layered metadata in documents.metadata_json and the indexer adds content_hash and chunk_count.
- The RAG dashboard document list now receives and renders document_type, title, agency/ministry, business_type, and submission_deadline when available.
- Added metadata-focused tests in tests/test_services/test_rag_metadata.py.
- Verification used the existing project venv directly because uv/python/pytest were not on the shell PATH:
  - .venv/bin/python -m pytest tests/test_services/test_rag_metadata.py tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py
  - Result: 8 passed in 1.62s.
  - .venv/bin/python -m ruff check src/openharness/services/rag_metadata.py src/openharness/services/rag_indexing.py scripts/web_mvp_server.py tests/test_services/test_rag_metadata.py tests/test_services/test_web_mvp_rag.py
  - Result: All checks passed.

Remaining next steps:
- Add retrieval filtering for document_type, ministry, agency, rd_or_non_rd, and business_type.
- Extend source chunk display with stable metadata once retrieval filtering is in place.

## 2026-04-12 RAG Retrieval Filtering Update

Developed:
- Added optional RAG retrieval filters for document_type, ministry, agency, rd_or_non_rd, and business_type.
- Retrieval now skips chunks whose document metadata does not match active filters before ranking by cosine similarity.
- Retrieved source chunks now carry stable metadata fields for the browser source display.
- The Web MVP chat UI now exposes lightweight RAG filter controls and sends them with chat requests.
- The RAG document dashboard payload now includes rd_or_non_rd when available.
- Announcement metadata extraction now prefers labeled ministry/agency lines such as `주관부처` and `전담기관` before falling back to broad regex matching.

Changed files:
- `src/openharness/services/rag_types.py`: added `RagRetrievalFilters` and metadata fields on retrieved chunks.
- `src/openharness/services/rag_retrieval.py`: added metadata filter matching and metadata-enriched retrieval results.
- `src/openharness/services/rag_metadata.py`: stores announcement rd_or_non_rd at the common dashboard/filtering level.
- `src/openharness/services/rag_metadata.py`: improves labeled ministry/agency extraction for Korean announcement text.
- `scripts/web_mvp_server.py`: accepts optional chat `rag_filters` and returns applied filters plus enriched source metadata.
- `frontend/web/index.html`: added RAG filter controls.
- `frontend/web/app.js`: sends RAG filters and renders source metadata.
- `frontend/web/styles.css`: added filter layout styles.
- `tests/test_services/test_rag_core.py`: added metadata filter coverage.
- `tests/test_services/test_web_mvp_rag.py`: added server filter/status coverage.

Verified:
- `.venv/bin/python -m pytest tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_rag_metadata.py`
- `.venv/bin/python -m pytest tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_web_runtime.py`

## 2026-04-12 Ingestion Pipeline Shell

Developed:
- Added `docs/INGESTION_PIPELINE_PLAN.md` to record the RAG/data-pipeline direction.
- Added ingestion dataclasses for sources, plans, jobs, and review items.
- Added SQLite ingestion tables inside the existing project-local RAG database.
- Added store helpers to create/list ingestion sources, plans, jobs, and review items.
- Added review status updates for `needs_review`, `approved`, `rejected`, `failed`, and `stale`.
- Connected Web MVP document uploads to ingestion tracking so each upload creates an upload source and review item.
- Added API shell endpoints:
  - `GET /api/ingestion/state`
  - `GET /api/ingestion/sources`
  - `GET /api/ingestion/plans`
  - `GET /api/ingestion/jobs`
  - `GET /api/ingestion/review-items`
  - `POST /api/ingestion/review`

Design decision:
- Keep ingestion inside the agent product, but isolate it as a service/storage layer.
- Keep SQLite as the initial implementation while preserving a path to future MetadataStore, VectorStore, and RawStore adapters.
- Do not add real filesystem scanning, DB connectors, OCR, or scheduler automation yet. The first pass is the pipeline shell and review state model.

Verified:
- `.venv/bin/python -m pytest tests/test_services/test_ingestion_pipeline.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_rag_core.py tests/test_services/test_web_runtime.py tests/test_services/test_rag_metadata.py tests/test_services/test_document_processing.py tests/test_services/test_announcement_workflow.py tests/test_services/test_compact.py`
- Result: 30 passed in 2.61s.
- `.venv/bin/python -m ruff check src/openharness/services src/openharness/tools scripts/web_mvp_server.py tests/test_services`
- Result: All checks passed.

Next plan:
- Add a dashboard panel for ingestion sources and review items.
- Add a dry-run ingestion plan creator before implementing real folder or DB scanning.
- Add RAG search/list/get document tools so the future agent loop uses stable tool interfaces instead of direct SQLite/RAG internals.

## 2026-04-12 RAG Toolization And Document Dashboard

Developed:
- Added RAG tools to prepare for a future agentic RAG implementation:
  - `rag_search`
  - `rag_list_documents`
  - `rag_get_document`
- Registered the RAG tools in the default OpenHarness tool registry.
- Moved embedding-profile selection into the RAG service layer so web handlers and tools share the same selection behavior.
- Split the Web MVP into two UI workspaces:
  - Chat
  - Document Pipeline
- Added a right-side navigation panel to switch between chat and document processing.
- Added a dedicated Document Processing Dashboard area with indexed RAG documents and ingestion review items.
- Added browser controls to mark ingestion review items as approved, rejected, or needing review.

Design decision:
- RAG is now exposed through stable tool interfaces while the current implementation remains SQLite plus OpenAI-compatible embeddings.
- The future agent loop should call `rag_search`/`rag_list_documents`/`rag_get_document` rather than directly calling SQLite or chunking internals.
- Later agentic RAG can replace the internals behind `rag_search` without changing the tool contract.

Verified:
- `.venv/bin/python -m pytest tests/test_tools/test_rag_tools.py tests/test_services/test_ingestion_pipeline.py tests/test_services/test_web_mvp_rag.py tests/test_services/test_rag_core.py tests/test_services/test_web_runtime.py tests/test_services/test_rag_metadata.py tests/test_services/test_document_processing.py tests/test_services/test_announcement_workflow.py tests/test_services/test_compact.py`
- Result: 32 passed in 2.26s.
- `.venv/bin/python -m ruff check src/openharness/services src/openharness/tools scripts/web_mvp_server.py tests/test_services tests/test_tools`
- Result: All checks passed.
- `/home/kiakiakia/.vscode-server/bin/07ff9d6178ede9a1bd12ad3399074d726ebe6e43/node --check frontend/web/app.js`
- Result: passed.

Next plan:
- Run the browser UI and manually check chat/document navigation plus ingestion review actions.
- Add the first web agent endpoint after the RAG tool contract is stable.
- Consider adding `rag_index_document` as a write tool only after user approval semantics are clearer.

## 2026-04-12 Proposal Ops Preview UI

Developed:
- Added `docs/DEVELOPMENT_JOURNAL.md` as a date-based work log.
- Added `docs/PROPOSAL_OPS_PLAN.md` as the feature plan for proposal operations automation.
- Added `src/openharness/services/workflows/proposal_ops.py` to build a deterministic operations preview from announcement analysis output.
- Added `proposal_ops` to the document upload response payload.
- Added a separate `Proposal Ops` web workspace. It is intentionally separate from `Document Pipeline`.
- Added right-side navigation entries for `Chat`, `Document Pipeline`, and `Proposal Ops`.

Current Proposal Ops preview includes:
- Project summary.
- Submission checklist.
- Manager questions.
- Role tasks.
- Reminder plan.
- Folder plan.
- File output plan.
- Execution preview.
- Manual inputs still needed.

Verified:
- `.venv/bin/python -m pytest tests/test_services/test_proposal_ops_workflow.py tests/test_services/test_web_mvp_rag.py tests/test_tools/test_rag_tools.py tests/test_services/test_ingestion_pipeline.py tests/test_services/test_rag_core.py tests/test_services/test_web_runtime.py tests/test_services/test_rag_metadata.py tests/test_services/test_document_processing.py tests/test_services/test_announcement_workflow.py tests/test_services/test_compact.py`
- Result: 33 passed in 2.29s.
- `.venv/bin/python -m ruff check src/openharness/services src/openharness/tools scripts/web_mvp_server.py tests/test_services tests/test_tools`
- Result: All checks passed.
- `/home/kiakiakia/.vscode-server/bin/07ff9d6178ede9a1bd12ad3399074d726ebe6e43/node --check frontend/web/app.js`
- Result: passed.
- Review server started at `http://127.0.0.1:8012`.
- HTML smoke check confirmed the page includes `Proposal Ops` and `Document Pipeline`.

Next plan:
- Add persistence for proposal projects/tasks/questions instead of only returning preview payloads.
- Add a preview/approve/execute boundary before any folder creation, file moves, file writes, or message sends.

## 2026-04-12 Fixed Web MVP Runtime Data Path

Developed:
- Added `scripts/run_web_mvp.sh`.
- The script pins config/data directories to the normal user OpenHarness directory:
  - `/home/kiakiakia/.openharness`
  - `/home/kiakiakia/.openharness/data`
- The script defaults the Web MVP server to `http://127.0.0.1:8013`.

Reason:
- Codex is running in a snap environment where `HOME` can resolve to `/home/kiakiakia/snap/codex/34`.
- Directly running `scripts/web_mvp_server.py` in that environment makes OpenHarness look at the wrong RAG DB.
- Existing uploaded/RAG documents are under `/home/kiakiakia/.openharness/data/rag/...`.

Operational rule:
- Use `bash scripts/run_web_mvp.sh` for local Web MVP review and development.
- `.venv/bin/python -m ruff check src/openharness/services/rag_types.py src/openharness/services/rag_retrieval.py src/openharness/services/rag_metadata.py scripts/web_mvp_server.py tests/test_services/test_rag_core.py tests/test_services/test_web_mvp_rag.py`
- `/home/kiakiakia/.vscode-server/bin/07ff9d6178ede9a1bd12ad3399074d726ebe6e43/node --check frontend/web/app.js`
- Real Web MVP smoke test on `http://127.0.0.1:8010` with `openai-compatible`:
  - Uploaded `smoke-commercialization-notice.txt`.
  - Indexed 1 chunk with `document_type=announcement`, `ministry=산업통상자원부`, `agency=한국산업기술진흥원`, `rd_or_non_rd=non_rd`, and `business_type=Commercialization`.
  - Chat with active filters retrieved 1 matching source chunk and answered the deadline/agency question from RAG context.

Remaining next steps:
- Decide whether the filter UI should stay free-form or derive selectable values from indexed document metadata.
- Add a cleanup/reset affordance for smoke-test documents or document-level test fixtures if this dashboard becomes a regular manual QA surface.
