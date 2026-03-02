# 리서치 — 검증 시스템 심층 분석

**Date:** 2026-03-02

---

## 1. 파이프라인 전체 흐름

```
수집(collector) → 선별(filter) → 요약(summarizer) → 검증(verifier) → 렌더링(renderer)
```

검증은 4단계에서 실행된다. 요약 단계에서 스크래핑된 `_article_text`가 검증 단계의 입력으로 그대로 전달된다.

### 1-1. 검증 단계 데이터 흐름

```
Article._article_text (최대 5000자 잘림)
    ↓
VERIFY_PROMPT_TEMPLATE에 삽입 (headline + article_text + today 날짜)
    ↓
Gemini 2.5 Flash + Google Search Grounding으로 호출
    ↓
응답에서 2가지 추출:
  (a) response.text → JSON 파싱 → tag, reason, evidence
  (b) response.candidates[0].grounding_metadata → grounding_chunks(출처), search_entry_point(검색 위젯)
    ↓
(a)와 (b)의 evidence를 병합 (URL 중복 제거)
    ↓
Article 필드에 저장: verification_tag, verification_reason, evidence_links, search_entry_point
```

---

## 2. 핵심 컴포넌트 상세 분석

### 2-1. VERIFY_PROMPT_TEMPLATE (`verifier.py:16-42`)

**구조:**
1. 역할 부여: "뉴스 보도의 신뢰성을 교차확인하는 팩트체커"
2. 날짜 주입: `{today}` — KST 기준 오늘 날짜
3. 입력: `{headline}` + `{article_text}`
4. 작업 지시: Google 검색 → 공식 출처와 대조 → JSON 응답
5. 출력 형식: `{"tag", "reason", "evidence"}`
6. 판단 기준: verified / unconfirmed / misleading 3종

**현재 판단 기준 원문:**
```
- verified: 공식 출처(정부, 기관, 공식 통계)로 핵심 내용이 뒷받침됨
- unconfirmed: 공식 출처를 찾을 수 없거나 충분히 확인되지 않음
- misleading: 공식 출처와 내용이 다르거나, 사실 오류 포함, 맥락 누락으로 오해 유도
- 확신이 없으면 반드시 unconfirmed으로 판단하세요
```

**문제점:**
- misleading 정의가 넓다: "공식 출처와 내용이 다르거나" + "맥락 누락으로 오해 유도"
- "내용이 다르다"가 "검색에서 안 나왔다"와 구분되지 않는다
- "확신이 없으면 unconfirmed" 규칙이 4번째 줄에 묻혀 강조가 약하다

### 2-2. Google Search Grounding 동작 원리

**Gemini + Google Search Grounding의 실제 동작:**

1. Gemini가 프롬프트를 분석하여 자동으로 검색 쿼리를 생성
2. 생성된 쿼리로 Google 검색을 실행
3. 검색 결과를 기반으로 응답을 생성
4. 응답에 `grounding_metadata` 포함:
   - `grounding_chunks`: 참조한 웹 소스 (title + uri)
   - `search_entry_point`: 검색 위젯 HTML
   - `grounding_supports`: 응답 텍스트의 어느 부분이 어떤 소스에 기반하는지

**핵심 한계:**
- Gemini가 **자동으로 검색 쿼리를 생성**한다 → 쿼리 품질이 결과를 좌우
- 한국어 뉴스의 세부 사항(예: "샤오미 1차 출시국에 한국 포함")은 검색 쿼리로 변환되기 어려움
- Google 검색 자체가 모든 사실을 인덱싱하지 않음 → **"검색에 안 나옴" ≠ "사실이 아님"**
- Google에 따르면 hallucination을 ~40% 줄이지만, **없는 정보에 대한 판단(false negative)은 여전히 취약**

### 2-3. _verify_with_gemini (`verifier.py:133-188`)

**핵심 로직:**
```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=GROUNDING_CONFIG,  # Google Search 도구 활성화
)
```

- 모델: `gemini-2.5-flash`
- `article_text[:5000]` — 본문을 5000자로 잘라서 전달
- rate limit (429) 발생 시 60초 대기 후 최대 3회 재시도
- 모든 실패 케이스에서 `UNCONFIRMED_FALLBACK` 반환 (보수적 처리)

**입력에 포함되는 것:**
- 기사 본문 전체 (사진 캡션, 기자 정보, 관련 기사 링크 등 포함)
- 스크래핑 품질에 따라 불필요한 텍스트가 섞일 수 있음

### 2-4. _parse_verification_response (`verifier.py:100-130`)

**JSON 파싱 방어 로직:**
1. 마크다운 코드 블록(```) 제거
2. JSON 파싱
3. tag가 VALID_TAGS(`verified`, `unconfirmed`, `misleading`)에 없으면 → unconfirmed 처리
4. 파싱 실패 → unconfirmed 처리

**안전장치:** 파싱이나 API 호출이 실패하면 항상 unconfirmed으로 떨어진다. 이것은 올바른 설계다.

### 2-5. _extract_grounding_evidence (`verifier.py:70-97`)

- `response.candidates[0].grounding_metadata`에서 추출
- `grounding_chunks` → `[{title, url}]` 리스트로 변환
- `search_entry_point` → HTML 문자열 추출
- 실패 시 빈 리스트 반환 (안전)

### 2-6. Evidence 병합 (`verifier.py:165-172`)

```python
# JSON 응답의 evidence + grounding_metadata의 evidence를 합침
# URL 기준 중복 제거
seen_urls = {e["url"] for e in result.get("evidence", [])}
for e in grounding_evidence:
    if e["url"] and e["url"] not in seen_urls:
        result.setdefault("evidence", []).append(e)
```

두 소스의 evidence를 병합하되 URL 중복을 제거한다.

### 2-7. UNCONFIRMED_FALLBACK (`verifier.py:48-53`)

```python
UNCONFIRMED_FALLBACK = {
    "tag": "unconfirmed",
    "reason": "이 브리핑 시점에 AI가 충분히 확인하지 못했어요.",
    "evidence": [],
    "search_entry_point": "",
}
```

API 실패, 파싱 실패, rate limit 초과 시 사용되는 기본값. 안전한 설계.

---

## 3. 실제 출력 분석 (2026-03-02 브리핑)

### 3-1. 태그 분포

| 태그 | 건수 | 비율 |
|------|------|------|
| ✅ verified | 6건 | 46% |
| ⚠️ unconfirmed | 5건 | 38% |
| ❌ misleading | 2건 | 15% |

총 13건 기사.

### 3-2. misleading으로 분류된 2건 분석

**사례 1: 이란-미 항모 기사**
- reason: "기사 본문에서는 항모가 이란 해안 근접 위치라고 했지만, 첨부된 사진 설명에는 2025년 8월 샌디에이고 정박 중이라고 적혀 있어서 혼란을 줄 수 있어요"
- **오판 원인:** 사진 캡션을 본문 사실로 취급
- **올바른 태그:** unconfirmed (양측 주장이 교차확인되지 않은 상태)
- **상태:** 사진 캡션 규칙 추가로 이미 수정됨 → 오늘 재실행 결과에서는 "사실 확인 중"으로 변경 확인

**사례 2: MWC26 중국 스마트폰 기사** ← 현재 문제
- reason: "샤오미 1차 출시국에 한국 포함 — 검색에서 확인 안 됨", "메인홀 부스 — 공식 출처에서 전부 확인되지 않음", "대부분의 내용은 확인됨"
- **오판 원인:** "검색에서 확인 안 됨"을 "사실과 다름"으로 비약
- **올바른 태그:** unconfirmed (일부 세부사항 미확인, 대부분 확인됨)

### 3-3. unconfirmed으로 올바르게 분류된 사례들

| 기사 | reason | 분류 |
|------|--------|------|
| 충북 무료 예식장 | "충북도 공식 발표를 통해 독립적으로 확인되지 않았어요" | ✅ 올바름 |
| 폴리마켓 이란 베팅 | "AI가 충분히 확인하지 못했어요" (fallback) | ✅ 올바름 |
| 이란 공습 대통령 대응 | "AI가 충분히 확인하지 못했어요" (fallback) | ✅ 올바름 |
| 스페이스X 상장 | "AI가 충분히 확인하지 못했어요" (fallback) | ✅ 올바름 |

**패턴:** fallback으로 떨어진 unconfirmed(4건 중 3건)은 API가 응답을 제대로 생성하지 못한 경우. 충북 예식장(1건)은 Gemini가 올바르게 unconfirmed 판단.

### 3-4. 오분류 패턴 정리

```
Gemini의 판단 흐름 (현재):
1. 기사 본문 읽기
2. Google 검색 실행
3. 검색 결과와 기사 대조
4. 일치 → verified
   검색 안 됨 → misleading (❌ 잘못된 비약) 또는 unconfirmed
   모순 발견 → misleading

문제: 3→4 단계에서 "검색 안 됨"이 misleading으로 가는 경로가 존재
```

---

## 4. 근본 원인 분석

### 4-1. 프롬프트 구조 문제

| 문제 | 설명 |
|------|------|
| **misleading 정의가 너무 넓다** | "공식 출처와 내용이 다르거나"가 "검색에서 안 나왔는데 기사에는 있다"를 포함할 수 있음 |
| **경계 규칙이 약하다** | "확신이 없으면 unconfirmed" 규칙이 목록의 4번째 줄에 묻혀 있음 |
| **"확인 안 됨 ≠ 사실과 다름" 미명시** | 이 핵심 구분이 프롬프트 어디에도 없음 |
| **부분 미확인 기준 없음** | "대부분 확인되고 일부만 미확인"일 때 어떤 태그를 붙일지 기준 없음 |

### 4-2. 입력 데이터 문제

| 문제 | 설명 |
|------|------|
| **스크래핑 잡음** | newspaper3k/trafilatura가 사진 캡션, 관련 기사 링크, 기자 정보 등을 본문에 포함시킴 |
| **5000자 잘림** | `article_text[:5000]`으로 자르기 때문에 긴 기사의 후반부 맥락이 누락될 수 있음 |

### 4-3. Google Search Grounding 한계

| 한계 | 설명 |
|------|------|
| **검색 쿼리 품질** | Gemini가 자동 생성하는 검색 쿼리가 세부 사항(예: "샤오미 1차 출시국 한국")을 정확히 찾지 못할 수 있음 |
| **인덱싱 지연** | 최신 뉴스의 세부사항이 아직 Google에 인덱싱되지 않았을 수 있음 |
| **한국어 검색 한계** | 한국 뉴스 세부 정보가 영문 검색 결과에 없을 수 있고, 검색 쿼리가 영문으로 생성될 가능성 |

---

## 5. 코드 안전장치 현황

| 안전장치 | 위치 | 상태 |
|----------|------|------|
| API 실패 → unconfirmed | `_verify_with_gemini:175-185` | ✅ 작동 |
| Rate limit → 재시도 후 unconfirmed | `_verify_with_gemini:176-188` | ✅ 작동 |
| JSON 파싱 실패 → unconfirmed | `_parse_verification_response:128-130` | ✅ 작동 |
| 유효하지 않은 태그 → unconfirmed | `_parse_verification_response:112-114` | ✅ 작동 |
| grounding_metadata 없음 → 빈 evidence | `_extract_grounding_evidence:80-81` | ✅ 작동 |
| **"검색 미확인"을 misleading과 구분** | **프롬프트** | ❌ **미작동** |

코드 레벨 안전장치는 모두 잘 작동한다. **문제는 오직 프롬프트에만 있다.**

---

## 6. 테스트 현황 (`test_verifier.py`)

| 테스트 클래스 | 건수 | 범위 |
|--------------|------|------|
| TestExtractGroundingEvidence | 4 | grounding_metadata 추출 |
| TestParseVerificationResponse | 6 | JSON 파싱 + 방어 로직 |
| TestVerifyWithGemini | 5 | API 호출 + evidence 병합 + 재시도 |
| TestVerifyArticles | 4 | 전체 흐름 + 폴백 |
| **합계** | **19** | |

테스트는 모두 mock 기반이라 프롬프트 텍스트 변경에 영향받지 않는다.
프롬프트의 판단 품질을 검증하는 테스트는 없다 (실제 API 호출이 필요하므로 자동 테스트가 어려움).

---

## 7. 위험도 평가

| 시나리오 | 위험도 | 이유 |
|----------|--------|------|
| 사실인 기사에 ❌왜곡 태그 | **매우 높음** | 서비스 핵심 가치(팩트체크 신뢰)를 정면으로 훼손 |
| 미확인 기사에 ✅사실 태그 | 높음 | 검증되지 않은 정보를 사실로 오인할 위험 |
| 왜곡 기사에 ⚠️확인중 태그 | 중간 | 보수적이라 사용자 피해는 적지만, 검증 가치가 떨어짐 |

**현재 발생 중인 문제는 "매우 높음" 등급이다.**

---

## 8. 수정 방향 제안

### 프롬프트 수정 (plan-검증오분류방지.md에 반영)

1. **misleading 정의 강화**: "명백히 모순될 때만" 조건 추가
2. **"확인 안 됨 ≠ 사실과 다름" 별도 경고 섹션**: 가장 눈에 띄는 위치에 배치
3. **부분 미확인 기준 명시**: "일부만 미확인이고 나머지가 사실이면 unconfirmed"
4. **판단 우선순위 명시**: "의심스러우면 misleading이 아니라 unconfirmed"

### 향후 고려사항 (이번 수정 범위 밖)

| 개선 | 설명 | 우선순위 |
|------|------|----------|
| 스크래핑 전처리 | 사진 캡션, 기자 정보, 관련 기사 링크를 본문에서 제거한 뒤 검증 | 중간 |
| 검증 2차 확인 | misleading 판정 시 재검증 (같은 기사를 한번 더 호출하여 확인) | 높음 — 비용 낮음 |
| reason 기반 자동 보정 | reason 텍스트에 "확인되지 않았"이 있으면 misleading → unconfirmed 자동 변환 | 낮음 — 프롬프트 우회 |
| 검증 결과 로깅 | misleading 판정 건수를 별도 추적하여 오판율 모니터링 | 중간 |

---

## 9. 리서치 소스

- 소스코드: `pipeline/verifier.py`, `pipeline/summarizer.py`, `pipeline/models.py`, `pipeline/main.py`
- 테스트: `tests/test_verifier.py` (19개 테스트)
- 실제 출력: `data/2026-03-02.json` (13개 기사, misleading 2건)
- 배포 결과: `factlens.pages.dev` (2026-03-02 브리핑)
- [Gemini Grounding with Google Search 공식 문서](https://ai.google.dev/gemini-api/docs/google-search)
- [Google Developers Blog — Grounding 소개](https://developers.googleblog.com/en/gemini-api-and-ai-studio-now-offer-grounding-with-google-search/)
- [Gemini Grounding 동작 원리 분석 — DEJAN](https://dejan.ai/blog/gemini-grounding/)
