import logging
import time
import uuid
from html.parser import HTMLParser

import feedparser

from pipeline.models import Article, SourceArticle

logger = logging.getLogger(__name__)

TOPIC_FEEDS: list[str] = [
    "https://news.google.com/rss/headlines/section/topic/NATION?hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko",
]

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2


class _ClusterHTMLParser(HTMLParser):
    """description HTML에서 클러스터 기사 링크를 추출하는 파서."""

    def __init__(self) -> None:
        super().__init__()
        self.articles: list[SourceArticle] = []
        self._current_url: str = ""
        self._current_title: str = ""
        self._in_a_tag: bool = False
        self._in_font_tag: bool = False
        self._current_publisher: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._in_a_tag = True
            for name, value in attrs:
                if name == "href" and value:
                    self._current_url = value
        elif tag == "font":
            self._in_font_tag = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_a_tag = False
        elif tag == "font":
            self._in_font_tag = False
            if self._current_url and self._current_publisher:
                self.articles.append(
                    SourceArticle(
                        publisher=self._current_publisher,
                        url=self._current_url,
                    )
                )
            self._current_url = ""
            self._current_title = ""
            self._current_publisher = ""

    def handle_data(self, data: str) -> None:
        if self._in_a_tag:
            self._current_title += data
        elif self._in_font_tag:
            self._current_publisher += data


def _fetch_rss(url: str, max_retries: int = MAX_RETRIES) -> list[feedparser.FeedParserDict]:
    """RSS 피드를 가져와 엔트리 리스트 반환. 실패 시 재시도."""
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                raise ValueError(f"RSS 파싱 실패: {feed.bozo_exception}")

            if feed.bozo:
                logger.warning("RSS 파싱 경고 (계속 진행): %s", feed.bozo_exception)

            return list(feed.entries)
        except Exception as e:
            last_error = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "RSS 가져오기 실패 (시도 %d/%d): %s, %d초 후 재시도",
                attempt + 1, max_retries, e, delay,
            )
            time.sleep(delay)

    logger.error("RSS 가져오기 최종 실패: %s", last_error)
    return []


def _decode_google_news_url(encoded_url: str) -> str:
    """Google News 인코딩 URL을 원본 기사 URL로 디코딩."""
    try:
        from googlenewsdecoder import new_decoderv1

        decoded = new_decoderv1(encoded_url, interval=0.5)
        if decoded.get("status"):
            return str(decoded["decoded_url"])
    except Exception as e:
        logger.warning("URL 디코딩 실패: %s — %s", encoded_url[:80], e)

    return ""


def _strip_publisher_from_title(title: str) -> str:
    """RSS title에서 ' - 언론사명' 접미사를 제거하여 순수 제목만 반환."""
    last_dash = title.rfind(" - ")
    if last_dash > 0:
        return title[:last_dash].strip()
    return title.strip()


def _parse_cluster_articles(description_html: str) -> list[SourceArticle]:
    """description HTML에서 클러스터 관련 기사 링크 추출."""
    if not description_html:
        return []

    parser = _ClusterHTMLParser()
    try:
        parser.feed(description_html)
    except Exception as e:
        logger.warning("클러스터 HTML 파싱 실패: %s", e)
        return []

    return parser.articles


def _parse_entry(entry: feedparser.FeedParserDict) -> Article:
    """feedparser 엔트리를 Article 객체로 변환."""
    raw_title: str = entry.get("title", "")
    headline = _strip_publisher_from_title(raw_title)

    google_news_url: str = entry.get("link", "")
    original_url = _decode_google_news_url(google_news_url)

    publisher = ""
    source = entry.get("source", {})
    if hasattr(source, "get"):
        publisher = source.get("title", "")
    elif hasattr(source, "title"):
        publisher = source.title

    published_at = ""
    if entry.get("published"):
        published_at = str(entry["published"])

    description: str = entry.get("summary", "") or entry.get("description", "")
    source_articles = _parse_cluster_articles(description)

    return Article(
        id=str(uuid.uuid4()),
        headline=headline,
        google_news_url=google_news_url,
        original_url=original_url,
        published_at=published_at,
        publisher=publisher,
        source_articles=source_articles,
    )


def collect_news() -> list[list[Article]]:
    """Google News 토픽별 RSS 3개에서 뉴스를 수집하여 피드별 Article 리스트로 반환."""
    all_feeds: list[list[Article]] = []

    for feed_url in TOPIC_FEEDS:
        entries = _fetch_rss(feed_url)
        if not entries:
            logger.warning("피드에서 엔트리를 가져오지 못함: %s", feed_url[:60])
            all_feeds.append([])
            continue

        articles: list[Article] = []
        for entry in entries:
            try:
                article = _parse_entry(entry)
                if article.headline:
                    articles.append(article)
            except Exception as e:
                logger.warning("엔트리 파싱 실패: %s", e)
                continue

        logger.info("피드에서 %d개 기사 수집: %s", len(articles), feed_url[:60])
        all_feeds.append(articles)

    return all_feeds
