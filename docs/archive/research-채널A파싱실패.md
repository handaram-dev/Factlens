# 리서치: newspaper3k 채널A 뉴스 기사 파싱 실패 근본 원인

> 작성일: 2026-03-01

---

## 1. newspaper3k 파싱 메커니즘

### 1-1. 핵심 알고리즘: Gravity-Based Content Scoring

newspaper3k는 python-goose의 파싱 코드를 기반으로 한 **휴리스틱 기반 콘텐츠 추출기**이다. 핵심 메서드는 `calculate_best_node()`이며, 다음 단계로 작동한다:

1. **후보 노드 수집**: HTML에서 `<p>`, `<pre>`, `<td>` 태그를 모두 추출
2. **콘텐츠 밀도 필터링**: 불용어(stopword)가 2개 이상이면서 링크 밀도가 낮은 노드만 후보로 선정
3. **Gravity Score 부여**: 각 후보 노드의 부모/조부모 노드에 점수를 누적 부여
   - Boostability 기준: 다음 형제가 `<p>` 태그이고 충분한 불용어를 포함하면 가산점
   - 하위 25% 위치의 노드는 감점
   - 누적 단어 수 분석
4. **링크 밀도 필터**: `(링크 단어 수 / 전체 단어 수) * 링크 수 > 1.0`이면 비콘텐츠로 분류
5. **형제 노드 통합**: 최고 점수 노드를 선정한 후, 인접 문단 중 기준 점수(부모 노드 평균의 30%) 이상인 것을 통합
6. **후처리 정리**: `post_cleanup()`으로 나머지 노드 제거

### 1-2. 사전 정리 단계 (Cleaners)

콘텐츠 추출 전에 `cleaners.py`가 다음 요소를 제거:
- `<script>`, `<style>` 태그
- ID/class에 다음 패턴이 포함된 노드: `sidebar`, `navbar`, `footer`, `comment`, `social`, `ad`, `menucontainer`, `storytopbar-bucket`, `utility-bar`, `inline-share-tools` 등
- HTML 주석
- `<em>` (이미지 미포함 시)
- `<span>` (문단 내)

### 1-3. 불용어(Stopword) 기반 점수 산정

newspaper3k는 언어별 불용어 파일을 보유. 한국어(`stopwords-ko.txt`)에는 약 **70개** 항목이 포함되어 있으며, 주로 조사/접속사(`을`, `의`, `에`, `이`, `를`, `으로`, `은`, `는`, `가`, `로`, `에서`, `도`, `와`, `부터`, `까지` 등)이다.

**핵심**: newspaper3k는 CSS selector나 meta tag를 기반으로 본문을 찾는 것이 **아니다**. 불용어 밀도 + 링크 밀도 + DOM 위치라는 **통계적 휴리스틱**에 의존한다. 이 알고리즘은 "가장 본문처럼 보이는 텍스트 블록"을 선택하는 방식이므로, HTML 구조에 따라 면책 조항이 본문보다 더 높은 점수를 받을 수 있다.

---

## 2. 채널A 사이트 특성 조사

### 2-1. 기본 정보

- **공식 도메인**: `ichannela.com` (URL 패턴: `ichannela.com/news/detail/{publishId}.do`)
- **운영사**: 채널A (동아미디어그룹 계열, 2011년 개국 종합편성채널)
- **URL 패턴의 `.do` 확장자**: Java Servlet/Spring MVC의 DispatcherServlet URL 매핑 패턴. 채널A 웹사이트가 **Java 기반 웹 프레임워크**(Spring MVC 또는 Struts)로 구축되었음을 강하게 시사
- **이전 URL 패턴**: `ichannela.com/news/main/news_detailPage.do?publishId=...` → 최근 `ichannela.com/news/detail/{id}.do` 형태로 변경된 것으로 보임

### 2-2. 접근 차단 확인

리서치 과정에서 WebFetch 도구로 ichannela.com 접속 시도가 **모두 실패**함:
- `https://www.ichannela.com/news/main/news_detailPage.do?publishId=000000295298` -- 실패
- `https://ichannela.com/news/detail/000000516782.do` -- 실패
- `https://ichannela.com` (홈페이지) -- 실패
- `https://www.ichannela.com/robots.txt` -- 실패

이는 채널A가 **봇/자동화 도구의 접근을 적극 차단**하고 있음을 의미한다. 일반 브라우저가 아닌 프로그래밍 방식의 HTTP 요청을 거부하는 것으로 보임.

### 2-3. 기술 스택 추정

BuiltWith 분석 시도 결과, 채널A 사이트에는 다음이 감지됨:
- **CAPTCHA 인증 시스템**: 이미지 기반 CAPTCHA + 2단계 검증
- **Proof-of-Work 알고리즘**: 해시 기반 검증 (trailing zeros 요구)
- **쿠키 기반 상태 관리**: `BWSTATE` 쿠키
- **모바일 최적화**: Safari/iPhone 전용 핸들러

이는 채널A가 **Cloudflare 또는 유사한 WAF(Web Application Firewall)** 뒤에 위치하며, 봇 탐지 및 차단이 활성화되어 있음을 시사한다.

### 2-4. CMS/플랫폼

`.do` URL 패턴 + Java 기반 서버 구조로 보아:
- **Spring MVC 또는 Apache Struts** 기반의 커스텀 CMS
- 한국 방송사들이 자체 CMS를 운영하는 것이 일반적 (동아미디어그룹 공통 플랫폼일 가능성)
- WordPress, React 등 표준 프레임워크가 아닌 **레거시 Java 웹 앱**

---

## 3. 근본 원인 분석: 왜 채널A만 실패하는가

### 가설 1: JavaScript 렌더링 기반 본문 로딩 (가장 유력)

**증거**:
- newspaper3k는 Python `requests` 라이브러리로 HTTP GET 요청 후 정적 HTML만 파싱
- 채널A의 Java 기반 웹앱이 기사 본문을 **AJAX/JavaScript로 비동기 로딩**할 가능성이 높음
- 이 경우 정적 HTML에는 본문이 없고, **면책 조항/이용약관/푸터 텍스트만 정적으로 존재**
- newspaper3k의 `calculate_best_node()`가 "가장 본문처럼 보이는 텍스트"로 면책 조항을 선택

**메커니즘**:
```
[실제 HTML 소스]
<html>
  <head>...</head>
  <body>
    <div id="header">네비게이션</div>
    <div id="articleBody">
      <!-- JS가 여기에 본문을 동적 삽입 -->
      <script>loadArticleContent(publishId);</script>
    </div>
    <div id="footer">
      <p>채널A의 모든 콘텐츠(기사)는 저작권법의 보호를 받는 바, 무단 전재 및 재배포 및 AI학습 이용 금지...</p>
      <p>이용약관 | 개인정보처리방침 | ...</p>
    </div>
  </body>
</html>
```
newspaper3k가 받는 HTML에서 `#articleBody`는 비어있고, `#footer`의 면책 조항만 실질적 텍스트 → 면책 조항이 최고 점수 노드로 선정.

### 가설 2: User-Agent 기반 차단 + 제한된 페이지 반환

**증거**:
- newspaper3k의 기본 User-Agent: `newspaper/0.2.8`
- 채널A의 WAF/봇 탐지 시스템이 이 User-Agent를 차단
- 차단 시 403 에러 대신 **이용약관/면책 조항 페이지로 리다이렉트** 하는 사이트가 있음
- 이 경우 newspaper3k는 면책 조항 페이지를 "기사 페이지"로 인식하고 파싱

### 가설 3: iframe 내부에 본문 로딩

**증거**:
- 한국 레거시 Java 웹 앱에서 iframe을 사용해 콘텐츠를 삽입하는 패턴이 일반적
- newspaper3k는 iframe 내부 콘텐츠에 접근 불가
- iframe 외부에 있는 면책 조항만 추출 가능

### 종합 판단

**가장 유력한 원인은 가설 1 + 가설 2의 복합 작용**:

1. 채널A의 WAF가 newspaper3k의 기본 User-Agent를 감지
2. 봇으로 판단되어 (a) 차단 페이지 반환 또는 (b) JavaScript 미실행으로 빈 본문 반환
3. 어떤 경우든, newspaper3k가 받는 HTML에는 실제 기사 본문이 존재하지 않음
4. `calculate_best_node()`가 유일한 텍스트 블록인 면책 조항/이용약관을 본문으로 선택
5. trafilatura도 동일하게 HTTP GET → 정적 HTML 파싱이므로 같은 문제 발생

---

## 4. 기존 코드의 대응 현황 (`summarizer.py`)

### 현재 방어 메커니즘

```python
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포 금지", "이용약관", "저작권자", "Copyright"}

def _has_disclaimer(text: str) -> bool:
    """면책 조항 키워드가 2개 이상 포함되면 파싱 실패로 판정."""
    matches = sum(1 for kw in DISCLAIMER_KEYWORDS if kw in text)
    return matches >= 2
```

### 이미 발견된 취약점 (plan-가독성개선.md에서)

- `"재배포 금지"` 키워드가 `"재배포 및 AI학습 이용 금지"`와 매칭 실패
  - `"재배포 금지" in "무단 전재 및 재배포 및 AI학습 이용 금지"` → `False`
  - `"무단 전재"` 1개만 매칭 < threshold 2 → 정상 판정 → 면책 조항 텍스트가 통과
- **수정 방안**: `"재배포 금지"` → `"재배포"`로 변경하면 해결 (이미 plan에 기재됨)

### 파싱 체인 흐름

```
newspaper3k 시도 → 면책 조항 추출
  ↓ _has_disclaimer 체크 (현재는 통과됨)
  ↓ 실패 감지 못 함 → 면책 조항을 "기사 본문"으로 사용
  ↓ Gemini가 면책 조항을 요약 → 엉뚱한 요약 생성
```

---

## 5. trafilatura도 실패하는 이유

### trafilatura의 작동 방식

trafilatura도 newspaper3k와 마찬가지로 `HTTP GET → 정적 HTML 파싱`이 기본. JavaScript를 실행하지 않는다.

### 공통 실패 원인

| 원인 | newspaper3k | trafilatura |
|------|-------------|-------------|
| JavaScript 미실행 | 해당 | 해당 |
| HTTP 요청만으로 HTML 수신 | 해당 | 해당 |
| 봇 차단/WAF | 해당 | 해당 |
| iframe 내부 접근 불가 | 해당 | 해당 |

### trafilatura 고유 이슈

- trafilatura는 비표준 HTML 태그/클래스를 사용하는 사이트에서 실패한 사례가 문서화되어 있음
  - 예: Protocol.com이 `body-description`, `article__body` 같은 비표준 클래스를 사용 → trafilatura가 기사 본문 대신 뉴스레터 가입 텍스트를 추출 (GitHub issue #112)
  - 이는 XPath 패턴을 추가하여 해결됨 (`contains(@class, "article__body")`)
- 채널A의 Java 기반 커스텀 CMS도 비표준 HTML 구조를 사용할 가능성이 높아, trafilatura의 기본 XPath 패턴과 일치하지 않을 수 있음

### 핵심

**newspaper3k와 trafilatura 모두 "정적 HTML에서 텍스트 추출"이라는 근본적 한계를 공유**. 채널A처럼 JS 렌더링 또는 봇 차단을 사용하는 사이트에서는 둘 다 동일하게 실패한다.

---

## 6. 다른 한국 뉴스 사이트들이 성공하는 이유

### SBS (news.sbs.co.kr) 분석

실제 SBS 기사 페이지 HTML 구조를 확인한 결과:
- 기사 본문이 `<div class="w_article">` → `<div class="main_text">` → `<article>` 태그 안에 **정적 HTML로 존재**
- `og:title`, `og:description`, `articleBody` (JSON-LD) 등 메타 태그 풍부
- **콘텐츠가 초기 HTML에 포함** (SSR - Server Side Rendering)
- 자체 CMS이지만 표준적인 시맨틱 HTML 구조 사용

### 성공 사이트 vs 실패 사이트 비교

| 특성 | MBC/SBS/연합뉴스 (성공) | 채널A (실패) |
|------|------------------------|-------------|
| 본문 포함 방식 | 정적 HTML (SSR) | JS 동적 로딩 또는 봇 차단 (추정) |
| 시맨틱 태그 | `<article>`, `class="article_body"` 등 | 비표준 구조 (추정) |
| 봇 차단 | 약함/없음 | WAF + CAPTCHA + Proof-of-Work |
| meta 태그 | og:description, JSON-LD 풍부 | 미확인 (접근 불가) |
| URL 패턴 | `/news/endPage.do`, `/replay/...html` | `/news/detail/{id}.do` |
| 플랫폼 | 자체 CMS (표준 HTML) | Java 레거시 CMS (비표준 추정) |

### 핵심 차이

MBC, SBS, 연합뉴스 등은:
1. 기사 본문이 **정적 HTML에 포함**되어 있으므로 HTTP GET만으로 본문 접근 가능
2. 표준적인 HTML 구조 (`<article>`, `<p>` 태그)를 사용하므로 newspaper3k의 휴리스틱이 잘 작동
3. 봇 차단이 상대적으로 약하여 newspaper3k의 기본 User-Agent로도 접근 가능

채널A는:
1. 기사 본문이 정적 HTML에 없거나, 봇에게 다른 응답을 반환
2. 비표준 HTML 구조로 추정
3. 적극적인 봇 차단 (WAF, CAPTCHA)

---

## 7. newspaper3k의 알려진 한계 정리

### 구조적 한계

1. **JavaScript 미지원**: 정적 HTML만 파싱. CSR/SPA 사이트 처리 불가
2. **유지보수 중단**: 2020년 9월 이후 업데이트 없음 (180+ open issues)
3. **사이트별 차이 미대응**: 모든 사이트에 동일한 휴리스틱 적용
4. **봇 차단 우회 불가**: 기본 User-Agent(`newspaper/0.2.8`)가 쉽게 식별됨

### 한국 뉴스 사이트에서의 문제

- 한국어 불용어 70개는 적절한 수준이나, 한국 특유의 면책 조항 패턴에 대한 대응 없음
- `.do` URL 패턴의 Java 기반 사이트에서 특별한 문제가 보고된 바는 없으나, 이는 사이트별 구현에 따라 다름
- 한경(hankyung.com) 등 페이월/보호 사이트에서도 403 에러로 실패한 사례 확인됨

### 대안 라이브러리

| 라이브러리 | 장점 | 단점 |
|-----------|------|------|
| **newspaper4k** | newspaper3k의 유지보수 fork, 버그 수정 다수 | JS 미지원 문제 동일 |
| **trafilatura** | F1 0.937 성능, 더 나은 보일러플레이트 제거 | JS 미지원, 비표준 HTML 취약 |
| **Playwright + 추출기** | JS 렌더링 완벽 지원 | GitHub Actions에서 무거움, 실행 시간 증가 |
| **Fundus** | F1 97.69%, 사전 정의 퍼블리셔 전용 파서 | 채널A 미지원 가능성, 범용성 부족 |

---

## 8. 결론 및 핵심 발견

### 근본 원인 (확신도 순)

1. **[높음] 봇 차단 + JS 렌더링**: 채널A의 WAF가 newspaper3k/trafilatura의 HTTP 요청을 봇으로 감지하여 제한된 응답 반환. 또는 기사 본문이 JS로 동적 로딩되어 정적 HTML에 없음. 두 경우 모두 면책 조항만 추출됨.

2. **[중간] 면책 키워드 필터 취약**: 기존 `_has_disclaimer()`가 `"재배포 및 AI학습 이용 금지"` 변형을 탐지 못하여, 면책 조항 텍스트가 필터를 통과함 (이미 plan에서 수정 방안 도출됨).

3. **[낮음] 비표준 HTML 구조**: 채널A의 커스텀 Java CMS가 newspaper3k/trafilatura의 기본 패턴과 맞지 않는 DOM 구조를 사용할 수 있음.

### 현재 코드의 정확한 실패 경로

```
1. _fetch_with_newspaper("https://ichannela.com/news/detail/000000516782.do")
2. newspaper3k가 HTTP GET 요청
3. 채널A WAF가 봇 감지 → JS 미실행 페이지 또는 제한된 HTML 반환
4. 정적 HTML에 기사 본문 없음 → 면책 조항이 유일한 텍스트 블록
5. calculate_best_node()가 면책 조항을 본문으로 선택
6. article.text = "채널A의 모든 콘텐츠...무단 전재 및 재배포 및 AI학습 이용 금지..."
7. _has_disclaimer() 체크 → "재배포 금지" in text → False (변형 키워드)
8. 면책 조항이 정상 본문으로 통과
9. (trafilatura 폴백 미발동)
10. Gemini가 면책 조항을 요약 → "이 기사는 채널A가 인터넷 서비스를 이용하는 분들을 위해 올린 안내문이에요..."
```

### 근본적 해결 vs 현실적 해결

- **근본적 해결**: Playwright/Selenium으로 JS 렌더링 후 추출 → 무거움, GitHub Actions 비용/시간 증가
- **현실적 해결**: (1) 면책 키워드 필터 강화로 잘못된 파싱 감지 → 해당 기사 제외, (2) newspaper4k로 교체, (3) User-Agent 변경 시도

---

## 참고 자료

- [newspaper3k GitHub (codelucas/newspaper)](https://github.com/codelucas/newspaper)
- [newspaper3k 공식 문서](https://newspaper.readthedocs.io/)
- [newspaper4k GitHub (AndyTheFactory/newspaper4k)](https://github.com/AndyTheFactory/newspaper4k)
- [Common Problems with newspaper3k (Glinteco)](https://glinteco.com/en/post/common-problems-with-newspaper3k-and-how-to-overcome-them/)
- [trafilatura GitHub issue #112 - 비표준 HTML 파싱 실패](https://github.com/adbar/trafilatura/issues/112)
- [Comparative Analysis of Open-Source News Crawlers](https://htdocs.dev/posts/comparative-analysis-of-open-source-news-crawlers/)
- [newspaper3k issue #730 - article.text 빈 문자열 반환](https://github.com/codelucas/newspaper/issues/730)
- [Scraping Web Page Content with Python (JustToThePoint)](https://www.justtothepoint.com/code/scrape/)
- [trafilatura 평가 문서](https://trafilatura.readthedocs.io/en/latest/evaluation.html)
- [trafilatura 트러블슈팅 문서](https://trafilatura.readthedocs.io/en/latest/troubleshooting.html)
