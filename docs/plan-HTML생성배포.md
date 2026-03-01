# Plan: FR-006 정적 HTML 생성 및 배포

> **범위**: 구현 순서 7~11 (HTML 렌더링 + 파이프라인 통합 + GitHub Actions + Cloudflare Pages + 스타일링)
> **관련 TRD**: FR-006, 섹션 3~4, 8~9
> **입력**: 파이프라인 처리 완료된 `Briefing` 객체 (articles 전부 채워진 상태)
> **출력**: `dist/index.html` + `data/YYYY-MM-DD.json` + Cloudflare Pages 배포

---

## 1. 전체 구현 범위

| 단계 | 내용 | 파일 |
|------|------|------|
| Step 1 | JSON 직렬화 + 저장 | `pipeline/renderer.py` |
| Step 2 | Jinja2 → HTML 렌더링 | `pipeline/renderer.py` + `templates/index.html.j2` |
| Step 3 | 파이프라인 통합 | `pipeline/main.py` |
| Step 4 | GitHub Actions 워크플로우 | `.github/workflows/daily-briefing.yml` |
| Step 5 | Cloudflare Pages 배포 설정 | wrangler.toml 또는 GitHub 연동 |
| Step 6 | 프론트엔드 스타일링 | `static/style.css` |

---

## 2. 주요 결정 사항

### 결정 1: JSON 직렬화 방식

| 선택지 | 장점 | 단점 |
|--------|------|------|
| **A. dataclass → dict → json.dumps** | 표준 라이브러리만 사용, 의존성 없음 | 수동 변환 로직 필요 |
| B. dataclasses.asdict() 사용 | 한 줄로 변환 | `_article_text` 같은 내부 필드도 포함됨 |

**→ 선택: A** — `_article_text` 등 내부 필드를 제외하는 커스텀 직렬화 함수 작성. `asdict()` + 필드 제외보다 명시적.

### 결정 2: CSS 방식

| 선택지 | 장점 | 단점 |
|--------|------|------|
| **A. 외부 CSS 파일 (`static/style.css`)** | 관심사 분리, 캐싱 가능 | 파일 2개 배포 필요 |
| B. HTML 내 `<style>` 인라인 | 단일 파일 배포 | 파일이 커짐, 캐싱 불가 |

**→ 선택: A** — TRD 디렉토리 구조에 `static/style.css` 명시. Cloudflare Pages가 정적 파일 서빙 지원.

### 결정 3: Cloudflare Pages 배포 방식

| 선택지 | 장점 | 단점 |
|--------|------|------|
| **A. GitHub 연동 (자동 배포)** | push하면 자동 빌드/배포, 설정 간단 | 빌드 명령어 설정 필요 | 
| B. Wrangler CLI (GitHub Actions에서 직접 배포) | 배포 타이밍 완전 제어 | wrangler 설치 + API 토큰 관리 |

**→ 선택: A** — 가장 단순. GitHub Actions가 HTML 생성 → commit → push → Cloudflare Pages가 자동 감지하여 배포. 별도 배포 스크립트 불필요.

### 결정 4: 파이프라인 에러 처리 전략

| 상황 | 대응 |
|------|------|
| 개별 피드 실패 | 해당 토픽 스킵, 나머지로 진행 |
| 개별 기사 요약/검증 실패 | 해당 기사 제외 |
| 최종 기사 수 0개 | 파이프라인 실패, HTML 생성 안 함, 이전 HTML 유지 |
| 렌더링 실패 | 파이프라인 실패, 이전 HTML 유지 |

---

## 3. 파이프라인 통합 (`pipeline/main.py`)

### 전체 흐름

```python
def run_pipeline() -> None:
    """일일 브리핑 파이프라인 전체 실행."""

    # 1. 수집 (3개 토픽 피드)
    feeds = collect_news()           # → list[list[Article]]

    # 2. 필터링/선별 (라운드 로빈, 상위 10개)
    articles = filter_and_select(feeds)  # → list[Article]

    # 3. 요약 생성 (본문 스크래핑 + Gemini)
    articles = summarize_articles(articles)  # → list[Article] (summary 채움)

    # 4. 교차검증 + 태그 부여 + source_articles 보완
    articles = verify_articles(articles)  # → list[Article] (전체 필드 채움)

    # 5. Briefing 객체 생성
    briefing = build_briefing(articles)  # → Briefing

    # 6. JSON 저장 + HTML 렌더링
    save_json(briefing)              # → data/YYYY-MM-DD.json
    render_html(briefing)            # → dist/index.html
```

---

## 4. 렌더링 모듈 설계 (`pipeline/renderer.py`)

### 공개 인터페이스

```python
def build_briefing(articles: list[Article]) -> Briefing:
    """Article 리스트로 Briefing 객체 생성. 날짜, 제목 자동 설정."""

def save_json(briefing: Briefing) -> None:
    """Briefing → data/YYYY-MM-DD.json 저장."""

def render_html(briefing: Briefing) -> None:
    """Briefing → Jinja2 렌더링 → dist/index.html 저장."""
```

### 내부 함수

```python
def _briefing_to_dict(briefing: Briefing) -> dict:
    """Briefing → JSON 직렬화 가능한 dict. 내부 필드(_article_text) 제외."""

def _format_briefing_title(date: datetime.date) -> str:
    """'2026년 3월 1일 (토) 모닝 브리핑' 형식 제목 생성."""
```

---

## 5. Jinja2 템플릿 구조 (`templates/index.html.j2`)

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ briefing.title }} — 팩트렌즈</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <h1>팩트렌즈</h1>
        <p class="tagline">팩트가 검증된 쉬운 뉴스 브리핑</p>
    </header>

    <main>
        <h2>{{ briefing.title }}</h2>

        {% for article in briefing.articles %}
        <article class="news-card">
            <h3>📰 "{{ article.headline }}"</h3>

            <section class="summary">
                <h4>쉬운 요약</h4>
                <p>{{ article.summary }}</p>
            </section>

            <section class="verification">
                <h4>검증 태그</h4>
                <span class="tag tag--{{ article.verification_tag }}">
                    {% if article.verification_tag == 'verified' %}✅ 사실 확인됨
                    {% elif article.verification_tag == 'unconfirmed' %}⚠️ 사실 확인 중
                    {% elif article.verification_tag == 'misleading' %}❌ 왜곡/오류
                    {% endif %}
                </span>
                <p>{{ article.verification_reason }}</p>
                {% for evidence in article.evidence_links %}
                <a href="{{ evidence.url }}" target="_blank" rel="noopener">{{ evidence.title }}</a>
                {% endfor %}
            </section>

            <section class="sources">
                <h4>원문 보기</h4>
                {% for source in article.source_articles %}
                <a href="{{ source.url }}" target="_blank" rel="noopener">{{ source.publisher }}</a>
                {% endfor %}
            </section>
        </article>
        {% endfor %}
    </main>

    <footer>
        <p>AI 기반 자동 검증이며, 최종 판단은 독자의 몫입니다.</p>
        <a href="https://buymeacoffee.com/factlens" target="_blank" rel="noopener">
            ☕ 이 브리핑이 유용했다면 커피 한 잔 사주세요
        </a>
    </footer>
</body>
</html>
```

> 스타일링은 `static/style.css`에서 처리. 템플릿은 시맨틱 HTML + 접근성(aria, target, rel) 중심.

---

## 6. GitHub Actions 워크플로우

```yaml
# .github/workflows/daily-briefing.yml
name: Daily Briefing

on:
  schedule:
    - cron: '0 22 * * *'  # UTC 22:00 = KST 07:00
  workflow_dispatch:        # 수동 실행 가능

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - run: pip install -r requirements.txt

      - run: python -m pipeline.main
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GOOGLE_CSE_API_KEY: ${{ secrets.GOOGLE_CSE_API_KEY }}
          GOOGLE_CSE_CX: ${{ secrets.GOOGLE_CSE_CX }}

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/ dist/
          git diff --staged --quiet || git commit -m "chore: daily briefing $(date +%Y-%m-%d)"
          git push
```

> Cloudflare Pages가 main 브랜치 push를 감지하여 `dist/` 디렉토리 자동 배포.

---

## 7. Cloudflare Pages 설정

| 항목 | 값 |
|------|-----|
| 프로덕션 브랜치 | `master` |
| 빌드 출력 디렉토리 | `dist` |
| 빌드 명령어 | (없음 — GitHub Actions가 이미 빌드) |
| 정적 파일 | `dist/index.html`, `dist/static/style.css`, `dist/static/favicon.ico` |

> renderer가 `static/` 파일들을 `dist/static/`으로 복사해야 함.

---

## 8. 프론트엔드 스타일링 방향

- **모바일 우선 반응형** (TRD 지시)
- **뉴스 카드 중심 레이아웃** — 카드 간 구분선, 여백
- **검증 태그 시각적 구분** — verified(초록), unconfirmed(주황), misleading(빨강)
- **최소한의 디자인** — MVP에서는 기능 중심, 화려함 배제
- **다크모드 미지원** (MVP 비목표)

> 상세 CSS는 구현 단계에서 작성. plan에서는 방향만 정의.

---

## 9. 파일 변경 목록

### 새로 생성
```
pipeline/main.py                        # 파이프라인 엔트리포인트
pipeline/renderer.py                    # JSON 저장 + HTML 렌더링
templates/index.html.j2                 # Jinja2 템플릿
static/style.css                        # CSS
static/favicon.ico                      # 파비콘
.github/workflows/daily-briefing.yml    # GitHub Actions
tests/test_renderer.py                  # 렌더링 테스트
```

---

## 10. 테스트 전략

### 테스트 케이스
```
test_format_briefing_title         — 날짜 → "YYYY년 M월 D일 (요일) 모닝 브리핑" 변환
test_briefing_to_dict              — Briefing → dict 변환, _article_text 제외 확인
test_save_json                     — JSON 파일 저장 + 내용 검증
test_render_html                   — Jinja2 렌더링 → HTML 파일 생성
test_render_html_contains_cards    — HTML에 뉴스 카드 포함 확인
test_render_html_footer            — AI 한계 고지 + 후원 버튼 포함
test_render_html_verification_tags — 3종 태그 클래스 올바르게 렌더링
test_build_briefing                — Article 리스트 → Briefing 객체 생성
```

---

## 11. 트레이드오프 / 리스크

| 항목 | 리스크 | 대응 |
|------|--------|------|
| GitHub Actions cron 정확도 | 최대 15분 지연 가능 | 표기가 "모닝 브리핑"이라 시간 미노출. 지연 무관 |
| Cloudflare Pages 빌드 한도 | 월 500회 | 하루 1회 = 월 30회. 충분 |
| 이전 HTML 유지 정책 | 파이프라인 실패 시 어제 뉴스가 계속 표시됨 | commit하지 않으면 이전 HTML 자동 유지. 실패 알림은 추후 |
| static 파일 경로 | dist/에 복사 안 하면 CSS/favicon 404 | renderer에서 static → dist/static 복사 로직 포함 |
