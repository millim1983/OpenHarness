# _refs 파일명 규칙

Claude가 파일을 받으면 이 규칙에 따라 자동으로 파일명을 변경합니다.

## 파일명 패턴

```
{YYYYMMDD}_{service}_{description}.{ext}
```

| 부분 | 규칙 |
|------|------|
| `YYYYMMDD` | 수신일 기준 (예: `20260413`) |
| `service` | 해당 서비스 식별자 (아래 목록 참고) |
| `description` | 내용을 나타내는 영문 snake_case |
| `ext` | 원본 확장자 유지 |

## 서비스 식별자

| 식별자 | 서비스 |
|--------|--------|
| `proposal_ops` | 제안 운영 |
| `announcement` | 공고 에이전트 |
| `rag` | RAG / 문서 처리 |
| `common` | 공통 / 서비스 무관 |

## 폴더별 예시

### `prototypes/`
```
20260413_proposal_ops_dashboard.html
20260413_announcement_result_view.html
```

### `designs/`
```
20260413_proposal_ops_dashboard_v1.png
```

### `specs/`
```
20260413_proposal_ops_requirements.md
20260413_common_role_model.md
```

### `manuals/`
(proposal_assets/manuals/ 또는 서비스별 manuals/ 하위에 저장)
```
20260413_proposal_ops_workflow_guide.md
```
