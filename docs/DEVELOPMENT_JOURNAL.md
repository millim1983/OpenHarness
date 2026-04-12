# Development Journal

## 2026-04-12

### Private Git Workflow
- Added private development remote `private` for `millim1983/openharness_mm`.
- Pushed active development to `private/web-mvp-rag`.
- Kept public `origin` and original `upstream` untouched.

### Web MVP, RAG, And Ingestion
- Added document upload, extraction, RAG indexing, retrieval-backed chat, RAG document dashboard, and ingestion pipeline shell.
- Added RAG tool interfaces for future agentic RAG:
  - `rag_search`
  - `rag_list_documents`
  - `rag_get_document`

### Proposal Operations Plan
- Started the Proposal Operations Agent direction.
- The first implementation target is a web-visible operations preview, not full automation.
- Automation will later move through preview, user approval, execution, logging, and review.
- Added the first Proposal Ops preview generator.
- Kept Proposal Ops as a separate UI workspace instead of merging it into the document-processing dashboard.
- Started review server at `http://127.0.0.1:8012`.
- Added `scripts/run_web_mvp.sh` to pin OpenHarness config/data paths outside the snap HOME.
- Started the announcement agent automation path for generated project folders and Excel workbooks.
- Updated announcement-agent folder naming to `yymmdd-전문기관약자 또는 전문기관명-사업명`.
