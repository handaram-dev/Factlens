from dataclasses import dataclass, field


@dataclass
class SourceArticle:
    """언론사 원문 링크."""

    publisher: str
    url: str


@dataclass
class EvidenceLink:
    """검증 근거 출처."""

    title: str
    url: str


@dataclass
class Article:
    """뉴스 카드.

    수집 단계에서는 일부 필드만 채워지고,
    파이프라인 진행에 따라 나머지 필드가 채워진다.
    """

    id: str
    headline: str
    summary: str = ""
    verification_tag: str = ""
    verification_reason: str = ""
    evidence_links: list[EvidenceLink] = field(default_factory=list)
    source_articles: list[SourceArticle] = field(default_factory=list)
    google_news_url: str = ""
    original_url: str = ""
    published_at: str = ""
    publisher: str = ""
    search_entry_point: str = field(default="", repr=False)
    _article_text: str = field(default="", repr=False)


@dataclass
class Briefing:
    """일일 브리핑."""

    date: str
    title: str
    articles: list[Article] = field(default_factory=list)
    generated_at: str = ""
