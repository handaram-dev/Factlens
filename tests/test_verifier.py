import json
from unittest.mock import MagicMock, patch

from pipeline.models import Article
from pipeline.verifier import (
    _build_search_context,
    _parse_verification_response,
    _search_google,
    _verify_with_gemini,
    verify_articles,
)


def _article(
    headline: str = "테스트 기사",
    article_text: str = "기사 본문 내용",
) -> Article:
    a = Article(id="test-id", headline=headline, original_url="https://example.com/1")
    a._article_text = article_text
    return a


def _search_result(title: str = "관련 기사", url: str = "https://example.com") -> dict[str, str]:
    return {"title": title, "url": url, "snippet": "관련 내용 스니펫"}


class TestSearchGoogle:
    @patch("pipeline.verifier.requests.get")
    def test_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {"title": "기사1", "link": "https://a.com", "snippet": "내용1"},
                {"title": "기사2", "link": "https://b.com", "snippet": "내용2"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with patch.dict("os.environ", {"GOOGLE_CSE_API_KEY": "key", "GOOGLE_CSE_CX": "cx"}):
            result = _search_google("테스트 쿼리")
        assert len(result) == 2
        assert result[0]["title"] == "기사1"
        assert result[0]["url"] == "https://a.com"

    @patch("pipeline.verifier.requests.get", side_effect=Exception("network error"))
    def test_failure(self, mock_get: MagicMock) -> None:
        with patch.dict("os.environ", {"GOOGLE_CSE_API_KEY": "key", "GOOGLE_CSE_CX": "cx"}):
            result = _search_google("테스트 쿼리")
        assert result == []

    def test_missing_env(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = _search_google("테스트 쿼리")
        assert result == []


class TestBuildSearchContext:
    def test_with_results(self) -> None:
        results = [_search_result("기사A", "https://a.com")]
        context = _build_search_context(results)
        assert "기사A" in context
        assert "https://a.com" in context

    def test_empty_results(self) -> None:
        context = _build_search_context([])
        assert context == "(검색 결과 없음)"


class TestParseVerificationResponse:
    def test_verified(self) -> None:
        response = json.dumps({
            "tag": "verified",
            "reason": "다수 언론이 동일하게 보도했어요.",
            "evidence": [{"title": "연합뉴스", "url": "https://yna.co.kr/1"}],
        })
        result = _parse_verification_response(response)
        assert result["tag"] == "verified"
        assert result["reason"] == "다수 언론이 동일하게 보도했어요."
        assert len(result["evidence"]) == 1

    def test_unconfirmed(self) -> None:
        response = json.dumps({
            "tag": "unconfirmed",
            "reason": "확인할 출처가 부족해요.",
            "evidence": [],
        })
        result = _parse_verification_response(response)
        assert result["tag"] == "unconfirmed"

    def test_misleading(self) -> None:
        response = json.dumps({
            "tag": "misleading",
            "reason": "다른 보도와 내용이 달라요.",
            "evidence": [{"title": "공식 발표", "url": "https://gov.kr/1"}],
        })
        result = _parse_verification_response(response)
        assert result["tag"] == "misleading"

    def test_invalid_json(self) -> None:
        result = _parse_verification_response("이건 JSON이 아닙니다")
        assert result["tag"] == "unconfirmed"
        assert "충분히 확인하지 못했어요" in result["reason"]

    def test_invalid_tag(self) -> None:
        response = json.dumps({"tag": "unknown_tag", "reason": "이유", "evidence": []})
        result = _parse_verification_response(response)
        assert result["tag"] == "unconfirmed"

    def test_markdown_code_block(self) -> None:
        response = '```json\n{"tag": "verified", "reason": "확인됐어요.", "evidence": []}\n```'
        result = _parse_verification_response(response)
        assert result["tag"] == "verified"


class TestVerifyWithGemini:
    def test_success(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tag": "verified",
            "reason": "확인됐어요.",
            "evidence": [{"title": "출처", "url": "https://example.com"}],
        })
        mock_client.models.generate_content.return_value = mock_response

        result = _verify_with_gemini(mock_client, "제목", "본문", "검색 결과")
        assert result["tag"] == "verified"

    def test_api_failure(self) -> None:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")

        result = _verify_with_gemini(mock_client, "제목", "본문", "검색 결과")
        assert result["tag"] == "unconfirmed"

    @patch("pipeline.verifier.time.sleep")
    def test_rate_limit_retry(self, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tag": "verified", "reason": "확인됐어요.", "evidence": [],
        })
        mock_client.models.generate_content.side_effect = [
            Exception("429 Resource exhausted"),
            mock_response,
        ]

        result = _verify_with_gemini(mock_client, "제목", "본문", "검색 결과")
        assert result["tag"] == "verified"
        mock_sleep.assert_called_once()


class TestVerifyArticles:
    @patch("pipeline.verifier._init_gemini")
    @patch("pipeline.verifier._search_google", return_value=[_search_result()])
    @patch("pipeline.verifier._verify_with_gemini")
    def test_full_flow(
        self,
        mock_verify: MagicMock,
        mock_search: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        mock_verify.return_value = {
            "tag": "verified",
            "reason": "확인됐어요.",
            "evidence": [{"title": "출처", "url": "https://example.com"}],
        }
        articles = [_article("기사1"), _article("기사2")]
        result = verify_articles(articles)
        assert len(result) == 2
        assert result[0].verification_tag == "verified"
        assert result[0].verification_reason == "확인됐어요."
        assert len(result[0].evidence_links) == 1
        assert result[0].evidence_links[0].title == "출처"

    @patch("pipeline.verifier._init_gemini")
    @patch("pipeline.verifier._search_google", return_value=[])
    @patch("pipeline.verifier._verify_with_gemini")
    def test_all_tagged(
        self,
        mock_verify: MagicMock,
        mock_search: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        mock_verify.return_value = {
            "tag": "unconfirmed",
            "reason": "확인 안 됨",
            "evidence": [],
        }
        articles = [_article("기사1"), _article("기사2"), _article("기사3")]
        result = verify_articles(articles)
        assert len(result) == 3
        for article in result:
            assert article.verification_tag != ""

    @patch("pipeline.verifier._init_gemini")
    @patch("pipeline.verifier._search_google", return_value=[])
    @patch("pipeline.verifier._verify_with_gemini")
    def test_fallback_on_failure(
        self,
        mock_verify: MagicMock,
        mock_search: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        mock_verify.return_value = {
            "tag": "unconfirmed",
            "reason": "이 브리핑 시점에 AI가 충분히 확인하지 못했어요.",
            "evidence": [],
        }
        articles = [_article("기사1")]
        result = verify_articles(articles)
        assert result[0].verification_tag == "unconfirmed"

    @patch("pipeline.verifier._init_gemini")
    def test_empty_input(self, mock_init: MagicMock) -> None:
        result = verify_articles([])
        assert result == []
