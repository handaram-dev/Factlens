from unittest.mock import MagicMock, patch

from pipeline.collector import (
    _decode_google_news_url,
    _parse_cluster_articles,
    _parse_entry,
    _strip_publisher_from_title,
    collect_news,
    _fetch_rss,
)
from pipeline.models import SourceArticle


def _make_entry(
    title: str = "테스트 기사 - 연합뉴스",
    link: str = "https://news.google.com/rss/articles/CBMiTest",
    published: str = "Sun, 01 Mar 2026 02:03:00 GMT",
    summary: str = "",
    source_title: str = "연합뉴스",
    source_url: str = "https://www.yna.co.kr",
) -> dict[str, object]:
    return {
        "title": title,
        "link": link,
        "published": published,
        "summary": summary,
        "source": {"title": source_title, "href": source_url},
    }


class TestStripPublisherFromTitle:
    def test_normal(self) -> None:
        assert _strip_publisher_from_title("정부 정책 발표 - 조선일보") == "정부 정책 발표"

    def test_multiple_dashes(self) -> None:
        assert _strip_publisher_from_title("A - B - 연합뉴스") == "A - B"

    def test_no_dash(self) -> None:
        assert _strip_publisher_from_title("제목만 있음") == "제목만 있음"


class TestParseClusterArticles:
    def test_normal_cluster(self) -> None:
        html = (
            '<ol>'
            '<li><a href="https://news.google.com/articles/1">기사1</a>'
            '&nbsp;<font color="#6f6f6f">조선일보</font></li>'
            '<li><a href="https://news.google.com/articles/2">기사2</a>'
            '&nbsp;<font color="#6f6f6f">한겨레</font></li>'
            '</ol>'
        )
        result = _parse_cluster_articles(html)
        assert len(result) == 2
        assert result[0].publisher == "조선일보"
        assert result[0].url == "https://news.google.com/articles/1"
        assert result[1].publisher == "한겨레"

    def test_empty_description(self) -> None:
        assert _parse_cluster_articles("") == []

    def test_no_cluster(self) -> None:
        html = '<a href="https://example.com">기사</a>'
        result = _parse_cluster_articles(html)
        assert len(result) == 0


class TestDecodeGoogleNewsUrl:
    @patch("googlenewsdecoder.new_decoderv1")
    def test_success(self, mock_decoder: MagicMock) -> None:
        mock_decoder.return_value = {
            "status": True,
            "decoded_url": "https://www.yna.co.kr/view/123",
        }
        result = _decode_google_news_url("https://news.google.com/rss/articles/CBMiTest")
        assert result == "https://www.yna.co.kr/view/123"

    @patch("googlenewsdecoder.new_decoderv1", side_effect=Exception("fail"))
    def test_failure_returns_empty(self, mock_decoder: MagicMock) -> None:
        result = _decode_google_news_url("https://news.google.com/rss/articles/CBMiFail")
        assert result == ""


class TestParseEntry:
    @patch("pipeline.collector._decode_google_news_url", return_value="https://yna.co.kr/123")
    def test_normal(self, mock_decode: MagicMock) -> None:
        entry = _make_entry()
        article = _parse_entry(entry)
        assert article.headline == "테스트 기사"
        assert article.publisher == "연합뉴스"
        assert article.original_url == "https://yna.co.kr/123"
        assert article.google_news_url == "https://news.google.com/rss/articles/CBMiTest"
        assert article.id

    @patch("pipeline.collector._decode_google_news_url", return_value="")
    def test_missing_source(self, mock_decode: MagicMock) -> None:
        entry = _make_entry()
        del entry["source"]
        article = _parse_entry(entry)
        assert article.publisher == ""


class TestFetchRss:
    @patch("pipeline.collector.feedparser.parse")
    def test_success(self, mock_parse: MagicMock) -> None:
        mock_feed = MagicMock()
        mock_feed.bozo = 0
        mock_feed.entries = [_make_entry(), _make_entry()]
        mock_parse.return_value = mock_feed
        result = _fetch_rss("https://example.com/rss")
        assert len(result) == 2

    @patch("pipeline.collector.feedparser.parse")
    def test_bozo_with_entries(self, mock_parse: MagicMock) -> None:
        mock_feed = MagicMock()
        mock_feed.bozo = 1
        mock_feed.bozo_exception = "minor issue"
        mock_feed.entries = [_make_entry()]
        mock_parse.return_value = mock_feed
        result = _fetch_rss("https://example.com/rss")
        assert len(result) == 1

    @patch("pipeline.collector.feedparser.parse")
    @patch("pipeline.collector.time.sleep")
    def test_retry_on_failure(self, mock_sleep: MagicMock, mock_parse: MagicMock) -> None:
        mock_feed = MagicMock()
        mock_feed.bozo = 1
        mock_feed.bozo_exception = ValueError("fail")
        mock_feed.entries = []
        mock_parse.return_value = mock_feed
        result = _fetch_rss("https://example.com/rss", max_retries=2)
        assert result == []
        assert mock_sleep.call_count == 2


class TestCollectNews:
    @patch("pipeline.collector._fetch_rss")
    @patch("pipeline.collector._decode_google_news_url", return_value="https://example.com/1")
    def test_three_topics(self, mock_decode: MagicMock, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [_make_entry()]
        result = collect_news()
        assert len(result) == 3
        for feed in result:
            assert len(feed) == 1

    @patch("pipeline.collector._fetch_rss")
    def test_partial_fail(self, mock_fetch: MagicMock) -> None:
        mock_feed = MagicMock()
        mock_feed.bozo = 0
        mock_feed.entries = [_make_entry()]
        mock_fetch.side_effect = [
            [_make_entry()],
            [],
            [_make_entry()],
        ]
        with patch("pipeline.collector._decode_google_news_url", return_value=""):
            result = collect_news()
        assert len(result) == 3
        assert len(result[0]) == 1
        assert len(result[1]) == 0
        assert len(result[2]) == 1

    @patch("pipeline.collector._fetch_rss")
    @patch("pipeline.collector._decode_google_news_url", return_value="")
    def test_returns_feeds(self, mock_decode: MagicMock, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [_make_entry(), _make_entry()]
        result = collect_news()
        assert len(result) == 3
        for feed in result:
            assert len(feed) == 2
