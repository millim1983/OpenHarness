# Latest Handoff

## 우분투 서버 이전
Updated: 2026-04-14 17:15 KST

## GitHub

- Private remote: `https://github.com/millim1983/openharness_mm.git`
- Branch: `web-mvp-rag`
- Latest pushed commit: `71e2002 feat(web-mvp): RAG 기반 웹 MVP 기능 구현 및 UI 개선`
- `private/web-mvp-rag` and `origin/web-mvp-rag` currently point at `71e2002`.
- Original `upstream` is not used for this private development flow.

## Server Environment Variables

Use these on the company Ubuntu server:

```bash
export OPENHARNESS_CONFIG_DIR=/home/회사계정/.openharness
export OPENHARNESS_DATA_DIR=/home/회사계정/.openharness/data
export OPENHARNESS_WEB_HOST=0.0.0.0
export OPENHARNESS_WEB_PORT=8014
export OPENHARNESS_PROPOSAL_OUTPUT_DIR=/data/openharness/announcements
export OPENHARNESS_RAG_EMBEDDING_PROFILE=openai-compatible
```

Meanings:

- `OPENHARNESS_CONFIG_DIR`: settings, credentials, project context, and feedback logs.
- `OPENHARNESS_DATA_DIR`: local RAG/VectorDB data.
- `OPENHARNESS_WEB_HOST=0.0.0.0`: allow access from the company network or externally routed IP.
- `OPENHARNESS_WEB_PORT=8014`: web UI port.
- `OPENHARNESS_PROPOSAL_OUTPUT_DIR`: root directory where the project program creates announcement folders and output files.
- `OPENHARNESS_RAG_EMBEDDING_PROFILE`: embedding profile used by RAG indexing/search.

## Folder And Output Behavior

The project program can create folders and output files on the Ubuntu server.

Required condition:

- The Linux user running OpenHarness must have write permission to `OPENHARNESS_PROPOSAL_OUTPUT_DIR`.

Current announcement-agent behavior:

- User uploads a folder/file set from the web UI.
- Program finds the PDF notice file identified by `공고`.
- Program analyzes and RAG-indexes only that PDF notice.
- HWP, Excel, PPT, forms, manuals, and regulations are not parsed at this stage.
- Program creates a new announcement folder under `OPENHARNESS_PROPOSAL_OUTPUT_DIR`.
- Program saves the uploaded file set into that generated folder.
- Program creates `총괄장.xlsx` and `첨부파일목록.json` inside the generated folder.
- Program updates `공고리스트.json` and regenerates `공고리스트_yyyymmdd.xlsx` under `OPENHARNESS_PROPOSAL_OUTPUT_DIR`.

Important distinction:

- If files are uploaded through a browser, the server receives file bytes and saves them to the server output directory.
- The server cannot directly create folders or move files inside the user's original local PC folder chosen by the browser.
- If a company shared drive is mounted on the Ubuntu server, the program can create folders and move files there.
- A future watched-folder mode can support true server-side file movement from an intake folder into the generated announcement folder.

Short rule:

- User-selected browser folder = source for uploading files.
- Preconfigured server folder = destination where the program creates folders and output files.
- Server-mounted shared drive folder = location where the program can later watch and truly move files.

## Network Notes

To open the web UI on the company network:

- Run the web server with `OPENHARNESS_WEB_HOST=0.0.0.0`.
- Open `OPENHARNESS_WEB_PORT` in Ubuntu firewall, router/firewall, and cloud/security gateway if present.
- For external access, route the fixed public IP and external port to the Ubuntu server IP and `OPENHARNESS_WEB_PORT`.

Security note:

- Do not expose this MVP directly to the public internet without an auth layer or VPN/reverse proxy access control.

## Latest UI Note

- Web UI user-facing copy has been localized to Korean across chat, document processing, proposal operations, and announcement-agent screens.
- Technical acronyms such as RAG, DB, PDF, HWP, and R&D remain as standard labels.

## Current Development State

Latest completed development:

- 공고 에이전트 folder/file-set upload flow is implemented.
- The announcement-stage folder is created under `OPENHARNESS_PROPOSAL_OUTPUT_DIR`.
- Uploaded files are preserved under the generated announcement folder.
- Only the PDF notice file identified by `공고` is parsed and RAG-indexed.
- Non-notice attachments are saved and listed in `첨부파일목록.json`, but not parsed yet.
- `총괄장.xlsx`, `공고리스트.json`, and date-stamped `공고리스트_yyyymmdd.xlsx` are generated.
- Web UI copy is localized to Korean.
- VectorDB-first processing has been implemented: extract text, index to VectorDB, assemble chunks, then run LLM analysis.
- `proposal_assets/config/extraction_schema.json` now drives announcement extraction fields.
- `RagStore.patch_document_metadata()` updates metadata after structured analysis without rewriting chunks.
- Proposal operations dashboard UI has replaced the earlier plain text preview.
- Service tests previously passed for the touched service layer: 70 tests.

Known local working-tree notes before continuing:

- `_refs/` contains local development reference material and a proposal operations dashboard prototype.
- `.claude/settings.local.json` is a local tool-permission file and should not be committed.

## Next Work: Knowledge Store Upgrade

The next agreed direction is to move from one-shot extraction toward an accumulating, evidence-backed business knowledge store.

Problem being solved:

- A notice PDF can imply or hallucinate a wrong project structure, such as treating a MOTIE/산자부 project as if it supports `위탁연구비`.
- The system must distinguish what the notice explicitly says, what the applicable regulation says, and what still needs human confirmation or inquiry.
- Regulations change over time, and individual notices may override or narrow the general rule.

Core principle:

- The agent should not depend on manually typed hard rules as the primary source.
- It should read notices and regulations, extract structured knowledge from those source documents, store the evidence and relationships, and let a user confirm or correct the knowledge.

Target knowledge hierarchy:

- Regulation: general rule, versioned and date-sensitive.
- Notice: project-specific requirements and overrides; always must be read carefully.
- Confirmed knowledge item: human-reviewed fact with source evidence and status.

Important fields to extract and validate:

- 사업명
- 전문기관
- 제출일자
- 접수처
- 총연구기간
- 총연구비 또는 과제당 총연구비
- 당해연도 연구기간
- 당해연도 연구비 또는 과제당 당해연도 연구비
- 과제 구성 유형: 주관+공동, 주관+공동+수요필수, 주관+공동+위탁, 주관+공동+위탁+수요필수 등
- 수요기관 필수 여부
- 수요기관 연구비 사용 가능 여부
- 수요기관이 공동연구기관으로 참여하는지 여부
- 부처별 R&D 특성: 산자부, 과기부, 중기부, 기타 부처의 공통점과 차이점
- 공고별 특이 조건
- 공고에 명시되지 않았지만 규정상 적용될 수 있는 민간부담금 감면, 총예산 반영 등 문의 필요 항목

Recommended MVP storage approach:

- Start with structured JSON files plus the existing VectorDB/RAG store.
- Add a graph-shaped relation index before adopting a dedicated graph database server.
- Later migration target can be embedded Kuzu if relation queries become central and JSON relation indexes become limiting.

Proposed storage shape:

```text
knowledge_store/
  announcements/{announcement_id}.json
  regulations/{regulation_id}.json
  knowledge_items/{knowledge_item_id}.json
  relations.json
```

Each knowledge item should include:

- source type: notice, regulation, human correction, generated inference.
- source reference: file, page or section when available, regulation name and article when available.
- ministry, agency, business type, announcement id, regulation id.
- certainty level: explicit, inferred, uncertain.
- verification status: unreviewed, confirmed, rejected, needs_inquiry, needs_recheck, expired.
- effective date and source document date/version.
- conflict or override markers when a notice differs from a general regulation.

## Immediate Development Plan

1. Knowledge item schema
   - Add a structured schema/config for announcement/regulation knowledge items.
   - Include verification status, source evidence, certainty, date/version, ministry/agency/business-type scope, and inquiry-needed fields.
   - Add unit tests for schema loading and default status handling.

2. Knowledge extraction pipeline
   - Extend the announcement workflow so notice processing can emit candidate knowledge items in addition to the existing `총괄장` fields.
   - Keep notice extraction and regulation-derived extraction separate so source priority is visible.
   - Store candidate items in the MVP JSON store and link them to the existing RAG document id where possible.

3. Human verification UI
   - Add a web panel for extracted knowledge items.
   - Provide user actions: `맞음`, `수정`, `틀림`, `문의필요`, `재검토필요`.
   - Confirmed items should be reused in later analysis and unresolved items should be surfaced as inquiry warnings.

4. Regulation freshness and conflict checks
   - Track regulation document date/version.
   - If a newer regulation source is added, mark related knowledge items as `needs_recheck`.
   - If a notice-specific rule conflicts with a stored general regulation, show the conflict instead of silently choosing one.

5. Development hygiene
   - Update tests after each step.
   - Keep `docs/DEVELOPMENT_JOURNAL.md` and this handoff file current.
   - Push completed increments to `private/web-mvp-rag`.
