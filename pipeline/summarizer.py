import logging
import os
import time

import trafilatura
from google import genai
from newspaper import Article as NewspaperArticle

from pipeline.models import Article

logger = logging.getLogger(__name__)

DISCLAIMER_KEYWORDS = {"무단 전재", "재배포", "이용약관", "저작권자", "Copyright"}
MIN_ARTICLE_LENGTH = 200

SUMMARY_PROMPT_TEMPLATE = """당신은 뉴스를 쉽게 풀어서 설명해주는 뉴스 브리핑 작가입니다.

아래 뉴스 기사를 읽고, 다음 규칙에 따라 쉬운 요약을 작성하세요.

## 규칙
- 해요체로 작성 (~에요, ~거든요, ~했어요)
- 3~5문장으로 핵심만 요약
- 전문용어 사용 금지 — 어려운 개념은 일상적인 비유로 풀어쓰기
- 2~3문장마다 빈 줄을 넣어 문단을 나눠주세요
- 배경 맥락이 필요하면 "이게 왜 중요하냐면" 식으로 먼저 깔아주기
- 의견이나 감정 표현 없이 사실만 전달
- 특정 언론사나 정치적 입장을 지지하거나 비판하지 않기
- 만약 아래 본문이 뉴스 기사가 아니라 이용약관, 면책 조항, 로그인 페이지 등이면 '[[INVALID]]'만 출력하세요

## 기사 제목
{headline}

## 기사 본문
{article_text}

## 출력
요약문만 작성하세요. 다른 설명이나 서문 없이 요약문만 출력하세요."""

RATE_LIMIT_RETRY_DELAY = 60
MAX_RETRIES = 3
REQUEST_INTERVAL = 5


def _init_gemini() -> genai.Client:
    """Gemini 클라이언트 초기화."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다")
    return genai.Client(api_key=api_key)


def _has_disclaimer(text: str) -> bool:
    """추출 텍스트가 불량인지 판별. 최소 길이 미달 또는 면책 키워드 2개 이상이면 True."""
    if not text or len(text) < MIN_ARTICLE_LENGTH:
        return True
    matches = sum(1 for kw in DISCLAIMER_KEYWORDS if kw in text)
    return matches >= 2


def _fetch_with_newspaper(url: str) -> str:
    """newspaper3k로 기사 본문 추출."""
    try:
        article = NewspaperArticle(url)
        article.download()
        article.parse()
        return article.text or ""
    except Exception as e:
        logger.warning("newspaper3k 추출 실패: %s — %s", url[:80], e)
        return ""


def _fetch_with_trafilatura(url: str) -> str:
    """trafilatura로 기사 본문 추출 (폴백)."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded) or ""
        return ""
    except Exception as e:
        logger.warning("trafilatura 추출 실패: %s — %s", url[:80], e)
        return ""


def _fetch_article_text(url: str) -> str:
    """URL에서 기사 본문 텍스트 추출. newspaper3k → trafilatura 폴백 체인."""
    if not url:
        return ""

    text = _fetch_with_newspaper(url)
    if text and not _has_disclaimer(text):
        return text

    logger.info("newspaper3k 결과 불량, trafilatura로 재시도: %s", url[:80])
    text = _fetch_with_trafilatura(url)
    if text and not _has_disclaimer(text):
        return text

    return ""


def _generate_summary(
    client: genai.Client,
    headline: str,
    article_text: str,
) -> str:
    """Gemini Flash API로 쉬운 요약 생성."""
    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        headline=headline,
        article_text=article_text[:5000],
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response.text:
                stripped = response.text.strip()
                if "[[INVALID]]" in stripped:
                    logger.warning("Gemini가 비정상 본문 감지: %s", headline[:40])
                    return ""
                return stripped
            return ""
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "resource" in error_msg:
                logger.warning(
                    "Rate limit, %d초 후 재시도 (%d/%d)",
                    RATE_LIMIT_RETRY_DELAY, attempt + 1, MAX_RETRIES,
                )
                time.sleep(RATE_LIMIT_RETRY_DELAY)
                continue
            logger.warning("요약 생성 실패: %s", e)
            return ""

    logger.error("요약 생성 최종 실패 (rate limit)")
    return ""


def summarize_articles(articles: list[Article]) -> list[Article]:
    """각 Article의 original_url에서 본문을 가져와 Gemini로 요약 생성.

    summary 필드와 _article_text 필드를 채운다.
    요약 실패한 기사는 리스트에서 제외.
    """
    client = _init_gemini()
    result: list[Article] = []

    for article in articles:
        text = _fetch_article_text(article.original_url)
        if not text:
            text = _fetch_article_text(article.google_news_url)

        if not text:
            logger.warning("기사 본문 없음, 스킵: %s", article.headline[:40])
            continue

        article._article_text = text

        summary = _generate_summary(client, article.headline, text)
        if not summary:
            logger.warning("요약 생성 실패, 스킵: %s", article.headline[:40])
            continue

        article.summary = summary
        result.append(article)
        logger.info("요약 완료: %s", article.headline[:40])
        time.sleep(REQUEST_INTERVAL)

    logger.info("요약 완료: %d/%d 기사", len(result), len(articles))
    return result
