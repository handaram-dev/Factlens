import json
from unittest.mock import MagicMock, patch

from pipeline.models import Article
from pipeline.verifier import (
    _extract_grounding_evidence,
    _parse_verification_response,
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


def _mock_grounding_chunk(title: str, uri: str) -> MagicMock:
    chunk = MagicMock()
    chunk.web.title = title
    chunk.web.uri = uri
    return chunk


def _mock_response(
    text: str,
    grounding_chunks: list[MagicMock] | None = None,
    search_entry_point_html: str = "",
) -> MagicMock:
    """Gemini 응답 mock 생성."""
    response = MagicMock()
    response.text = text

    candidate = MagicMock()
    metadata = MagicMock()

    metadata.grounding_chunks = grounding_chunks or []

    if search_entry_point_html:
        metadata.search_entry_point.rendered_content = search_entry_point_html
    else:
        metadata.search_entry_point = None

    candidate.grounding_metadata = metadata
    response.candidates = [candidate]

    return response


class TestExtractGroundingEvidence:
    def test_success(self) -> None:
        chunks = [
            _mock_grounding_chunk("연합뉴스", "https://yna.co.kr/1"),
            _mock_grounding_chunk("KBS", "https://kbs.co.kr/1"),
        ]
        response = _mock_response("text", grounding_chunks=chunks)
        evidence, sep = _extract_grounding_evidence(response)
        assert len(evidence) == 2
        assert evidence[0]["title"] == "연합뉴스"
        assert evidence[0]["url"] == "https://yna.co.kr/1"

    def test_no_metadata(self) -> None:
        response = MagicMock()
        response.candidates = [MagicMock()]
        response.candidates[0].grounding_metadata = None
        evidence, sep = _extract_grounding_evidence(response)
        assert evidence == []
        assert sep == ""

    def test_search_entry_point(self) -> None:
        response = _mock_response(
            "text",
            search_entry_point_html="<div>Google 검색 위젯</div>",
        )
        evidence, sep = _extract_grounding_evidence(response)
        assert "Google 검색 위젯" in sep

    def test_empty_candidates(self) -> None:
        response = MagicMock()
        response.candidates = []
        evidence, sep = _extract_grounding_evidence(response)
        assert evidence == []
        assert sep == ""


class TestParseVerificationResponse:
    def test_verified(self) -> None:
        response = json.dumps({
            "tag": "verified",
            "reason": "공식 출처로 확인됐어요.",
            "evidence": [{"title": "정부 발표", "url": "https://gov.kr/1"}],
        })
        result = _parse_verification_response(response)
        assert result["tag"] == "verified"
        assert result["reason"] == "공식 출처로 확인됐어요."
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
            "reason": "공식 출처와 내용이 달라요.",
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
        chunks = [_mock_grounding_chunk("출처", "https://example.com")]
        response = _mock_response(
            json.dumps({
                "tag": "verified",
                "reason": "확인됐어요.",
                "evidence": [{"title": "출처A", "url": "https://a.com"}],
            }),
            grounding_chunks=chunks,
            search_entry_point_html="<div>widget</div>",
        )
        mock_client.models.generate_content.return_value = response

        result = _verify_with_gemini(mock_client, "제목", "본문")
        assert result["tag"] == "verified"
        assert result["search_entry_point"] == "<div>widget</div>"
        # JSON evidence + grounding evidence 병합
        assert len(result["evidence"]) >= 1

    def test_grounding_config_passed(self) -> None:
        mock_client = MagicMock()
        response = _mock_response(
            json.dumps({"tag": "verified", "reason": "ok", "evidence": []}),
        )
        mock_client.models.generate_content.return_value = response

        _verify_with_gemini(mock_client, "제목", "본문")
        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs.kwargs.get("config") is not None

    def test_api_failure(self) -> None:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")

        result = _verify_with_gemini(mock_client, "제목", "본문")
        assert result["tag"] == "unconfirmed"

    @patch("pipeline.verifier.time.sleep")
    def test_rate_limit_retry(self, mock_sleep: MagicMock) -> None:
        mock_client = MagicMock()
        response = _mock_response(
            json.dumps({"tag": "verified", "reason": "확인됐어요.", "evidence": []}),
        )
        mock_client.models.generate_content.side_effect = [
            Exception("429 Resource exhausted"),
            response,
        ]

        result = _verify_with_gemini(mock_client, "제목", "본문")
        assert result["tag"] == "verified"
        mock_sleep.assert_called_once()

    def test_merges_evidence_without_duplicates(self) -> None:
        mock_client = MagicMock()
        chunks = [_mock_grounding_chunk("출처A", "https://a.com")]
        response = _mock_response(
            json.dumps({
                "tag": "verified",
                "reason": "ok",
                "evidence": [{"title": "출처A", "url": "https://a.com"}],
            }),
            grounding_chunks=chunks,
        )
        mock_client.models.generate_content.return_value = response

        result = _verify_with_gemini(mock_client, "제목", "본문")
        urls = [e["url"] for e in result["evidence"]]
        assert urls.count("https://a.com") == 1


class TestVerifyArticles:
    @patch("pipeline.verifier._init_gemini")
    @patch("pipeline.verifier._verify_with_gemini")
    def test_full_flow(
        self,
        mock_verify: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        mock_verify.return_value = {
            "tag": "verified",
            "reason": "확인됐어요.",
            "evidence": [{"title": "출처", "url": "https://example.com"}],
            "search_entry_point": "<div>widget</div>",
        }
        articles = [_article("기사1"), _article("기사2")]
        result = verify_articles(articles)
        assert len(result) == 2
        assert result[0].verification_tag == "verified"
        assert result[0].verification_reason == "확인됐어요."
        assert len(result[0].evidence_links) == 1
        assert result[0].evidence_links[0].title == "출처"
        assert result[0].search_entry_point == "<div>widget</div>"

    @patch("pipeline.verifier._init_gemini")
    @patch("pipeline.verifier._verify_with_gemini")
    def test_all_tagged(
        self,
        mock_verify: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        mock_verify.return_value = {
            "tag": "unconfirmed",
            "reason": "확인 안 됨",
            "evidence": [],
            "search_entry_point": "",
        }
        articles = [_article("기사1"), _article("기사2"), _article("기사3")]
        result = verify_articles(articles)
        assert len(result) == 3
        for article in result:
            assert article.verification_tag != ""

    @patch("pipeline.verifier._init_gemini")
    @patch("pipeline.verifier._verify_with_gemini")
    def test_fallback_on_failure(
        self,
        mock_verify: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        mock_verify.return_value = {
            "tag": "unconfirmed",
            "reason": "이 브리핑 시점에 AI가 충분히 확인하지 못했어요.",
            "evidence": [],
            "search_entry_point": "",
        }
        articles = [_article("기사1")]
        result = verify_articles(articles)
        assert result[0].verification_tag == "unconfirmed"

    @patch("pipeline.verifier._init_gemini")
    def test_empty_input(self, mock_init: MagicMock) -> None:
        result = verify_articles([])
        assert result == []
