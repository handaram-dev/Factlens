import json
import os
import tempfile
from datetime import datetime, timezone, timedelta

from pipeline.models import Article, Briefing, EvidenceLink, SourceArticle
from pipeline.renderer import (
    _briefing_to_dict,
    _format_briefing_title,
    build_briefing,
    render_html,
    save_json,
)


def _article(
    headline: str = "테스트 기사",
    verification_tag: str = "verified",
) -> Article:
    a = Article(
        id="test-id",
        headline=headline,
        summary="쉬운 요약이에요.",
        verification_tag=verification_tag,
        verification_reason="다수 언론이 보도했어요.",
        evidence_links=[EvidenceLink(title="연합뉴스", url="https://yna.co.kr/1")],
        source_articles=[SourceArticle(publisher="조선일보", url="https://chosun.com/1")],
        original_url="https://example.com/1",
        publisher="연합뉴스",
    )
    a._article_text = "내부 본문 텍스트 (직렬화에서 제외되어야 함)"
    return a


def _briefing(articles: list[Article] | None = None) -> Briefing:
    return Briefing(
        date="2026-03-01",
        title="AI가 검증한 오늘의 뉴스 — 3월 1일 (일)",
        articles=articles or [_article()],
        generated_at="2026-03-01T07:00:00+09:00",
    )


KST = timezone(timedelta(hours=9))


class TestFormatBriefingTitle:
    def test_weekday(self) -> None:
        # 2026-03-01 is Sunday (일)
        dt = datetime(2026, 3, 1, 7, 0, 0, tzinfo=KST)
        result = _format_briefing_title(dt)
        assert result == "AI가 검증한 오늘의 뉴스 — 3월 1일 (일)"

    def test_monday(self) -> None:
        dt = datetime(2026, 3, 2, 7, 0, 0, tzinfo=KST)
        result = _format_briefing_title(dt)
        assert result == "AI가 검증한 오늘의 뉴스 — 3월 2일 (월)"


class TestBriefingToDict:
    def test_excludes_article_text(self) -> None:
        briefing = _briefing()
        result = _briefing_to_dict(briefing)
        for article in result["articles"]:
            assert "_article_text" not in article

    def test_includes_all_fields(self) -> None:
        briefing = _briefing()
        result = _briefing_to_dict(briefing)
        assert result["date"] == "2026-03-01"
        assert result["title"] == "AI가 검증한 오늘의 뉴스 — 3월 1일 (일)"
        assert len(result["articles"]) == 1

        article = result["articles"][0]
        assert article["headline"] == "테스트 기사"
        assert article["summary"] == "쉬운 요약이에요."
        assert article["verification_tag"] == "verified"
        assert len(article["evidence_links"]) == 1
        assert len(article["source_articles"]) == 1


class TestSaveJson:
    def test_creates_file(self) -> None:
        briefing = _briefing()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_json(briefing, data_dir=tmpdir)
            assert os.path.exists(path)
            assert path.endswith("2026-03-01.json")

    def test_content(self) -> None:
        briefing = _briefing()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_json(briefing, data_dir=tmpdir)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert data["date"] == "2026-03-01"
            assert len(data["articles"]) == 1
            assert "_article_text" not in data["articles"][0]


class TestRenderHtml:
    def test_creates_file(self) -> None:
        briefing = _briefing()
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
        )
        static_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = render_html(
                briefing,
                templates_dir=templates_dir,
                dist_dir=tmpdir,
                static_dir=static_dir,
            )
            assert os.path.exists(path)
            assert path.endswith("index.html")

    def test_contains_cards(self) -> None:
        briefing = _briefing([_article("기사A"), _article("기사B")])
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
        )
        static_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = render_html(
                briefing,
                templates_dir=templates_dir,
                dist_dir=tmpdir,
                static_dir=static_dir,
            )
            with open(path, encoding="utf-8") as f:
                html = f.read()
            assert "기사A" in html
            assert "기사B" in html
            assert "news-card" in html

    def test_footer(self) -> None:
        briefing = _briefing()
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
        )
        static_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = render_html(
                briefing,
                templates_dir=templates_dir,
                dist_dir=tmpdir,
                static_dir=static_dir,
            )
            with open(path, encoding="utf-8") as f:
                html = f.read()
            assert "최종 판단은 독자의 몫" in html
            assert "buymeacoffee" in html

    def test_verification_tags(self) -> None:
        articles = [
            _article("기사1", verification_tag="verified"),
            _article("기사2", verification_tag="unconfirmed"),
            _article("기사3", verification_tag="misleading"),
        ]
        briefing = _briefing(articles)
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
        )
        static_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = render_html(
                briefing,
                templates_dir=templates_dir,
                dist_dir=tmpdir,
                static_dir=static_dir,
            )
            with open(path, encoding="utf-8") as f:
                html = f.read()
            assert "tag--verified" in html
            assert "tag--unconfirmed" in html
            assert "tag--misleading" in html

    def test_copies_static(self) -> None:
        briefing = _briefing()
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
        )
        static_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            render_html(
                briefing,
                templates_dir=templates_dir,
                dist_dir=tmpdir,
                static_dir=static_dir,
            )
            assert os.path.exists(os.path.join(tmpdir, "static", "style.css"))


class TestBuildBriefing:
    def test_creates_briefing(self) -> None:
        articles = [_article("기사1"), _article("기사2")]
        result = build_briefing(articles)
        assert len(result.articles) == 2
        assert result.date  # YYYY-MM-DD 형식
        assert "AI가 검증한 오늘의 뉴스" in result.title
        assert result.generated_at

    def test_empty_articles(self) -> None:
        result = build_briefing([])
        assert result.articles == []
        assert result.date
