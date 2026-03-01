# 리서치: 파싱 불가 사이트를 확실히 감지해서 건너뛰는 방법

> 작성일: 2026-03-01

---

## 목차
1. [현재 구현과 한계](#1-현재-구현과-한계)
2. [접근법 1: 텍스트 품질 기반 감지 (통계적 휴리스틱)](#2-접근법-1-텍스트-품질-기반-감지-통계적-휴리스틱)
3. [접근법 2: 헤드라인-본문 관련성 체크](#3-접근법-2-헤드라인-본문-관련성-체크)
4. [접근법 3: HTML 응답 자체 검증](#4-접근법-3-html-응답-자체-검증)
5. [접근법 4: newspaper3k/trafilatura 내부 신뢰도 활용](#5-접근법-4-newspaper3ktrafilatura-내부-신뢰도-활용)
6. [접근법 5: 블랙리스트/화이트리스트](#6-접근법-5-블랙리스트화이트리스트)
7. [접근법 6: 기존 라이브러리/도구의 품질 기능](#7-접근법-6-기존-라이브러리도구의-품질-기능)
8. [종합 비교 및 MVP 추천](#8-종합-비교-및-mvp-추천)
9. [참고 자료](#9-참고-자료)

---

## 1. 현재 구현과 한계

### 현재 코드 (`summarizer.py`)

```python
DISCLAIMER_KEYWORDS = {"무단 전재", "재배포 금지", "이용약관", "저작권자", "Copyright"}

def _has_disclaimer(text: str) -> bool:
    """면책 조항 키워드가 2개 이상 포함되면 파싱 실패로 판정."""
    if not text:
        return True
    matches = sum(1 for kw in DISCLAIMER_KEYWORDS if kw in text)
    return matches >= 2
```

### 파싱 체인 흐름

```
newspaper3k 시도 → 텍스트 추출
  ↓ _has_disclaimer 체크
  ├─ True (불량) → trafilatura 폴백
  └─ False (통과) → 본문으로 사용

trafilatura 시도 → 텍스트 추출
  ↓ _has_disclaimer 체크
  ├─ True (불량) → 빈 문자열 반환 → 기사 스킵
  └─ False (통과) → 본문으로 사용
```

### 한계점

| 한계 | 설명 | 실제 사례 |
|------|------|----------|
| **부분 매칭 실패** | `"재배포 금지"`는 `"재배포 및 AI학습 이용 금지"`에 매칭 안 됨 | 채널A 면책 조항이 필터 통과 |
| **키워드 변형 대응 불가** | 새로운 면책 문구가 나올 때마다 키워드 추가 필요 | "무단 복제", "전재·배포 금지" 등 |
| **False Negative** | 면책 조항이 아닌 쓰레기 텍스트 감지 불가 | 로그인 페이지, CAPTCHA 페이지, 네비게이션 텍스트 |
| **False Positive 위험** | 정상 기사에 면책 조항이 포함될 수 있음 | 저작권 관련 뉴스 보도 |
| **구조적 한계** | 텍스트 품질 자체를 판단하지 않음 | 짧은 쓰레기 텍스트도 키워드 없으면 통과 |

---

## 2. 접근법 1: 텍스트 품질 기반 감지 (통계적 휴리스틱)

### 핵심 아이디어

키워드에 의존하지 않고, 추출된 텍스트의 **통계적 특성**만으로 "이것이 뉴스 기사 본문인가?"를 판별한다.

### 한국어 뉴스 기사의 일반적 특성

학술 데이터나 공식 통계는 부족하지만, 경험적으로 한국어 뉴스 기사는 다음 특성을 보인다:

| 지표 | 정상 기사 (추정) | 파싱 실패 텍스트 (추정) |
|------|----------------|----------------------|
| **전체 길이** | 500~5,000자 | 50~300자 |
| **문장 수** | 5~30문장 | 1~5문장 |
| **평균 문장 길이** | 20~60자 | 불규칙 (매우 짧거나 매우 긺) |
| **문장 종결어미** | `~다.`, `~했다.`, `~이다.` 등 | 명사형 종결, 불완전 문장 |
| **줄바꿈 패턴** | 문단 구분 있음 | 줄바꿈 없거나 과도 |

### 구현 가능한 휴리스틱 지표

#### 2-1. 최소 텍스트 길이 (가장 단순)

```
IF len(text) < 200자:
    → 파싱 실패로 판정
```

- **장점**: 구현 0줄, 면책 조항/네비게이션 텍스트 대부분 걸러냄
- **단점**: 속보 등 매우 짧은 기사가 False Positive 될 수 있음
- **현실**: 200자 미만 정상 기사는 매우 드묾. trafilatura의 기본 `MIN_EXTRACTED_SIZE`도 250자

#### 2-2. 문장 수 체크

```
문장 수 = text.count('.') + text.count('다.') 등으로 근사
IF 문장 수 < 3:
    → 파싱 실패 의심
```

- 한국어 문장 끝 패턴: `다.`, `요.`, `까.`, `죠.` 등
- **장점**: 면책 조항은 보통 1~2문장이므로 효과적
- **단점**: 정확한 한국어 문장 분리는 복잡 (`.`이 약어에도 쓰임)

#### 2-3. 텍스트 밀도 비율

```
"텍스트 내 고유 단어 수 / 전체 단어 수" 비율
정상 기사: 다양한 어휘 → 비율 높음
쓰레기 텍스트: 반복적 → 비율 낮음
```

- **장점**: 이용약관 같은 반복적 텍스트 감지에 효과적
- **단점**: 단어 분리가 한국어에서는 공백 기준으로만 가능 (형태소 분석 없이)

#### 2-4. 복합 점수 (권장)

여러 지표를 조합한 품질 점수:

```
quality_score = 0
IF len(text) >= 200: quality_score += 1
IF len(text) >= 500: quality_score += 1
IF 문장 수 >= 3: quality_score += 1
IF 문장 수 >= 5: quality_score += 1
IF 평균 문장 길이 in (15~80자): quality_score += 1

IF quality_score < 3: → 불량 판정
```

### 평가

| 항목 | 평가 |
|------|------|
| **구현 복잡도** | 낮음 (순수 Python, 외부 의존성 없음) |
| **False Positive** | 중간 (매우 짧은 속보에서 발생 가능) |
| **False Negative** | 낮음 (대부분의 쓰레기 텍스트는 짧고 구조가 다름) |
| **유지보수** | 매우 낮음 (임계값 조정만 필요) |
| **MVP 적합도** | **매우 높음** — 가장 먼저 도입해야 할 방어선 |
| **키워드 의존** | 없음 |

---

## 3. 접근법 2: 헤드라인-본문 관련성 체크

### 핵심 아이디어

RSS에서 이미 `headline`을 알고 있으므로, 추출된 텍스트가 해당 헤드라인과 **의미적으로 관련**이 있는지 확인한다. 면책 조항이나 로그인 페이지 텍스트는 어떤 뉴스 제목과도 관련이 없을 것이다.

### 방법 A: 단순 키워드 오버랩

```
headline 단어 = {"윤석열", "대통령", "탄핵", "헌재"}
body 단어 = {본문에서 추출한 단어 집합}
overlap = len(headline 단어 & body 단어) / len(headline 단어)

IF overlap < 0.3: → 파싱 실패 의심
```

- **장점**: 외부 의존성 없음, 구현 매우 간단, 빠름
- **단점**: 한국어 조사 문제 ("윤석열" vs "윤석열의", "윤석열이"), 제목이 은유적인 경우 실패
- **한국어 특수성**: 공백 기반 토큰화 시 조사가 붙어있어 매칭이 안 될 수 있음 → "윤석열" in body_text 방식이 더 적절

### 방법 B: TF-IDF + 코사인 유사도

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

vectorizer = TfidfVectorizer()
tfidf = vectorizer.fit_transform([headline, body_text])
similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]

IF similarity < threshold: → 파싱 실패 의심
```

- **장점**: 통계적으로 더 견고, sklearn만으로 구현 가능
- **단점**: sklearn 의존성 추가, 임계값 튜닝 필요, 제목이 짧아서 TF-IDF가 불안정
- **성능**: 기사 10개 기준 무시할 수준 (<100ms 전체)

### 방법 C: Gemini API 활용

```
프롬프트: "다음 텍스트가 '{headline}'이라는 뉴스 기사의 본문인지 판단하세요.
          YES/NO만 답하세요."
```

- **장점**: 가장 정확한 판단 가능, 문맥/의미 이해
- **단점**: API 호출 추가 비용 (기사당 ~$0.001), 요약 전에 검증 호출 = 파이프라인 지연, Rate limit 소비 증가
- **트레이드오프**: 이미 요약에 Gemini를 쓰고 있으므로, 요약 프롬프트에 "본문이 기사 내용이 아니면 'INVALID'를 반환하라"는 지시를 추가하는 것이 더 효율적

### 방법 D: 요약 프롬프트에 검증 통합 (가장 효율적)

```
기존 SUMMARY_PROMPT에 추가:
"만약 아래 본문이 뉴스 기사 내용이 아니라 면책 조항, 이용약관, 로그인 페이지 등이면
 '[[INVALID]]'만 출력하세요."
```

- **장점**: 추가 API 호출 없음, Gemini가 의미 기반 판단, 가장 높은 정확도 기대
- **단점**: 프롬프트 안정성에 의존 (Gemini가 항상 INVALID를 제대로 반환하는지), 프롬프트 길이 증가
- **주의**: 요약 생성 실패 시의 폴백 로직 필요

### 평가

| 항목 | 키워드 오버랩 | TF-IDF | Gemini 별도 호출 | 프롬프트 통합 |
|------|-------------|--------|----------------|-------------|
| **구현 복잡도** | 매우 낮음 | 낮음 | 낮음 | 매우 낮음 |
| **정확도** | 중간 | 중상 | 높음 | 높음 |
| **추가 비용** | 없음 | 없음 | API 호출당 ~$0.001 | 없음 |
| **추가 지연** | 없음 | <100ms | 1~3초/기사 | 없음 |
| **유지보수** | 낮음 | 낮음 | 낮음 | 낮음 |
| **MVP 적합도** | 높음 | 중간 | 낮음 | **매우 높음** |

---

## 4. 접근법 3: HTML 응답 자체 검증

### 핵심 아이디어

텍스트 추출 **전에** HTTP 응답과 HTML 자체를 검증하여, 파싱 시도 자체를 건너뛴다.

### 3-1. HTTP Status Code 확인

현재 `_fetch_with_newspaper()`는 newspaper3k 내부에서 HTTP 요청을 하므로 status code에 직접 접근하기 어렵다. 별도 requests 호출이 필요하다.

```
403 Forbidden → 봇 차단, 접근 거부
503 Service Unavailable → 서버 과부하 또는 봇 차단
301/302 → 리다이렉트 (로그인 페이지 등으로)
200 → 정상 (하지만 내용이 쓰레기일 수 있음)
```

- **장점**: 가장 확실한 차단 감지 (403/503)
- **단점**: 채널A처럼 200 OK를 반환하면서 쓰레기 내용을 주는 경우 감지 불가
- **현실**: 봇 차단 사이트 중 상당수가 200을 반환하면서 CAPTCHA/차단 페이지를 보냄

### 3-2. Content-Type 확인

```
Content-Type: text/html → 정상 (하지만 내용은 확인 필요)
Content-Type: application/json → API 응답일 수 있음
Content-Type 없음 → 비정상
```

- **실용성**: 낮음. 대부분의 사이트가 text/html을 반환

### 3-3. HTML 구조 검증

```
1. <article> 태그 존재 여부
2. og:description meta 태그 존재 여부
3. JSON-LD (schema.org/NewsArticle) 존재 여부
4. <meta name="robots" content="noindex"> 존재 여부 → 차단 페이지 신호
```

- **장점**: 기사 페이지 vs 비기사 페이지 구분에 효과적
- **단점**: 한국 레거시 사이트는 시맨틱 태그를 안 쓸 수 있음, HTML 파싱이 추가로 필요
- **활용**: `og:description`이 존재하면 본문 추출 없이도 요약 가능한 최소 정보를 확보

### 3-4. 봇 차단 페이지 패턴 감지

```python
BOT_BLOCK_PATTERNS = [
    "captcha",
    "challenge",
    "cf-browser-verification",  # Cloudflare
    "please verify you are a human",
    "access denied",
    "just a moment",  # Cloudflare challenge page
]

def _is_blocked_page(html: str) -> bool:
    html_lower = html.lower()
    return any(pattern in html_lower for pattern in BOT_BLOCK_PATTERNS)
```

- **장점**: Cloudflare/WAF 차단 페이지를 HTML 수준에서 감지
- **단점**: 한국어 봇 차단 메시지 패턴 추가 필요, newspaper3k가 내부적으로 HTML을 다운로드하므로 HTML에 직접 접근하려면 별도 요청 필요

### 3-5. Response 헤더 기반 감지

```
Server: cloudflare → Cloudflare 보호 사이트
X-Robots-Tag: noindex → 차단 가능성
Set-Cookie: __cf_bm → Cloudflare Bot Management
```

- **실용성**: 보조 신호로 유용하지만 단독으로는 부족

### 평가

| 항목 | 평가 |
|------|------|
| **구현 복잡도** | 중간 (별도 HTTP 요청 필요, HTML 파싱) |
| **False Positive** | 낮음 |
| **False Negative** | 높음 (200 OK + 쓰레기 내용은 감지 못 함) |
| **유지보수** | 중간 (봇 차단 패턴 업데이트 필요) |
| **MVP 적합도** | **중간** — Status code 체크만 하면 간단, HTML 구조 검증은 오버엔지니어링 |
| **핵심 한계** | 200 OK를 반환하는 봇 차단 사이트에서는 무용 |

---

## 5. 접근법 4: newspaper3k/trafilatura 내부 신뢰도 활용

### 5-1. newspaper3k

newspaper3k는 **품질 점수나 신뢰도 지표를 제공하지 않는다**.

활용 가능한 신호:
- `article.text`가 빈 문자열 → 추출 실패 (현재 이미 체크 중)
- `article.title`, `article.authors`, `article.publish_date` 등 메타데이터 존재 여부 → 보조 신호
- `article.is_valid_url()` → URL 유효성만 체크, 콘텐츠 품질과 무관

**한계**: newspaper3k는 2020년 이후 유지보수 중단. 새 기능 추가 가능성 없음.

### 5-2. trafilatura

trafilatura는 newspaper3k보다 더 많은 신호를 제공한다.

#### `extract()` 반환값

- `None` 반환 → 추출 실패 (현재 이미 체크 중: `trafilatura.extract(downloaded) or ""`)
- 문자열 반환 → 추출 성공 (하지만 품질은 미보장)

#### `bare_extraction()` 활용

`bare_extraction()`은 딕셔너리를 반환하며, 메타데이터를 포함한다:

```python
result = trafilatura.bare_extraction(downloaded, with_metadata=True)
# result = {
#     'text': '...',          # 추출된 본문
#     'title': '...',         # 페이지 제목
#     'author': '...',        # 저자
#     'date': '...',          # 발행일
#     'url': '...',           # URL
#     'hostname': '...',      # 호스트명
#     'description': '...',   # meta description
#     'categories': '...',    # 카테고리
#     'tags': '...',          # 태그
#     'comments': '...',      # 댓글
#     ...
# }
```

활용 가능한 품질 신호:
- `result['text']`의 길이 → 최소 길이 체크
- `result['title']`이 존재하는지 → 페이지 메타데이터 품질
- `result['date']`이 존재하는지 → 뉴스 기사는 대체로 날짜가 있음

#### `favor_precision` 모드

```python
text = trafilatura.extract(downloaded, favor_precision=True)
```

- precision 모드에서는 확실하지 않은 텍스트 블록을 제외
- 면책 조항처럼 본문과 동떨어진 텍스트가 제외될 가능성이 높아짐
- **하지만**: 봇 차단으로 HTML에 본문 자체가 없는 경우, precision 모드도 쓰레기를 반환하거나 None 반환

#### `MIN_EXTRACTED_SIZE` 설정 커스터마이징

```python
from trafilatura.settings import use_config

my_config = use_config()
my_config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "300")  # 기본 250에서 상향
my_config.set("DEFAULT", "MIN_OUTPUT_SIZE", "200")      # 기본 1에서 상향

text = trafilatura.extract(downloaded, config=my_config)
```

- `MIN_EXTRACTED_SIZE`를 올리면, 짧은 쓰레기 텍스트가 추출 기준 미달로 None 반환
- **주의**: 기본값 250은 이미 상당히 높은 편. 300~500으로 올리면 짧은 속보 기사도 누락 가능

#### `is_probably_readerable()` 활용

```python
from trafilatura.readability_lxml import is_probably_readerable

html = trafilatura.fetch_url(url)
if html and is_probably_readerable(html):
    text = trafilatura.extract(html)
else:
    text = ""  # 추출 시도 자체를 건너뜀
```

- Mozilla Readability.js에서 포팅된 함수 (trafilatura 1.10+)
- HTML을 사전 검사하여 "이 페이지에 추출할 만한 메인 텍스트가 있는가?"를 추정
- **장점**: 추출 전에 차단 페이지/빈 페이지를 걸러낼 수 있음
- **한계**: HTML 수준 판단이므로, HTML에 면책 조항이 "메인 텍스트"처럼 보이면 True 반환

### 5-3. newspaper4k (newspaper3k의 유지보수 fork)

[newspaper4k](https://github.com/AndyTheFactory/newspaper4k)는 newspaper3k의 활발히 유지보수되는 fork이다.

개선점:
- 기사 본문 감지 로직 개선 (`<article>`, `<div>` 태그를 콘텐츠 부모 노드 후보에 추가)
- 문단 순서 보정
- 버그 수정 다수
- Python 3.10+ 지원 강화

**하지만**: 품질 점수나 신뢰도 지표는 여전히 제공하지 않음. JS 미지원 문제도 동일.

### 평가

| 항목 | 평가 |
|------|------|
| **구현 복잡도** | 낮음~중간 |
| **추가 신호** | `bare_extraction` 메타데이터, `is_probably_readerable`, `MIN_EXTRACTED_SIZE` 조정 |
| **정확도 향상** | 중간 (근본적 해결은 아님) |
| **유지보수** | 낮음 |
| **MVP 적합도** | **높음** — `favor_precision`, `MIN_EXTRACTED_SIZE` 조정은 설정만 바꾸면 됨 |

---

## 6. 접근법 5: 블랙리스트/화이트리스트

### 6-1. 도메인 블랙리스트

```python
UNPARSEABLE_DOMAINS = {
    "ichannela.com",   # 채널A: WAF + JS 렌더링
    # 향후 추가...
}

def _is_blacklisted(url: str) -> bool:
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "")
    return domain in UNPARSEABLE_DOMAINS
```

- **장점**: 100% 확실한 감지, 구현 매우 간단, 쓸데없는 HTTP 요청 자체를 방지
- **단점**: 수동 관리 필요, 새로운 파싱 불가 사이트를 사전에 알 수 없음, 사이트가 나중에 고쳐져도 블랙리스트에 남음
- **현실**: MVP에서 가장 확실한 즉시 해결책. 채널A 같은 "이미 확인된" 실패 사이트에 즉시 적용 가능

### 6-2. 도메인 화이트리스트

```python
PARSEABLE_DOMAINS = {
    "news.sbs.co.kr",
    "imnews.imbc.com",
    "www.yna.co.kr",
    # ...
}
```

- **장점**: 가장 안전한 접근 (검증된 사이트만 파싱)
- **단점**: Google News RSS가 반환하는 모든 도메인을 미리 등록해야 함, 새 언론사 기사가 자동으로 제외됨
- **현실**: MVP에서 비현실적. Google News에서 수십 개 언론사가 등장하므로 유지 불가

### 6-3. 자동 블랙리스트 갱신

```
파싱 실패가 동일 도메인에서 N회 이상 발생 → 자동 블랙리스트 추가
```

- **장점**: 수동 관리 부담 감소
- **단점**: 상태 저장 필요 (파일/DB), 일시적 장애와 영구 차단 구분 어려움
- **구현 복잡도**: 중간 (카운터 + 영속 저장)

### 평가

| 항목 | 블랙리스트 | 화이트리스트 | 자동 블랙리스트 |
|------|----------|------------|---------------|
| **구현 복잡도** | 매우 낮음 | 낮음 | 중간 |
| **확실성** | 100% | 100% | 높음 |
| **유지보수** | 수동 추가 필요 | 모든 도메인 등록 필요 | 낮음 |
| **새 사이트 대응** | 불가 | 불가 | 자동 |
| **MVP 적합도** | **높음** (이미 알려진 사이트) | 낮음 | 중간 (Phase 2) |

---

## 7. 접근법 6: 기존 라이브러리/도구의 품질 기능

### 7-1. jusText — 보일러플레이트 감지 전문 도구

[jusText](https://github.com/miso-belica/jusText)는 HTML 페이지에서 보일러플레이트를 제거하는 휴리스틱 기반 도구이다.

**알고리즘 요약** (jusText의 텍스트 블록 분류):

1. HTML을 블록 단위로 분할
2. 각 블록에 대해 3가지 지표 계산:
   - **링크 밀도**: `<a>` 태그 문자 비율 (>0.2이면 bad)
   - **불용어 밀도**: 기능어 비율 (>0.32이면 good 후보)
   - **길이**: 문자 수 (<70이면 short)
3. 컨텍스트 기반 재분류: short/near-good 블록을 주변 블록 기반으로 판정

**FactLens에 적용 가능성**:
- jusText를 파싱 결과 검증에 사용하기보다는, trafilatura가 이미 유사한 로직을 내장하고 있음
- 별도로 jusText를 도입하면 의존성만 추가되고, trafilatura의 `favor_precision`과 기능이 중복
- **결론**: MVP에서 별도 도입 가치 낮음

### 7-2. Fundus — 퍼블리셔별 맞춤 파서

[Fundus](https://github.com/flairNLP/fundus) (ACL 2024 발표)는 뉴스 스크래핑에 특화된 프레임워크이다.

**핵심 차별점**:
- 각 언론사별로 **수동으로 작성된 맞춤 파서** 사용
- CSS 셀렉터, XPath를 사이트별로 최적화
- 벤치마크 결과: F1 97.69% (trafilatura 89.81% 대비)
- `Article.exception` 속성으로 추출 실패를 프로그래밍적으로 감지 가능

**한국 언론사 지원 여부**:
- Fundus는 주로 영어권/유럽 언론사를 지원
- 한국 언론사 파서는 현재 포함되지 않은 것으로 보임
- 한국 언론사 파서를 직접 작성해서 기여할 수는 있으나, MVP 범위를 벗어남

**결론**: MVP에서 도입 비현실적. 장기적으로 한국 언론사 파서가 추가되면 가치 있음

### 7-3. readability-lxml

[readability-lxml](https://pypi.org/project/readability-lxml/)은 Mozilla Readability의 Python 포팅이다.

- 벤치마크: F1 0.922 (trafilatura와 유사 수준)
- 처리 속도: 450 pages/sec
- **품질 점수 없음** — 추출 결과만 반환
- trafilatura가 이미 readability 로직을 내장하고 있으므로 (`is_probably_readerable` 등) 별도 도입 불필요

### 7-4. goose3

[goose3](https://github.com/goose3/goose3)는 newspaper3k와 유사한 휴리스틱 기반 추출기이다.

- 벤치마크: F1 0.896
- 특징: **가장 높은 precision** (정확하지만 recall이 낮음)
- **품질 점수 없음**
- trafilatura보다 성능이 낮고, 속도도 느림
- **결론**: 추가 도입 가치 없음

### 7-5. pyplexity — 퍼플렉시티 기반 보일러플레이트 감지

[pyplexity](https://github.com/citiususc/pyplexity)는 언어 모델의 **perplexity** (당혹도)를 활용하여 보일러플레이트를 감지한다.

- 원리: 보일러플레이트 텍스트는 반복적이고 예측 가능 → 낮은 perplexity, 뉴스 본문은 다양한 내용 → 상대적으로 높은 perplexity
- **장점**: 키워드 무관, 언어 독립적
- **단점**: 언어 모델 필요 (무거움), 한국어 모델 필요, MVP에 과도
- **결론**: 흥미로운 접근이지만 MVP 범위 밖

### 종합 평가

| 라이브러리 | 품질 지표 제공 | 한국어 지원 | MVP 도입 가치 |
|-----------|-------------|-----------|-------------|
| jusText | 블록 분류 (good/bad/short) | 불용어 리스트 필요 | 낮음 (trafilatura와 중복) |
| Fundus | exception 속성 | 한국 언론사 미지원 | 낮음 (장기적으로 가치) |
| readability-lxml | 없음 | 있음 | 낮음 (trafilatura 내장) |
| goose3 | 없음 | 있음 | 없음 |
| pyplexity | perplexity 점수 | 한국어 모델 필요 | 없음 (과도) |

---

## 8. 종합 비교 및 MVP 추천

### 접근법별 종합 비교

| 접근법 | 구현 복잡도 | 감지 정확도 | 유지보수 | 추가 비용 | MVP 적합도 |
|--------|-----------|-----------|---------|----------|-----------|
| 1. 텍스트 품질 휴리스틱 | **매우 낮음** | 중상 | 매우 낮음 | 없음 | **최상** |
| 2-A. 키워드 오버랩 | 매우 낮음 | 중간 | 낮음 | 없음 | 높음 |
| 2-D. 프롬프트 통합 검증 | **매우 낮음** | **높음** | 낮음 | 없음 | **최상** |
| 3. HTML 응답 검증 | 중간 | 중간 | 중간 | 없음 | 중간 |
| 4. trafilatura 설정 조정 | **매우 낮음** | 중간 | 매우 낮음 | 없음 | **높음** |
| 5. 도메인 블랙리스트 | **매우 낮음** | 100% (알려진 사이트) | 수동 | 없음 | **높음** |
| 6. 외부 라이브러리 | 높음 | 다양 | 중간~높음 | 다양 | 낮음 |

### MVP 추천: 다층 방어 전략

MVP에서는 다음 **4가지를 조합**하는 것을 추천한다. 각각 구현이 매우 간단하면서도, 조합하면 거의 모든 파싱 실패를 감지할 수 있다.

#### Layer 1: 도메인 블랙리스트 (즉시 차단)

- 이미 확인된 파싱 불가 도메인을 블랙리스트로 관리
- HTTP 요청 자체를 방지하여 시간/리소스 절약
- `ichannela.com` 등 즉시 등록

#### Layer 2: 텍스트 품질 휴리스틱 (통계 기반 1차 필터)

- 추출된 텍스트의 길이, 문장 수로 기본 품질 검증
- 임계값 예시: `최소 200자 AND 최소 3문장`
- 키워드와 무관하게 작동 → 미지의 쓰레기 텍스트도 감지

#### Layer 3: 키워드 매칭 강화 (기존 방어선 보완)

- 기존 `DISCLAIMER_KEYWORDS`를 부분 매칭으로 변경
- `"재배포 금지"` → `"재배포"`로 완화하여 변형 대응
- 키워드 추가: `"무단 복제"`, `"전재·배포"`, `"AI학습"` 등

#### Layer 4: Gemini 프롬프트 통합 검증 (최종 방어선)

- 요약 프롬프트에 "본문이 기사가 아니면 `[[INVALID]]` 반환" 지시 추가
- 추가 API 호출 없이 의미 기반 검증
- Layer 1~3을 통과한 교묘한 쓰레기 텍스트의 최종 방어선

### 추천 구현 우선순위

```
1순위: Layer 2 (텍스트 품질 휴리스틱) + Layer 3 (키워드 강화)
       → _has_disclaimer()를 _is_valid_article_text()로 리팩터링
       → 길이/문장 수 체크 + 개선된 키워드 매칭

2순위: Layer 1 (도메인 블랙리스트)
       → UNPARSEABLE_DOMAINS set + URL 체크 함수

3순위: Layer 4 (프롬프트 통합 검증)
       → SUMMARY_PROMPT_TEMPLATE에 INVALID 반환 조건 추가
       → _generate_summary() 반환값에서 [[INVALID]] 체크

향후: trafilatura 설정 조정 (favor_precision, MIN_EXTRACTED_SIZE)
      자동 블랙리스트 갱신
```

### trafilatura 설정 조정 (보조)

현재 코드에서 trafilatura 사용 부분도 개선 가능:

```python
# 현재
text = trafilatura.extract(downloaded) or ""

# 개선안
from trafilatura.settings import use_config
my_config = use_config()
my_config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "300")
my_config.set("DEFAULT", "MIN_OUTPUT_SIZE", "150")
text = trafilatura.extract(downloaded, favor_precision=True, config=my_config) or ""
```

이것만으로도 짧은 쓰레기 텍스트가 None으로 반환되어 자연스럽게 필터링된다.

### 예상 효과

| 시나리오 | 현재 | 개선 후 |
|---------|------|--------|
| 채널A 면책 조항 | 통과 (False Negative) | Layer 1(블랙리스트) 또는 Layer 2(짧음) 또는 Layer 3(키워드)에서 차단 |
| CAPTCHA/로그인 페이지 | 통과 가능 | Layer 2(짧거나 문장 부족)에서 차단 |
| 새로운 봇 차단 사이트 | 통과 가능 | Layer 2 + Layer 4에서 감지 |
| 정상 기사 | 통과 | 통과 (False Positive 최소화) |
| 짧은 속보 (200자 미만) | 통과 | 일부 누락 가능 → 임계값 조정으로 대응 |

---

## 9. 참고 자료

### 공식 문서
- [trafilatura 공식 문서 — Settings and customization](https://trafilatura.readthedocs.io/en/latest/settings.html)
- [trafilatura 공식 문서 — Core functions](https://trafilatura.readthedocs.io/en/latest/corefunctions.html)
- [trafilatura 공식 문서 — With Python](https://trafilatura.readthedocs.io/en/latest/usage-python.html)
- [trafilatura settings.cfg (GitHub)](https://github.com/adbar/trafilatura/blob/master/trafilatura/settings.cfg)
- [newspaper3k 공식 문서](https://newspaper.readthedocs.io/)
- [newspaper4k GitHub](https://github.com/AndyTheFactory/newspaper4k)
- [newspaper4k API Reference](https://newspaper4k.readthedocs.io/en/latest/user_guide/api_reference.html)

### 라이브러리/도구
- [jusText GitHub](https://github.com/miso-belica/jusText) — 보일러플레이트 감지 알고리즘
- [jusText 알고리즘 상세](https://github.com/miso-belica/jusText/blob/main/doc/algorithm.rst)
- [Fundus GitHub](https://github.com/flairNLP/fundus) — 뉴스 스크래핑 프레임워크
- [readability-lxml (PyPI)](https://pypi.org/project/readability-lxml/)
- [pyplexity GitHub](https://github.com/citiususc/pyplexity) — 퍼플렉시티 기반 보일러플레이트 감지
- [article-extraction-benchmark (ScrapingHub)](https://github.com/scrapinghub/article-extraction-benchmark)

### 논문/벤치마크
- [Fundus: A Simple-to-Use News Scraper Optimized for High Quality Extractions (ACL 2024)](https://aclanthology.org/2024.acl-demos.29/)
- [Boilerplate Detection using Shallow Text Features](https://course.khoury.northeastern.edu/cs6200sp15/extra/07_du/Boilerplate%20Detection%20using%20Shallow%20Text%20Features.pdf)
- [An Evaluation of Main Content Extraction Libraries (SANDIA 2024)](https://www.osti.gov/servlets/purl/2429881)
- [Evaluating scraping and text extraction tools for Python (Barbaresi)](https://adrien.barbaresi.eu/blog/evaluating-text-extraction-python.html)

### 봇 차단/우회 관련
- [How To Bypass Anti-Bots With Python (ScrapeOps)](https://scrapeops.io/python-web-scraping-playbook/python-how-to-bypass-anti-bots/)
- [Error 403 in Web Scraping: 7 Easy Solutions (ZenRows)](https://www.zenrows.com/blog/403-web-scraping)

### 텍스트 유사도
- [Ultimate Guide To Text Similarity With Python (NewsCatcher)](https://www.newscatcherapi.com/blog-posts/ultimate-guide-to-text-similarity-with-python)
- [Cosine Similarity — Text Similarity Metric](https://studymachinelearning.com/cosine-similarity-text-similarity-metric/)

### 프로젝트 내부 참고
- [research-채널A파싱실패.md](./research-채널A파싱실패.md) — 채널A 파싱 실패 근본 원인 분석
- [plan-가독성개선.md](./plan-가독성개선.md) — 키워드 매칭 수정 방안 (`"재배포 금지"` → `"재배포"`)
