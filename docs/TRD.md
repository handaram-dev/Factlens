# TRD: FactLens (팩트렌즈)

> **관련 PRD**: `docs/PRD.md` v0.3

## 1. 기술 개요

매일 오전 GitHub Actions가 Python 파이프라인을 실행하여 Google News RSS에서 뉴스를 수집하고, Gemini Flash API로 요약·검증한 뒤, 정적 HTML을 생성하여 Cloudflare Pages에 배포하는 서버리스 뉴스 브리핑 시스템.

---

## 2. 기술 스택

| 영역 | 기술 | 선택 이유 |
|------|------|-----------|
| 파이프라인 실행 | **GitHub Actions** (cron) | 무료 티어, 스케줄 트리거 지원, 별도 서버 불필요 |
| 파이프라인 코드 | **Python 3.12** | feedparser 등 RSS 파싱 생태계, AI API 연동 편의 |
| AI 요약/검증 | **Gemini Flash API** | 무료 티어 넉넉, 한국어 품질 양호 |
| 교차검증 검색 | **Google Custom Search API** | 100회/일 무료, 프로그래매틱 웹 검색 |
| Frontend | **정적 HTML** (Jinja2 템플릿) | SPA 불필요, 빌드 타임 렌더링으로 충분 |
| 호스팅 | **Cloudflare Pages** | 무료, 대역폭 무제한, 한국 CDN 노드 |
| 데이터 저장 | **JSON 파일** (Git 관리) | DB 불필요, 하루 1회 갱신되는 정적 데이터 |

### 외부 라이브러리/API

| 이름 | 용도 |
|------|------|
| `feedparser` | Google News RSS 파싱 |
| `google-generativeai` | Gemini Flash API 호출 |
| `requests` | HTTP 요청 (Google Custom Search 등) |
| `jinja2` | HTML 템플릿 렌더링 |

---

## 3. 시스템 아키텍처

```
[GitHub Actions — cron 매일 07:00 KST]
        │
        ▼
[Python Pipeline]
        │
        ├─ 1. 수집 ──→ [Google News RSS]
        │
        ├─ 2. 필터링 (연예·스포츠 제외, 상위 10~15개 선별)
        │
        ├─ 3. AI 처리 ──→ [Gemini Flash API]
        │   ├─ 쉬운 요약 생성
        │   ├─ 교차검증 ──→ [Google Custom Search API]
        │   ├─ 검증 태그 부여 (✅/⚠️/❌)
        │   └─ 관련 언론사 원문 링크 수집
        │
        ├─ 4. JSON 저장 (data/YYYY-MM-DD.json)
        │
        └─ 5. HTML 생성 (Jinja2) → dist/index.html
                │
                ▼
        [Cloudflare Pages 배포]
                │
                ▼
        [사용자 브라우저]
```

---

## 4. 디렉토리 구조

```
factlens/
├── .github/
│   └── workflows/
│       └── daily-briefing.yml    # GitHub Actions 워크플로우
├── pipeline/
│   ├── __init__.py
│   ├── main.py                   # 파이프라인 엔트리포인트
│   ├── collector.py              # Google News RSS 수집
│   ├── filter.py                 # 카테고리 필터링 + 선별
│   ├── summarizer.py             # Gemini 요약 생성
│   ├── verifier.py               # 교차검증 + 태그 부여
│   ├── renderer.py               # Jinja2 → HTML 생성
│   └── models.py                 # 데이터 모델 (dataclass)
├── templates/
│   └── index.html.j2             # 브리핑 페이지 템플릿
├── static/
│   ├── style.css
│   └── favicon.ico
├── data/                         # 일별 JSON (Git 관리)
│   └── 2026-03-01.json
├── dist/                         # 빌드 산출물 (Cloudflare Pages 루트)
│   └── index.html
├── tests/
│   ├── test_collector.py
│   ├── test_filter.py
│   ├── test_summarizer.py
│   └── test_verifier.py
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

---

## 5. 데이터 모델

### Briefing (일일 브리핑)
| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| date | string (YYYY-MM-DD) | ✅ | 브리핑 날짜 |
| title | string | ✅ | "2026년 3월 1일 (토) 모닝 브리핑" |
| articles | Article[] | ✅ | 뉴스 카드 목록 (10~15개) |
| generated_at | string (ISO 8601) | ✅ | 생성 시각 |

### Article (뉴스 카드)
| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| id | string (UUID) | ✅ | PK |
| headline | string | ✅ | 원본 기사 제목 |
| summary | string | ✅ | 쉬운 요약 (3~5문장, 해요체) |
| verification_tag | enum | ✅ | "verified" / "disputed" / "misleading" |
| verification_reason | string | ✅ | 태그 판별 근거 텍스트 |
| evidence_links | EvidenceLink[] | ✅ | 판별 근거 출처 링크 (1개 이상) |
| source_articles | SourceArticle[] | ✅ | 관련 언론사 원문 링크 (2개 이상) |
| google_news_url | string | ✅ | Google News 원본 URL |

### EvidenceLink (검증 근거)
| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| title | string | ✅ | 출처 제목 (예: "고용노동부 공식 발표") |
| url | string | ✅ | 출처 URL |

### SourceArticle (언론사 원문)
| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| publisher | string | ✅ | 언론사명 (예: "조선일보") |
| url | string | ✅ | 기사 URL |

### 엔티티 관계
```
[Briefing] 1──N [Article] 1──N [EvidenceLink]
                          1──N [SourceArticle]
```

### JSON 예시 (`data/2026-03-01.json`)
```json
{
  "date": "2026-03-01",
  "title": "2026년 3월 1일 (토) 모닝 브리핑",
  "generated_at": "2026-03-01T07:05:00+09:00",
  "articles": [
    {
      "id": "a1b2c3d4",
      "headline": "정부, 최저임금 1만2000원 확정",
      "summary": "내년 최저임금이 올해보다 5.1% 오른 1만2000원으로 결정됐어요. 2026년 1월부터 적용돼요.",
      "verification_tag": "verified",
      "verification_reason": "고용노동부 공식 발표와 최저임금위원회 의결 내용이 일치해요.",
      "evidence_links": [
        { "title": "고용노동부 공식 발표", "url": "https://..." },
        { "title": "최저임금위원회 의결", "url": "https://..." }
      ],
      "source_articles": [
        { "publisher": "조선일보", "url": "https://..." },
        { "publisher": "한겨레", "url": "https://..." },
        { "publisher": "연합뉴스", "url": "https://..." }
      ],
      "google_news_url": "https://news.google.com/..."
    }
  ]
}
```

---

## 6. API 명세

> 본 프로젝트는 정적 사이트이므로 자체 API 서버가 없다. 파이프라인에서 사용하는 외부 API만 명세한다.

### Google News RSS
- **Method**: GET
- **Endpoint**: `https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko`
- **설명**: 한국 주요뉴스 RSS 피드 수집

### Gemini Flash API
- **Method**: POST
- **설명**: 뉴스 요약 생성 + 검증 태그 부여
- **Rate Limit**: 무료 티어 (분당/일일 한도 내 사용)

### Google Custom Search API
- **Method**: GET
- **Endpoint**: `https://www.googleapis.com/customsearch/v1`
- **설명**: 기사 핵심 주장 교차검증용 웹 검색
- **Rate Limit**: 100회/일 무료 → 기사당 최대 3회 제한

---

## 7. 기능 요구사항

### FR-001: Google News RSS 수집
- **처리 로직**: feedparser로 RSS 파싱 → 아이템 목록 추출
- **엣지 케이스**: RSS 접근 실패 시 재시도 3회 후 파이프라인 실패 처리
- **수락 기준**:
  - [ ] RSS에서 최소 20개 이상 아이템 수집
  - [ ] 각 아이템에 제목, URL, 발행일이 포함됨

### FR-002: 카테고리 필터링 및 선별
- **처리 로직**: 연예·스포츠 키워드 기반 필터링 → Google News 노출 순서 기준 상위 10~15개 선별
- **엣지 케이스**: 필터링 후 10개 미만이면 필터 기준 완화 또는 전체 포함
- **수락 기준**:
  - [ ] 연예·스포츠 기사가 결과에 포함되지 않음
  - [ ] 최종 선별 기사 수가 10~15개

### FR-003: 쉬운 요약 생성
- **처리 로직**: Gemini Flash에 기사 원문 + 톤 가이드(해요체, 3~5문장, 전문용어 금지) 전달 → 요약 반환
- **엣지 케이스**: API 실패 시 해당 기사 스킵 (최소 10개 확보 필요)
- **수락 기준**:
  - [ ] 해요체로 작성되어 있다
  - [ ] 3~5문장 이내다
  - [ ] 전문용어가 포함되어 있지 않다
  - [ ] 의견/감정 표현 없이 사실만 전달한다

### FR-004: 교차검증 및 태그 부여
- **처리 로직**: 기사 핵심 주장 추출 → Google Custom Search로 공식 출처 검색 → Gemini에 교차검증 결과 전달 → 태그(✅/⚠️/❌) + 근거 반환
- **엣지 케이스**: 검색 결과 부족 시 ⚠️ 보수적 부여
- **수락 기준**:
  - [ ] 기사 1건당 태그 1개 부여
  - [ ] 태그 없는 기사 0건
  - [ ] 판별 근거 텍스트 + 출처 링크 1개 이상 첨부

### FR-005: 관련 언론사 원문 링크 수집
- **처리 로직**: Google News 클러스터링 활용 + 추가 검색으로 같은 사건 보도 언론사 원문 수집
- **엣지 케이스**: 단독 보도로 타 언론사 기사 없을 경우 원본 1개만 표시
- **수락 기준**:
  - [ ] 같은 사건 보도 언론사 원문 2개 이상 나열
  - [ ] 모든 링크가 실제 접근 가능

### FR-006: 정적 HTML 생성 및 배포
- **처리 로직**: JSON 데이터 → Jinja2 템플릿 렌더링 → dist/index.html 생성 → Cloudflare Pages 자동 배포
- **엣지 케이스**: 렌더링 실패 시 이전 날 HTML 유지 (배포 스킵)
- **수락 기준**:
  - [ ] 브리핑 제목이 "YYYY년 M월 D일 (요일) 모닝 브리핑" 형식
  - [ ] 뉴스 카드 10~15개 표시
  - [ ] 하단에 AI 한계 고지 + 후원 버튼 포함

---

## 8. 환경변수

```env
# Gemini API
GEMINI_API_KEY=

# Google Custom Search
GOOGLE_CSE_API_KEY=
GOOGLE_CSE_CX=

# Cloudflare Pages (GitHub Actions에서 관리)
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
```

---

## 9. 구현 순서

1. 프로젝트 초기화 — 디렉토리 구조, requirements.txt, .env.example, CLAUDE.md
2. 데이터 모델 정의 — `pipeline/models.py` (dataclass)
3. RSS 수집 모듈 — `pipeline/collector.py` + 테스트
4. 필터링/선별 모듈 — `pipeline/filter.py` + 테스트
5. AI 요약 모듈 — `pipeline/summarizer.py` + 테스트
6. 교차검증 모듈 — `pipeline/verifier.py` + 테스트
7. HTML 렌더링 — `pipeline/renderer.py` + Jinja2 템플릿 + 테스트
8. 파이프라인 통합 — `pipeline/main.py` (전체 흐름 연결)
9. GitHub Actions 워크플로우 — `.github/workflows/daily-briefing.yml`
10. Cloudflare Pages 배포 설정
11. 프론트엔드 스타일링 — `static/style.css` (모바일 우선 반응형)

---

## 10. Claude Code 지시사항

- Python 3.12 기준, type hint 필수 (any/Unknown 금지)
- dataclass 사용 (Pydantic 미사용 — 의존성 최소화)
- 모듈별 단일 책임 원칙 — collector, filter, summarizer, verifier, renderer 분리
- 테스트: pytest 사용, 외부 API 호출은 mock 처리
- 에러 핸들링: 개별 기사 실패가 전체 파이프라인을 중단시키지 않도록 처리
- 환경변수: `os.environ`으로 직접 접근 (dotenv는 로컬 개발 시에만)
- 커밋 메시지: Conventional Commits (`feat:`, `fix:`, `docs:` 등)
- Jinja2 템플릿: 시맨틱 HTML, 접근성 고려 (alt 텍스트, aria 등)
