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

## 2026-04-14

### GitHub 상태 정리
- `private/web-mvp-rag`에 누락되어 있던 `71e2002 feat(web-mvp): RAG 기반 웹 MVP 기능 구현 및 UI 개선` 커밋을 푸시했다.
- `origin/web-mvp-rag`와 `private/web-mvp-rag` 모두 `71e2002` 기준으로 맞췄다.
- 로컬 전용 `.claude/settings.local.json`은 커밋 대상에서 제외하도록 `.gitignore`에 추가했다.

### 다음 개발 방향: 지식 스토어 업그레이드
- 다음 목표는 공고/규정을 읽고 누적되는 근거 기반 업무 지식 스토어를 만드는 것이다.
- 당장 전용 Graph DB 서버를 붙이기보다 JSON 기반 지식 아이템 저장소와 relation index를 먼저 만들고, 기존 VectorDB/RAG와 연결한다.
- 핵심 구현 순서는 지식 아이템 스키마, 공고 처리 중 후보 지식 추출 파이프라인, 사람이 `맞음`/`수정`/`문의필요` 등을 표시하는 검증 UI다.

### 암묵지 지식그래프 및 문서 파이프라인 계획
- `docs/TACIT_KNOWLEDGE_GRAPH_PLAN.md`를 추가해 사용자 메모, 사후 회고, 문의 결과, 규정/공고 기반 지식을 graph-shaped card로 축적하는 계획을 기록했다.
- 핵심은 원문 메모를 보존하되 에이전트가 `언제 꺼낼지`, `어떤 사업/부처/단계에 적용되는지`, `체크리스트인지 문의항목인지 규정근거인지`를 구조화해서 저장하는 것이다.
- `docs/INGESTION_PIPELINE_PLAN.md`에 HWP, PDF, Word, PPT, Excel 등 혼합 문서 처리 방향을 추가했다.
- 문서 처리는 모든 파일을 PDF로 변환하는 방식이 아니라 원본 보존, Markdown 정규화, Excel/표 JSON화, page/slide/sheet anchor 보존, VectorDB/RAG 및 지식카드 추출로 연결하는 방식으로 잡았다.

### 암묵지 지식 메모 MVP 구현
- `proposal_assets/config/knowledge_categories.json`을 추가해 지식 유형, 검증 상태, 업무 단계, 표출 방식, 키워드 기반 초안 분류 규칙을 코드 밖 설정으로 분리했다.
- `src/openharness/services/tacit_knowledge.py`를 추가해 원문 메모 저장, 구조화 초안 카드 생성, 확정 저장, relation edge 생성을 JSON 파일 기반으로 구현했다.
- 웹 API `/api/knowledge/state`, `/api/knowledge/draft`, `/api/knowledge/save`를 추가했다.
- 웹 UI에 `지식 메모` 탭을 추가해 자유 메모 입력, 사업/부처/기관/케이스 메타데이터 입력, 구조화 초안 미리보기, JSON 수정 후 확정 저장, 저장된 지식 카드 목록 표시를 지원한다.
- 첫 구현은 LLM 호출 없이 키워드 규칙 기반으로 동작한다. 저장/검토/확정 데이터 구조를 먼저 안정화한 뒤 같은 API 뒤에 모델 기반 구조화기를 붙일 계획이다.
- `tests/test_services/test_tacit_knowledge.py`를 추가했고 2개 테스트 통과를 확인했다.

### 저장된 지식 카드의 공고/RFP 분석 연결
- `KnowledgeStore.find_matching_cards()`를 추가해 저장된 확정 지식 카드를 공고/RFP 분석 결과와 매칭한다.
- 매칭 기준은 부처, 기관, 사업구분, 사업유형, 업무단계, 트리거 키워드, 카테고리, 검증 상태를 점수화하는 방식으로 시작했다.
- 공고/문서 분석 후 `structured.knowledge_matches`에 체크리스트, 문의항목, 주의사항, 작성가이드를 주입하도록 웹 서버 흐름을 연결했다.
- 제안 운영 대시보드의 제출 체크리스트와 확인 필요사항에도 `knowledge_matches`가 병합되도록 `proposal_ops.py`를 수정했다.
- 웹의 구조화 분석 출력에 `지식 기반 체크리스트/문의항목` 섹션을 추가했다.
- 관련 테스트를 4개로 확장했고, 지식 매칭/제안 운영/RAG 웹 흐름 총 13개 테스트 통과를 확인했다.

### 지식 매칭 카드 UI 분리
- 문서 처리 화면에 별도 `지식 기반 체크리스트` 패널을 추가했다.
- 공고/RFP 분석 결과의 `structured.knowledge_matches`를 문의 필요, 체크리스트, 주의사항, 작성 가이드 카드로 분리해 렌더링한다.
- 각 카드에는 지식 ID, 우선순위, 매칭 근거가 표시되고, 사용자가 화면에서 확인 표시를 토글할 수 있다.
- 기존 구조화 분석 텍스트 안에 묻혀 있던 지식 매칭 결과를 별도 업무 체크 영역으로 분리해 실제 검토 흐름에서 쓰기 쉽게 했다.

## 2026-04-17

### 진짜 에이전트 전환 계획
- 현재까지 만든 RAG, 공고 분석, 암묵지 지식카드, 제안 운영, 총괄장 생성은 에이전트가 사용할 도구로 재정의한다.
- 다음 개발 목표는 단순 기능 추가가 아니라 `AnnouncementProposalAgent` 오케스트레이터를 도입하는 것이다.
- `docs/ANNOUNCEMENT_PROPOSAL_AGENT_PLAN.md`를 추가해 Plan, Tool Use, Evidence, Decision, Assignment, Communication, Feedback을 기록하는 에이전트 표준을 명시했다.
- 다음 접속 시 바로 시작할 일은 `src/openharness/services/workflows/announcement_proposal_agent.py` 생성, `AgentRun` 구조 추가, 실행/단계/판단 기록 저장소 구현, 기존 공고 에이전트 흐름을 최소 오케스트레이터로 감싸는 것이다.
- GitHub 상태는 계획 수립 전 `HEAD = private/web-mvp-rag = origin/web-mvp-rag = 2c41eb4`로 확인했다.
