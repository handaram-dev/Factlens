import json
import logging
import os
import shutil
from datetime import datetime, timezone, timedelta

from jinja2 import Environment, FileSystemLoader

from pipeline.models import Article, Briefing, EvidenceLink, SourceArticle

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def _format_briefing_title(date: datetime) -> str:
    """'2026년 3월 1일 (토) 모닝 브리핑' 형식 제목 생성."""
    weekday = WEEKDAY_KO[date.weekday()]
    return f"{date.year}년 {date.month}월 {date.day}일 ({weekday}) 모닝 브리핑"


def _article_to_dict(article: Article) -> dict[str, object]:
    """Article → JSON 직렬화 가능한 dict. 내부 필드 제외."""
    return {
        "id": article.id,
        "headline": article.headline,
        "summary": article.summary,
        "verification_tag": article.verification_tag,
        "verification_reason": article.verification_reason,
        "evidence_links": [
            {"title": e.title, "url": e.url}
            for e in article.evidence_links
        ],
        "source_articles": [
            {"publisher": s.publisher, "url": s.url}
            for s in article.source_articles
        ],
        "google_news_url": article.google_news_url,
        "original_url": article.original_url,
        "published_at": article.published_at,
        "publisher": article.publisher,
        "search_entry_point": article.search_entry_point,
    }


def _briefing_to_dict(briefing: Briefing) -> dict[str, object]:
    """Briefing → JSON 직렬화 가능한 dict. 내부 필드(_article_text) 제외."""
    return {
        "date": briefing.date,
        "title": briefing.title,
        "generated_at": briefing.generated_at,
        "articles": [_article_to_dict(a) for a in briefing.articles],
    }


def build_briefing(articles: list[Article]) -> Briefing:
    """Article 리스트로 Briefing 객체 생성. 날짜, 제목 자동 설정."""
    now = datetime.now(tz=KST)
    date_str = now.strftime("%Y-%m-%d")
    title = _format_briefing_title(now)
    generated_at = now.isoformat()

    return Briefing(
        date=date_str,
        title=title,
        articles=articles,
        generated_at=generated_at,
    )


def save_json(briefing: Briefing, data_dir: str = DATA_DIR) -> str:
    """Briefing → data/YYYY-MM-DD.json 저장. 저장 경로 반환."""
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"{briefing.date}.json")

    data = _briefing_to_dict(briefing)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("JSON 저장: %s", file_path)
    return file_path


def render_html(
    briefing: Briefing,
    templates_dir: str = TEMPLATES_DIR,
    dist_dir: str = DIST_DIR,
    static_dir: str = STATIC_DIR,
) -> str:
    """Briefing → Jinja2 렌더링 → dist/index.html 저장. 저장 경로 반환."""
    os.makedirs(dist_dir, exist_ok=True)

    # static/ → dist/static/ 복사
    dist_static = os.path.join(dist_dir, "static")
    if os.path.exists(static_dir):
        if os.path.exists(dist_static):
            shutil.rmtree(dist_static)
        shutil.copytree(static_dir, dist_static)

    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=True,
    )
    template = env.get_template("index.html.j2")

    briefing_dict = _briefing_to_dict(briefing)
    html = template.render(briefing=briefing_dict)

    output_path = os.path.join(dist_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # sitemap.xml 생성
    sitemap_path = os.path.join(dist_dir, "sitemap.xml")
    sitemap_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        "    <loc>https://factlens.pages.dev/</loc>\n"
        f"    <lastmod>{briefing.date}</lastmod>\n"
        "    <changefreq>daily</changefreq>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap_content)

    # robots.txt 생성
    robots_path = os.path.join(dist_dir, "robots.txt")
    robots_content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Sitemap: https://factlens.pages.dev/sitemap.xml\n"
    )
    with open(robots_path, "w", encoding="utf-8") as f:
        f.write(robots_content)

    logger.info("HTML 렌더링 완료: %s", output_path)
    return output_path
