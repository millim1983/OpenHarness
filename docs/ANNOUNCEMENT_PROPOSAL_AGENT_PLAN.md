# Announcement Proposal Agent Plan

Updated: 2026-04-17 KST

## Goal

Move beyond the Web MVP and build a real business agent for the announcement-to-proposal workflow.

The agent must not be a single document-analysis prompt or a keyword checklist renderer. It must execute a work process:

```text
announcement folder upload
  -> workspace/folder creation
  -> document classification and processing
  -> announcement/RFP analysis
  -> tacit-knowledge retrieval
  -> applicability judgment
  -> proposal work assignment
  -> checklist and inquiry generation
  -> workbook/file generation
  -> user review and feedback memory
```

The user should be able to upload a notice/RFP folder and press a button. The system should carry out the workflow and expose decisions, evidence, owners, outputs, and review points.

## Product Definition

Working name:

```text
AnnouncementProposalAgent
공고-제안 운영 에이전트
```

This agent uses existing MVP pieces as tools:

- RAG/indexing: document memory and evidence lookup.
- Announcement analysis: notice/RFP understanding.
- Tacit knowledge store: human experience and domain memory.
- Proposal Ops: work assignment and checklist generation.
- Announcement agent output writer: folder/workbook/file generation.
- Web UI: run console and review surface.

## Agent Standard

From 2026-04-17 onward, a feature should not be called an agent feature unless it includes:

- Plan: explicit steps and intended workflow.
- Tool use: calls to stable local services/tools.
- Evidence: source document or knowledge item references.
- Decision: applicable/not applicable/needs inquiry/reference only.
- Assignment: owner/role and workflow stage.
- Communication: reason, confidence, and action text.
- Feedback: user review can affect later runs.

## Target Button Flow

```text
공고-제안 에이전트 실행
  1. 파일 접수 및 분류
  2. 사업 폴더 생성
  3. 제안 준비 폴더트리 생성
  4. 원본 파일 보존
  5. 문서 처리 및 RAG 색인
  6. 공고/RFP 핵심 필드 분석
  7. 암묵지/규정/과거 문의 결과 후보 검색
  8. 후보 지식의 적용성 판단
  9. 업무 분장 및 담당 역할 배정
  10. 제출 체크리스트/문의사항/주의사항 생성
  11. 총괄장 및 운영 산출물 생성
  12. 웹 UI에서 결과 검토
  13. 사용자 피드백을 지식으로 저장
```

## Agent Run State

Add a first-class run record.

```json
{
  "run_id": "APR-yyyymmdd-001",
  "status": "planned | running | completed | failed | needs_review",
  "goal": "공고 업로드부터 제안 준비 산출물 생성",
  "created_at": "",
  "updated_at": "",
  "input_files": [],
  "workspace": {
    "root_dir": "",
    "folder_tree": []
  },
  "plan": [],
  "steps": [],
  "tool_calls": [],
  "decisions": [],
  "assignments": [],
  "outputs": [],
  "review_items": []
}
```

Each step should be recorded.

```json
{
  "step_id": "STEP-004",
  "name": "knowledge_applicability_judgment",
  "status": "completed",
  "input_summary": "",
  "decision_summary": "",
  "evidence": [],
  "outputs": []
}
```

## Knowledge Judgment Contract

Replace direct keyword matching as the final output path.

Current problem:

```text
saved knowledge card
  -> weak keyword match
  -> shown in checklist
```

Target:

```text
candidate knowledge retrieval
  -> applicability judgment
  -> decision and role assignment
  -> surfaced only when useful
```

Judgment output:

```json
{
  "knowledge_id": "KI-20260415-001",
  "decision": "applicable | not_applicable | needs_inquiry | reference_only",
  "surface_as": "checklist | inquiry_item | warning | writing_guidance | hidden",
  "assigned_role": "사업관리 | 예산 | 기술 | 제안서본문 | 대표확인 | 미배정",
  "workflow_stage": "announcement_review",
  "confidence": "high | medium | low",
  "reason": "",
  "evidence": [
    {
      "source_type": "announcement | rfp | tacit_knowledge | regulation | prior_inquiry",
      "source_id": "",
      "quote_or_summary": ""
    }
  ],
  "action": ""
}
```

Important:

- `not_applicable` decisions should be stored in the run record, but hidden from normal UI.
- `needs_inquiry` should become a visible inquiry item.
- `domain_rule` cards without evidence should not become final checklist items automatically.
- User feedback such as "이건 아님" should become a negative condition or review record.

## Proposed Folder Output

The agent should create a project workspace like:

```text
yymmdd-기관약자-사업명/
  00_공고_원문/
  01_공고_RFP_분석/
    공고분석.json
    공고분석.md
    적용지식_판단.json
  02_총괄장/
    총괄장.xlsx
  03_제안운영/
    제안업무분장.json
    제안업무분장.xlsx
    체크리스트.md
    문의사항.md
  04_제출서류/
    첨부파일목록.json
  05_작성참고/
    암묵지_주의사항.md
    규정_확인사항.md
  99_로그/
    agent_run.json
    decisions.json
```

## Proposed Module Structure

Add:

```text
src/openharness/services/workflows/announcement_proposal_agent.py
tests/test_services/test_announcement_proposal_agent.py
```

Initial internal components:

- `AgentRunStore`: JSON persistence for runs.
- `AnnouncementProposalAgent`: orchestrates the workflow.
- `IntakeStep`: classify uploaded files.
- `WorkspaceStep`: create workspace and folder tree.
- `DocumentProcessingStep`: extract/index/analyze usable source documents.
- `KnowledgeJudgmentStep`: judge tacit/regulation knowledge applicability.
- `ProposalPlanningStep`: assignment/checklist/inquiry generation.
- `OutputGenerationStep`: write workbooks and markdown/json outputs.

## Web API Direction

Add new API while keeping the old endpoint temporarily:

```text
POST /api/announcement-proposal-agent/run
GET  /api/announcement-proposal-agent/state
POST /api/announcement-proposal-agent/review
```

The old `/api/announcement-agent/run` can later delegate to the new orchestrator or be deprecated.

## UI Direction

Rename or replace `공고 에이전트` with:

```text
공고-제안 에이전트
```

UI sections:

- Upload folder.
- Run button.
- Agent progress timeline.
- Generated workspace/folder tree.
- 공고 분석.
- 제안업무 분장.
- 제출 체크리스트.
- 문의 필요.
- 암묵지 적용 판단.
- 생성 파일.
- Review actions: `맞음`, `아님`, `수정`, `문의필요`, `다음에도 체크`.

## Immediate Start Tasks

Date to resume: 2026-04-17 or next session.

Start here, in this order:

1. Create `src/openharness/services/workflows/announcement_proposal_agent.py`.
2. Add dataclasses or typed dicts for:
   - `AgentRun`
   - `AgentStep`
   - `AgentDecision`
   - `AgentAssignment`
   - `AgentOutput`
3. Add `AgentRunStore` that persists run JSON under the project RAG/data directory.
4. Write focused tests for run creation, step recording, and decision recording.
5. Implement a minimal orchestrator that wraps the existing announcement-agent flow and records:
   - plan
   - steps
   - tool calls
   - outputs
6. Add `KnowledgeJudgmentStep` that converts current `knowledge_matches` into explicit decisions:
   - applicable
   - not_applicable
   - needs_inquiry
   - reference_only
7. Update Proposal Ops to consume judgments, not raw keyword matches.
8. Add the first `/api/announcement-proposal-agent/run` endpoint.
9. Update the web UI only after the backend run record is stable.

## Do Not Do Next

- Do not add more checklist UI before adding `AgentRun`.
- Do not make keyword matching the final judgment path.
- Do not call the workflow an agent unless decisions/evidence/assignments are recorded.
- Do not delete existing MVP endpoints until the new orchestrator is stable.
