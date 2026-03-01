# Plan: 파싱 실패 감지 강화

> **배경**: 채널A 트럼프 기사가 면책 조항 텍스트로 잘못 요약됨. 파싱 불가 사이트를 확실히 감지하여 건너뛰어야 함.
> **리서치**: `docs/research-채널A파싱실패.md`, `docs/research-파싱감지.md` 참조

---

## 1. 근본 원인 요약

채널A는 **봇 차단(WAF) + JS 렌더링** → newspaper3k/trafilatura 모두 정적 HTML에서 기사 본문에 접근 불가. 유일한 텍스트인 면책 조항이 "본문"으로 선택됨.

현재 `_has_disclaimer()`는 `"재배포 금지"` 키워드로 감지하지만, 실제 텍스트는 `"재배포 및 AI학습 이용 금지"` → `"재배포 금지"` 부분 문자열 불일치 → 필터 통과.

MBC, SBS, 연합뉴스 등은 기사 본문이 정적 HTML(SSR)에 포함되어 있고 봇 차단이 약해서 정상 파싱됨.

---

## 2. 변경 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `pipeline/summarizer.py` | 수정 | 키워드 교체, 최소 길이 체크, 프롬프트 INVALID 규칙, INVALID 반환 처리 |
| `tests/test_summarizer.py` | 수정 | 새 테스트 케이스 추가 |

---

## 3. 3층 방어 전략

리서치 결과 6가지 접근법을 비교 검토한 뒤, MVP에 적합한 3개 레이어를 선정.

### Layer 1: 키워드 매칭 강화

`"재배포 금지"` → `"재배포"`로 교체.

```python
# 현재 (L13)
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포 금지", "이용약관", "저작권자", "Copyright"}

# 변경
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포", "이용약관", "저작권자", "Copyright"}
```

- `"재배포 및 AI학습 이용 금지"`에서 `"재배포"` 매칭 성공
- `"무단 전재"` + `"재배포"` = 2개 → 불량 판정 → trafilatura 폴백
- 정상 기사도 맨 끝에 "무단 전재 및 재배포 금지"가 있으면 2개 매칭되지만, trafilatura로 폴백하여 정상 본문을 가져오므로 기사가 사라지지 않음

### Layer 2: 최소 텍스트 길이 체크

키워드와 무관하게, 추출 텍스트가 200자 미만이면 파싱 실패로 판정.

```python
MIN_ARTICLE_LENGTH = 200

def _has_disclaimer(text: str) -> bool:
    """추출 텍스트가 불량인지 판별. 최소 길이 미달 또는 면책 키워드 2개 이상이면 True."""
    if not text or len(text) < MIN_ARTICLE_LENGTH:
        return True
    matches = sum(1 for kw in DISCLAIMER_KEYWORDS if kw in text)
    return matches >= 2
```

근거:
- 면책 조항, CAPTCHA 페이지, 네비게이션 텍스트는 대부분 200자 미만
- trafilatura 기본 `MIN_EXTRACTED_SIZE`도 250자
- 200자 미만 정상 뉴스 기사는 극히 드묾

### Layer 3: Gemini 프롬프트 통합 검증

요약 프롬프트에 검증 조건을 추가. 추가 API 호출 없이, Layer 1~2를 통과한 교묘한 쓰레기 텍스트를 감지.

```python
# SUMMARY_PROMPT_TEMPLATE 규칙 섹션에 추가 (L27 다음):
"- 만약 아래 본문이 뉴스 기사가 아니라 이용약관, 면책 조항, 로그인 페이지 등이면 '[[INVALID]]'만 출력하세요"
```

```python
# _generate_summary() 에서 반환값 체크 (L116-117 사이):
if response.text:
    stripped = response.text.strip()
    if "[[INVALID]]" in stripped:
        logger.warning("Gemini가 비정상 본문 감지: %s", headline[:40])
        return ""
    return stripped
```

---

## 4. 구체적 코드 변경

### 4-1. `pipeline/summarizer.py`

**변경 1 — L13 키워드 교체:**
```python
# 현재
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포 금지", "이용약관", "저작권자", "Copyright"}
# 변경
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포", "이용약관", "저작권자", "Copyright"}
```

**변경 2 — L13 아래에 상수 추가:**
```python
MIN_ARTICLE_LENGTH = 200
```

**변경 3 — L50-55 `_has_disclaimer()` 수정:**
```python
# 현재
def _has_disclaimer(text: str) -> bool:
    """면책 조항 키워드가 2개 이상 포함되면 파싱 실패로 판정."""
    if not text:
        return True
    matches = sum(1 for kw in DISCLAIMER_KEYWORDS if kw in text)
    return matches >= 2

# 변경
def _has_disclaimer(text: str) -> bool:
    """추출 텍스트가 불량인지 판별. 최소 길이 미달 또는 면책 키워드 2개 이상이면 True."""
    if not text or len(text) < MIN_ARTICLE_LENGTH:
        return True
    matches = sum(1 for kw in DISCLAIMER_KEYWORDS if kw in text)
    return matches >= 2
```

**변경 4 — L26-27 프롬프트 규칙 추가:**
```
- 특정 언론사나 정치적 입장을 지지하거나 비판하지 않기
- 만약 아래 본문이 뉴스 기사가 아니라 이용약관, 면책 조항, 로그인 페이지 등이면 '[[INVALID]]'만 출력하세요
```

**변경 5 — L116-117 `_generate_summary()` INVALID 체크:**
```python
# 현재
if response.text:
    return response.text.strip()

# 변경
if response.text:
    stripped = response.text.strip()
    if "[[INVALID]]" in stripped:
        logger.warning("Gemini가 비정상 본문 감지: %s", headline[:40])
        return ""
    return stripped
```

### 4-2. `tests/test_summarizer.py`

**TestHasDisclaimer에 추가:**

```python
def test_partial_redistribution_keyword(self) -> None:
    """'재배포 및 AI학습 이용 금지' 같은 변형도 감지."""
    text = "기사 내용... 무단 전재 및 재배포 및 AI학습 이용 금지" + "." * 200
    assert _has_disclaimer(text) is True

def test_too_short(self) -> None:
    """200자 미만 텍스트는 불량 판정."""
    text = "짧은 텍스트"
    assert _has_disclaimer(text) is True

def test_long_normal_article(self) -> None:
    """200자 이상 정상 기사는 통과."""
    text = "이재명 대통령이 싱가포르를 방문했습니다. " * 20
    assert _has_disclaimer(text) is False
```

**TestGenerateSummary에 추가:**

```python
def test_invalid_article_returns_empty(self) -> None:
    """Gemini가 [[INVALID]] 반환 시 빈 문자열."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "[[INVALID]]"
    mock_client.models.generate_content.return_value = mock_response
    result = _generate_summary(mock_client, "기사 제목", "이용약관 텍스트")
    assert result == ""
```

**기존 테스트 호환성:**

- `test_disclaimer_detected`: `"무단 전재 재배포 금지 Copyright"` → `"재배포"` 매칭 + `"무단 전재"` + `"Copyright"` = 3개 → True. 단, 텍스트가 200자 미만이면 길이 체크에서 먼저 True. 어느 쪽이든 결과 동일.
- `test_normal_article`: `"이재명 대통령이..."` 47자 → 200자 미만 → True로 변경됨. **수정 필요**: 텍스트를 200자 이상으로 늘려야 함.
- `test_single_keyword_ok`: `"기사 본문 내용입니다. Copyright 2026"` 21자 → 200자 미만 → True로 변경됨. **수정 필요**: 텍스트를 200자 이상으로 늘려야 함.
- `test_fallback_to_trafilatura`: newspaper mock 반환값 `"무단 전재 재배포 금지 이용약관"` → 200자 미만이지만, `_has_disclaimer` 판정은 True (길이 미달) → 폴백 발동. 결과 동일.
- `test_both_fail`: 동일 이유로 결과 동일.

---

## 5. 구현 순서

1. `pipeline/summarizer.py`:
   - `DISCLAIMER_KEYWORDS`에서 `"재배포 금지"` → `"재배포"` 교체
   - `MIN_ARTICLE_LENGTH = 200` 상수 추가
   - `_has_disclaimer()`에 최소 길이 체크 추가
   - `SUMMARY_PROMPT_TEMPLATE`에 `[[INVALID]]` 반환 규칙 추가
   - `_generate_summary()`에서 `[[INVALID]]` 반환 시 빈 문자열 처리
2. `tests/test_summarizer.py`:
   - 기존 테스트 수정 (200자 미만 텍스트를 200자 이상으로 변경)
   - 새 테스트 추가 (변형 키워드, 짧은 텍스트, 긴 정상 기사, INVALID)
3. 전체 테스트 실행: `python -m pytest tests/ -v`

---

## 6. 검증 방법

1. `python -m pytest tests/ -v` — 전체 테스트 통과
2. GitHub Actions workflow_dispatch 재실행
3. 파이프라인 로그 확인:
   - 채널A 기사가 `_has_disclaimer`에서 감지되어 스킵/폴백하는지
   - Gemini가 `[[INVALID]]` 반환하는 케이스가 있는지
   - 정상 기사가 False Positive로 스킵되지 않는지

---

## 7. 채택하지 않은 접근법과 이유

| 접근법 | 미채택 이유 |
|--------|------------|
| TOS_KEYWORDS (이용약관 키워드) | 정상 기사에도 포함될 수 있음. 사용자 피드백으로 제외 |
| 도메인 블랙리스트 | 수동 관리 필요. 새 사이트 대응 불가. 3층 방어로 충분 |
| HTML 응답 검증 | 200 OK 반환 봇 차단에 무용. 별도 HTTP 요청 필요 |
| TF-IDF 유사도 | sklearn 의존성 추가. MVP에 과도 |
| Gemini 별도 검증 호출 | 추가 비용/지연. 프롬프트 통합이 더 효율적 |
| newspaper4k 교체 | JS 미지원 문제 동일. 근본 해결 안 됨 |
| Playwright (headless browser) | 무거움, GitHub Actions 비용/시간 증가. MVP 범위 밖 |
