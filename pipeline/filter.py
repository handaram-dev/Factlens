import logging
from itertools import zip_longest

from pipeline.models import Article

logger = logging.getLogger(__name__)


def _deduplicate(articles: list[Article]) -> list[Article]:
    """headline 완전 일치 기준 중복 제거. 먼저 나온 것 유지."""
    seen: set[str] = set()
    result: list[Article] = []
    for article in articles:
        if article.headline not in seen:
            seen.add(article.headline)
            result.append(article)
    return result


def filter_and_select(
    feeds: list[list[Article]],
    max_count: int = 10,
) -> list[Article]:
    """여러 피드의 Article 리스트를 받아 중복 제거 후
    피드 순서 기반 라운드 로빈으로 상위 max_count개 선별."""
    interleaved: list[Article] = []
    for items in zip_longest(*feeds):
        for item in items:
            if item is not None:
                interleaved.append(item)

    deduplicated = _deduplicate(interleaved)

    selected = deduplicated[:max_count]

    if len(selected) < max_count:
        logger.warning(
            "선별된 기사 수(%d)가 목표(%d)보다 적음",
            len(selected), max_count,
        )

    return selected
