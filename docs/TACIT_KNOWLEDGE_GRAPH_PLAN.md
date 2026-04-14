# Tacit Knowledge Graph Plan

Updated: 2026-04-14 KST

## Goal

Build a system that captures tacit business knowledge from project preparation, submission, post-project review, regulations, notices, and RFPs, then reuses it during later announcement/RFP analysis.

The system should answer:

- When should this knowledge be shown again?
- Which business type, ministry, agency, document type, and workflow stage does it apply to?
- Is this a regulation-backed rule, notice-specific fact, human experience, submission warning, or inquiry item?
- Is the knowledge confirmed, uncertain, rejected, stale, or waiting for inquiry?
- What source or experience produced it?

## Design Position

Do not store only free-form notes.

Free-form notes are allowed as input, but the system must preserve the raw note and also convert it into structured, reviewable knowledge cards.

Do not start with a heavy graph database server.

Use JSON-based knowledge cards plus a relation index first. Keep the data shaped like graph nodes and edges so it can later migrate to an embedded graph database such as Kuzu if relation queries become central.

## Core Flow

```text
User memo / project review / inquiry result / notice / RFP / regulation
  -> raw note or source document stored
  -> agent creates structured draft cards
  -> user reviews draft cards
  -> approved cards are stored in the knowledge store
  -> later announcement/RFP analysis retrieves matching cards
  -> checklist, inquiry items, risks, and writing guidance are surfaced
```

## Storage Shape

```text
knowledge_store/
  raw_notes/
    RN-yyyymmdd-serial.json
  lessons/
    TK-yyyymmdd-serial.json
  rules/
    KR-yyyymmdd-serial.json
  facts/
    KF-yyyymmdd-serial.json
  inquiries/
    IQ-yyyymmdd-serial.json
  relations.json
```

Suggested config files:

```text
proposal_assets/config/
  tacit_knowledge_schema.json
  knowledge_item_schema.json
  knowledge_categories.json
  knowledge_extraction_prompt.json
  document_ingestion_profiles.json
```

## Knowledge Card Types

- `lesson`: human tacit knowledge, project review, repeated practical checklist.
- `domain_rule`: regulation-backed or regulation-like rule that needs source evidence.
- `announcement_fact`: fact explicitly extracted from a notice or RFP.
- `submission_warning`: formatting, file, copy, signature, color, print, or submission-channel warning.
- `strategy_hint`: proposal strategy or writing guidance.
- `inquiry_item`: item that must be confirmed with the agency/contact point.
- `correction`: human correction to a model output or previous extraction.

## Required Fields

Each structured card should include:

```json
{
  "id": "",
  "title": "",
  "content": "",
  "knowledge_type": "lesson",
  "category": [],
  "business_domain": [],
  "ministry": [],
  "agency": [],
  "business_type": [],
  "project_structure": [],
  "workflow_stage": [],
  "document_type": [],
  "trigger": {
    "keywords": [],
    "conditions": [],
    "negative_conditions": [],
    "when_to_show": []
  },
  "recommended_action": "",
  "display": {
    "surface_as": "checklist",
    "priority": "medium",
    "message": ""
  },
  "evidence": [
    {
      "source_type": "human_experience",
      "source_id": "",
      "source_name": "",
      "page": null,
      "section": null,
      "quote": "",
      "note": ""
    }
  ],
  "verification": {
    "status": "unreviewed",
    "reviewed_by": null,
    "reviewed_at": null,
    "confidence": "medium"
  },
  "relations": {
    "related_announcements": [],
    "related_regulations": [],
    "related_knowledge_items": [],
    "conflicts_with": [],
    "supersedes": []
  },
  "lifecycle": {
    "created_at": "",
    "updated_at": "",
    "last_used_at": null,
    "expires_at": null
  }
}
```

## When-To-Show Logic

The most important field is not only the note content. It is `trigger.when_to_show`.

Examples:

- `announcement_review`: show while reading a new notice.
- `rfp_review`: show while reviewing an RFP.
- `proposal_planning`: show when deciding consortium, budget, and writing strategy.
- `budget_planning`: show when research cost, private contribution, cash/in-kind burden, and total budget are being prepared.
- `submission_document_preparation`: show while preparing forms, certificates, consents, seals, and supporting documents.
- `pre_submission_review`: show before final upload/print/submission.
- `post_project_retrospective`: show while recording lessons after a submission or project.

## Example: SI Proposal Submission Review

One raw memo should become multiple cards:

- 현황 분석 and 배경/필요성 작성 품질 check.
- 목표 시스템 user/persona/scenario check.
- 목표 시스템 구성도, 기능 구성도, HW/SW delivery architecture check.
- 부본 흑백 제출 condition check when RFP mentions black-and-white copies.
- HWP/PDF conversion warning: do not use grey text that can disappear after PDF conversion; use black text for body copy.

Example card:

```json
{
  "title": "부본 흑백 제출 조건 확인",
  "content": "공고 또는 RFP에 부본을 흑백으로 제출하라는 조건이 있으면 제출 전 PDF/인쇄본의 흑백 변환 여부를 확인한다.",
  "knowledge_type": "submission_warning",
  "business_domain": ["SI용역"],
  "agency": ["한국철도공사"],
  "workflow_stage": ["rfp_review", "pre_submission_review"],
  "document_type": ["공고", "RFP", "제출서류"],
  "category": ["제출주의사항"],
  "trigger": {
    "keywords": ["부본", "흑백", "제출서류", "인쇄본"],
    "conditions": ["RFP에 부본 흑백 제출 조건이 있을 때"],
    "when_to_show": ["rfp_review", "pre_submission_review"]
  },
  "display": {
    "surface_as": "checklist",
    "priority": "high",
    "message": "부본 흑백 제출 조건과 제출본 흑백 처리 여부를 확인한다."
  },
  "verification": {
    "status": "confirmed",
    "reviewed_by": "user",
    "reviewed_at": null,
    "confidence": "high"
  }
}
```

## Example: R&D Demand Organization Knowledge

The `수요기관` topic must be split into conditional cards instead of one large note.

Example cards:

- MOTIE R&D: if a demand company participates as a joint research organization and receives research funds, check whether ministry rules allow middle-market/large companies to bear private contribution and cash burden at SME-level exception rates.
- MSS R&D: if a middle-market or large demand company participates, check whether it may only participate as a subcontracted/entrusted organization.
- Research-fund-free demand organization: if the demand organization does not receive research funds and is not an agreement party, prepare participation commitment letter and optional business consultation letter to show consortium readiness.

These should surface during:

- `announcement_review`
- `rfp_review`
- `consortium_planning`
- `budget_planning`
- `submission_document_preparation`

If a new notice does not explicitly mention the rule, surface it as `inquiry_item` rather than silently applying it.

## Relation Model For Future Graph DB

Initial `relations.json` should store edge-like records:

```json
[
  {
    "from_type": "knowledge_item",
    "from_id": "TK-20260414-001",
    "relation": "applies_to",
    "to_type": "business_domain",
    "to_id": "SI용역"
  },
  {
    "from_type": "knowledge_item",
    "from_id": "KR-20260414-001",
    "relation": "triggered_by",
    "to_type": "topic",
    "to_id": "수요기관"
  }
]
```

Future graph node types:

- business domain
- ministry
- agency
- document
- workflow stage
- topic
- regulation
- announcement
- knowledge item
- inquiry result

Future graph edge types:

- `applies_to`
- `used_in`
- `triggered_by`
- `derived_from`
- `requires_inquiry`
- `conflicts_with`
- `overrides`
- `supersedes`

## UI Plan

Support multiple input modes:

- Free memo: user writes natural language.
- Guided form: title, business type, category, importance, memo.
- Feedback from analysis: user marks model output as wrong, missing, or inquiry-needed.
- Post-submission retrospective: user records what was missed and what to check next time.
- Inquiry result: user records answer from agency/contact point.

Save flow:

```text
User enters memo
  -> agent proposes structured cards
  -> UI shows category, trigger, scope, action, evidence, status
  -> user clicks save, edit, split, merge, or discard
  -> confirmed cards are stored and become reusable
```

## MVP Implementation Plan

1. Add config files for categories, statuses, workflow stages, and extraction prompts.
2. Add dataclasses and JSON store for raw notes, knowledge cards, and relation edges.
3. Add tests for schema validation, default values, relation indexing, and store round trip.
4. Add web API for creating a raw memo and getting structured draft cards.
5. Add web UI for memo entry and structured preview.
6. Add save/edit/discard actions for draft cards.
7. Add retrieval of matching lesson/rule cards during announcement/RFP analysis.
8. Surface matches as checklist items, inquiry items, writing guidance, and warnings.
9. Track `last_used_at` so recurring useful knowledge can be ranked higher.
