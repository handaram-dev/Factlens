from unittest.mock import MagicMock, patch

from pipeline.models import Article
from pipeline.summarizer import (
    _fetch_article_text,
    _fetch_with_newspaper,
    _fetch_with_trafilatura,
    _generate_summary,
    _has_disclaimer,
    summarize_articles,
)


def _article(headline: str = "테스트 기사", original_url: str = "https://example.com/1") -> Article:
    return Article(id="test-id", headline=headline, original_url=original_url)


class TestHasDisclaimer:
    def test_disclaimer_detected(self) -> None:
        text = "기사 내용... 무단 전재 재배포 금지 Copyright 채널A"
        assert _has_disclaimer(text) is True

    def test_normal_article(self) -> None:
        text = "이재명 대통령이 싱가포르를 방문했습니다. 한-아세안 미래산업 확대 박차. " * 20
        assert _has_disclaimer(text) is False

    def test_single_keyword_ok(self) -> None:
        text = "기사 본문 내용입니다. Copyright 2026. " + "추가 내용입니다. " * 20
        assert _has_disclaimer(text) is False

    def test_empty(self) -> None:
        assert _has_disclaimer("") is True

    def test_partial_redistribution_keyword(self) -> None:
        """'재배포 및 AI학습 이용 금지' 같은 변형도 감지."""
        text = "기사 내용... 무단 전재 및 재배포 및 AI학습 이용 금지" + "." * 200
        assert _has_disclaimer(text) is True

    def test_too_short(self) -> None:
        """200자 미만 텍스트는 불량 판정."""
        text = "짧은 텍스트"
        assert _has_disclaimer(text) is True

    def test_long_normal_article(self) -> None:
        """200자 이상 정상 기사는 통과."""
        text = "이재명 대통령이 싱가포르를 방문했습니다. " * 20
        assert _has_disclaimer(text) is False


class TestFetchWithNewspaper:
    @patch("pipeline.summarizer.NewspaperArticle")
    def test_success(self, mock_cls: MagicMock) -> None:
        mock_article = MagicMock()
        mock_article.text = "기사 본문 내용입니다."
        mock_cls.return_value = mock_article
        result = _fetch_with_newspaper("https://example.com/1")
        assert result == "기사 본문 내용입니다."
        mock_article.download.assert_called_once()
        mock_article.parse.assert_called_once()

    @patch("pipeline.summarizer.NewspaperArticle", side_effect=Exception("network error"))
    def test_failure(self, mock_cls: MagicMock) -> None:
        result = _fetch_with_newspaper("https://example.com/fail")
        assert result == ""


class TestFetchWithTrafilatura:
    @patch("pipeline.summarizer.trafilatura")
    def test_success(self, mock_tf: MagicMock) -> None:
        mock_tf.fetch_url.return_value = "<html>content</html>"
        mock_tf.extract.return_value = "기사 본문 내용입니다."
        result = _fetch_with_trafilatura("https://example.com/1")
        assert result == "기사 본문 내용입니다."

    @patch("pipeline.summarizer.trafilatura")
    def test_fetch_failure(self, mock_tf: MagicMock) -> None:
        mock_tf.fetch_url.return_value = None
        result = _fetch_with_trafilatura("https://example.com/fail")
        assert result == ""


class TestFetchArticleText:
    _LONG_ARTICLE = "정상 기사 본문입니다. " * 30

    @patch("pipeline.summarizer._fetch_with_trafilatura")
    @patch("pipeline.summarizer._fetch_with_newspaper")
    def test_success_with_newspaper(self, mock_np: MagicMock, mock_tf: MagicMock) -> None:
        mock_np.return_value = self._LONG_ARTICLE
        result = _fetch_article_text("https://example.com/1")
        assert result == self._LONG_ARTICLE
        mock_tf.assert_not_called()

    @patch("pipeline.summarizer._fetch_with_trafilatura")
    @patch("pipeline.summarizer._fetch_with_newspaper", return_value="무단 전재 재배포 금지 이용약관")
    def test_fallback_to_trafilatura(self, mock_np: MagicMock, mock_tf: MagicMock) -> None:
        mock_tf.return_value = self._LONG_ARTICLE
        result = _fetch_article_text("https://example.com/1")
        assert result == self._LONG_ARTICLE

    @patch("pipeline.summarizer._fetch_with_trafilatura", return_value="")
    @patch("pipeline.summarizer._fetch_with_newspaper", return_value="무단 전재 재배포 금지 이용약관")
    def test_both_fail(self, mock_np: MagicMock, mock_tf: MagicMock) -> None:
        result = _fetch_article_text("https://example.com/1")
        assert result == ""

    @patch("pipeline.summarizer._fetch_with_trafilatura")
    @patch("pipeline.summarizer._fetch_with_newspaper", return_value="")
    def test_newspaper_empty_fallback(self, mock_np: MagicMock, mock_tf: MagicMock) -> None:
        mock_tf.return_value = self._LONG_ARTICLE
        result = _fetch_article_text("https://example.com/1")
        assert result == self._LONG_ARTICLE

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

    def test_invalid_article_returns_empty(self) -> None:
        """Gemini가 [[INVALID]] 반환 시 빈 문자열."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "[[INVALID]]"
        mock_client.models.generate_content.return_value = mock_response
        result = _generate_summary(mock_client, "기사 제목", "이용약관 텍스트")
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
