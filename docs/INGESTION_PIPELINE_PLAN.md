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

## 2026-04-14 Update: Document Knowledge Base Pipeline

The project knowledge base must handle mixed source types: HWP, PDF, Word, PPT, Excel, images/scans, notices, RFPs, regulations, forms, prior proposals, and project retrospective notes.

Do not convert everything to PDF as the only ingestion path.

Recommended storage principle:

- Preserve the original file.
- Create a canonical text representation for LLM/RAG, preferably Markdown when the document is mostly narrative.
- Create structured JSON metadata for fields, tables, sections, evidence, and graph-ready relations.
- Use PDF as a fallback or layout-preservation artifact, not as the only source of truth.

Recommended canonical forms by source type:

| Source | Primary extraction | Canonical form for LLM/RAG | Notes |
|---|---|---|---|
| PDF text | PDF text extraction | Markdown + page anchors | Keep page numbers for evidence. Use OCR only when text extraction is empty/poor. |
| Scanned PDF/images | OCR | Markdown + OCR confidence + page anchors | Needs human review for low-confidence spans. |
| Word/DOCX | Native document extraction | Markdown + headings/tables | Better than PDF conversion because structure survives. |
| HWP/HWPX | Native extraction when available; conversion fallback | Markdown + section/table blocks | Prefer HWP/HWPX to text/HTML/ODT/DOCX then Markdown. Use HWP -> PDF -> OCR/Markdown only as fallback. |
| PPT/PPTX | Slide extraction | Markdown per slide + image refs | Preserve slide number, title, bullets, notes, and important diagrams/screenshots. |
| Excel/XLSX | Workbook extraction | JSON tables + Markdown summaries | Do not flatten only to PDF. Preserve sheets, cell ranges, headers, formulas, and table semantics. |
| CSV | Structured parse | JSON table + Markdown summary | Keep delimiter/encoding metadata. |
| Existing Markdown/Text | Direct parse | Markdown | Keep original path and heading anchors. |

Target pipeline:

```text
source file
  -> file registry record
  -> type-specific extractor
  -> normalized document package
       original file
       extracted markdown
       structured JSON
       page/slide/sheet anchors
       assets/images when needed
  -> chunking
  -> embeddings/vector index
  -> metadata store
  -> candidate knowledge extraction
  -> human review
  -> confirmed knowledge graph records
```

Normalized document package shape:

```text
processed_documents/{document_id}/
  original/{original_filename}
  content.md
  structure.json
  assets/
  extraction_report.json
```

`structure.json` should include:

- document id, source file name, source type, content hash, created/modified dates when available.
- pages, slides, sheets, headings, tables, figures, and attachments.
- extraction method, tool version, warnings, and OCR confidence when relevant.
- business metadata when known: ministry, agency, business domain, business type, notice/RFP/regulation/form/proposal.
- graph-ready relation candidates: mentions regulation, applies to ministry, applies to workflow stage, has topic, has inquiry item.

LLM usage rule:

- Use Markdown chunks for narrative reasoning.
- Use JSON tables for Excel/budget/form data.
- Use page/slide/sheet anchors as evidence references.
- Use original/PDF only when layout, signatures, stamps, diagrams, or visual fidelity must be checked.

For HWP:

- Prefer direct extraction to text/HTML/ODT/DOCX, then normalize to Markdown.
- If direct extraction is unavailable or poor, convert to PDF and run PDF text extraction/OCR.
- Always preserve the original HWP/HWPX because conversion can lose fields, tables, and layout.

For Excel:

- Do not convert to PDF for analysis by default.
- Store sheet-level JSON and table summaries.
- Convert selected sheets to PDF/images only for visual review or print-layout checks.

For PPT:

- Extract slide title, bullets, notes, and embedded text.
- Store image references for diagrams.
- Use vision/OCR later only for image-heavy slides.

This pipeline lets the agent use documents during announcement/RFP analysis and also generate reusable knowledge cards for the tacit knowledge graph.
