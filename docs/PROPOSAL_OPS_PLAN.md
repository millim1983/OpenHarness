# Proposal Operations Agent Plan

## Goal

Build a business-management agent for the proposal operations flow:

1. Analyze a public notice and attached forms.
2. Classify the opportunity.
3. Identify deadlines, required documents, questions, risks, and owner tasks.
4. Create a proposed folder/file/checklist execution plan.
5. Show the plan in the web dashboard for review.
6. Later, execute approved folder creation, file movement, file generation, reminders, and reporting.

This agent is focused on proposal operations management, not long-form technical proposal writing.

## Core Principle

Use a hybrid structure:

- LLM judgment for interpretation, planning, question discovery, and draft task breakdown.
- Deterministic workflow state for deadlines, checklists, reminders, execution logs, and review.
- User approval before external messages, file movement, file overwrites, or final submission actions.

## Initial Web-Visible MVP

The first pass returns a `proposal_ops` payload after document analysis:

- Project summary
- Submission checklist
- Manager questions
- Role tasks
- Reminder plan
- Folder plan
- File output plan
- Execution preview

No real filesystem mutation happens in this pass.

## Current UI Placement

Proposal Operations is a separate web workspace.

It should not be merged into the Document Pipeline dashboard. The Document Pipeline page is for upload,
RAG indexing, ingestion review, and document analysis. The Proposal Ops page is for proposal-management
workflow planning and later approval/execution controls.

Current navigation:

- Chat
- Document Pipeline
- Proposal Ops

## Announcement Agent First Automation Target

The announcement agent handles discovered/uploaded notices regardless of final go/no-go decision.

Initial behavior:

1. Process the uploaded notice through the document/RAG path.
2. Extract structured announcement information from the notice.
3. Create a project folder under the configured proposal output root.
4. Use folder naming rule: `yymmdd-전문기관약자 또는 전문기관명-사업명`.
5. Save the uploaded source file under `00_공고_원문`.
6. Create `총괄장.xlsx` with tabs:
   - `사업개요`
   - `문의처`
   - `접수`
   - `제출서류`
   - `컨소시엄`
7. Create/update `공고_모니터링.xlsx` at the output root.

Current output root:

- Default: project-local `.openharness/proposal_outputs`
- Override: `OPENHARNESS_PROPOSAL_OUTPUT_DIR`

Current limitation:

- Multi-file folder upload and folder monitoring are not implemented yet.
- The first pass saves the uploaded file and generates workbooks for the analyzed notice.
- Monitoring workbook updates are implemented by regenerating the workbook from a JSON sidecar.

## Agency Alias Rule

The announcement agent uses an agency alias dictionary for the folder name.

- Alias source: `proposal_assets/config/agency_aliases.json`
- If the extracted agency matches a known agency, use the managed abbreviation.
- If no alias exists, use the full extracted agency name.
- The extracted agency field may be called `agency`, `professional_agency`, `dedicated_agency`, `ordering_agency`, or `client` depending on business type.

The agency means the organization responsible for evaluation/administration:

- SI: 발주처
- R&D: 전문기관
- Non-R&D/support programs: 전담기관 or 사업담당부서

## Config Files

Proposal automation settings are separated from code under `proposal_assets/config/`.

- `agency_aliases.json`: 전문기관/전담기관/발주처 alias dictionary.
- `feature_flags.json`: feature on-off switches.
- `folder_rules.json`: folder naming rule and source-field priority.
- `folder_tree.json`: generated project folder tree.
- `role_book.json`: role labels and default owners.
- `workflow_process.json`: proposal submission stages, automation types, and safety rules.

Runtime override:

- Set `OPENHARNESS_PROPOSAL_CONFIG_DIR` to load a different config directory.

Feature flag policy:

- Advanced or risky features should be gated behind `feature_flags.json`.
- File writes, file moves, message sends, reminder scheduling, and final submission actions must be individually gated.
- `proposal_submission_agent.final_submit` must stay disabled; final submission is human-only.

## Future Configurable Inputs

- Role book: 담당자, 기본 역할, +1 매니저 업무, 연락 채널, 대체 담당자.
- Intake manual: 공고 접수 후 처리 절차, 온라인 접수 절차, 검수 규칙.
- Folder template: 사업별 기본 폴더 구조.
- File template: 체크리스트, 문의사항, 접수전 점검표, 접수후 리포트.
- Business-type rules: R&D, 비R&D, 지원사업, 용역사업, 부처별 규칙.
- Reminder policy: 일반일 1회, 마감 D-3부터 오전/오후 2회 등.

## Future Automation Boundary

Preview first:

- Create folders
- Move uploaded source files
- Generate checklist files
- Generate question files
- Generate submission readiness files
- Send assignee checklist messages
- Schedule reminders

Execute only after approval:

- Filesystem writes
- File moves
- Message sends
- Reminder scheduling
- External portal actions

Never automate final online submission without explicit human confirmation.
