# Plan: FR-002 카테고리 필터링 및 선별

> **범위**: 구현 순서 4 (필터링/선별 모듈)
> **관련 TRD**: FR-002
> **입력**: `collect_news()`가 반환한 `list[Article]` (3개 토픽 피드 합산)
> **출력**: 중복 제거 후 상위 10개 `list[Article]`

---

## 1. 접근 방식 변경

### 기존: 메인 피드 1개 + 키워드 필터링
### **변경: 토픽별 피드 3개 수집 → 키워드 필터링 불필요**

**변경 이유:**
- RSS 아이템에 `<category>` 태그 없음 → 키워드 기반 판별만 가능
- 키워드 필터링은 false positive 리스크가 큼 ("경기 침체", "정치 선수", "감독 기관" 등 오분류)
- Google News가 토픽별 RSS 피드를 제공하므로, 원하는 카테고리만 수집하면 필터링 자체가 불필요

### 수집 피드 (collector 변경 — plan-rss-수집.md 연동)

| 토픽 | 피드 URL | 아이템 수 | 비고 |
|------|----------|----------|------|
| 정치+사회 | `.../section/topic/NATION?hl=ko&gl=KR&ceid=KR:ko` | ~30개 | 정치와 사회가 합쳐져 있음 |
| 경제 | `.../section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko` | ~30개 | |
| 국제 | `.../section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko` | ~30개 | |

> collector에서 3개 피드를 수집하여 합산 후 `list[Article]`로 반환.
> 각 Article에 `topic` 필드 추가하여 출처 피드 구분.

---

## 2. 주요 결정 사항

### 결정 1: 중복 제거 기준

| 선택지 | 장점 | 단점 |
|--------|------|------|
| **A. headline 완전 일치** | 단순, 빠름 | 제목 살짝 다른 중복 놓칠 수 있음 |
| B. URL 기반 | 정확 | 같은 기사도 피드마다 다른 Google News URL 부여 가능 |
| C. 유사도 비교 | 정교 | 구현 복잡, MVP에 과도 |

**→ 선택: A** — 토픽이 다른 피드에서 온 기사는 제목이 같을 확률이 매우 낮음. 동일 기사가 두 피드에 실린 경우 제목이 완전히 같으므로 충분.

### 결정 2: 토픽별 선별 비율

| 선택지 | 설명 |
|--------|------|
| **A. 피드 순서 기반 라운드 로빈** | 3개 피드를 피드 순서(=중요도) 기준으로 인터리브하여 상위 10개 선별 |
| B. 토픽별 균등 배분 | 정치+사회 4개, 경제 3개, 국제 3개 고정 |
| C. pubDate 최신순 | 최신 기사 우선 | 새벽 기사 편중, 중요도 미반영 |

**→ 선택: A** — 각 피드의 순서가 곧 Google News의 중요도 랭킹. 라운드 로빈으로 인터리브하면 각 토픽의 중요 기사를 공정하게 반영. 토픽 상한 없음 — 사용자는 토픽 균형이 아니라 가장 중요한 뉴스를 원함.

---

## 3. 파일 변경 목록

### 새로 생성
```
pipeline/filter.py          # 중복 제거 + 선별 모듈
tests/test_filter.py        # 테스트
```

### 수정 (plan-rss-수집.md 연동)
```
pipeline/collector.py       # 3개 토픽 피드 수집, 피드별 리스트 반환으로 변경
```

---

## 4. 모듈 설계 (`pipeline/filter.py`)

### 공개 인터페이스

```python
def filter_and_select(
    feeds: list[list[Article]],
    max_count: int = 10,
) -> list[Article]:
    """
    여러 피드의 Article 리스트를 받아 중복 제거 후
    피드 순서 기반 라운드 로빈으로 상위 max_count개 선별.
    """
```

### 내부 함수

```python
def _deduplicate(articles: list[Article]) -> list[Article]:
    """headline 완전 일치 기준 중복 제거. 먼저 나온 것 유지."""
```

### 처리 흐름

```
1. 입력: list[list[Article]] (3개 피드, 각 피드는 피드 순서=중요도 유지)
2. 라운드 로빈 인터리브:
   - 각 피드의 1위 기사 → 각 피드의 2위 기사 → ... 순서로 합산
   - 피드가 소진되면 나머지 피드에서 계속
3. _deduplicate()로 headline 중복 제거
4. 상위 max_count(10개) 선별
5. 반환: list[Article]
```

---

## 6. 테스트 전략

### 테스트 케이스
```
test_deduplicate_same_headline       — 동일 제목 기사 중복 제거
test_deduplicate_different_headline  — 다른 제목은 유지
test_select_max_10                   — 10개 초과 시 상위 10개만 반환
test_round_robin_interleave          — 3개 피드 라운드 로빈 인터리브 순서 확인
test_feed_exhausted                  — 1개 피드 소진 시 나머지 피드에서 계속
test_empty_input                     — 빈 리스트 입력 시 빈 리스트 반환
test_fewer_than_max                  — 전체 기사가 10개 미만이면 전부 반환
```

---

## 7. 트레이드오프 / 리스크

| 항목 | 리스크 | 대응 |
|------|--------|------|
| 토픽 피드 구조 변경 | Google이 토픽 피드 URL/구조 변경 가능 | 메인 피드 폴백 로직 (collector에서 처리) |
| 중복 기사 누락 | 제목이 살짝 다른 중복 놓칠 수 있음 | MVP에서는 headline 완전 일치로 충분. 정교한 중복 제거는 추후 |
| 토픽 편중 | 특정 이슈 폭발 시 한 토픽에 쏠림 | 사용자가 원하는 건 중요한 뉴스이므로 편중 허용. 문제 아님 |
