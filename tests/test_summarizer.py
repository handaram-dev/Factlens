from unittest.mock import MagicMock, patch

from pipeline.models import Article
from pipeline.summarizer import (
    _fetch_article_text,
    _generate_summary,
    summarize_articles,
)


def _article(headline: str = "테스트 기사", original_url: str = "https://example.com/1") -> Article:
    return Article(id="test-id", headline=headline, original_url=original_url)


class TestFetchArticleText:
    @patch("pipeline.summarizer.NewspaperArticle")
    def test_success(self, mock_cls: MagicMock) -> None:
        mock_article = MagicMock()
        mock_article.text = "기사 본문 내용입니다."
        mock_cls.return_value = mock_article
        result = _fetch_article_text("https://example.com/1")
        assert result == "기사 본문 내용입니다."
        mock_article.download.assert_called_once()
        mock_article.parse.assert_called_once()

    @patch("pipeline.summarizer.NewspaperArticle", side_effect=Exception("network error"))
    def test_failure(self, mock_cls: MagicMock) -> None:
        result = _fetch_article_text("https://example.com/fail")
        assert result == ""

    def test_empty_url(self) -> None:
        result = _fetch_article_text("")
        assert result == ""


class TestGenerateSummary:
    def test_success(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "쉬운 요약 내용이에요."
        mock_client.models.generate_content.return_value = mock_response
        result = _generate_summary(mock_client, "기사 제목", "기사 본문")
        assert result == "쉬운 요약 내용이에요."

    def test_api_failure(self) -> None:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        result = _generate_summary(mock_client, "기사 제목", "기사 본문")
        assert result == ""

    @patch("pipeline.summarizer.time.sleep")
    def test_rate_limit_retry(self, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "요약 결과"
        mock_client.models.generate_content.side_effect = [
            Exception("429 Resource exhausted"),
            mock_response,
        ]
        result = _generate_summary(mock_client, "제목", "본문")
        assert result == "요약 결과"
        mock_sleep.assert_called_once()


class TestSummarizeArticles:
    @patch("pipeline.summarizer._init_gemini")
    @patch("pipeline.summarizer._fetch_article_text", return_value="기사 본문")
    @patch("pipeline.summarizer._generate_summary", return_value="쉬운 요약이에요.")
    def test_full_flow(
        self,
        mock_summary: MagicMock,
        mock_fetch: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        articles = [_article("기사1"), _article("기사2")]
        result = summarize_articles(articles)
        assert len(result) == 2
        assert result[0].summary == "쉬운 요약이에요."
        assert result[0]._article_text == "기사 본문"

    @patch("pipeline.summarizer._init_gemini")
    @patch("pipeline.summarizer._fetch_article_text", return_value="")
    def test_skip_no_text(self, mock_fetch: MagicMock, mock_init: MagicMock) -> None:
        articles = [_article("기사1")]
        result = summarize_articles(articles)
        assert len(result) == 0

    @patch("pipeline.summarizer._init_gemini")
    @patch("pipeline.summarizer._fetch_article_text", return_value="본문 있음")
    @patch("pipeline.summarizer._generate_summary", return_value="")
    def test_skip_failed_summary(
        self,
        mock_summary: MagicMock,
        mock_fetch: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        articles = [_article("기사1")]
        result = summarize_articles(articles)
        assert len(result) == 0

    @patch("pipeline.summarizer._init_gemini")
    def test_empty_input(self, mock_init: MagicMock) -> None:
        result = summarize_articles([])
        assert result == []
