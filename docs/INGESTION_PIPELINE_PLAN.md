# Ingestion Pipeline Plan

## Goal

Add the first shell of a data ingestion pipeline for the Web MVP and future agent system.

The pipeline should support this product flow:

1. A user connects or uploads a source.
2. The system proposes an ingestion plan.
3. The user approves scope, schedule, and batch size.
4. The system processes a small batch.
5. The user reviews the result.
6. Approved items become eligible RAG context for agents.

## Design Direction

Keep ingestion inside the agent product, but isolate it as its own service layer.

The agent should call stable ingestion and RAG interfaces. It should not know about SQLite tables,
embedding JSON, filesystem scanning details, or vector database internals.

Initial storage remains SQLite in the project-local RAG database. Future storage should be swappable
behind metadata/vector/raw-store interfaces.

## Initial Scope

Implement a non-invasive ingestion shell:

- Source records for uploads, folders, databases, chat memory, or APIs.
- Plan records with user-visible scope, schedule, batch size, and approval status.
- Job records for small batch runs.
- Review records for indexed documents.
- API endpoints to list the initial pipeline state.
- Upload integration so uploaded documents are also recorded as ingestion review items.

Out of scope for this pass:

- Real filesystem scanning.
- Real database connectors.
- OCR.
- Scheduler daemon integration.
- External vector database migration.
- Automatic memory extraction from chat.

## State Model

Source types:

- `upload`
- `folder`
- `database`
- `chat`
- `api`

Plan statuses:

- `draft`
- `approved`
- `paused`
- `archived`

Job statuses:

- `queued`
- `running`
- `completed`
- `failed`
- `cancelled`

Review statuses:

- `needs_review`
- `approved`
- `rejected`
- `failed`
- `stale`

## API Shell

- `GET /api/ingestion/state`
- `GET /api/ingestion/sources`
- `GET /api/ingestion/plans`
- `GET /api/ingestion/jobs`
- `GET /api/ingestion/review-items`
- `POST /api/ingestion/review`

The first POST endpoint only updates review status for an existing review item.

## Next Implementation Milestones

1. Add typed ingestion dataclasses.
2. Add SQLite tables and store methods.
3. Record uploaded Web MVP documents as upload sources and review items.
4. Add read-only state APIs plus review status update API.
5. Add dashboard rendering after the API shell is stable.
6. Add filesystem source planning and dry-run scanning later.
7. Add VectorStore/MetadataStore interfaces before replacing SQLite.
