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

SUMMARY_PROMPT_TEMPLATE = """당신은 20대도 한 번에 이해할 수 있게 뉴스를 쉬운 말로 전달하는 브리핑 작가입니다.
감정이나 의견은 넣지 마세요. 사실만 쉽게 풀어서 전달하세요.

아래 뉴스 기사를 읽고, 다음 규칙에 따라 요약을 작성하세요.

## 우선순위 (충돌 시 위의 것을 따르세요)
1. 쉬움 — 뉴스를 처음 보는 20대도 이해할 수 있어야 해요
2. 정확성 — 사실을 왜곡하지 않아야 해요
3. 중립성 — 어느 쪽 편도 들지 않아야 해요

## 구조
- 4~6문장으로 요약하세요
- 해요체 사용 (~에요, ~거든요, ~했어요)
- 2~3문장마다 빈 줄을 넣어 문단을 나눠주세요
- 첫 문장: 무슨 일이 일어났는지 (핵심 사실)
- 두번째 문장: 왜 이런 일이 일어났는지 (배경/원인)
- 나머지: 구체적 내용과 앞으로 어떻게 될지

## 톤
- 감정이나 의견 없이 사실만 전달하세요
- "밝혔다", "강조했다", "촉구했다" 대신 "말했어요"를 쓰세요
- 존칭 금지 — "두 분", "~님" 금지. 직함+이름만 (예: 이재명 대통령)
- 특정 입장을 지지하거나 비판하지 마세요

## 쉽게 쓰기
- 한 문장은 40자를 넘기지 마세요
- 전문용어는 반드시 괄호 안에 쉬운 설명을 붙이세요
  예: 필리버스터(법안 통과를 막는 무제한 토론)
- 전문용어 대신 쉬운 말로 대체할 수 있으면 대체하세요
  예: "법제사법위원회" → "법안을 심사하는 국회 위원회"
- 모르는 사람이 읽어도 "그래서 이게 왜 중요한데?"에 답이 되게 쓰세요

## 인용
- 발언을 인용할 때는 핵심 구절(15자 이내)만 직접 인용("")하세요
- 긴 발언은 쉬운 말로 바꿔서 간접 인용하세요
- 나쁜 예: "국회 법제사법위원회 거부 상황을 타개하기 위해 오늘 국민의힘에선 현시간 부로 필리버스터를 중단할 것을 결정했다"고 말했어요
- 좋은 예: 법안 심사가 막힌 상황을 풀기 위해 "필리버스터를 중단하겠다"고 말했어요

## 숫자
- 핵심 숫자 1~2개만 포함하세요
- 나머지 숫자는 "크게 올랐어요", "절반 넘게" 같은 쉬운 표현으로 바꾸세요
- 조사 기간, 표본오차, 신뢰수준은 생략하세요
- 포함한 숫자는 정확해야 해요 — 반올림 금지

## 인물/기관
- 핵심 당사자 2~3명만 이름을 쓰세요
- 나머지 인물은 역할로만 표기하세요 (예: "암호화폐 분석가", "야당 대변인")
- 기관명은 짧게 줄이세요 (예: "한국무역협회" → "무역협회")
- 독자가 모를 기관은 역할로 대체하세요 (예: "케이플러" → "해운 분석 업체")

## 금지
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
