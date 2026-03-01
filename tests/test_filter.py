from pipeline.filter import _deduplicate, filter_and_select
from pipeline.models import Article


def _article(headline: str, article_id: str = "") -> Article:
    return Article(id=article_id or headline, headline=headline)


class TestDeduplicate:
    def test_removes_same_headline(self) -> None:
        articles = [_article("기사A", "1"), _article("기사A", "2"), _article("기사B", "3")]
        result = _deduplicate(articles)
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].headline == "기사B"

    def test_keeps_different_headlines(self) -> None:
        articles = [_article("A"), _article("B"), _article("C")]
        result = _deduplicate(articles)
        assert len(result) == 3


class TestFilterAndSelect:
    def test_round_robin_interleave(self) -> None:
        feed_a = [_article("A1"), _article("A2"), _article("A3")]
        feed_b = [_article("B1"), _article("B2"), _article("B3")]
        feed_c = [_article("C1"), _article("C2"), _article("C3")]
        result = filter_and_select([feed_a, feed_b, feed_c], max_count=9)
        headlines = [a.headline for a in result]
        assert headlines == ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"]

    def test_select_max_10(self) -> None:
        feed = [_article(f"기사{i}") for i in range(20)]
        result = filter_and_select([feed], max_count=10)
        assert len(result) == 10

    def test_deduplicate_same_headline(self) -> None:
        feed_a = [_article("같은 제목")]
        feed_b = [_article("같은 제목")]
        result = filter_and_select([feed_a, feed_b], max_count=10)
        assert len(result) == 1

    def test_feed_exhausted(self) -> None:
        feed_a = [_article("A1")]
        feed_b = [_article("B1"), _article("B2"), _article("B3")]
        result = filter_and_select([feed_a, feed_b], max_count=10)
        assert len(result) == 4
        headlines = [a.headline for a in result]
        assert headlines == ["A1", "B1", "B2", "B3"]

    def test_empty_input(self) -> None:
        result = filter_and_select([], max_count=10)
        assert result == []

    def test_fewer_than_max(self) -> None:
        feed = [_article("A"), _article("B")]
        result = filter_and_select([feed], max_count=10)
        assert len(result) == 2

    def test_preserves_order_within_feed(self) -> None:
        feed = [_article(f"기사{i}") for i in range(5)]
        result = filter_and_select([feed], max_count=5)
        for i, article in enumerate(result):
            assert article.headline == f"기사{i}"
