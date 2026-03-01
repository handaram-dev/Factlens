# Plan: 가독성 개선 + 기사 수 확대 + 파싱 강화

> **배경**: 모바일 테스트 결과 (1) 가독성이 떨어짐, (2) 파싱 실패로 7/10개만 표시, (3) 채널A 등 면책 조항 감지 실패
> **리서치**: `docs/research-CSS개선.md` 참조

---

## 1. 변경 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `static/style.css` | 수정 | 타이포그래피, 카드 디자인, 섹션 분리, 태그 강화, 여백 조정 |
| `templates/index.html.j2` | 수정 | 3번째 기사 뒤에 후원 배너 삽입 |
| `pipeline/filter.py` | 수정 | max_count 기본값 10 → 15 |
| `pipeline/main.py` | 수정 | 주석 "상위 10개" → "상위 15개" |
| `pipeline/summarizer.py` | 수정 | DISCLAIMER_KEYWORDS 확장 + TOS_KEYWORDS 추가 + `_is_bad_extraction()` 로직 개선 |
| `tests/test_summarizer.py` | 수정 | 새 키워드/로직 대응 테스트 추가 |

---

## 2. `static/style.css` — 가독성 전면 개선

### 2-1. body 배경색

```css
/* 현재 */
background-color: #f5f5f5;
/* 변경 */
background-color: #f0f0f0;  /* 카드(#fff) 대비 강화 */
```

### 2-2. .news-card

```css
/* 현재 */
.news-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* 변경 */
.news-card {
  background: #fff;
  border-radius: 16px;                          /* 12 → 16 */
  padding: 24px;                                /* 20 → 24 */
  margin-bottom: 20px;                          /* 16 → 20 */
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);   /* 그림자 조정 */
  border: 1px solid rgba(0, 0, 0, 0.06);        /* 미세 보더 추가 */
}
```

### 2-3. .card-headline

```css
/* 현재 */
.card-headline {
  font-size: 1.1rem;
  font-weight: 700;
  color: #111;
  margin-bottom: 12px;
  line-height: 1.5;
}

/* 변경 */
.card-headline {
  font-size: 1.25rem;     /* 20px — 본문(16px)과 1.25배 비율 */
  font-weight: 800;       /* 더 굵게 */
  color: #000;            /* 최대 대비 */
  margin-bottom: 16px;    /* 12 → 16 */
  line-height: 1.4;       /* 제목은 타이트하게 */
  word-break: keep-all;   /* 한글 어절 단위 줄바꿈 */
}
```

### 2-4. .card-summary p

```css
/* 현재 */
.card-summary p {
  font-size: 0.95rem;
  color: #333;
  line-height: 1.8;
  margin-bottom: 14px;
}

/* 변경 */
.card-summary p {
  font-size: 1rem;         /* 16px — 모바일 최소 권장 충족 */
  color: #222;             /* 더 선명하게 */
  line-height: 1.7;        /* 한글 최적 범위 */
  margin-bottom: 12px;     /* 14 → 12 */
  word-break: keep-all;
}

/* 추가 */
.card-summary p:last-child {
  margin-bottom: 0;        /* 마지막 문단 하단 여백 제거 */
}
```

### 2-5. .card-verification — 섹션 분리 구분선 추가

```css
/* 현재 */
.card-verification {
  margin-bottom: 14px;
}

/* 변경 */
.card-verification {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;    /* 요약↔검증 구분선 */
  margin-bottom: 0;                  /* sources가 처리 */
}
```

### 2-6. .tag — pill shape 뱃지 강화

```css
/* 현재 */
.tag {
  display: inline-block;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  margin-bottom: 6px;
}

/* 변경 */
.tag {
  display: inline-block;
  font-size: 0.8rem;
  font-weight: 700;        /* 600 → 700 */
  padding: 6px 14px;       /* 4px 10px → 6px 14px */
  border-radius: 20px;     /* 6 → 20 (pill) */
  margin-bottom: 10px;     /* 6 → 10 */
  letter-spacing: 0.3px;   /* 소형 텍스트 가독성 */
}
```

### 2-7. 태그 색상 강화

```css
/* 현재 → 변경 */
.tag--verified {
  background-color: #d1fae5;   /* #dcfce7 → 더 진한 녹색 */
  color: #065f46;              /* #166534 → 더 진한 텍스트 */
}

.tag--unconfirmed {
  background-color: #fef3c7;   /* 유지 */
  color: #78350f;              /* #92400e → 더 진한 갈색 */
}

.tag--misleading {
  background-color: #fee2e2;   /* #fecaca → 조정 */
  color: #991b1b;              /* 유지 */
  border: 1px solid #fca5a5;   /* 추가: 위험 강조 */
}
```

### 2-8. .verification-reason

```css
/* 현재 */
.verification-reason {
  font-size: 0.85rem;
  color: #555;
  margin-top: 4px;
}

/* 변경 */
.verification-reason {
  font-size: 0.9rem;       /* 0.85 → 0.9 */
  color: #444;             /* #555 → #444 */
  margin-top: 8px;         /* 4 → 8 */
  line-height: 1.6;        /* 추가 */
  word-break: keep-all;    /* 추가 */
}
```

### 2-9. .card-sources — 섹션 분리 추가

```css
/* 현재 */
.card-sources h4 {
  font-size: 0.85rem;
  font-weight: 600;
  color: #666;
  margin-bottom: 6px;
}

/* 변경 */
.card-sources {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e8e8e8;    /* 검증↔원문보기 구분선 */
}

.card-sources h4 {
  font-size: 0.8rem;       /* 0.85 → 0.8 (캡션 사이즈) */
  font-weight: 600;
  color: #888;             /* #666 → #888 (보조 정보 느낌) */
  margin-bottom: 8px;      /* 6 → 8 */
}
```

### 2-10. 모바일 반응형

```css
/* 현재 */
@media (max-width: 480px) {
  body { padding: 0 12px; }
  .site-title { font-size: 1.5rem; }
  .news-card { padding: 16px; border-radius: 8px; }
  .card-headline { font-size: 1rem; }
}

/* 변경 */
@media (max-width: 480px) {
  body { padding: 0 16px; }                /* 12 → 16 (최소 여백 확보) */
  .site-title { font-size: 1.5rem; }       /* 유지 */
  .news-card { padding: 20px; border-radius: 12px; }   /* 16→20, 8→12 */
  .card-headline { font-size: 1.125rem; }  /* 1rem → 1.125rem (본문과 차이 유지) */
}
```

### 2-11. 전체 여백 흐름 (시각화)

```
[카드 padding: 24px]
  headline (mb: 16px)
  ─────────────────
  summary-p (mb: 12px)
  summary-p (mb: 0 — 마지막)
  ─────────────────
  [16px + 1px border-top + 16px padding-top]
  ─────────────────
  tag pill (mb: 10px)
  verification-reason (mb: 12px)
  evidence-toggle
  ─────────────────
  [16px + 1px border-top + 12px padding-top]
  ─────────────────
  원문보기 h4 (mb: 8px)
  source-list pills
[/카드]
(20px card gap)
```

---

## 3. `templates/index.html.j2` — 후원 배너 중간 삽입

3번째 기사 뒤에 후원 배너를 삽입하고, 기존 footer 후원 링크도 유지.

### 현재 (L19-67):
```html
{% for article in briefing.articles %}
<article class="news-card">
    ...
</article>
{% endfor %}
```

### 변경 후:
```html
{% for article in briefing.articles %}
<article class="news-card">
    ...
</article>
{% if loop.index == 3 %}
<div class="mid-support-banner">
    <a class="support-link" href="https://buymeacoffee.com/factlens" target="_blank" rel="noopener">
        가짜뉴스 없는 세상, 후원으로 함께 만들어주세요
    </a>
</div>
{% endif %}
{% endfor %}
```

### CSS 추가 (mid-support-banner):
```css
.mid-support-banner {
  text-align: center;
  margin-bottom: 20px;
}
```

기존 footer 후원 링크는 그대로 유지.

---

## 4. `pipeline/filter.py` — 기사 수 10 → 15

### 변경 전 (L20-23):
```python
def filter_and_select(
    feeds: list[list[Article]],
    max_count: int = 10,
) -> list[Article]:
```

### 변경 후:
```python
def filter_and_select(
    feeds: list[list[Article]],
    max_count: int = 15,
) -> list[Article]:
```

### `pipeline/main.py` 주석 수정 (L30):
```python
# 현재
# 2. 필터링/선별 (라운드 로빈, 상위 10개)
# 변경
# 2. 필터링/선별 (라운드 로빈, 상위 15개)
```

---

## 5. `pipeline/summarizer.py` — 파싱 실패 감지 강화

### 5-1. 근본 원인

> 상세: `docs/research-파싱감지.md` 참조

채널A 트럼프 기사가 필터를 통과한 이유:
- **채널A는 봇 차단(WAF) + JS 렌더링** → newspaper3k/trafilatura 모두 기사 본문에 접근 불가
- 정적 HTML에 기사 본문이 없으므로, 파서가 면책 조항/이용약관을 "본문"으로 선택
- 키워드 `"재배포 금지"`가 실제 텍스트 `"재배포 및 AI학습 이용 금지"`에서 **연속 부분 문자열로 존재하지 않음** → `"재배포 금지" in text` → `False`
- 매칭 1개(무단 전재) < threshold(2) → 정상 판정 → 쓰레기 텍스트 통과

다른 뉴스 사이트(MBC, SBS, 연합뉴스)는 기사 본문이 **정적 HTML에 포함(SSR)** 되어 있고 봇 차단이 약하므로 정상 파싱됨.

### 5-2. 다층 방어 전략

리서치 결과, 키워드 매칭 하나에 의존하지 않고 **3개 레이어를 조합**하여 파싱 실패를 감지한다.

#### Layer 1: 키워드 매칭 강화 — `"재배포 금지"` → `"재배포"`

```python
# 현재
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포 금지", "이용약관", "저작권자", "Copyright"}

# 변경
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포", "이용약관", "저작권자", "Copyright"}
```

`"재배포 및 AI학습 이용 금지"`에서 `"재배포"` 매칭 성공 → `"무단 전재"` + `"재배포"` = 2개 → 불량 판정 → trafilatura 폴백.

정상 기사도 맨 끝에 "무단 전재 및 재배포 금지"가 있으면 2개 매칭되지만, trafilatura로 폴백하여 정상 본문을 가져오므로 기사가 사라지지 않음.

#### Layer 2: 텍스트 품질 휴리스틱 — 최소 길이 체크

키워드와 무관하게, 추출된 텍스트가 뉴스 기사로서 최소 품질을 갖추는지 확인.

```python
MIN_ARTICLE_LENGTH = 200  # 자

def _has_disclaimer(text: str) -> bool:
    if not text or len(text) < MIN_ARTICLE_LENGTH:
        return True
    matches = sum(1 for kw in DISCLAIMER_KEYWORDS if kw in text)
    return matches >= 2
```

- 면책 조항, CAPTCHA 페이지, 네비게이션 텍스트는 대부분 200자 미만
- trafilatura 기본 `MIN_EXTRACTED_SIZE`도 250자
- 200자 미만 정상 기사는 극히 드묾

#### Layer 3: Gemini 프롬프트 통합 검증 — 최종 방어선

요약 프롬프트에 검증 조건을 추가하여, Layer 1~2를 통과한 교묘한 쓰레기 텍스트도 감지.

```
SUMMARY_PROMPT_TEMPLATE에 규칙 추가:
"- 만약 아래 본문이 뉴스 기사가 아니라 이용약관, 면책 조항, 로그인 페이지 등이면 '[[INVALID]]'만 출력하세요"
```

`_generate_summary()` 에서 반환값이 `"[[INVALID]]"`이면 빈 문자열 반환 → 기사 스킵.
추가 API 호출 없이 기존 요약 호출에 통합.

### 5-3. 변경 코드 요약

**`_has_disclaimer()`**: 키워드 교체 + 최소 길이 체크 추가
**`_generate_summary()`**: `[[INVALID]]` 반환 체크 추가
**`SUMMARY_PROMPT_TEMPLATE`**: INVALID 반환 규칙 추가

---

## 6. `tests/test_summarizer.py` — 테스트 업데이트

### 6-1. TestHasDisclaimer에 새 케이스 추가

```python
def test_partial_redistribution_keyword(self) -> None:
    """'재배포 및 AI학습 이용 금지' 같은 변형도 감지."""
    text = "기사 내용... 무단 전재 및 재배포 및 AI학습 이용 금지"
    assert _has_disclaimer(text) is True

def test_too_short(self) -> None:
    """200자 미만 텍스트는 불량 판정."""
    text = "짧은 텍스트"
    assert _has_disclaimer(text) is True
```

### 6-2. TestGenerateSummary에 INVALID 케이스 추가

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

### 6-3. 기존 테스트 호환

`test_disclaimer_detected`의 텍스트 `"무단 전재 재배포 금지 Copyright"` → `"재배포"` 매칭 + `"무단 전재"` 매칭 + `"Copyright"` 매칭 = 3개 → 여전히 True. 변경 불필요.

기존 `TestFetchArticleText` mock 테스트는 `_fetch_with_newspaper`/`_fetch_with_trafilatura`를 mock하므로 변경 불필요.

---

## 7. 구현 순서

1. `pipeline/summarizer.py`:
   - DISCLAIMER_KEYWORDS에서 `"재배포 금지"` → `"재배포"` 교체
   - `_has_disclaimer()`에 최소 길이(200자) 체크 추가
   - `SUMMARY_PROMPT_TEMPLATE`에 `[[INVALID]]` 반환 규칙 추가
   - `_generate_summary()`에서 `[[INVALID]]` 반환 시 빈 문자열 처리
2. `tests/test_summarizer.py` — 변형 키워드 + 짧은 텍스트 + INVALID 테스트 추가
3. `pipeline/filter.py` — max_count 10 → 15
4. `pipeline/main.py` — 주석 수정
5. `static/style.css` — 가독성 전면 개선 (2장 전체)
6. `templates/index.html.j2` — 후원 배너 중간 삽입
7. 전체 테스트 실행: `python -m pytest tests/ -v`

---

## 8. 검증 방법

1. `python -m pytest tests/ -v` — 전체 테스트 통과
2. GitHub Actions workflow_dispatch 재실행
3. factlens.pages.dev 모바일 확인:
   - 카드 간 분리감 (border + shadow)
   - 헤드라인이 본문보다 확실히 큼
   - 요약 ↔ 검증 ↔ 원문보기 사이 구분선
   - 태그가 pill shape로 눈에 띔
   - 한글 어절 단위 줄바꿈 (word-break: keep-all)
   - 기사 수 10개 이상
   - 3번째 기사 뒤에 후원 배너
   - 채널A 등 면책 조항 변형이 감지되어 스킵/폴백
