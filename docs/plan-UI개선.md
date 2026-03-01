# Plan: UI/UX 개선 + 파싱 품질 강화

> **배경**: 첫 배포 후 발견된 6가지 문제. (1) 출처 목록이 너무 길어 카드가 비대, (2) 후원 문구가 서비스 가치를 못 전달, (3) 요약이 한 문단 덩어리라 가독성 떨어짐, (4) 검색 위젯 가로 잘림, (5) newspaper3k 파싱 실패로 면책 조항이 요약됨 (신뢰 문제), (6) unconfirmed 기사에 출처가 무의미하게 표시됨.
> **리서치**: `docs/research-UI개선.md` 참조

---

## 1. 변경 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `templates/index.html.j2` | 수정 | 출처 토글, 후원 문구, unconfirmed 출처 숨김, 검색 위젯 위치 |
| `static/style.css` | 수정 | 토글 스타일, 검색 위젯 가로 스크롤 |
| `pipeline/summarizer.py` | 수정 | 프롬프트에 문단 분리 지시 추가, 파서 체인 (newspaper3k → trafilatura), 면책 키워드 필터 |
| `tests/test_summarizer.py` | 수정 | 파서 체인 테스트, 면책 키워드 필터 테스트 추가 |
| `requirements.txt` | 수정 | `trafilatura` 의존성 추가 |

---

## 2. `templates/index.html.j2` 변경

### 2-1. 출처 토글 + 검색 위젯 + unconfirmed 숨김

현재 (L27-47):
```html
<section class="card-verification">
    <!-- tag, reason -->
    {% if article.evidence_links %}
    <ul class="evidence-list">
        {% for evidence in article.evidence_links %}
        <li><a href="{{ evidence.url }}">{{ evidence.title }}</a></li>
        {% endfor %}
    </ul>
    {% endif %}
    {% if article.search_entry_point %}
    <div class="search-widget">
        {{ article.search_entry_point | safe }}
    </div>
    {% endif %}
</section>
```

변경 후:
```html
<section class="card-verification">
    <!-- tag, reason -->
    {% if article.verification_tag != 'unconfirmed' and article.evidence_links %}
    <details class="evidence-toggle">
        <summary>출처 확인하기 ({{ article.evidence_links | length }}건)</summary>
        <ul class="evidence-list">
            {% for evidence in article.evidence_links %}
            <li><a href="{{ evidence.url }}" target="_blank" rel="noopener">{{ evidence.title }}</a></li>
            {% endfor %}
        </ul>
        {% if article.search_entry_point %}
        <div class="search-widget">
            {{ article.search_entry_point | safe }}
        </div>
        {% endif %}
    </details>
    {% endif %}
</section>
```

변경 포인트:
- `{% if article.verification_tag != 'unconfirmed' %}` — unconfirmed일 때 출처+위젯 전체 숨김
- `<details>/<summary>` — 기본 접힌 상태, 클릭 시 펼침
- 검색 위젯을 토글 안으로 이동 (UX 우선)
- 출처 건수 표시: `({{ article.evidence_links | length }}건)`

### 2-2. 후원 문구 변경

현재 (L62-64):
```html
<a class="support-link" href="https://buymeacoffee.com/factlens" target="_blank" rel="noopener">
    &#x2615; 이 브리핑이 유용했다면 커피 한 잔 사주세요
</a>
```

변경 후:
```html
<a class="support-link" href="https://buymeacoffee.com/factlens" target="_blank" rel="noopener">
    가짜뉴스 없는 세상, 후원으로 함께 만들어주세요
</a>
```

### 2-3. 요약 문단 분리

현재:
```html
<section class="card-summary">
    <p>{{ article.summary }}</p>
</section>
```

변경 후:
```html
<section class="card-summary">
    {% for paragraph in article.summary.split('\n\n') %}
    <p>{{ paragraph }}</p>
    {% endfor %}
</section>
```

이미 `.card-summary p`에 `margin-bottom: 14px`가 있어서 문단 간 여백 자동 적용.

---

## 3. `static/style.css` 변경

### 3-1. 토글 스타일

```css
/* ===== Evidence Toggle ===== */
.evidence-toggle {
  margin-top: 8px;
}

.evidence-toggle summary {
  font-size: 0.8rem;
  color: #2563eb;
  cursor: pointer;
  font-weight: 500;
}

.evidence-toggle summary:hover {
  text-decoration: underline;
}

.evidence-toggle[open] summary {
  margin-bottom: 6px;
}
```

### 3-2. 검색 위젯 가로 스크롤

```css
.search-widget {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin-top: 8px;
}
```

---

## 4. `pipeline/summarizer.py` 변경

### 4-1. 프롬프트 문단 분리 지시

`SUMMARY_PROMPT_TEMPLATE`의 규칙 섹션에 추가:
```
- 2~3문장마다 빈 줄을 넣어 문단을 나눠주세요
```

위치: L19 (`- 전문용어 사용 금지` 다음)에 삽입.

### 4-2. 파서 체인 — trafilatura 폴백

현재 `_fetch_article_text()` (L46-57):
```python
def _fetch_article_text(url: str) -> str:
    if not url:
        return ""
    try:
        article = NewspaperArticle(url)
        article.download()
        article.parse()
        return article.text or ""
    except Exception as e:
        logger.warning(...)
        return ""
```

변경 후:
```python
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포 금지", "이용약관", "저작권자", "Copyright"}

def _has_disclaimer(text: str) -> bool:
    """면책 조항 키워드가 본문 대부분을 차지하는지 확인."""
    if not text:
        return True
    matches = sum(1 for kw in DISCLAIMER_KEYWORDS if kw in text)
    return matches >= 2

def _fetch_with_newspaper(url: str) -> str:
    """newspaper3k로 기사 본문 추출."""
    try:
        article = NewspaperArticle(url)
        article.download()
        article.parse()
        return article.text or ""
    except Exception as e:
        logger.warning("newspaper3k 추출 실패: %s — %s", url[:80], e)
        return ""

def _fetch_with_trafilatura(url: str) -> str:
    """trafilatura로 기사 본문 추출 (폴백)."""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded) or ""
        return ""
    except Exception as e:
        logger.warning("trafilatura 추출 실패: %s — %s", url[:80], e)
        return ""

def _fetch_article_text(url: str) -> str:
    """URL에서 기사 본문 텍스트 추출. newspaper3k → trafilatura 폴백 체인."""
    if not url:
        return ""

    text = _fetch_with_newspaper(url)
    if text and not _has_disclaimer(text):
        return text

    logger.info("newspaper3k 결과 불량, trafilatura로 재시도: %s", url[:80])
    text = _fetch_with_trafilatura(url)
    if text and not _has_disclaimer(text):
        return text

    return ""
```

핵심:
- newspaper3k로 먼저 시도
- 결과에 면책 키워드 2개 이상 포함 시 → 파싱 실패로 판정
- trafilatura로 재시도
- 그래도 실패하면 빈 문자열 반환 → `summarize_articles()`에서 스킵됨

---

## 5. `tests/test_summarizer.py` 변경

### 추가 테스트

```python
class TestHasDisclaimer:
    def test_disclaimer_detected(self) -> None:
        text = "기사 내용... 무단 전재 재배포 금지 Copyright ..."
        assert _has_disclaimer(text) is True

    def test_normal_article(self) -> None:
        text = "이재명 대통령이 싱가포르를 방문했습니다..."
        assert _has_disclaimer(text) is False

    def test_empty(self) -> None:
        assert _has_disclaimer("") is True

class TestFetchArticleText:
    # 기존 테스트 유지 + 아래 추가

    @patch("pipeline.summarizer._fetch_with_trafilatura", return_value="정상 본문")
    @patch("pipeline.summarizer._fetch_with_newspaper", return_value="무단 전재 재배포 금지 이용약관")
    def test_fallback_to_trafilatura(self, mock_np: MagicMock, mock_tf: MagicMock) -> None:
        result = _fetch_article_text("https://example.com/1")
        assert result == "정상 본문"

    @patch("pipeline.summarizer._fetch_with_trafilatura", return_value="")
    @patch("pipeline.summarizer._fetch_with_newspaper", return_value="무단 전재 재배포 금지 이용약관")
    def test_both_fail(self, mock_np: MagicMock, mock_tf: MagicMock) -> None:
        result = _fetch_article_text("https://example.com/1")
        assert result == ""
```

기존 `TestFetchArticleText` 테스트는 `_fetch_with_newspaper`를 mock하도록 수정.

---

## 6. `requirements.txt` 변경

추가:
```
trafilatura>=2.0.0
```

---

## 7. 구현 순서

1. `requirements.txt` — trafilatura 추가
2. `pipeline/summarizer.py` — 프롬프트 문단 분리 + 파서 체인 + 면책 필터
3. `tests/test_summarizer.py` — 새 테스트 추가
4. `templates/index.html.j2` — 출처 토글, unconfirmed 숨김, 후원 문구, 요약 문단 분리
5. `static/style.css` — 토글 스타일, 검색 위젯 스크롤
6. 전체 테스트 실행
7. 커밋 + 푸시 + workflow_dispatch

---

## 8. 검증 방법

1. `python -m pytest tests/ -v` — 전체 테스트 통과
2. GitHub Actions workflow_dispatch 재실행
3. factlens.pages.dev 확인:
   - 출처가 토글로 접혀있는지
   - 토글 클릭 시 출처 + 검색 위젯이 펼쳐지는지
   - unconfirmed 기사에 출처가 숨겨져 있는지
   - 요약이 여러 문단으로 나뉘어 표시되는지
   - 후원 문구가 변경됐는지
   - 채널A 같은 사이트의 기사가 정상 파싱되는지 (또는 깔끔하게 스킵)
