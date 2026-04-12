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

### Web UI Korean Localization
- Localized the web UI copy from English to Korean across chat, document processing, proposal operations, and announcement-agent screens.
- Localized dynamic browser messages for RAG documents, ingestion review, document analysis, proposal operations, and copy/status feedback.
- Kept technical acronyms such as RAG, DB, PDF, HWP, and R&D where they are standard user-facing terms.

### VectorDB-First 처리 흐름 재설계
- 문서 업로드 후 처리 순서를 VectorDB 인덱싱 먼저로 변경: 텍스트 추출 → VectorDB 인덱싱 → 청크 조립 → LLM 분석 순서로 재구성.
- 기존 흐름은 LLM 분석 후 인덱싱이었고, 분석 시 텍스트가 잘릴 수 있는 구조였음.
- 변경 후 LLM은 항상 VectorDB에서 조립된 전체 청크 텍스트를 입력으로 받으므로 truncation이 원천 차단됨.
- `RagStore.patch_document_metadata()` 신규 추가: 인덱싱 직후에는 structured 분석 결과가 없으므로, 분석 완료 후 청크를 건드리지 않고 메타데이터(title, ministry, agency 등)만 갱신하는 메서드.

### 추출 스키마 Config화
- 공고 분석 추출 필드 정의를 `proposal_assets/config/extraction_schema.json`으로 분리.
- 기존에는 `document_processing.py`에 필드 목록이 하드코딩되어 있었음.
- 이제 필드 추가·수정 시 JSON 파일만 편집하면 되고, `lru_cache` 로더로 런타임에 한 번만 읽음.
- `build_document_analysis_prompt()`가 스키마 기반 프롬프트를 생성하며 항상 `truncated=False` 반환.

### 제안 운영 대시보드 UI 구축
- 제안 운영 탭의 출력을 `<pre>` 텍스트에서 카드형 대시보드로 교체.
- `.po-*` CSS 클래스 체계 신규 도입(흰 배경 + 블루 계열).
- `renderProposalOpsDashboard()` JS 함수가 메트릭·체크리스트·폴더 구조·리마인더를 렌더링.
- 체크리스트 onclick 버그 수정: 인라인 `.toString()` 방식이 HTML 속성 파싱을 깨뜨리던 문제를 `window._poUpdateChecklist` 전역 참조 방식으로 해결.
- `announcementAgentMeta` 엘리먼트 위치 오류 수정: proposalOpsView 내부에 잘못 포함되어 있던 것을 announcementAgentView로 이동.

### Config 연동 및 버그 수정
- `proposal_ops.py` 폴더트리·역할북·에이전시 별칭·폴더 규칙을 `lru_cache` 로더 기반으로 전환(하드코딩 제거).
- `announcement_agent.py`의 `_agency_folder_label()` / `_monitoring_row()`가 존재하지 않는 `structured["metadata"]` 딕셔너리를 참조하던 버그 수정 → `announcement_overview` 하위 필드로 경로 수정.
- `_refs/` 참조 자료 폴더 신설 및 파일 명명 규칙(`CONVENTIONS.md`) 문서화.

### 테스트 정비
- `test_announcement_agent.py`, `test_web_mvp_rag.py`: 필드 경로 변경에 맞게 테스트 데이터 수정.
- `test_document_processing.py`: 삭제된 `build_document_summary_prompt` / `MAX_SUMMARY_SOURCE_CHARS` 참조 제거, truncation 미발생 검증으로 교체.
- 서비스 테스트 전체 70개 통과 확인.

## 내일 할 일 (2026-04-14 예정)

- **실제 공고 PDF End-to-End 검증**: 서버 실행 후 실제 공고 파일을 업로드해서 마감일·제출서류·전문기관이 총괄장에 정확히 들어가는지 확인. VectorDB-First 흐름 실동작 체크.
- **제안 운영 대시보드 피드백 반영**: 실제 공고 결과를 보고 대시보드에서 빠지거나 어색한 항목 수정.
- **`extraction_schema.json` 필드 정밀화**: 실제 추출 결과를 보고 필드 정의나 extraction_rules 보완.
- **`LATEST_HANDOFF.md` 업데이트**: 현재 구조에 맞게 핸드오프 문서 갱신.
