# AGENTS.md — 스마트쿱 제안서 제출 자동화 에이전트 시스템

> 이 파일을 프로젝트 루트에 `AGENTS.md`로 저장하세요.
> Codex(및 Claude Code)는 이 파일을 자동으로 읽어 컨텍스트로 사용합니다.

---

## 1. 시스템 개요

**목적**: 정부과제 제안서 제출 전 과정을 AI 에이전트로 보조·자동화
**핵심 루프**: 공고 수집 → 공고 분석(RAG) → 업무 루프 실행 → 제안서 제출

```
[공고 수집/업로드]
      ↓
[0단계] 기획 — R&R 확정, 일정 수립
      ↓
[1단계] 온라인 접수 — IRIS 가입, 과제번호, 컨소시엄 구성
      ↓
[2단계] 제출 서류 — 배포/취합/안내
      ↓
[3단계] 예산 — 예산 확정, 참여연구원 확정
      ↓
[4단계] 제안서 작성 — 전략 도출, 작성, 품질 검토
      ↓
[최종 제출] IRIS 제출 + 서류 제출
```

---

## 2. 역할(Role) 분류 체계

> 시스템은 **사람을 이름이 아닌 role로 식별**합니다.
> 현재는 스마트쿱 내부 인원이 각 role을 담당하지만,
> 컨소시엄사 참여 시 해당 role을 외부 담당자에게 위임할 수 있습니다.

### 2-1. 역할 타입 계층

```
ParticipantRole
├── INTERNAL (스마트쿱 내부)
│   ├── COORDINATOR        — 제안 전체 조율 및 의사결정
│   ├── PROPOSAL_LEAD      — 제안서 작성 총괄
│   ├── PMO                — 일정·요건 관리
│   ├── QUALITY            — 품질 검토 및 리스크 판단
│   ├── BUDGET_OWNER       — 예산 최종 승인
│   └── SUBMISSION_MANAGER — IRIS 접수 및 서류 처리
│
└── CONSORTIUM (컨소시엄 참여기관 — 현재 또는 향후)
    ├── LEAD_AGENCY        — 주관기관 담당자
    ├── CO_AGENCY          — 공동기관 담당자
    ├── SUBCONTRACT        — 위탁기관 담당자
    └── DEMAND_AGENCY      — 수요기관 담당자
```

### 2-2. 현재 역할 → 담당자 매핑 (스마트쿱 내부)

| role | 담당자 | 비고 |
|---|---|---|
| `COORDINATOR` | 제안 코디 (TBD) | 과제마다 지정 |
| `PROPOSAL_LEAD` | 제안 담당자 (TBD) | 과제마다 지정 |
| `PMO` | 제안 PMO 매니저 (TBD) | 과제마다 지정 |
| `QUALITY` | 제안 품질 매니저 (TBD) | 과제마다 지정 |
| `BUDGET_OWNER` | 이역수 사장 | 고정 |
| `SUBMISSION_MANAGER` | 강경숙 대표 + 염현준 선임 | 고정 |

> 스마트쿱이 주관기관인 경우 `LEAD_AGENCY`는 `SUBMISSION_MANAGER`가 겸임합니다.
> 스마트쿱이 공동기관인 경우 `CO_AGENCY` role이 별도 활성화됩니다.

### 2-3. 역할별 상세 책임 정의

#### COORDINATOR (제안 코디)
```
책임:
  - 기획 개시 및 전체 방향 설정
  - 컨소시엄 커뮤니케이션 채널 관리
  - 컨소시엄간 제안 R&R 확정 및 공유
  - 개발 R&R 확정 및 공유
  - 예산 배분 확정 후 전체 공유
  - 제출 포기 여부 최종 의사결정
  - 수요처 등 외부 협력 요청 처리

자동화 불가 항목 (반드시 직접 수행):
  - 기획 방향 최종 결정
  - 컨소시엄 관계 협상
  - 제출 포기 의사결정

시스템에서 받는 알림:
  - 기획 개시 트리거
  - R&R 초안 생성 완료 (검토 요청)
  - 단계 전환 알림
  - 제출 여유일 부족 경고
```

#### PROPOSAL_LEAD (제안 담당자)
```
책임:
  - 기획서 및 프로젝트 큰그림 제시
  - 제안서 양식 배포 및 완성본 취합
  - 제안 전략·특장점·차별화 포인트 도출
  - 수요처 참여요청 서류 작성 (COORDINATOR 요청 시)
  - 컨소시엄 R&R·연락망 단톡방 관리
  - 마감 1일 전 완성본 확정

자동화 불가 항목:
  - 제안 전략·차별화 도출 (창의적 판단)
  - 제안서 최종 검토 및 승인

시스템에서 받는 알림:
  - 양식 배포 트리거
  - 취합 현황 리포트 (일일)
  - 마감 D-1 완성 여부 경고
  - 품질 체크 리포트
```

#### PMO (제안 PMO 매니저)
```
책임:
  - 추진일정 수립 및 마감 역산 관리
  - 제안 요건 파악 및 필요 정보 조사
  - 서류 목록 정보 확인

자동화 불가 항목:
  - 없음 (전항목 AI 보조 가능, 최종 확인만 사람이)

시스템에서 받는 알림:
  - 일정 역산 초안 생성 완료
  - 서류 목록 추출 완료
  - 요건 분석 완료
```

#### QUALITY (제안 품질 매니저)
```
책임:
  - 제출 마감 기준 최소 여유일 확보 여부 점검
  - 여유일 미달 시 제출 포기 협의 (→ COORDINATOR)
  - RFP 필수 기술 요건 누락 여부 점검
  - 제출 요건 전반 검토

자동화 불가 항목:
  - 제출 포기 권고 (경영 판단 협의)
  - 최종 품질 승인

시스템에서 받는 알림:
  - 여유일 부족 경고 (즉시)
  - AI 품질 체크 리포트 (검토 요청)
  - 누락 항목 발생 시 즉시 알림
```

#### BUDGET_OWNER (예산 책임자)
```
책임:
  - 항목별 예산 세부 내역 최종 확정
  - 사업관리팀 예산 규정 확인 및 컨소시엄 공유
  - 참여연구원 명단·역할 최종 확정
  - 인건비 산정 기준 적용 확인

자동화 불가 항목:
  - 예산 최종 승인 (경영 책임)
  - 참여연구원 개인 동의 수령

시스템에서 받는 알림:
  - 예산 시뮬레이션 초안 생성 완료 (승인 요청)
  - 참여연구원 적격 검토 완료 (확인 요청)
  - 예산 규정 분석 요약 완료
```

#### SUBMISSION_MANAGER (접수 담당자)
```
책임:
  - IRIS 가입 안내 및 완료 확인 총괄
  - 과제번호 취득 및 전체 공유
  - 과제명 수정 가능 여부 확인
  - 컨소시엄 구성 및 과제정보 입력
  - 서류 배포·취합·안내 총괄
  - IRIS 최종 제출 (직접 클릭)

자동화 불가 항목:
  - IRIS 최종 제출 클릭 (법적 제출 행위)
  - 외부기관 서류 직접 발급
  - 주관사 대행 접수 시 ID/PW 처리

시스템에서 받는 알림:
  - IRIS 미가입자 발생 즉시
  - 과제번호 생성 완료
  - 서류 취합 현황 (일일)
  - 전체 체크리스트 완료 → 최종 제출 대기 알림
```

---

### 2-4. 컨소시엄 역할 정의

> 컨소시엄사가 합류할 때 아래 role로 시스템에 등록합니다.
> 각 role은 해당 기관에서 1명 이상의 담당자를 지정합니다.

#### LEAD_AGENCY (주관기관 담당자)
```
해당 조건: 스마트쿱이 공동기관일 때 외부 주관기관 담당자

책임:
  - IRIS 과제 구성 및 컨소시엄 초대
  - 주관기관 과제정보 입력
  - 최종 제출 권한 보유

시스템 권한:
  - 과제 생성/수정
  - 컨소시엄 구성원 초대
  - 최종 제출 버튼 활성화
```

#### CO_AGENCY (공동기관 담당자)
```
해당 조건: 스마트쿱 또는 외부 기관이 공동기관으로 참여

책임:
  - 소속 기관 IRIS 정보 입력
  - 소속 기관 참여연구원 등록
  - 소속 기관 서류 제출
  - 소속 기관 예산 파트 입력

시스템 권한:
  - 소속 기관 데이터 열람/수정 (타 기관 데이터 열람 불가)
  - 서류 업로드
  - 체크리스트 중 소속 기관 항목만 완료 처리
```

#### SUBCONTRACT (위탁기관 담당자)
```
해당 조건: 위탁 연구 기관이 있을 때

책임:
  - 위탁 과제 내용 및 예산 입력
  - 위탁 기관 IRIS 가입 및 정보 입력
  - 위탁 관련 서류 제출

시스템 권한:
  - CO_AGENCY와 동일하나 위탁 파트에 한정
```

#### DEMAND_AGENCY (수요기관 담당자)
```
해당 조건: 수요기관이 예산을 받거나 전문기관 요구 시 IRIS 등록 필요

책임:
  - 수요기관 IRIS 가입 (요구 시)
  - 수요기관 확인서 발급 및 제출
  - 수요 현황 관련 정보 제공

시스템 권한:
  - 읽기 전용 (자기 기관 서류 업로드만 가능)
```

---

## 3. 역할별 알림 수신 매트릭스

| 알림 이벤트 | COORDINATOR | PROPOSAL_LEAD | PMO | QUALITY | BUDGET_OWNER | SUBMISSION_MGR | CO_AGENCY | SUBCONTRACT |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 기획 개시 | ✅ | ✅ | ✅ | ✅ | - | - | - | - |
| R&R 초안 생성 | ✅(승인) | ✅ | - | - | - | - | ✅(수신) | ✅(수신) |
| 일정 역산 초안 | ✅ | - | ✅(승인) | - | - | - | - | - |
| IRIS 미가입자 | - | - | - | - | - | ✅ | - | - |
| 과제번호 생성 | ✅ | ✅ | ✅ | - | - | ✅ | ✅ | ✅ |
| 서류 배포 | - | - | - | - | - | ✅ | ✅ | ✅ |
| 예산 초안 생성 | - | - | - | - | ✅(승인) | - | - | - |
| 참여연구원 검토 | - | - | - | - | ✅(승인) | - | - | - |
| 품질 체크 완료 | - | ✅ | - | ✅(승인) | - | - | - | - |
| 여유일 부족 경고 | ✅ | - | ✅ | ✅ | - | - | - | - |
| 마감 D-3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 마감 D-1 경고 | ✅ | ✅ | ✅ | ✅ | - | ✅ | ✅ | ✅ |
| 전체 완료 → 제출 대기 | ✅ | - | - | ✅ | - | ✅(실행) | - | - |

---

## 4. 자동화 분류

### 4-1. 완전 자동 (auto)

| 업무 | 담당 role | 트리거 |
|---|---|---|
| IRIS 가입 안내 발송 | SUBMISSION_MANAGER | 과제 생성 이벤트 |
| IRIS 미가입자 리마인더 | SUBMISSION_MANAGER | 마감 D-3, D-1 |
| 과제번호 생성 즉시 전파 | SUBMISSION_MANAGER | 과제번호 입력 완료 |
| 마감 D-day 알림 | 전체 | 매일 00:00 크론 |
| 체크리스트 미완료 알림 | 항목 담당 role | 마감 D-3 |
| 서류 템플릿 자동 배포 | SUBMISSION_MANAGER | 2단계 진입 |
| 발급 서류 선제 알림 | SUBMISSION_MANAGER | 2단계 진입 + D-14 |
| 서류 취합 현황 갱신 | SUBMISSION_MANAGER | 파일 업로드 이벤트 |
| RFP 필수 요건 추출 | PMO + QUALITY | RFP 파일 업로드 |
| 완성 경고 D-1 | PROPOSAL_LEAD | 마감 전날 크론 |

### 4-2. AI 보조 (assist) — AI 초안 → 담당자 승인

| 업무 | AI 역할 | 승인 role |
|---|---|---|
| R&R 초안 생성 | 역할 분담 초안 작성 | COORDINATOR |
| 추진일정 역산 | 마감 기준 단계별 일정 계산 | PMO |
| 서류 목록 추출 | RFP 파싱 → 서류 목록 | PMO |
| 예산 배분 시뮬레이션 | 규정 기반 배분 초안 | BUDGET_OWNER |
| 참여연구원 적격 검토 | 규정 대비 적격 여부 체크 | BUDGET_OWNER |
| 성과지표 초안 | 유사 과제 기반 지표 추천 | PROPOSAL_LEAD |
| 제안서 품질 체크 | RFP 요건 vs 제안서 비교 | QUALITY |
| IRIS 입력값 사전 검증 | 입력 전 오류·누락 탐지 | SUBMISSION_MANAGER |
| 컨소시엄 R&R 초안 | 참여기관별 역할 초안 | COORDINATOR |

### 4-3. 사람 전담 (human) — 절대 자동화 금지

| 업무 | 담당 role | 불가 이유 |
|---|---|---|
| 기획 방향 최종 결정 | COORDINATOR | 경영 판단 |
| 컨소시엄 관계 협상 | COORDINATOR | 대외 신뢰 관계 |
| 예산 최종 승인 | BUDGET_OWNER | 경영 책임 |
| 직인 및 법적 서명 | 각 기관 대표 | 법적 행위 |
| 제출 포기 의사결정 | COORDINATOR + QUALITY | 경영 판단 |
| 제안 전략·차별화 도출 | PROPOSAL_LEAD | 창의적 판단 |
| 수요처 설득·협력 요청 | COORDINATOR | 대외 관계 |
| 제안서 최종 검토·승인 | QUALITY + PROPOSAL_LEAD | 내용 책임 |
| 외부기관 서류 직접 발급 | SUBMISSION_MANAGER | 외부 기관 방문 |
| IRIS 최종 제출 클릭 | SUBMISSION_MANAGER 또는 LEAD_AGENCY | 법적 제출 행위 |
| 참여연구원 개인 동의 수령 | SUBMISSION_MANAGER | 개인 동의 행위 |

---

## 5. 데이터 모델

### Project

```python
class Project:
    id: str                          # 과제번호 (IRIS 기준)
    name: str
    status: ProjectStatus            # PLANNING|IRIS|DOCUMENTS|BUDGET|PROPOSAL|SUBMITTED
    deadline: datetime
    announcement_file: str           # 공고 원문 파일 경로 (RAG 인덱싱용)
    our_role: AgencyRole             # LEAD_AGENCY | CO_AGENCY | SUBCONTRACT
    consortium: List[ConsortiumMember]
    role_assignments: Dict[RoleType, List[PersonInfo]]  # role → 담당자 목록
    checklist: List[ChecklistItem]
    budget_draft: Optional[BudgetDraft]
    researchers: List[Researcher]
    documents: List[DocumentItem]
```

### ConsortiumMember

```python
class ConsortiumMember:
    org_id: str
    org_name: str
    role: AgencyRole                 # LEAD_AGENCY | CO_AGENCY | SUBCONTRACT | DEMAND_AGENCY
    contact_persons: List[PersonInfo]
    iris_joined: bool
    budget_allocated: Optional[int]
    documents_submitted: List[str]
    checklist_status: Dict[str, bool]  # 해당 기관 담당 항목만
```

### PersonInfo

```python
class PersonInfo:
    person_id: str
    name: str
    org_name: str
    role: RoleType
    contact: str
    iris_id: Optional[str]
    notification_channels: List[str]  # ["slack", "kakaotalk", "email"]
    is_internal: bool                 # 스마트쿱 내부 여부
```

### ChecklistItem

```python
class ChecklistItem:
    id: str
    stage: int                        # 0~4
    title: str
    automation_type: AutoType         # AUTO | ASSIST | HUMAN
    assigned_roles: List[RoleType]
    responsible_org: str              # 담당 기관 (컨소시엄 데이터 격리 기준)
    status: ItemStatus                # PENDING | IN_PROGRESS | DONE | NA
    completed_at: Optional[datetime]
    deadline_offset_days: int         # 메인 마감 기준 며칠 전까지 완료
```

---

## 6. 단계 전환 조건

```python
STAGE_TRANSITION_CONDITIONS = {
    0: {
        "required_items": ["rr_confirmed", "schedule_confirmed"],
        "required_approvals": [RoleType.COORDINATOR],
        "auto_notify": [RoleType.SUBMISSION_MANAGER, RoleType.PMO]
    },
    1: {
        "required_items": ["iris_all_joined", "task_number_issued", "consortium_configured"],
        "required_approvals": [RoleType.SUBMISSION_MANAGER],
        "auto_notify": [RoleType.COORDINATOR, RoleType.PMO, "ALL_CONSORTIUM"]
    },
    2: {
        "required_items": ["documents_distributed", "collection_started"],
        "required_approvals": [],
        "auto_notify": [RoleType.BUDGET_OWNER]
    },
    3: {
        "required_items": ["budget_approved", "researchers_confirmed"],
        "required_approvals": [RoleType.BUDGET_OWNER],  # 필수 — 없으면 진입 차단
        "auto_notify": [RoleType.PROPOSAL_LEAD, RoleType.QUALITY]
    },
    4: {
        "required_items": ["proposal_completed", "quality_check_passed", "all_documents_collected"],
        "required_approvals": [RoleType.QUALITY, RoleType.PROPOSAL_LEAD],
        "auto_notify": [RoleType.SUBMISSION_MANAGER],
        "final_action": "HUMAN_ONLY"  # IRIS 제출은 사람만 — 절대 자동화 금지
    }
}
```

---

## 7. RAG 파이프라인

```python
RAG_QUERY_PATTERNS = {
    "required_documents": "제출 서류 목록 및 양식",
    "technical_requirements": "필수 기술 요건 및 평가 기준",
    "budget_rules": "연구비 계상 기준 및 비목별 한도",
    "eligibility": "참여 자격 및 제한 사항",
    "evaluation_criteria": "평가 항목 및 배점",
    "submission_format": "제안서 작성 양식 및 분량 제한",
    "milestones": "연차별 목표 및 성과지표 기준"
}

class AnnouncementAnalysis:
    project_type: str
    total_budget: int
    duration_years: int
    deadline: datetime
    required_documents: List[DocumentRequirement]
    technical_requirements: List[str]
    eligibility_conditions: List[str]
    evaluation_criteria: List[EvaluationItem]
    auto_generated_checklist: List[ChecklistItem]
    warnings: List[str]
    source_references: List[SourceRef]   # 출처 문서 + 페이지
    confidence_scores: Dict[str, float]  # 항목별 신뢰도 (0.7 미만 = 원문 확인 필요 태그)
```

---

## 8. 개발 규칙

1. **법적 제출 행위 절대 자동화 금지**
   `final_action: HUMAN_ONLY` 항목은 버튼만 제공, 실행은 사람이 직접

2. **예산 승인 없이 4단계 진입 불가**
   `BUDGET_OWNER` 승인 플래그 없으면 제안서 작성 단계 차단

3. **컨소시엄 데이터 격리**
   `responsible_org` 기준으로 접근 제어, 타 기관 데이터 열람 불가

4. **알림 과부하 방지**
   동일 항목 알림 하루 최대 2회 / D-7 이전은 일일 요약으로 묶어서 발송

5. **RAG 출처 투명성**
   모든 분석 결과에 `source_references` + `confidence_scores` 필수 포함

6. **역할 위임 지원 (컨소시엄 확장 대비)**
   담당자 이름 하드코딩 금지 — 항상 `role_assignments` 테이블 참조
   향후 컨소시엄사 참여 시 role 재배정만으로 알림·권한 자동 전환
