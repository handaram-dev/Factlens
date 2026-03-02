# Plan: 공개 준비 — 히어로 섹션 + og:image

> **배경**: 서비스를 사람들에게 공개하기 전, 첫 방문자가 3초 안에 핵심 가치를 이해할 수 있도록 준비
> **리서치**: `docs/research-공개전략.md` 참조
> **결론**: 별도 랜딩페이지 X, 브리핑 상단에 히어로 섹션 추가 + og:image 추가

---

## 1. 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `templates/index.html.j2` | 수정 | 히어로 섹션 추가 + og:image 메타 태그 |
| `static/style.css` | 수정 | 히어로 섹션 스타일 |
| `static/og-image.svg` | 신규 | 소셜 공유용 OG 이미지 (SVG → PNG 변환 필요 없이 SVG 직접 사용) |

---

## 2. 히어로 섹션

### 2.1 위치

현재 구조:
```
<header> 팩트렌즈 / 태그라인 </header>
<main> 브리핑 타이틀 → 기사 카드들 </main>
```

변경 후:
```
<header> 팩트렌즈 / 태그라인 </header>
<section class="hero"> 히어로 섹션 </section>   ← 추가
<main> 브리핑 타이틀 → 기사 카드들 </main>
```

### 2.2 히어로 콘텐츠

```html
<section class="hero">
    <h2 class="hero-headline">뉴스, 어렵지 않아요</h2>
    <p class="hero-sub">
        AI가 오늘의 뉴스를 <strong>쉬운 말</strong>로 요약하고<br>
        <strong>팩트체크</strong>까지 해드려요.
    </p>
    <ul class="hero-features">
        <li>쉬운 요약 — 전문용어 없이 누구나 이해</li>
        <li>팩트체크 — AI가 여러 언론사를 교차 확인</li>
        <li>다양한 시각 — 같은 사건, 다른 언론사 원문 비교</li>
    </ul>
    <p class="hero-update">매일 아침 자동 업데이트</p>
</section>
```

핵심 요소:
- **헤드라인**: "뉴스, 어렵지 않아요" — 타겟(뉴스 이탈층)의 문제를 짚는 문제 해결형
- **서브헤드**: 핵심 가치 2가지 (쉬운 말 + 팩트체크) 볼드 강조
- **3가지 가치**: 리스트로 한눈에 스캔 가능
- **재방문 유도**: "매일 아침 자동 업데이트" 명시

### 2.3 히어로 스타일

```css
/* ===== Hero Section ===== */
.hero {
  text-align: center;
  padding: 32px 20px;
  margin-bottom: 24px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.hero-headline {
  font-size: 1.5rem;
  font-weight: 800;
  color: #111;
  margin-bottom: 8px;
}

.hero-sub {
  font-size: 1rem;
  color: #444;
  line-height: 1.6;
  margin-bottom: 20px;
}

.hero-features {
  list-style: none;
  text-align: left;
  display: inline-block;
  margin-bottom: 16px;
}

.hero-features li {
  font-size: 0.9rem;
  color: #333;
  padding: 4px 0;
  word-break: keep-all;
}

.hero-features li::before {
  content: "✓ ";
  color: #10b981;
  font-weight: 700;
}

.hero-update {
  font-size: 0.8rem;
  color: #888;
}

@media (max-width: 480px) {
  .hero {
    padding: 24px 16px;
  }

  .hero-headline {
    font-size: 1.25rem;
  }
}
```

디자인 원칙:
- 뉴스 카드와 동일한 카드 스타일 (radius 16px, 그림자, 흰 배경) → 일관성
- 컴팩트하게 — 모바일에서 스크롤 한 번이면 브리핑 시작
- 기존 사이트 색상 팔레트 유지 (#2563eb, #10b981, #111)

---

## 3. og:image

### 3.1 방향

- 정적 SVG 1장 (매일 동적 생성은 overkill)
- 팩트렌즈 로고(돋보기+체크마크) + 서비스명 + 핵심 카피
- 1200x630px 비율 (소셜 미디어 표준)

### 3.2 SVG 내용

`static/og-image.svg`:
- 배경: 흰색
- 중앙: 팩트렌즈 로고 (기존 favicon.svg 요소 재활용)
- 로고 아래: "팩트렌즈" 텍스트
- 하단: "AI가 검증한 쉬운 뉴스 브리핑" 서브텍스트

### 3.3 메타 태그 추가

`templates/index.html.j2` `<head>`에:
```html
<meta property="og:image" content="https://factlens.pages.dev/static/og-image.svg">
<meta name="twitter:image" content="https://factlens.pages.dev/static/og-image.svg">
<meta name="twitter:card" content="summary_large_image">
```

기존 `<meta name="twitter:card" content="summary">`를 `summary_large_image`로 변경 — 큰 이미지가 클릭률이 더 높음.

---

## 4. 구현 순서

1. `static/og-image.svg` 생성
2. `templates/index.html.j2` — 히어로 섹션 추가 + og:image 메타 태그 추가
3. `static/style.css` — 히어로 스타일 추가
4. 테스트 실행 (81개 통과 확인)
5. 커밋 & 푸시
6. workflow_dispatch 실행
7. factlens.pages.dev에서 확인
8. 소셜 공유 미리보기 확인 (https://www.opengraph.xyz/)

---

## 5. 채택하지 않은 사항

| 사항 | 이유 |
|------|------|
| 별도 랜딩페이지 | 전환 목표 없는 현재 단계에서 오버엔지니어링. 이탈만 유발 |
| 히어로 접기/숨기기 | 구현 복잡도 대비 효과 미미. 히어로가 충분히 컴팩트 |
| PNG og:image 동적 생성 | 매일 날짜 바꾸는 것은 overkill. 정적 1장이면 충분 |
| 이메일 구독 CTA | 현재 이메일 인프라 없음. 향후 과제 |
| 운영자 About 페이지 | 단일 페이지 구조에서 별도 페이지는 과함. 향후 고려 |
