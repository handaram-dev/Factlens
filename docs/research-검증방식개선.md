# Research: Gemini Google Search Grounding을 활용한 검증 방식 개선

> 작성일: 2026-03-01
> 목적: 현재 Google CSE 기반 검증의 근본적 한계를 파악하고, Gemini Google Search Grounding으로 대체 가능한지 조사

---

## 1. 현재 문제

### 문제 1: Google CSE 검색 결과 부족
- 16개 도메인 한정 검색 → 결과가 없거나 부족
- 결과 없으면 Gemini가 판단 근거 없어 전부 "사실 확인 중" 처리
- 6개 기사 중 6개가 unconfirmed — 서비스 의미 없음

### 문제 2: Gemini 내부 지식 오류
- 학습 데이터에 최신 정보(이재명 대통령 등) 없음
- 자기 지식 기준으로 "윤석열이 대통령"이라고 판단 → 정확한 기사를 오류로 분류
- 프롬프트 개선으로는 해결 불가 — **실시간 검색이 필수**

---

## 2. Gemini Google Search Grounding이란

Gemini API 호출 시 `google_search` 도구를 활성화하면, 모델이 **직접 Google 검색을 수행**하고 그 결과를 바탕으로 답변한다. 별도의 검색 API(CSE) 호출 불필요.

### 동작 방식
1. 프롬프트를 받은 Gemini가 검색이 필요하다고 판단하면 자동으로 Google Search 실행
2. 검색 결과를 읽고, 그 내용을 근거로 응답 생성
3. 응답에 `grounding_metadata` 포함 — 어떤 검색어로 검색했는지, 어떤 출처를 참고했는지 메타데이터 제공

---

## 3. API 사용법 (google-genai SDK)

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='2026년 3월 현재 대한민국 대통령은 누구인가?',
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
)

print(response.text)  # 실시간 검색 기반 답변
```

- `types.Tool(google_search=types.GoogleSearch())` 한 줄 추가로 활성화
- 모델이 자동으로 검색 여부 결정 (수동 제어 불필요)
- gemini-2.5-flash 완전 지원

---

## 4. 응답 구조 — grounding_metadata

```python
metadata = response.candidates[0].grounding_metadata

# 사용 가능한 필드:
metadata.web_search_queries        # list[str] — 모델이 실행한 검색어 목록
metadata.grounding_chunks          # list[GroundingChunk] — 참고한 웹 출처
metadata.grounding_supports        # list[GroundingSupport] — 응답 텍스트↔출처 매핑
metadata.search_entry_point        # SearchEntryPoint — 검색 위젯 HTML (ToS상 표시 필수)
```

### 출처 추출
```python
for chunk in metadata.grounding_chunks:
    if chunk.web:
        print(f"제목: {chunk.web.title}")
        print(f"URL: {chunk.web.uri}")
```

### 텍스트↔출처 매핑 (인라인 인용)
```python
for support in metadata.grounding_supports:
    text = support.segment.text                     # 응답 텍스트 구간
    for i, idx in enumerate(support.grounding_chunk_indices):
        source = metadata.grounding_chunks[idx]
        confidence = support.confidence_scores[i]   # 신뢰도 점수
        print(f"'{text}' → {source.web.uri} (신뢰도: {confidence})")
```

---

## 5. 핵심 제약사항

### 제약 1: Structured Output + Grounding 호환 문제 ⚠️

**`response_json_schema`(구조화 출력)와 `google_search`를 동시에 사용하면 `grounding_chunks`, `grounding_supports`가 빈 값으로 반환됨.**

- `web_search_queries`는 정상 반환 (검색은 수행됨)
- 하지만 출처 메타데이터가 사라짐

**우회 방법:**
- (A) JSON 스키마 없이 프롬프트에서 JSON 출력 요청 → grounding_metadata 정상 반환
- (B) JSON 스키마에 source URL 필드를 포함시켜 모델이 직접 채우게 함 → grounding_metadata 없어도 출처 확보
- (C) 2회 호출: 1회차 grounding으로 출처 확보 → 2회차 structured output으로 판정 (비용 2배)

**→ (A) 방식 권장**: 현재 verifier도 프롬프트에서 JSON 출력을 요청하는 방식이라 호환됨. `response_json_schema` 파라미터만 안 쓰면 됨.

### 제약 2: 검색 위젯 표시 의무 (ToS)

응답에 `search_entry_point`가 포함되면 해당 HTML 위젯을 사용자에게 표시해야 함 (Google 이용 약관).

**→ 대응**: `search_entry_point.rendered_content` HTML을 브리핑 페이지에 포함

### 제약 3: 검색 자동 결정

모델이 검색 필요 여부를 자동 판단. 검색하지 않기로 결정할 수도 있음.

**→ 대응**: 프롬프트에 "반드시 Google 검색으로 최신 정보를 확인하라"고 명시

---

## 6. 가격 및 한도

### 일일 한도

| 구분 | Grounding 한도 |
|------|---------------|
| 무료 티어 | 500 RPD (일일 요청) |
| 유료 티어 (현재 설정) | 1,500 RPD |
| 초과 시 | $35 / 1,000 요청 |

### 우리 사용량 계산

- 기사 10개 × 검증 1회 = **10 RPD**
- 무료 티어(500 RPD)로도 충분
- 유료 티어 불필요 → **무료로 전환 가능**

### 비용 절감 효과

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| Google CSE API | 필요 (100회/일 무료) | **불필요** |
| Gemini 호출 수 | 요약 10회 + 검증 10회 = 20회 | 동일 |
| 검색 비용 | CSE 무료 한도 내 | Grounding 무료 한도 내 |

**→ Google CSE API 키, CX 환경변수 제거 가능. 관리 포인트 감소.**

---

## 7. 지원 모델

| 모델 | Google Search Grounding |
|------|------------------------|
| gemini-2.5-flash ✅ | 지원 |
| gemini-2.5-pro | 지원 |
| gemini-2.5-flash-lite | 지원 |
| gemini-3-flash-preview | 지원 |

---

## 8. FactLens 적용 시 변경 사항

### 제거
- `_search_google()` 함수 (Google CSE 호출)
- `_build_search_context()` 함수
- `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_CX` 환경변수
- `requests` 의존성 (CSE 호출용이었음)

### 변경
- `_verify_with_gemini()`: `config`에 `tools=[types.Tool(google_search=types.GoogleSearch())]` 추가
- 검증 프롬프트: 검색 결과를 직접 넘기지 않음. 모델이 스스로 검색하도록 지시
- 응답에서 `grounding_metadata.grounding_chunks` → `evidence_links` 매핑
- HTML 템플릿에 `search_entry_point` 위젯 표시 영역 추가

### 추가
- `from google.genai import types` import
- grounding_metadata 파싱 로직

### 프롬프트 변경 방향
```
기존: "아래 검색 결과를 참고하여 판단하세요" + {search_results} 첨부
변경: "반드시 Google 검색으로 최신 정보를 확인하고, 공식 출처(정부 발표, 기관 보도자료, 공식 통계)를
      찾아서 판단하세요. 너의 사전 학습 지식은 오래되었을 수 있으니 검색 결과만 신뢰하세요."
```

---

## 9. 리스크 및 대응

| 리스크 | 대응 |
|--------|------|
| 모델이 검색 안 할 수도 있음 | 프롬프트에 검색 필수 명시 |
| grounding_metadata가 없을 수 있음 | 없으면 unconfirmed 폴백 유지 |
| 검색 위젯 표시 의무 (ToS) | HTML 템플릿에 위젯 영역 추가 |
| 무료 한도 500 RPD | 일 10회 사용으로 충분 |
| Structured output과 비호환 | JSON schema 파라미터 미사용, 프롬프트로 JSON 요청 (현재와 동일) |

---

## 10. 결론

**Google Search Grounding으로 전환 가능하며, 권장함.**

- 실시간 웹 검색으로 최신 정보 확인 가능 (이재명 대통령 등)
- 공식 출처 기반 판단 가능
- Google CSE 의존 제거 → 아키텍처 단순화, 환경변수 2개 감소
- 무료 한도 내에서 운영 가능
- 출처 URL/제목을 grounding_metadata에서 자동 추출 → evidence_links 품질 향상

---

## Sources
- [Grounding with Google Search — Gemini API 공식 문서](https://ai.google.dev/gemini-api/docs/google-search)
- [Gemini Developer API 가격](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [google-genai Python SDK (GitHub)](https://github.com/googleapis/python-genai)
- [Structured Output + Grounding 호환 이슈](https://discuss.ai.google.dev/t/grounding-metadata-grounding-chunks-grounding-supports-empty-when-using-structured-output-with-google-search-tool/113240)
