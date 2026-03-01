# Plan: FR-004 교차검증 및 태그 부여

> **범위**: 구현 순서 6 (교차검증 모듈)
> **관련 TRD**: FR-004, PRD 섹션 9 (검증 태그 시스템)
> **입력**: `summarize_articles()`가 반환한 `list[Article]` (summary 채워진 상태)
> **출력**: 각 Article의 `verification_tag`, `verification_reason`, `evidence_links` 채워진 `list[Article]`

---

## 1. 검증 흐름 개요

```
각 기사에 대해:
1. headline으로 Google Custom Search 검색 → 같은 사건의 다른 보도 + 공식 출처 확보
2. 기사 본문 + 검색 결과를 Gemini에 전달 → 보도 교차확인 → 검증 태그 + 근거 반환
```

> 검증 관점: "주장이 참인가?"가 아니라 **"이 기사가 충분한 근거를 갖고 있는가, 편파적이지 않은가"**를 판별.

---

## 2. 주요 결정 사항

### 결정 1: 기사 본문 재사용

summarizer에서 이미 `newspaper3k`로 기사 본문을 가져옴. verifier가 같은 본문을 다시 가져올 필요 없음.

| 선택지 | 설명 |
|--------|------|
| **A. Article에 `_article_text` 필드 추가** | summarizer가 채우고 verifier가 사용. JSON 직렬화에서 제외 (내부 처리용) |
| B. verifier에서 다시 스크래핑 | 중복 HTTP 요청, 차단 리스크 증가 |

**→ 선택: A** — 파이프라인 내에서 한 번만 스크래핑. `_article_text`는 언더스코어 접두사로 내부용 표시, JSON 저장 시 제외.

### 결정 2: Google Custom Search 쿼리 전략

- 기사당 **최대 2회** 검색 (100회/일 ÷ 10기사 = 기사당 10회 가능하지만 보수적으로)
- 쿼리 1: `{headline}` (기사 제목 그대로)
- 쿼리 2: `{headline} 공식 발표 OR 정부 OR 통계` (공식 출처 타겟팅)
- 각 검색에서 상위 5개 결과의 제목 + URL + snippet 수집

### 결정 3: 검증 태그 매핑

| 태그 (화면) | Article.verification_tag 값 | 부여 조건 |
|-------------|----------------------------|-----------|
| ✅ 사실 확인됨 | `"verified"` | 다수 언론 보도 일치, 공식 출처로 뒷받침됨 |
| ⚠️ 사실 확인 중 | `"unconfirmed"` | 충분한 근거 미확보, 출처 부족, 검증 실패 |
| ❌ 왜곡/오류 | `"misleading"` | 다른 보도·공식 출처와 내용이 다름, 맥락 누락 |

> 보수적 원칙: 확신 없으면 `"unconfirmed"` 부여. 기술적 실패도 동일.

---

## 3. 프롬프트 설계

### 검증 프롬프트

```
당신은 뉴스 보도의 신뢰성을 교차확인하는 팩트체커입니다.
아래 기사를 다른 언론 보도 및 공식 출처와 비교하여, 이 기사가 충분한 근거를 갖고 있는지, 편파적이지 않은지 판단하세요.

## 기사 제목
{headline}

## 기사 본문
{article_text}

## 같은 사건의 다른 보도 및 공식 출처 (검색 결과)
{search_results}

## 작업
1. 이 기사의 내용이 다른 보도 및 공식 출처와 일치하는지 비교하세요.
2. 기사에 근거가 충분한지, 사실 오류가 없는지, 맥락이 누락되지 않았는지 확인하세요.
3. 아래 JSON 형식으로만 응답하세요.

## 출력 형식 (JSON)
{
  "tag": "verified" | "unconfirmed" | "misleading",
  "reason": "판별 근거를 해요체 1~2문장으로 작성",
  "evidence": [
    {"title": "출처 제목", "url": "출처 URL"}
  ]
}

## 판단 기준
- verified: 다수 언론이 동일한 내용을 보도하고, 공식 출처(정부 발표, 공식 통계 등)로 뒷받침됨
- unconfirmed: 다른 보도나 공식 출처로 충분히 확인되지 않음 (출처 부족, 단독 보도, 아직 확정 안 됨)
- misleading: 다른 보도나 공식 출처와 내용이 다름, 사실 오류 포함, 맥락 누락으로 오해를 유도함
- 확신이 없으면 반드시 unconfirmed으로 판단하세요
- evidence에는 검색 결과에서 실제 비교에 사용한 출처만 포함하세요
```

---

## 4. 파일 변경 목록

### 새로 생성
```
pipeline/verifier.py        # 교차검증 + 태그 부여 모듈
tests/test_verifier.py      # 테스트
```

### 수정
```
pipeline/models.py          # Article에 _article_text 필드 추가
pipeline/summarizer.py      # _article_text 필드 채우도록 수정
requirements.txt            # requests 추가 (Google Custom Search용)
.env.example                # GOOGLE_CSE_API_KEY, GOOGLE_CSE_CX 추가
```

---

## 5. 모듈 설계 (`pipeline/verifier.py`)

### 공개 인터페이스

```python
def verify_articles(articles: list[Article]) -> list[Article]:
    """
    각 Article을 교차확인하여 verification_tag, verification_reason,
    evidence_links를 채움. 검증 실패 시 unconfirmed 태그를 보수적으로 부여.
    """
```

### 내부 함수

```python
def _search_google(query: str) -> list[dict]:
    """Google Custom Search API 호출. 상위 5개 결과 반환."""

def _build_search_context(results: list[dict]) -> str:
    """검색 결과를 프롬프트용 텍스트로 포맷팅."""

def _verify_with_gemini(headline: str, article_text: str, search_context: str) -> dict:
    """Gemini에 검증 요청. JSON 파싱하여 dict 반환."""

def _parse_verification_response(response_text: str) -> dict:
    """Gemini 응답 JSON 파싱. 실패 시 unconfirmed 기본값 반환."""
```

### 처리 흐름

```
1. 각 Article에 대해:
   a. headline으로 Google Custom Search 2회 호출
      - 쿼리 1: headline 그대로
      - 쿼리 2: headline + "공식 발표 OR 정부 OR 통계"
   b. 검색 결과를 _build_search_context()로 포맷
   c. _verify_with_gemini(headline, _article_text, search_context) 호출
   d. 응답 JSON 파싱 → Article 필드에 매핑:
      - tag → verification_tag
      - reason → verification_reason
      - evidence → evidence_links
   e. 파싱 실패 또는 API 실패 시:
      - verification_tag = "unconfirmed"
      - verification_reason = "이 브리핑 시점에 AI가 충분히 확인하지 못했어요."
      - evidence_links = [] (빈 리스트)
2. 모든 Article 반환 (태그 없는 기사 0건 보장)
```

---

## 6. Google Custom Search API

- **엔드포인트**: `https://www.googleapis.com/customsearch/v1`
- **파라미터**: `key`, `cx`, `q`, `num=5`, `lr=lang_ko`
- **무료 한도**: 100회/일
- **사용량**: 기사당 2회 × 10기사 = 20회/일 → 여유

---

## 7. 테스트 전략

### mock 대상
- `requests.get` (Google Custom Search) — fixture JSON 응답
- `genai.GenerativeModel.generate_content` — 고정 검증 결과

### 테스트 케이스
```
test_search_google_success          — 정상 검색 결과 반환
test_search_google_failure          — API 에러 시 빈 리스트 반환
test_verify_with_gemini_verified    — ✅ 사실 확인 응답 파싱
test_verify_with_gemini_unconfirmed — ⚠️ 사실 확인 중 응답 파싱
test_verify_with_gemini_misleading  — ❌ 왜곡 응답 파싱
test_parse_invalid_json             — Gemini 응답 JSON 파싱 실패 → unconfirmed 기본값
test_verify_articles_full           — 전체 흐름 통합
test_verify_articles_all_tagged     — 태그 없는 기사 0건 보장
test_verify_fallback_on_failure     — API 실패 시 unconfirmed 폴백
```

---

## 8. 트레이드오프 / 리스크

| 항목 | 리스크 | 대응 |
|------|--------|------|
| AI 검증 정확도 | Gemini가 틀린 판단을 할 수 있음 | 보수적 원칙 (확신 없으면 unconfirmed), "AI 보조 검증" 고지 |
| Google Custom Search 결과 품질 | 관련 없는 검색 결과 반환 가능 | 2개 쿼리 전략으로 커버리지 확보. Gemini가 관련성 판단 |
| JSON 파싱 실패 | Gemini가 비정형 응답 반환 | _parse_verification_response()에서 기본값(unconfirmed) 폴백 |
| 검색 한도 100회/일 | 기사 수 증가 시 부족 가능 | 현재 20회/일 사용. 부족 시 유료 전환 (₩5/1000쿼리) |
| 정치적 편향 시비 | 특정 태그 부여에 이의 제기 가능 | 검증 근거 + 출처 링크 투명 공개, 사용자 제보 체계 |
