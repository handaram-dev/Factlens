# Plan: 광고 플랫폼 도입 (Phase 1)

> **배경**: MVP 수익화 검증. PRD 10.1에 명시된 광고 플랫폼 중 즉시 적용 가능한 것부터 도입.
> **리서치**: `docs/research-광고플랫폼.md` 참조

---

## 1. Phase 1 범위

Phase 1에서는 **카카오 AdFit + 쿠팡 파트너스**를 동시 도입한다.

| 플랫폼 | 승인 | 과금 | 역할 |
|--------|------|------|------|
| 카카오 AdFit | 1~2일 | CPC+CPM | 메인 디스플레이 광고 |
| 쿠팡 파트너스 | 즉시 | CPS 3% | 보조 수익 (상품 배너) |

AdSense, Ezoic, 데이블은 콘텐츠/트래픽 축적 후 Phase 2~3에서 진행.

---

## 2. 광고 배치 위치

뉴스 중립성과 가독성을 해치지 않는 배치. PRD 10.2 광고 원칙 준수.

```
┌─────────────────────────┐
│  header (팩트렌즈)        │
├─────────────────────────┤
│  briefing-title          │
├─────────────────────────┤
│  뉴스 카드 1             │
│  뉴스 카드 2             │
│  뉴스 카드 3             │
├─────────────────────────┤
│  ▶ AdFit 배너 (320x100) │  ← 3번째 기사 뒤 (기존 후원 배너 아래)
├─────────────────────────┤
│  뉴스 카드 4             │
│  ...                    │
│  뉴스 카드 7             │
├─────────────────────────┤
│  ▶ 쿠팡 파트너스 배너     │  ← 7번째 기사 뒤
├─────────────────────────┤
│  뉴스 카드 8             │
│  ...                    │
│  뉴스 카드 11            │
├─────────────────────────┤
│  ▶ AdFit 배너 (320x100) │  ← 11번째 기사 뒤
├─────────────────────────┤
│  뉴스 카드 12~15         │
├─────────────────────────┤
│  footer                  │
│  (면책 + 후원 링크)       │
└─────────────────────────┘
```

- 기사 사이에 최대 3개 광고 (AdFit 2 + 쿠팡 1)
- 카드와 동일한 가로 폭, 중앙 정렬
- 광고임을 명확히 구분 (배경색/라벨 등은 플랫폼 정책에 따름)
- 기존 후원 배너(3번째 기사 뒤)는 유지, 그 아래에 AdFit 배치

---

## 3. 변경 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `templates/index.html.j2` | 수정 | AdFit 스크립트 + 쿠팡 배너 삽입 |
| `static/style.css` | 수정 | 광고 배너 컨테이너 스타일 |

---

## 4. 구체적 코드 변경

### 4-1. `templates/index.html.j2`

**변경 1 — `<head>`에 AdFit 스크립트 추가 (L8 다음):**
```html
<script async src="https://t1.daumcdn.net/kas/static/ba.min.js"></script>
```

**변경 2 — 기사 루프 안에 광고 배너 삽입:**

현재 3번째 기사 뒤에 후원 배너가 있다 (L67-73). 이 로직을 확장:

```html
{% if loop.index == 3 %}
<div class="mid-support-banner">
    <a class="support-link" href="https://buymeacoffee.com/factlens" target="_blank" rel="noopener">
        가짜뉴스 없는 세상, 후원으로 함께 만들어주세요
    </a>
</div>
<div class="ad-banner">
    <ins class="kakao_ad_area"
         style="display:none;"
         data-ad-unit="ADFIT_UNIT_ID_1"
         data-ad-width="320"
         data-ad-height="100"></ins>
</div>
{% endif %}

{% if loop.index == 7 %}
<div class="ad-banner">
    <a href="COUPANG_AFFILIATE_LINK" target="_blank" rel="noopener sponsored">
        <img src="COUPANG_BANNER_IMG_URL" alt="쿠팡 파트너스" width="320" height="100" loading="lazy">
    </a>
    <p class="ad-disclosure">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
</div>
{% endif %}

{% if loop.index == 11 %}
<div class="ad-banner">
    <ins class="kakao_ad_area"
         style="display:none;"
         data-ad-unit="ADFIT_UNIT_ID_2"
         data-ad-width="320"
         data-ad-height="100"></ins>
</div>
{% endif %}
```

**주의**: `ADFIT_UNIT_ID_1`, `ADFIT_UNIT_ID_2`, `COUPANG_AFFILIATE_LINK`, `COUPANG_BANNER_IMG_URL`은 실제 가입 후 발급받은 값으로 교체해야 한다.

### 4-2. `static/style.css`

```css
/* ===== Ad Banner ===== */
.ad-banner {
  text-align: center;
  margin-bottom: 20px;
}

.ad-disclosure {
  font-size: 0.7rem;
  color: #999;
  margin-top: 4px;
}
```

---

## 5. 사전 준비 (수동 작업)

코드 구현 전에 사용자가 직접 해야 하는 작업:

1. **카카오 AdFit 가입 + 매체 등록**
   - https://adfit.kakao.com 접속
   - 매체 등록: `https://factlens.pages.dev`
   - 광고 단위 2개 생성 (320x100 모바일 배너)
   - 발급받은 `data-ad-unit` ID 2개 확보
   - 승인 대기 (1~2 영업일)

2. **쿠팡 파트너스 가입 + 배너 생성**
   - https://partners.coupang.com 접속
   - 가입 + 활동 채널에 `https://factlens.pages.dev` 등록
   - 다이나믹 배너 또는 상품 링크 생성 (320x100)
   - 배너 이미지 URL + 어필리에이트 링크 확보

---

## 6. 구현 순서

1. 사용자에게 AdFit/쿠팡 가입 및 ID/링크 확보 요청
2. `templates/index.html.j2` — AdFit 스크립트 + 광고 배너 삽입
3. `static/style.css` — 광고 배너 스타일 추가
4. 로컬에서 HTML 렌더링하여 배치 확인
5. 커밋 + 푸시 + workflow_dispatch
6. factlens.pages.dev에서 광고 노출 확인

---

## 7. 쿠팡 파트너스 법적 고지

쿠팡 파트너스 이용약관에 따라 아래 문구를 광고 근처에 반드시 표시해야 함:

> "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."

---

## 8. 채택하지 않은 사항

| 사항 | 이유 |
|------|------|
| AdSense 즉시 신청 | 콘텐츠 20개 미확보, 승인 거절 가능성 높음. Phase 2에서 진행 |
| Ezoic | 한국어 지원 미비, AdSense 대안으로만 고려 |
| 데이블 | 일 PV 3,000 + 콘텐츠 300개 미달. Phase 3 |
| footer에 광고 배치 | 후원 링크와 경쟁. 기사 사이 배치가 CTR 더 높음 |
| 3개 이상 광고 | 15개 기사에 3개가 적정. 과도한 광고는 UX 저해 |
