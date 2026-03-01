# Plan: FR-001 Google News RSS 수집

> **범위**: 구현 순서 1~3 (프로젝트 초기화 + 데이터 모델 + RSS 수집 모듈)
> **관련 TRD**: FR-001, 섹션 4~5

---

## 1. 구현 범위

| 단계 | 내용 |
|------|------|
| Step 1 | 프로젝트 초기화 (디렉토리, requirements.txt, .env.example, CLAUDE.md) |
| Step 2 | 데이터 모델 정의 (`pipeline/models.py`) |
| Step 3 | RSS 수집 모듈 (`pipeline/collector.py`) + 테스트 |

---

## 2. 리서치 핵심 요약

### Google News RSS 피드 구조
- **형식**: RSS 2.0, UTF-8
- **아이템 필드 6개**: title, link, guid, pubDate, description, source
- **title 형식**: `"기사 제목 - 언론사명"` (대시로 구분되어 있으나, 언론사명은 title에서 추출하지 않음. ` - 언론사명` 접미사를 제거하여 순수 제목만 headline에 저장. 언론사 정보는 `source` 필드에서 가져옴)
- **link**: 원본 URL이 아닌 **Google 인코딩 URL** (`https://news.google.com/rss/articles/CBMi...`) 
- **description**: 클러스터된 관련 기사를 HTML `<ol>` 리스트로 포함 (3~5개)
- **source**: `<source url="도메인">언론사명</source>` 형태
- **피드당 최대 100개** 아이템, 페이지네이션 없음

### Google News URL 디코딩 문제
- Google News RSS의 link는 원본 기사 URL이 아님
- Legacy 포맷: Base64 디코딩으로 오프라인 추출 가능
- 신규 포맷 (2024.7~, `AU_yqL` 접두사): Google 서버에 API 호출 필요
- `googlenewsdecoder` 패키지가 두 포맷 모두 처리

### feedparser
- 최신 버전 6.0.12, Python 3.12 완전 호환
- 예외를 raise하지 않고 `bozo` 플래그로 에러 표시
- 네트워크 에러는 v6.x에서 직접 `try/except` 필요
- `entry.source.title` / `entry.source.href`로 언론사 정보 접근

---

## 3. 주요 결정 사항

### 결정 1: Google News URL 디코딩 방식

| 선택지 | 장점 | 단점 |
|--------|------|------|
| **A. `googlenewsdecoder` 패키지 사용** | 구현 간단, 두 포맷 모두 지원 | 역공학 기반, API 변경 시 깨질 수 있음 |
| B. 자체 Base64 디코딩 구현 | 외부 의존성 없음 | 신규 포맷 미지원, 유지보수 부담 |
| C. URL 디코딩 생략 (google_news_url만 저장) | 가장 단순 | 원본 URL 없이는 교차검증/원문 링크에 제약 |

**→ 선택: A** — 원본 URL이 후속 기능(FR-004 교차검증, FR-005 원문 링크)에 필수. 패키지 깨질 경우 교체 가능하도록 추상화.

### 결정 2: 클러스터 관련 기사 파싱 시점

| 선택지 | 설명 |
|--------|------|
| **A. collector에서 파싱** | 수집 단계에서 description HTML 파싱하여 관련 기사 목록 추출 |
| B. 별도 모듈에서 파싱 | collector는 raw data만, FR-005 구현 시 파싱 |

**→ 선택: A** — description의 관련 기사 링크가 FR-005(관련 언론사 원문)의 핵심 데이터. collector에서 함께 추출하면 Google News API 호출 최소화.

### 결정 3: 재시도 전략

- RSS 접근 실패 시 **3회 재시도** (TRD 요구사항)
- 재시도 간격: 지수 백오프 (2초, 4초, 8초)
- URL 디코딩 실패는 해당 기사만 스킵 (전체 파이프라인 중단 방지)

---

## 4. 파일 변경 목록

### 새로 생성
```
factlens/
├── pipeline/
│   ├── __init__.py
│   ├── models.py              # 데이터 모델 (dataclass)
│   └── collector.py           # RSS 수집 모듈
├── tests/
│   └── test_collector.py      # 수집 모듈 테스트
├── requirements.txt
├── .env.example
├── CLAUDE.md                  # 프로젝트별 컨벤션
└── .gitignore
```

---

## 5. 데이터 모델 설계 (`pipeline/models.py`)

TRD 섹션 5의 모델을 dataclass로 구현. collector가 사용하는 모델만 우선 정의하고, 나머지는 해당 기능 구현 시 추가.

```python
from dataclasses import dataclass, field

@dataclass
class SourceArticle:
    """언론사 원문 링크"""
    publisher: str          # "조선일보"
    url: str                # 원본 기사 URL

@dataclass
class EvidenceLink:
    """검증 근거 출처"""
    title: str
    url: str

@dataclass
class Article:
    """뉴스 카드 (수집 단계에서는 일부 필드만 채움)"""
    id: str                                    # UUID
    headline: str                              # 원본 기사 제목
    summary: str = ""                          # 쉬운 요약 (summarizer에서 채움)
    verification_tag: str = ""                 # verified/disputed/misleading (verifier에서 채움)
    verification_reason: str = ""              # 판별 근거 (verifier에서 채움)
    evidence_links: list[EvidenceLink] = field(default_factory=list)
    source_articles: list[SourceArticle] = field(default_factory=list)
    google_news_url: str = ""                  # Google News 원본 URL
    original_url: str = ""                     # 디코딩된 원본 기사 URL
    published_at: str = ""                     # 발행일 (ISO 8601)
    publisher: str = ""                        # 대표 언론사명 //topic을 반드시 화면에 제시해야할까? 사용자가 이걸 보고 큰 효용이 있을까? 나는 제거하는 게 좋을 것 같다고 생각하는데데.

@dataclass
class Briefing:
    """일일 브리핑"""
    date: str               # YYYY-MM-DD
    title: str              # "2026년 3월 1일 (토) 모닝 브리핑"
    articles: list[Article] = field(default_factory=list)
    generated_at: str = ""  # ISO 8601
```

**TRD 대비 추가 필드:**
- `Article.original_url` — 디코딩된 원본 기사 URL (google_news_url과 별도 저장)
- `Article.published_at` — RSS pubDate (필터링/정렬에 필요)
- `Article.publisher` — 대표 언론사명 (source 태그에서 추출)

---

## 6. RSS 수집 모듈 설계 (`pipeline/collector.py`)

### 수집 대상 피드 (토픽별 3개)

| 토픽 | 피드 URL |
|------|----------|
| 정치+사회 | `https://news.google.com/rss/headlines/section/topic/NATION?hl=ko&gl=KR&ceid=KR:ko` |
| 경제 | `https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko` |
| 국제 | `https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko` |

> 메인 피드 대신 토픽별 피드를 사용하여 연예·스포츠를 수집 단계에서 원천 차단.
> 키워드 기반 필터링 불필요 → false positive 리스크 제거.

### 공개 인터페이스

```python
def collect_news() -> list[list[Article]]:
    """
    Google News 토픽별 RSS 3개(NATION, BUSINESS, WORLD)에서 뉴스를 수집하여
    피드별 Article 리스트로 반환 (3개 리스트, 각 리스트는 피드 순서=중요도 유지).
    - 피드별 파싱 → Google News URL 디코딩 → 클러스터 관련 기사 추출
    - 개별 피드/기사 실패는 스킵, 전체 실패 시에만 예외 발생
    """
```

### 내부 함수

```python
def _fetch_rss(url: str, max_retries: int = 3) -> list[feedparser.FeedParserDict]:
    """RSS 피드를 가져와 엔트리 리스트 반환. 실패 시 재시도."""

def _decode_google_news_url(encoded_url: str) -> str:
    """Google News 인코딩 URL → 원본 기사 URL 디코딩."""

def _parse_cluster_articles(description_html: str) -> list[SourceArticle]:
    """description HTML에서 클러스터 관련 기사 링크 추출."""

def _parse_entry(entry: feedparser.FeedParserDict) -> Article:
    """feedparser 엔트리 → Article 변환."""
```

### 처리 흐름

```
1. 3개 토픽 피드 순회:
   a. _fetch_rss(url) — 피드 가져오기 (재시도 포함)
   b. 각 entry에 대해:
      - title에서 " - 언론사명" 접미사 제거 → 순수 headline 추출
      - _decode_google_news_url()로 원본 URL 추출
      - _parse_cluster_articles()로 관련 기사 추출
      - _parse_entry(entry)로 Article 객체 생성
   c. 개별 피드 실패 시 해당 토픽 스킵 (로그 경고)
2. 피드별 Article 리스트 3개를 그대로 반환 (합산하지 않음 — 피드 순서 보존)
   → filter_and_select()가 라운드 로빈으로 인터리브
```

---

## 7. 테스트 전략

### mock 대상
- `feedparser.parse()` — 실제 RSS 호출 대신 fixture 데이터
- `googlenewsdecoder` — URL 디코딩 결과 mock

### 테스트 케이스
```
test_fetch_rss_success          — 정상 파싱, 엔트리 목록 반환
test_fetch_rss_retry_on_failure — 네트워크 에러 시 3회 재시도 후 실패
test_fetch_rss_bozo_handling    — bozo 피드 처리 (파싱 가능하면 계속)
test_parse_entry_normal         — 정상 엔트리 → Article 변환
test_parse_entry_missing_source — source 필드 없는 엔트리 처리
test_decode_url_success         — URL 디코딩 성공
test_decode_url_failure_skip    — 디코딩 실패 시 google_news_url만 유지
test_parse_cluster_articles     — description HTML에서 관련 기사 추출
test_parse_cluster_empty        — 클러스터 없는 description 처리
test_collect_news_three_topics  — 3개 토픽 피드 합산 수집 확인
test_collect_news_returns_feeds — 피드별 분리된 리스트 반환 확인
test_collect_news_partial_fail  — 1개 피드 실패 시 나머지 2개로 계속 수집
test_collect_news_integration   — 전체 흐름 통합 테스트 (모든 외부 호출 mock)
```

---

## 8. requirements.txt

```
feedparser>=6.0.12
googlenewsdecoder>=0.1.2
```

> pytest, jinja2, google-generativeai, requests 등은 해당 기능 구현 시 추가.

---

## 9. 트레이드오프 / 리스크

| 항목 | 리스크 | 대응 |
|------|--------|------|
| `googlenewsdecoder` 의존성 | 역공학 기반, Google 변경 시 깨짐 | 디코딩 로직을 래퍼 함수로 추상화. 패키지 교체 시 한 곳만 수정 |
| description HTML 파싱 | Google이 마크업 변경 가능 | 파싱 실패 시 관련 기사 없이 진행 (graceful degradation) |
| RSS 피드 최대 100개 제한 | 토픽당 ~30개, 3개 합산 ~90개 | 10개 선별에 충분 |
| 토픽 피드 URL 변경 | Google이 토픽 피드 구조 변경 가능 | 메인 피드(`/rss?hl=ko&...`)를 폴백으로 사용 |
| feedparser 네트워크 에러 | v6.x에서 내부 처리 안 됨 | try/except로 직접 처리 |
