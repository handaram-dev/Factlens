import json
import logging
import os
import time

import requests
from google import genai

from pipeline.models import Article, EvidenceLink

logger = logging.getLogger(__name__)

VERIFY_PROMPT_TEMPLATE = """당신은 뉴스 보도의 신뢰성을 교차확인하는 팩트체커입니다.
아래 기사를 다른 언론 보도 및 공식 출처와 비교하여, 이 기사가 충분한 근거를 갖고 있는지, 편파적이지 않은지 판단하세요.

## 기사 제목
{headline}

## 기사 본문
{article_text}

## 같은 사건의 다른 보도 및 공식 출처 (검색 결과)
{search_results}

## 작업
1. 이 기사의 내용이 다른 보도 및 공식 출처와 일치하는지 비교하세요.
2. 기사에 근거가 충분한지, 사실 오류가 없는지, 맥락이 누락되지 않았는지 확인하세요.
3. 아래 JSON 형식으로만 응답하세요.

## 출력 형식 (JSON만 출력, 다른 텍스트 없이)
{{"tag": "verified 또는 unconfirmed 또는 misleading", "reason": "판별 근거를 해요체 1~2문장으로 작성", "evidence": [{{"title": "출처 제목", "url": "출처 URL"}}]}}

## 판단 기준
- verified: 다수 언론이 동일한 내용을 보도하고, 공식 출처(정부 발표, 공식 통계 등)로 뒷받침됨
- unconfirmed: 다른 보도나 공식 출처로 충분히 확인되지 않음 (출처 부족, 단독 보도, 아직 확정 안 됨)
- misleading: 다른 보도나 공식 출처와 내용이 다름, 사실 오류 포함, 맥락 누락으로 오해를 유도함
- 확신이 없으면 반드시 unconfirmed으로 판단하세요
- evidence에는 검색 결과에서 실제 비교에 사용한 출처만 포함하세요"""

RATE_LIMIT_RETRY_DELAY = 60
MAX_RETRIES = 3
SEARCH_NUM_RESULTS = 5
REQUEST_INTERVAL = 5

UNCONFIRMED_FALLBACK = {
    "tag": "unconfirmed",
    "reason": "이 브리핑 시점에 AI가 충분히 확인하지 못했어요.",
    "evidence": [],
}

VALID_TAGS = {"verified", "unconfirmed", "misleading"}


def _init_gemini() -> genai.Client:
    """Gemini 클라이언트 초기화."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다")
    return genai.Client(api_key=api_key)


def _search_google(query: str) -> list[dict[str, str]]:
    """Google Custom Search API 호출. 상위 결과 반환.

    각 결과는 {"title": ..., "url": ..., "snippet": ...} 형태.
    """
    api_key = os.environ.get("GOOGLE_CSE_API_KEY", "")
    cx = os.environ.get("GOOGLE_CSE_CX", "")
    if not api_key or not cx:
        logger.warning("Google CSE 환경변수 미설정, 검색 건너뜀")
        return []

    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": cx,
                "q": query,
                "num": SEARCH_NUM_RESULTS,
                "lr": "lang_ko",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in items
        ]
    except Exception as e:
        logger.warning("Google 검색 실패: %s", e)
        return []


def _build_search_context(results: list[dict[str, str]]) -> str:
    """검색 결과를 프롬프트용 텍스트로 포맷팅."""
    if not results:
        return "(검색 결과 없음)"

    lines: list[str] = []
    for i, item in enumerate(results, 1):
        lines.append(
            f"{i}. [{item['title']}]({item['url']})\n   {item['snippet']}"
        )
    return "\n".join(lines)


def _parse_verification_response(response_text: str) -> dict[str, object]:
    """Gemini 응답 JSON 파싱. 실패 시 unconfirmed 기본값 반환."""
    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)

        tag = data.get("tag", "")
        if tag not in VALID_TAGS:
            logger.warning("유효하지 않은 태그: %s → unconfirmed 처리", tag)
            return dict(UNCONFIRMED_FALLBACK)

        reason = str(data.get("reason", ""))
        evidence_raw = data.get("evidence", [])
        evidence: list[dict[str, str]] = []
        if isinstance(evidence_raw, list):
            for item in evidence_raw:
                if isinstance(item, dict) and "title" in item and "url" in item:
                    evidence.append({
                        "title": str(item["title"]),
                        "url": str(item["url"]),
                    })

        return {"tag": tag, "reason": reason, "evidence": evidence}
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning("검증 응답 파싱 실패: %s", e)
        return dict(UNCONFIRMED_FALLBACK)


def _verify_with_gemini(
    client: genai.Client,
    headline: str,
    article_text: str,
    search_context: str,
) -> dict[str, object]:
    """Gemini에 검증 요청. 파싱된 dict 반환."""
    prompt = VERIFY_PROMPT_TEMPLATE.format(
        headline=headline,
        article_text=article_text[:5000],
        search_results=search_context,
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response.text:
                return _parse_verification_response(response.text)
            return dict(UNCONFIRMED_FALLBACK)
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "resource" in error_msg:
                logger.warning(
                    "Rate limit, %d초 후 재시도 (%d/%d)",
                    RATE_LIMIT_RETRY_DELAY, attempt + 1, MAX_RETRIES,
                )
                time.sleep(RATE_LIMIT_RETRY_DELAY)
                continue
            logger.warning("검증 API 호출 실패: %s", e)
            return dict(UNCONFIRMED_FALLBACK)

    logger.error("검증 최종 실패 (rate limit)")
    return dict(UNCONFIRMED_FALLBACK)


def verify_articles(articles: list[Article]) -> list[Article]:
    """각 Article을 교차확인하여 verification_tag, verification_reason,
    evidence_links를 채움. 검증 실패 시 unconfirmed 태그를 보수적으로 부여.

    모든 기사에 태그가 부여된 상태로 반환 (태그 없는 기사 0건 보장).
    """
    client = _init_gemini()

    for article in articles:
        # Google Custom Search 2회 호출
        results_1 = _search_google(article.headline)
        results_2 = _search_google(
            f"{article.headline} 공식 발표 OR 정부 OR 통계"
        )

        # 중복 URL 제거하며 합치기
        seen_urls: set[str] = set()
        combined: list[dict[str, str]] = []
        for item in results_1 + results_2:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                combined.append(item)

        search_context = _build_search_context(combined)

        # Gemini 검증
        article_text = article._article_text or ""
        verification = _verify_with_gemini(
            client, article.headline, article_text, search_context,
        )

        article.verification_tag = str(verification["tag"])
        article.verification_reason = str(verification["reason"])
        article.evidence_links = [
            EvidenceLink(title=e["title"], url=e["url"])
            for e in verification.get("evidence", [])
            if isinstance(e, dict)
        ]

        logger.info(
            "검증 완료: %s → %s", article.headline[:40], article.verification_tag,
        )
        time.sleep(REQUEST_INTERVAL)

    logger.info("교차검증 완료: %d 기사", len(articles))
    return articles
