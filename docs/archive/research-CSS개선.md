# Research: 모바일 뉴스 브리핑 가독성 및 카드 UI CSS 개선

> 작성일: 2026-03-01
> 목적: factlens.pages.dev 모바일 가독성, 카드 시각적 계층, 섹션 분리를 위한 구체적 CSS 값 리서치

---

## 1. 한국어 모바일 뉴스 타이포그래피

### 1-1. 국내 주요 뉴스 플랫폼 실측 데이터

한국어 모바일 뉴스 타이포그래피 조사 ([출처: lqez.github.io](https://lqez.github.io/blog/hangul-typography-on-mobile-web.html)):

| 사이트 | 본문 크기 | 제목 크기 | 제목/본문 비율 | 본문 line-height |
|--------|-----------|-----------|----------------|------------------|
| 네이버 뉴스 | 17px | 24px | 1.41 | ~1.55 |
| 다음 뉴스 | 17px | 23px | 1.35 | 1.625 |
| 네이트 뉴스 | 17px | 26px | 1.53 | ~1.56 |
| 브런치 | 17.3px | 24px | 1.38 | ~1.7 |
| 퍼블리 | 17px | 32px | 1.88 | 1.8 |
| 미디엄 | 18px | 30px | 1.67 | ~1.7 |

### 1-2. 토스(Toss) 디자인 시스템 타이포그래피 스케일

토스 TDS 타이포그래피 ([출처: toss.tech](https://toss.tech/article/toss-design-system)):

| 스케일 | font-size | line-height | 용도 |
|--------|-----------|-------------|------|
| F11 | 11px | 16.5px (1.5) | 캡션, 라벨 |
| F13 | 13px | 19.5px (1.5) | 보조 텍스트 |
| F16 | 16px | 24px (1.5) | 본문 |
| F20 | 20px | 29px (1.45) | 소제목 |
| F30 | 30px | 40px (1.33) | 제목 |

### 1-3. 핵심 발견 - 한국어(Hangul) 고유 특성

W3C 한국어 텍스트 레이아웃 요구사항 ([출처: w3c.github.io/klreq](https://w3c.github.io/klreq/)):

- **letter-spacing**: 한글 기본은 0. 한글 글자 사이 기본 간격은 0으로 배열하는 것이 원칙. 음수 letter-spacing(-0.3px ~ -1px)은 네이버/다음이 사용하지만, 모바일에서는 가독성을 해칠 수 있으므로 0 또는 미세하게 음수(-0.2px)까지만 권장
- **line-height**: 한글은 글자 블록 구조(2~5개 자모가 하나의 블록으로 조합)로 인해 라틴 문자보다 시각적 밀도가 높음. 따라서 **1.6~1.8 범위**가 최적 (라틴 문자의 1.4~1.5보다 높아야 함)
- **font-weight**: 한글 고딕체는 Regular(400)과 Bold(700) 사이 대비가 라틴 폰트보다 약해보임. 헤드라인에 700~800 사용 시 본문은 반드시 400으로 대비 확보

### 1-4. 구체적 권장값 — 현재값 vs 제안값

| 요소 | 현재 값 | 문제 | 제안 값 |
|------|---------|------|---------|
| **card-headline** | 1.1rem (≈17.6px) | 본문(0.95rem=15.2px)과 크기 차이 미미. 스캔 불가 | **1.25rem (20px)** |
| **card-headline font-weight** | 700 | 적절하나, 본문과 동일 color로 구분 약함 | **800 + color: #000** |
| **card-headline line-height** | 1.5 | OK | **1.4** (제목은 좀 더 타이트하게) |
| **card-summary p font-size** | 0.95rem (15.2px) | 모바일 최소 권장(16px) 미달. 한국 뉴스 사이트 표준(17px)보다 작음 | **1rem (16px)** |
| **card-summary p line-height** | 1.8 | 약간 과도. 문단이 늘어져 보임 | **1.7** (한글 최적 범위) |
| **card-summary p color** | #333 | 약간 연함 | **#222** (더 선명하게) |
| **verification-reason font-size** | 0.85rem (13.6px) | 너무 작아서 읽기 어려움. 중요한 정보인데 묻힘 | **0.9rem (14.4px)** |
| **verification-reason color** | #555 | 본문과 대비 부족 | **#444** |
| **body letter-spacing** | 미지정 (0) | 한글 기본값이므로 OK | **0 또는 -0.1px** (유지) |
| **모바일 headline (@480px)** | 1rem (16px) | 본문과 동일해짐. 계층 완전 소실 | **1.125rem (18px)** |

---

## 2. 카드 디자인 패턴

### 2-1. 카드 외관 — 배경으로부터 분리

현재 문제: `box-shadow: 0 1px 3px rgba(0,0,0,0.08)` — 너무 연해서 카드가 배경과 거의 구분 안 됨.

**Material Design 3 엘리베이션 참고** ([출처: studioncreations.com](https://studioncreations.com/blog/material-design-3-box-shadow-css-values/)):

| 레벨 | box-shadow | 용도 |
|------|-----------|------|
| Level 1 | `0 1px 4px 0 rgba(0,0,0,0.37)` | 기본 카드 |
| Level 2 | `0 2px 2px 0 rgba(0,0,0,0.2), 0 6px 10px 0 rgba(0,0,0,0.3)` | 호버/강조 |

하지만 MD3 그림자는 뉴스 브리핑에 과도할 수 있음. 중간 수준이 적합.

**제안 — 두 가지 방식 조합:**

```css
/* 방식 A: 그림자 강화 */
.news-card {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06),
              0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 방식 B: 그림자 + 미세 보더 (한국 뉴스 앱에서 흔한 패턴) */
.news-card {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.06);
}
```

**방식 B 권장**. 이유:
- 네이버/카카오/토스 모두 카드에 미세한 border를 추가함
- 그림자만으로는 저해상도 모바일에서 구분이 잘 안 됨
- border + 약한 shadow 조합이 모바일에서 가장 선명하게 카드를 분리

### 2-2. 카드 패딩 및 border-radius

| 요소 | 현재 값 | 제안 값 | 근거 |
|------|---------|---------|------|
| **padding (데스크톱)** | 20px | **24px** | 8px 그리드 시스템. 내부 여백이 부족해 텍스트가 답답 |
| **padding (모바일 @480px)** | 16px | **20px** | 16px은 너무 좁음. 20px로 최소 여백 확보 |
| **border-radius** | 12px | **16px** | 토스/네이버 앱 트렌드. 더 부드러운 느낌 |
| **border-radius (모바일)** | 8px | **12px** | 8px은 각져 보임 |
| **margin-bottom (카드 간 간격)** | 16px | **20px** | 카드 간 "숨 쉴 공간" 확보. 8px 그리드 기준 |

### 2-3. 배경색 대비

현재: 카드 `#fff` vs 배경 `#f5f5f5` — 대비가 약함.

**제안:**
```css
body { background-color: #f0f0f0; }  /* #f5f5f5 → #f0f0f0 (약간 더 진하게) */
```

또는 카드와 배경 사이 대비를 높이려면 `#eee`까지도 가능하나, 너무 어두우면 눈이 피로. `#f0f0f0`이 적절한 중간값.

---

## 3. 카드 내부 시각적 계층 (Visual Hierarchy)

### 3-1. 현재 문제 분석

현재 카드 내부 구조: headline → summary → verification tag → reason → evidence toggle → sources
이 모든 요소가 동일한 배경(#fff)에, 구분선 없이, 비슷한 크기 텍스트로 나열됨.

**시각적 계층 원칙** ([출처: eleken.co](https://www.eleken.co/blog-posts/visual-hierarchy-in-ux)):
- 크기 대비: 가장 중요한 요소가 가장 커야 함
- 색상/무게 대비: 무게감(bold vs regular)과 색상으로 중요도 표현
- 공간 분리: 관련 요소는 가까이, 다른 그룹은 떨어뜨려야 함
- 배경색/테두리로 섹션 그룹핑

### 3-2. 섹션 분리 전략 (카드 내부)

**전략: 검증 영역을 배경색으로 그룹핑 + 요약과 검증 사이 구분선**

```
┌─ card ─────────────────────────────────────┐
│  [Headline] ─── 가장 크고 굵게              │
│                                             │
│  [Summary paragraphs] ─── 본문              │
│                                             │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ (구분선) ─ ─ ─ ─   │
│                                             │
│  ┌─ verification zone (배경색) ──────────┐  │
│  │ [Tag badge]                            │  │
│  │ [Verification reason]                  │  │
│  │ [Evidence toggle]                      │  │
│  └────────────────────────────────────────┘  │
│                                             │
│  [원문 보기: publisher pills]               │
└─────────────────────────────────────────────┘
```

**구현 CSS:**

```css
/* 요약과 검증 사이 구분선 */
.card-verification {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;
}

/* 검증 영역 배경 — 방안 A: 태그별 미세 배경 */
.card-verification {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
  margin-top: 16px;
}

/* 원문 보기 섹션 분리 */
.card-sources {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e8e8e8;
}
```

**두 방안 비교:**

| 방안 | 설명 | 장점 | 단점 |
|------|------|------|------|
| A: 구분선(border-top) | 요약↔검증 사이에 `1px solid #e8e8e8` | 심플, 가벼움 | 시각적 임팩트 약함 |
| B: 배경색 변경 | 검증 영역에 `background: #fafafa` + `border-radius: 8px` + `padding: 12px` | 확실한 그룹핑, 검증 영역이 '카드 안의 카드'처럼 보임 | 중첩 느낌이 과할 수 있음 |
| **C: 구분선 + 여백 (권장)** | `border-top: 1px solid #e8e8e8` + `margin-top: 16px` + `padding-top: 16px` | 깔끔하면서도 확실한 분리. 대부분의 뉴스 앱이 사용하는 방식 | - |

**방안 C 권장**. 구분선은 간결하면서 확실한 섹션 분리를 제공하고, 과도한 중첩을 피함.

### 3-3. 검증 태그(Badge) 강화

현재: `font-size: 0.8rem`, `padding: 4px 10px` — 작고 눈에 잘 안 띔.

뉴스 팩트체크에서 검증 태그는 **카드에서 헤드라인 다음으로 중요한 요소**. 사용자가 스캔할 때 가장 먼저 찾는 정보.

**최소 터치 타겟**: 모바일에서 48px 이상 ([출처: thisisglance.com](https://thisisglance.com/learning-centre/how-do-i-create-consistent-visual-hierarchy-in-mobile-apps))

**제안:**

```css
.tag {
  display: inline-block;
  font-size: 0.8rem;       /* 유지 — 뱃지는 작아도 됨 */
  font-weight: 700;         /* 600 → 700 (더 굵게) */
  padding: 6px 14px;        /* 4px 10px → 6px 14px (터치 타겟 확대 + 여백) */
  border-radius: 20px;      /* 6px → 20px (pill shape — 뱃지 느낌 강화) */
  margin-bottom: 10px;      /* 6px → 10px (아래 reason과 여유 확보) */
  letter-spacing: 0.3px;    /* 추가 — 소형 텍스트 가독성 개선 */
}
```

**태그 색상 강화:**

현재 색상이 약함 (pastel 톤). 좀 더 채도를 올려서 시각적 구분력 강화:

```css
/* 현재 → 제안 */
.tag--verified {
  background-color: #d1fae5;   /* #dcfce7 → 약간 더 진한 녹색 */
  color: #065f46;              /* #166534 → 더 진한 녹색 텍스트 */
}

.tag--unconfirmed {
  background-color: #fef3c7;   /* 유지 */
  color: #78350f;              /* #92400e → 더 진한 갈색 */
}

.tag--misleading {
  background-color: #fee2e2;   /* #fecaca → 약간 연하게 (배경) */
  color: #991b1b;              /* 유지 */
  border: 1px solid #fca5a5;   /* 추가 — 위험 신호를 더 강조 */
}
```

### 3-4. 원문 보기(Sources) 섹션 분리

현재: 검증 영역과 원문 보기가 구분 없이 이어짐.

```css
.card-sources {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e8e8e8;
}

.card-sources h4 {
  font-size: 0.8rem;        /* 0.85rem → 0.8rem (캡션 사이즈로 통일) */
  font-weight: 600;
  color: #888;               /* #666 → #888 (보조 정보 느낌 강화) */
  margin-bottom: 8px;        /* 6px → 8px */
  text-transform: uppercase; /* 선택: 영문이면 UPPERCASE로 라벨 느낌 */
}
```

---

## 4. 여백(Spacing)과 숨 쉴 공간(Breathing Room)

### 4-1. 8px 그리드 시스템

Apple HIG, Google Material Design, Toss TDS 모두 8px 기반 그리드를 사용.
모든 여백/패딩 값은 **4, 8, 12, 16, 20, 24, 32, 40, 48** 중 하나를 사용해야 일관성 유지.

([출처: conceptfusion.co.uk](https://www.conceptfusion.co.uk/post/web-design-spacing-and-sizing-best-practices))

### 4-2. 요소별 여백 제안

| 위치 | 현재 값 | 제안 값 | 근거 |
|------|---------|---------|------|
| **카드 간 간격** | 16px | **20px** | 카드가 뭉쳐 보이는 문제 해결. 밀도↓ |
| **카드 내부 패딩** | 20px (모바일: 16px) | **24px (모바일: 20px)** | 텍스트가 카드 테두리에 너무 가까움 |
| **헤드라인 → 요약 간격** | margin-bottom: 12px | **16px** | 헤드라인 아래 더 많은 공간으로 시각적 분리 |
| **요약 문단 간 간격** | margin-bottom: 14px | **12px** | 14px이 과하게 벌어짐. 문단 내 간격은 좁혀도 됨 |
| **요약 → 검증 간격** | 14px | **16px + border-top** | 섹션 전환 포인트 — 구분선과 함께 |
| **검증 태그 → reason 간격** | margin-top: 4px | **8px** | 태그와 이유 사이 여유 확보 |
| **reason → evidence toggle** | 8px | **12px** | |
| **검증 → 원문보기 간격** | 미지정 | **16px + border-top** | 섹션 분리 |

### 4-3. 전체 여백 흐름 시각화

```
body padding: 0 16px (모바일: 0 12px → 0 16px로 통일)

[카드 padding: 24px]
  headline (mb: 16px)
  ─────────────────
  summary-p (mb: 12px)
  summary-p (mb: 12px)
  summary-p (mb: 0 — 마지막 문단)
  ─────────────────
  [16px gap + 1px border-top + 16px padding-top]
  ─────────────────
  verification-tag (mb: 10px)
  verification-reason (mb: 12px)
  evidence-toggle
  ─────────────────
  [16px gap + 1px border-top + 12px padding-top]
  ─────────────────
  원문보기 h4 (mb: 8px)
  source-list pills
[/카드]
(20px card gap)
[다음 카드]
```

---

## 5. 참고 사이트 분석 요약

### 5-1. 네이버 뉴스 모바일

- **본문**: 17px, line-height 1.55, color #141414
- **letter-spacing**: -0.3px (약간 좁게)
- **카드**: 흰 배경, 얇은 border-bottom으로 구분
- **특징**: 기사 사이에 1px border만 사용, 그림자 거의 없음
- **교훈**: 심플한 구분선이 효과적. 과도한 그림자 불필요

### 5-2. 카카오(다음) 뉴스 모바일

- **본문**: 17px, line-height 1.625, color #000
- **헤드라인**: 23px (본문의 1.35배)
- **특징**: 카드형보다는 리스트형. 기사 클릭 시 내부 페이지
- **교훈**: 본문 17px가 한국어 모바일 표준. line-height 1.6 이상 필수

### 5-3. 토스(Toss) 뉴스/증권 피드

- **본문**: F16 스케일 (16px / line-height 24px = 1.5)
- **카드**: 카드 내 섹션을 배경색으로 그룹핑, pill 형태 버튼
- **여백**: 8px 그리드 철저 준수 (8, 16, 24, 32 단위)
- **border-radius**: 16px (둥근 카드)
- **태그/뱃지**: F11 스케일 (11px), padding 3px 6px, border-radius 4px
- **교훈**: 8px 그리드, 16px radius, 섹션 배경색 그룹핑

### 5-4. BBC / NYT 모바일

- **본문**: 16-17px, line-height 1.5-1.6 ([출처: learnui.design](https://www.learnui.design/blog/mobile-desktop-website-font-size-guidelines.html))
- **헤드라인**: 본문의 1.5~2배 크기
- **카드 패턴**: 명확한 이미지 → 헤드라인 → 요약 계층. 각 영역 사이 16-24px 여백
- **교훈**: 텍스트 기반 뉴스도 시각적 계층이 핵심. font-weight + size + color 조합으로 구분

### 5-5. 팩트체크 전문 사이트 (Snopes, PolitiFact)

- **검증 태그가 매우 크고 눈에 띔** — 카드 최상단 또는 헤드라인 바로 옆
- **색상 대비 강함** — 빨강(거짓), 초록(참), 노랑(혼합) 명확 구분
- **교훈**: 팩트렌즈에서 verification tag는 현재 너무 작음. 더 큰 pill + 더 진한 색상 필요

---

## 6. 최종 CSS 변경 제안 요약

### 6-1. body

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, "Noto Sans KR", sans-serif;
  line-height: 1.7;                    /* 유지 */
  color: #1a1a1a;                      /* 유지 */
  background-color: #f0f0f0;           /* #f5f5f5 → #f0f0f0 (카드 대비 강화) */
  max-width: 680px;                    /* 유지 */
  margin: 0 auto;
  padding: 0 16px;                     /* 유지 */
}
```

### 6-2. .news-card

```css
.news-card {
  background: #fff;
  border-radius: 16px;                 /* 12px → 16px */
  padding: 24px;                       /* 20px → 24px */
  margin-bottom: 20px;                 /* 16px → 20px */
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);  /* 그림자 약간 강화 */
  border: 1px solid rgba(0, 0, 0, 0.06);       /* 추가: 미세 보더 */
}
```

### 6-3. .card-headline

```css
.card-headline {
  font-size: 1.25rem;                  /* 1.1rem → 1.25rem (20px) */
  font-weight: 800;                    /* 700 → 800 */
  color: #000;                         /* #111 → #000 (최대 대비) */
  margin-bottom: 16px;                 /* 12px → 16px */
  line-height: 1.4;                    /* 1.5 → 1.4 (제목은 타이트하게) */
  word-break: keep-all;                /* 추가: 한글 단어 단위 줄바꿈 */
}
```

> `word-break: keep-all`은 한국어 텍스트에서 매우 중요. 음절 단위 줄바꿈 대신 어절 단위 줄바꿈을 보장하여 가독성 대폭 개선.

### 6-4. .card-summary p

```css
.card-summary p {
  font-size: 1rem;                     /* 0.95rem → 1rem (16px) */
  color: #222;                         /* #333 → #222 */
  line-height: 1.7;                    /* 1.8 → 1.7 */
  margin-bottom: 12px;                 /* 14px → 12px */
  word-break: keep-all;                /* 추가 */
}

.card-summary p:last-child {
  margin-bottom: 0;                    /* 추가: 마지막 문단 하단 여백 제거 */
}
```

### 6-5. .card-verification (섹션 분리 추가)

```css
.card-verification {
  margin-top: 16px;                    /* 추가: 요약과의 간격 */
  padding-top: 16px;                   /* 추가: 구분선 아래 여백 */
  border-top: 1px solid #e8e8e8;       /* 추가: 구분선 */
  margin-bottom: 0;                    /* 14px → 0 (하단은 sources가 처리) */
}
```

### 6-6. .tag (뱃지 강화)

```css
.tag {
  display: inline-block;
  font-size: 0.8rem;                   /* 유지 */
  font-weight: 700;                    /* 600 → 700 */
  padding: 6px 14px;                   /* 4px 10px → 6px 14px */
  border-radius: 20px;                 /* 6px → 20px (pill shape) */
  margin-bottom: 10px;                 /* 6px → 10px */
  letter-spacing: 0.3px;              /* 추가 */
}

.tag--verified {
  background-color: #d1fae5;           /* 더 진한 녹색 배경 */
  color: #065f46;                      /* 더 진한 녹색 텍스트 */
}

.tag--unconfirmed {
  background-color: #fef3c7;           /* 유지 */
  color: #78350f;                      /* 더 진한 갈색 */
}

.tag--misleading {
  background-color: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;           /* 추가: 위험 강조 보더 */
}
```

### 6-7. .verification-reason

```css
.verification-reason {
  font-size: 0.9rem;                   /* 0.85rem → 0.9rem */
  color: #444;                         /* #555 → #444 */
  margin-top: 8px;                     /* 4px → 8px */
  line-height: 1.6;                    /* 추가: 이유 텍스트 줄간격 */
  word-break: keep-all;                /* 추가 */
}
```

### 6-8. .card-sources (섹션 분리 추가)

```css
.card-sources {
  margin-top: 16px;                    /* 추가 */
  padding-top: 12px;                   /* 추가 */
  border-top: 1px solid #e8e8e8;       /* 추가: 구분선 */
}

.card-sources h4 {
  font-size: 0.8rem;                   /* 0.85rem → 0.8rem */
  font-weight: 600;
  color: #888;                         /* #666 → #888 */
  margin-bottom: 8px;                  /* 6px → 8px */
}
```

### 6-9. 모바일 반응형 (@max-width: 480px)

```css
@media (max-width: 480px) {
  body {
    padding: 0 16px;                   /* 12px → 16px (양옆 최소 여백 확보) */
  }

  .site-title {
    font-size: 1.5rem;                 /* 유지 */
  }

  .news-card {
    padding: 20px;                     /* 16px → 20px */
    border-radius: 12px;              /* 8px → 12px */
  }

  .card-headline {
    font-size: 1.125rem;              /* 1rem → 1.125rem (18px) — 본문과 차이 유지 */
  }
}
```

---

## 7. 변경 우선순위

CSS 변경은 한 번에 적용해도 되지만, 체감 효과 기준으로 정렬:

| 순위 | 변경 | 체감 효과 |
|------|------|-----------|
| 1 | 카드 내부 섹션 분리 (border-top 추가) | **매우 높음** — "텍스트 덤프" 느낌 즉시 해소 |
| 2 | headline 크기 + weight 강화 | **높음** — 스캔 가능한 계층 구조 |
| 3 | 검증 태그 pill shape + 크기 확대 | **높음** — 핵심 기능의 시각적 존재감 |
| 4 | 카드 여백/패딩 확대 | **중간** — 전체적인 '답답함' 해소 |
| 5 | 배경색 #f0f0f0 + 카드 border | **중간** — 카드 분리감 강화 |
| 6 | 본문 font-size 1rem + color #222 | **중간** — 가독성 미세 개선 |
| 7 | word-break: keep-all | **중간** — 한국어 줄바꿈 품질 향상 |
| 8 | 모바일 패딩/사이즈 조정 | **중간** — 모바일 전용 개선 |

---

## Sources

- [모바일 웹 사이트들의 한글 타이포그래피 (lqez.github.io)](https://lqez.github.io/blog/hangul-typography-on-mobile-web.html) — 한국 뉴스 사이트 실측 font-size, line-height 데이터
- [W3C Requirements for Hangul Text Layout](https://w3c.github.io/klreq/) — 한글 letter-spacing 기본값, 줄간격 표현법
- [토스 디자인 시스템 (toss.tech)](https://toss.tech/article/toss-design-system) — TDS 타이포그래피 스케일, 8px 그리드
- [Font Size Guidelines for Responsive Websites (learnui.design)](https://www.learnui.design/blog/mobile-desktop-website-font-size-guidelines.html) — 모바일 본문 16-20px 권장
- [Material Design 3 Box-Shadow CSS Values (studioncreations.com)](https://studioncreations.com/blog/material-design-3-box-shadow-css-values/) — MD3 엘리베이션 CSS 값
- [Web Design Spacing and Sizing Best Practices (conceptfusion.co.uk)](https://www.conceptfusion.co.uk/post/web-design-spacing-and-sizing-best-practices) — 8px 그리드 시스템
- [Visual Hierarchy in UX (eleken.co)](https://www.eleken.co/blog-posts/visual-hierarchy-in-ux) — 시각적 계층 원칙
- [Hangeul Typography Explained (morisawa-usa.com)](https://www.morisawa-usa.com/post/hangeul-typogarphy-guide) — 한글 타이포그래피 구조적 특성
- [Badges vs Pills vs Chips vs Tags (smart-interface-design-patterns.com)](https://smart-interface-design-patterns.com/articles/badges-chips-tags-pills/) — 뱃지/태그 디자인 패턴
- [Mobile App UI Design Best Practices (thedroidsonroids.com)](https://www.thedroidsonroids.com/blog/mobile-app-ui-design-guide) — 모바일 UI 트렌드
- [Consistent Visual Hierarchy in Mobile Apps (thisisglance.com)](https://thisisglance.com/learning-centre/how-do-i-create-consistent-visual-hierarchy-in-mobile-apps) — 모바일 터치 타겟 48px
- [Material Design Cards (m2.material.io)](https://m2.material.io/components/cards) — MD2 카드 엘리베이션 기본값
- [CJK Typesetting (typotheque.com)](https://www.typotheque.com/articles/typesetting-cjk-text) — CJK 텍스트 line-height 1.7 권장
