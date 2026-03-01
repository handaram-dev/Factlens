# Plan: 검증 방식 개선 — Google Search Grounding 전환

> **배경**: 첫 파이프라인 실행 결과, (1) 6개 기사 중 6개가 "사실 확인 중" 처리됨 (CSE 검색 결과 부족), (2) Gemini가 이재명 대통령을 윤석열로 오인하여 정확한 기사를 오류로 분류. 근본 원인은 Google CSE의 제한된 검색 결과와 Gemini의 오래된 학습 데이터. 프롬프트 개선이 아닌 실시간 검색 기능이 필요.
> **해결**: Google CSE를 제거하고 Gemini Google Search Grounding으로 전환. 모델이 직접 실시간 Google 검색을 수행하여 최신 정보 기반 검증.
> **리서치**: `docs/research-검증방식개선.md` 참조

---

## 1. 변경 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `pipeline/verifier.py` | **대폭 수정** | CSE 코드 제거, Grounding 도구 추가, 메타데이터 파싱 |
| `tests/test_verifier.py` | **전면 재작성** | CSE 테스트 제거, Grounding mock 테스트 |
| `templates/index.html.j2` | 수정 | Google 검색 위젯 표시 영역 추가 (ToS) |
| `pipeline/models.py` | 수정 | Article에 `search_entry_point` 필드 추가 |
| `pipeline/renderer.py` | 수정 | `_article_to_dict`에 `search_entry_point` 포함 |
| `.github/workflows/daily-briefing.yml` | 수정 | CSE 환경변수 제거 |
| `requirements.txt` | 수정 | `requests` 제거 가능 여부 확인 |

---

## 2. `pipeline/verifier.py` 상세 변경

### 제거할 코드

| 함수/상수 | 이유 |
|-----------|------|
| `_search_google()` (L62-98) | CSE 호출 — Grounding이 대체 |
| `_build_search_context()` (L101-111) | 검색 결과 포맷팅 — 모델이 직접 검색하므로 불필요 |
| `SEARCH_NUM_RESULTS` (L42) | CSE 전용 상수 |
| `import requests` (L6) | CSE 호출용이었음 |

### 추가할 import

```python
from google.genai import types
```

### `_verify_with_gemini()` 변경

현재 시그니처:
```python
def _verify_with_gemini(client, headline, article_text, search_context) -> dict:
```

변경 후:
```python
def _verify_with_gemini(client, headline, article_text) -> dict:
```

- `search_context` 파라미터 제거 (모델이 직접 검색)
- `client.models.generate_content()` 호출에 `config` 파라미터 추가:
  ```python
  config=types.GenerateContentConfig(
      tools=[types.Tool(google_search=types.GoogleSearch())]
  )
  ```
- 응답에서 `grounding_metadata` 추출하여 evidence_links 구성:
  ```python
  metadata = response.candidates[0].grounding_metadata
  ```
- `search_entry_point` HTML도 반환 dict에 포함

### 반환 dict 구조 변경

```python
# 기존
{"tag": "verified", "reason": "...", "evidence": [{"title": ..., "url": ...}]}

# 변경
{"tag": "verified", "reason": "...", "evidence": [...], "search_entry_point": "<html>..."}
```

- `evidence`: 기존처럼 JSON 응답에서 파싱 + `grounding_metadata.grounding_chunks`에서 추출 (두 소스 병합)
- `search_entry_point`: `metadata.search_entry_point.rendered_content` (없으면 빈 문자열)

### `_parse_verification_response()` 유지

- JSON 파싱 로직은 동일하게 유지 (프롬프트에서 JSON 출력 요청하는 방식 유지)
- `response_json_schema` 파라미터는 사용하지 않음 (Grounding 메타데이터와 비호환)

### `_extract_grounding_evidence()` 신규 함수

```python
def _extract_grounding_evidence(response) -> tuple[list[dict[str, str]], str]:
    """grounding_metadata에서 evidence 링크와 search_entry_point 추출."""
```

- `response.candidates[0].grounding_metadata`가 없으면 `([], "")` 반환
- `grounding_chunks`에서 `{"title": web.title, "url": web.uri}` 리스트 추출
- `search_entry_point.rendered_content` 추출

### `verify_articles()` 변경

현재 (L185-230):
```python
for article in articles:
    results_1 = _search_google(article.headline)           # 제거
    results_2 = _search_google(...)                        # 제거
    # ... 중복 제거, context 구성 ...                        # 제거
    search_context = _build_search_context(combined)       # 제거
    verification = _verify_with_gemini(client, ..., search_context)  # 변경
```

변경 후:
```python
for article in articles:
    verification = _verify_with_gemini(client, article.headline, article_text)
    article.verification_tag = verification["tag"]
    article.verification_reason = verification["reason"]
    article.evidence_links = [...]
    article.search_entry_point = verification.get("search_entry_point", "")
```

### 프롬프트 변경

기존 프롬프트에서 `{search_results}` 섹션 제거. 대신 검색 지시 추가:

```
당신은 뉴스 보도의 신뢰성을 교차확인하는 팩트체커입니다.

중요: 오늘 날짜는 {today}입니다. 너의 사전 학습 데이터는 오래되었을 수 있습니다.
반드시 Google 검색을 실행하여 최신 정보를 확인하고, 검색 결과만을 근거로 판단하세요.
너의 사전 지식에 의존하지 마세요.
## 기사 제목
{headline}

## 기사 본문
{article_text}

## 작업
1. Google 검색으로 이 기사와 관련된 공식 출처(정부 발표, 기관 보도자료, 공식 통계 등)를 찾으세요.
2. 기사 내용이 공식 출처와 일치하는지, 사실 오류가 없는지, 맥락이 누락되지 않았는지 확인하세요.
3. 아래 JSON 형식으로만 응답하세요.

## 출력 형식 (JSON만 출력)
{{"tag": "verified 또는 unconfirmed 또는 misleading", "reason": "판별 근거를 해요체 1~2문장으로 작성", "evidence": [{{"title": "출처 제목", "url": "출처 URL"}}]}}

## 판단 기준
- verified: 공식 출처(정부, 기관, 공식 통계)로 핵심 내용이 뒷받침됨
- unconfirmed: 공식 출처를 찾을 수 없거나 충분히 확인되지 않음
- misleading: 공식 출처와 내용이 다르거나, 사실 오류 포함, 맥락 누락으로 오해 유도
- 확신이 없으면 반드시 unconfirmed으로 판단하세요
- evidence에는 검색에서 실제 비교에 사용한 출처만 포함하세요
```

핵심 변경:
- `{search_results}` 섹션 제거 → "Google 검색으로 찾으세요" 지시
- `{today}` 추가 — 모델에 현재 날짜 명시
- "사전 지식에 의존하지 마세요" 명시적 경고

---

## 3. `pipeline/models.py` 변경

Article에 필드 추가:
```python
search_entry_point: str = ""  # Google 검색 위젯 HTML (ToS 표시 의무)
```

---

## 4. `pipeline/renderer.py` 변경

`_article_to_dict()`에 `search_entry_point` 필드 추가:
```python
"search_entry_point": article.search_entry_point,
```

---

## 5. `templates/index.html.j2` 변경

각 뉴스 카드의 `card-verification` 섹션 하단에 검색 위젯 표시 영역 추가:

```html
{% if article.search_entry_point %}
<div class="search-widget">
    {{ article.search_entry_point }}
</div>
{% endif %}
```

> 주의: `autoescape=True`이므로 HTML이 이스케이프됨. `| safe` 필터 적용 필요:
> `{{ article.search_entry_point | safe }}`

---

## 6. `.github/workflows/daily-briefing.yml` 변경

CSE 환경변수 제거:
```yaml
# 제거
GOOGLE_CSE_API_KEY: ${{ secrets.GOOGLE_CSE_API_KEY }}
GOOGLE_CSE_CX: ${{ secrets.GOOGLE_CSE_CX }}
```

변경 후:
```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

---

## 7. `requirements.txt` 변경

`requests` 패키지는 verifier의 CSE 호출 전용이었음. 다른 곳에서 사용하지 않으면 제거.

```
# 제거
requests>=2.31.0
```

---

## 8. `tests/test_verifier.py` 전면 재작성

### 제거할 테스트 클래스
- `TestSearchGoogle` (3개) — CSE 함수 제거
- `TestBuildSearchContext` (2개) — 포맷팅 함수 제거

### 변경할 테스트 클래스

**`TestVerifyWithGemini`** — 시그니처 변경 반영:
- `search_context` 파라미터 제거
- mock response에 `candidates[0].grounding_metadata` 추가
- grounding_metadata에서 evidence 추출 테스트

**`TestVerifyArticles`** — CSE mock 제거:
- `@patch("pipeline.verifier._search_google")` 제거
- `_verify_with_gemini` mock에 `search_entry_point` 포함

### 추가할 테스트

| 테스트 | 내용 |
|--------|------|
| `test_extract_grounding_evidence_success` | grounding_chunks에서 title/url 정상 추출 |
| `test_extract_grounding_evidence_no_metadata` | metadata 없을 때 빈 리스트 반환 |
| `test_extract_grounding_evidence_search_entry_point` | search_entry_point HTML 추출 |
| `test_verify_with_gemini_grounding_config` | generate_content 호출 시 google_search 도구 포함 확인 |
| `test_verify_articles_search_entry_point` | Article.search_entry_point에 값 저장 확인 |

---

## 9. 구현 순서

1. `pipeline/models.py` — `search_entry_point` 필드 추가
2. `pipeline/verifier.py` — CSE 제거, Grounding 전환, 프롬프트 변경
3. `tests/test_verifier.py` — 테스트 전면 재작성
4. `pipeline/renderer.py` — `_article_to_dict`에 필드 추가
5. `templates/index.html.j2` — 검색 위젯 영역 추가
6. `.github/workflows/daily-briefing.yml` — CSE 환경변수 제거
7. `requirements.txt` — `requests` 제거
8. 전체 테스트 실행
9. 커밋 + 푸시 + workflow_dispatch 재실행

---

## 10. 검증 방법

1. `python -m pytest tests/ -v` — 전체 테스트 통과 확인
2. GitHub Actions workflow_dispatch 수동 실행
3. `factlens.pages.dev` 접속하여 확인:
   - 기사별 검증 태그가 다양한지 (전부 unconfirmed 아닌지)
   - evidence_links에 실제 URL이 있는지
   - 검색 위젯이 표시되는지
   - "이재명 대통령" 관련 기사가 정상 처리되는지
