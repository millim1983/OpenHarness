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
- Split proposal automation settings into `proposal_assets/config/` and added feature flags.

## 2026-04-13

### 공고 에이전트 Folder Upload Flow
- Added a separate web workspace for `공고 에이전트`.
- Added browser folder/file-set upload, explicit Run action, and result reporting for generated folders/files.
- Updated the announcement-agent flow to create only the announcement-stage folder and preserve uploaded file-set paths inside it.
- Added a guard so the folder-upload flow must find a PDF `공고` file and use that PDF as the structured-analysis source.
- Limited RAG indexing and LLM extraction to the selected PDF notice; non-notice attachments are saved without parsing and listed in `첨부파일목록.json`.
- Kept proposal folder-tree creation out of the announcement stage; `folder_tree.json` is reserved for the later proposal-drive stage after proposal decision.
- Changed monitoring output to `공고리스트_yyyymmdd.xlsx` based on the latest update date, backed by `공고리스트.json`.
- Added monitoring dashboard stats for upload date, ministry, business type, and business domain.
