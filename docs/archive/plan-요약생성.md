# Plan: FR-003 쉬운 요약 생성

> **범위**: 구현 순서 5 (AI 요약 모듈)
> **관련 TRD**: FR-003
> **입력**: `filter_and_select()`가 반환한 `list[Article]` (headline, original_url 등 채워진 상태)
> **출력**: 각 Article의 `summary` 필드가 채워진 `list[Article]`

---

## 1. 선결 과제: 기사 본문 확보

collector는 headline, URL, publisher만 제공. Gemini에 요약을 시키려면 **기사 본문 텍스트**가 필요.

### 결정 1: 기사 본문 확보 방법

| 선택지 | 장점 | 단점 |
|--------|------|------|
| **A. 원본 URL 스크래핑 (newspaper3k/BeautifulSoup)** | 실제 기사 내용으로 정확한 요약 가능 | 사이트마다 구조 다름, 일부 사이트 차단 가능, 의존성 추가 |
| B. headline만으로 Gemini에 요약 생성 요청 | 스크래핑 불필요, 단순 | 할루시네이션 위험 높음, 최신 정보 미반영, 사실상 "요약"이 아님 |
| C. Google News description(클러스터 HTML)의 텍스트 활용 | 추가 HTTP 요청 없음 | 제목과 언론사명뿐, 본문 없음 |

**→ 선택: A** — "쉬운 요약"이 핵심 기능인데 본문 없이는 정확한 요약 불가능. `newspaper3k`가 다양한 뉴스 사이트의 본문 추출을 잘 처리. 스크래핑 실패 시 해당 기사 스킵.

> 저작권 참고: 본문을 가져오되 **표시하지 않음**. AI 재작성 요약 + 원문 링크만 제공 (PRD 8.4 저작권 대응).

### 결정 2: Gemini 모델 및 API

| 선택지 | 장점 | 단점 |
|--------|------|------|
| **A. Gemini Flash (gemini-2.0-flash)** | 무료 티어 넉넉, 속도 빠름 | 품질이 Pro 대비 낮을 수 있음 |
| B. Gemini Pro | 품질 높음 | 무료 티어 한도 빠듯 |

**→ 선택: A** — TRD/PRD에 Gemini Flash로 명시. 품질 부족 시 모델 교체는 환경변수 하나로 가능하게 설계.

### 결정 3: 프롬프트 전략

| 선택지 | 설명 |
|--------|------|
| **A. 단일 프롬프트 (요약만)** | 기사 본문 + 톤 가이드 → 요약 반환 |
| B. FR-003 + FR-004 통합 프롬프트 | 요약 + 검증 태그를 한 번에 요청 |

**→ 선택: A** — 모듈 분리 원칙 유지 (summarizer / verifier 분리). 통합하면 디버깅 어려움. API 호출이 1회 더 들지만, 무료 티어 내에서 감당 가능.

---

## 2. 프롬프트 설계

```
당신은 뉴스를 쉽게 풀어서 설명해주는 뉴스 브리핑 작가입니다.

아래 뉴스 기사를 읽고, 다음 규칙에 따라 쉬운 요약을 작성하세요.

## 규칙
- 해요체로 작성 (~에요, ~거든요, ~했어요)
- 3~5문장으로 핵심만 요약
- 전문용어 사용 금지 — 어려운 개념은 일상적인 비유로 풀어쓰기
- 배경 맥락이 필요하면 "이게 왜 중요하냐면" 식으로 먼저 깔아주기
- 의견이나 감정 표현 없이 사실만 전달
- 특정 언론사나 정치적 입장을 지지하거나 비판하지 않기

## 기사 제목
{headline}

## 기사 본문
{article_text}

## 출력
요약문만 작성하세요. 다른 설명이나 서문 없이 요약문만 출력하세요.
```

---

## 3. 파일 변경 목록

### 새로 생성
```
pipeline/summarizer.py      # AI 요약 생성 모듈
tests/test_summarizer.py    # 테스트
```

### 수정
```
requirements.txt            # google-generativeai, newspaper3k 추가
.env.example                # GEMINI_API_KEY 추가
```

---

## 4. 모듈 설계 (`pipeline/summarizer.py`)

### 공개 인터페이스

```python
def summarize_articles(articles: list[Article]) -> list[Article]:
    """
    각 Article의 original_url에서 본문을 가져와 Gemini로 요약 생성.
    summary 필드를 채운 Article 리스트 반환.
    요약 실패한 기사는 리스트에서 제외.
    """
```

### 내부 함수

```python
def _fetch_article_text(url: str) -> str:
    """URL에서 기사 본문 텍스트 추출. newspaper3k 사용."""

def _generate_summary(headline: str, article_text: str) -> str:
    """Gemini Flash API로 쉬운 요약 생성."""

def _init_gemini() -> genai.GenerativeModel:
    """Gemini 모델 초기화. GEMINI_API_KEY 환경변수 사용."""
```

### 처리 흐름

```
1. _init_gemini()로 모델 초기화
2. 각 Article에 대해:
   a. _fetch_article_text(original_url) — 기사 본문 추출
      - 실패 시 google_news_url로 재시도
      - 재시도도 실패 시 해당 기사 스킵 (로그 경고)
   b. _generate_summary(headline, article_text) — 요약 생성
      - API 실패 시 해당 기사 스킵
      - Rate limit 시 잠시 대기 후 재시도
   c. Article.summary에 결과 저장
3. summary가 채워진 Article 리스트 반환
```

---

## 5. Rate Limit 대응

Gemini Flash 무료 티어 제한 (2026.03 기준 예상):
- 분당 15~60 요청
- 일일 1,500 요청

10개 기사 요약 → 10회 API 호출 → 무료 티어 내에서 여유.

| 상황 | 대응 |
|------|------|
| 429 Rate Limit | 30초 대기 후 재시도 (최대 3회) |
| API 일시 장애 | 해당 기사 스킵 |
| 일일 한도 초과 | 파이프라인 실패 처리 (사실상 발생 안 함) |

---

## 6. 테스트 전략

### mock 대상
- `newspaper3k` Article 다운로드 — fixture HTML 사용
- `genai.GenerativeModel.generate_content` — 고정 응답 반환

### 테스트 케이스
```
test_fetch_article_text_success     — 정상 URL에서 본문 추출
test_fetch_article_text_failure     — 스크래핑 실패 시 빈 문자열 반환
test_generate_summary_success       — Gemini 정상 응답 → 요약 반환
test_generate_summary_api_failure   — API 에러 시 빈 문자열 반환
test_generate_summary_rate_limit    — 429 시 재시도 후 성공
test_summarize_articles_full        — 전체 흐름 (본문 추출 + 요약 생성)
test_summarize_articles_skip_failed — 실패 기사 제외 확인
test_summarize_articles_empty_input — 빈 리스트 → 빈 리스트
```

---

## 7. requirements.txt 추가분

```
google-generativeai>=0.8.0
newspaper3k>=0.2.8
```

---

## 8. 트레이드오프 / 리스크

| 항목 | 리스크 | 대응 |
|------|--------|------|
| newspaper3k 스크래핑 실패 | 일부 사이트가 봇 차단 또는 JS 렌더링 필요 | 실패 시 해당 기사 스킵. 10개 중 7~8개만 성공해도 서비스 가능 |
| Gemini 요약 품질 | 해요체 미준수, 전문용어 사용 가능 | 프롬프트로 제어. 심각하면 모델 교체 (환경변수 하나) |
| 요약이 원문과 너무 유사 | 저작권 리스크 | 프롬프트에 "재작성" 명시. 유사도 체크는 추후 |
| Gemini 무료 티어 변경 | Google 정책 변경 시 비용 발생 | 10개 기사 수준이면 유료 전환해도 월 ₩1만 이하 |
