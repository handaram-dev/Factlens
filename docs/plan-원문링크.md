# Plan: FR-005 관련 언론사 원문 링크 수집

> **범위**: 구현 순서 — collector 후처리 + 검증 단계 보완
> **관련 TRD**: FR-005
> **입력**: 파이프라인 처리 완료된 `list[Article]`
> **출력**: 각 Article의 `source_articles`가 2개 이상 채워진 `list[Article]`

---

## 1. 현황: 이미 대부분 해결됨

FR-005의 핵심 데이터는 **이미 다른 모듈에서 수집됨**:

| 데이터 소스 | 담당 모듈 | 내용 |
|------------|-----------|------|
| RSS description HTML 클러스터 | collector (plan-rss-수집) | 같은 사건 보도 3~5개 언론사 링크 |
| Google Custom Search 결과 | verifier (plan-교차검증) | 같은 사건 관련 검색 결과 URL |

**collector가 `_parse_cluster_articles()`로 클러스터 기사를 파싱하여 `source_articles`에 채움.**
→ 대부분의 기사는 이미 2개 이상의 원문 링크를 갖고 있을 것.

---

## 2. 남은 작업

### 2.1 클러스터 기사 URL 디코딩

description HTML의 링크도 Google News 인코딩 URL. collector의 `_decode_google_news_url()`로 동일하게 디코딩 필요.

> 이미 plan-rss-수집의 `_parse_cluster_articles()`에서 처리하도록 설계됨. 추가 작업 없음.

### 2.2 source_articles 부족 시 보완

클러스터가 비어있거나 1개뿐인 경우 대비.

| 선택지 | 설명 |
|--------|------|
| **A. verifier 검색 결과에서 보완** | 교차검증 시 Google Custom Search 결과에 뉴스 URL이 포함됨. 이를 source_articles에 추가 |
| B. 별도 검색 호출 | source_articles 전용 Google Custom Search 추가 호출 |

**→ 선택: A** — verifier가 이미 기사당 2회 검색. 검색 결과에서 뉴스 도메인 URL을 뽑아 source_articles에 추가하면 별도 API 호출 불필요.

### 2.3 최소 보장

- 클러스터 + 검색 결과 합쳐도 2개 미만이면, 원본 기사 1개만 표시 (TRD 엣지 케이스)
- 이 경우에도 기사를 제거하지 않음 — source_articles가 1개여도 브리핑에 포함

---

## 3. 구현 방식: 별도 모듈 불필요

FR-005는 독립 모듈이 아니라 **기존 모듈의 후처리 로직**으로 충분:

| 작업 | 구현 위치 |
|------|-----------|
| 클러스터 기사 파싱 + URL 디코딩 | `collector.py` — `_parse_cluster_articles()` |
| 검색 결과에서 뉴스 URL 추출하여 source_articles 보완 | `verifier.py` — `verify_articles()` 내부 |
| 중복 URL 제거 | `verifier.py` — 보완 시 기존 source_articles와 URL 비교 |

### verifier.py에 추가할 로직

```python
def _supplement_source_articles(article: Article, search_results: list[dict]) -> None:
    """
    검색 결과에서 뉴스 URL을 추출하여 source_articles에 추가.
    이미 있는 URL은 중복 제거.
    """
```

### 처리 흐름 (verifier 내부에서)

```
verify_articles() 각 기사 처리 시:
1. (기존) 교차확인 → 태그 부여
2. (추가) 검색 결과에서 뉴스 도메인 URL 추출
3. 기존 source_articles에 없는 URL만 SourceArticle로 추가
4. 최종 source_articles 2개 미만이면 로그 경고 (기사는 유지)
```

---

## 4. 파일 변경 목록

### 새로 생성
```
(없음 — 별도 모듈 불필요)
```

### 수정
```
pipeline/verifier.py       # _supplement_source_articles() 추가
tests/test_verifier.py     # source_articles 보완 테스트 추가
```

---

## 5. 테스트 전략

### 기존 test_collector.py에 이미 포함
```
test_parse_cluster_articles     — description HTML에서 관련 기사 추출
test_parse_cluster_empty        — 클러스터 없는 description 처리
```

### test_verifier.py에 추가
```
test_supplement_source_articles        — 검색 결과에서 source_articles 보완
test_supplement_deduplication          — 기존 source_articles와 중복 URL 제거
test_supplement_no_news_in_search      — 검색 결과에 뉴스 URL 없으면 보완 안 함
test_source_articles_minimum_warning   — 2개 미만 시 로그 경고 + 기사 유지
```

---

## 6. 트레이드오프 / 리스크

| 항목 | 리스크 | 대응 |
|------|--------|------|
| 클러스터가 비어있는 기사 | 단독 보도거나 Google News가 클러스터링 안 한 경우 | verifier 검색 결과로 보완. 그래도 부족하면 원본 1개만 표시 |
| 검색 결과 URL이 뉴스가 아닌 경우 | 블로그, 포럼 등 비뉴스 URL 포함 가능 | 주요 뉴스 도메인 허용 목록 or URL 패턴으로 필터링 |
| 깨진 링크 | 원문 URL이 삭제/변경될 수 있음 | MVP에서는 검증 생략. PRD에도 "원문 URL 삭제 시 깨질 수 있음" 명시 |
