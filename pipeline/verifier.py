import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta

from google import genai
from google.genai import types

from pipeline.models import Article, EvidenceLink

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

VERIFY_PROMPT_TEMPLATE = """당신은 뉴스 보도의 신뢰성을 교차확인하는 팩트체커입니다.

중요: 오늘 날짜는 {today}입니다. 너의 사전 학습 데이터는 오래되었을 수 있습니다.
반드시 Google 검색을 실행하여 최신 정보를 확인하고, 검색 결과만을 근거로 판단하세요.
너의 사전 지식에 의존하지 마세요.

## 기사 제목
{headline}

## 기사 본문
{article_text}

## 작업
1. Google 검색으로 이 기사와 관련된 공식 출처(정부 발표, 기관 보도자료, 공식 통계 등)를 찾으세요.
2. 기사 내용이 공식 출처와 일치하는지, 사실 오류가 없는지, 맥락이 누락되지 않았는지 확인하세요.
3. 아래 JSON 형식으로만 응답하세요.

## 출력 형식 (JSON만 출력, 다른 텍스트 없이)
{{"tag": "verified 또는 unconfirmed 또는 misleading", "reason": "판별 근거를 해요체(~에요, ~했어요) 1~2문장으로. 합니다체(~습니다, ~했습니다) 금지. 구체적 사실이나 수치를 근거로 제시", "evidence": [{{"title": "출처 제목", "url": "출처 URL"}}]}}

## 판단 기준
- verified: 공식 출처(정부, 기관, 공식 통계)로 핵심 내용이 뒷받침됨
- unconfirmed: 공식 출처를 찾을 수 없거나 충분히 확인되지 않음
- misleading: 공식 출처와 내용이 다르거나, 사실 오류 포함, 맥락 누락으로 오해 유도
- 확신이 없으면 반드시 unconfirmed으로 판단하세요
- evidence에는 검색에서 실제 비교에 사용한 출처만 포함하세요"""

RATE_LIMIT_RETRY_DELAY = 60
MAX_RETRIES = 3
REQUEST_INTERVAL = 5

UNCONFIRMED_FALLBACK = {
    "tag": "unconfirmed",
    "reason": "이 브리핑 시점에 AI가 충분히 확인하지 못했어요.",
    "evidence": [],
    "search_entry_point": "",
}

VALID_TAGS = {"verified", "unconfirmed", "misleading"}

GROUNDING_CONFIG = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch())]
)


def _init_gemini() -> genai.Client:
    """Gemini 클라이언트 초기화."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다")
    return genai.Client(api_key=api_key)


def _extract_grounding_evidence(
    response: types.GenerateContentResponse,
) -> tuple[list[dict[str, str]], str]:
    """grounding_metadata에서 evidence 링크와 search_entry_point 추출."""
    evidence: list[dict[str, str]] = []
    search_entry_point = ""

    try:
        candidate = response.candidates[0]
        metadata = candidate.grounding_metadata
        if metadata is None:
            return evidence, search_entry_point

        if metadata.grounding_chunks:
            for chunk in metadata.grounding_chunks:
                if chunk.web:
                    evidence.append({
                        "title": chunk.web.title or "",
                        "url": chunk.web.uri or "",
                    })

        if metadata.search_entry_point:
            search_entry_point = metadata.search_entry_point.rendered_content or ""

    except (AttributeError, IndexError) as e:
        logger.warning("grounding_metadata 추출 실패: %s", e)

    return evidence, search_entry_point


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
) -> dict[str, object]:
    """Gemini + Google Search Grounding으로 검증. 파싱된 dict 반환."""
    today = datetime.now(tz=KST).strftime("%Y년 %m월 %d일")
    prompt = VERIFY_PROMPT_TEMPLATE.format(
        today=today,
        headline=headline,
        article_text=article_text[:5000],
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=GROUNDING_CONFIG,
            )

            # grounding_metadata에서 evidence + search_entry_point 추출
            grounding_evidence, search_entry_point = _extract_grounding_evidence(
                response,
            )

            # 텍스트 응답에서 JSON 파싱 (tag, reason, evidence)
            if response.text:
                result = _parse_verification_response(response.text)
            else:
                result = dict(UNCONFIRMED_FALLBACK)

            # grounding evidence를 JSON evidence와 병합 (중복 URL 제거)
            seen_urls = {e["url"] for e in result.get("evidence", []) if isinstance(e, dict)}
            for e in grounding_evidence:
                if e["url"] and e["url"] not in seen_urls:
                    seen_urls.add(e["url"])
                    result.setdefault("evidence", []).append(e)

            result["search_entry_point"] = search_entry_point
            return result

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
    evidence_links, search_entry_point를 채움.
    검증 실패 시 unconfirmed 태그를 보수적으로 부여.

    모든 기사에 태그가 부여된 상태로 반환 (태그 없는 기사 0건 보장).
    """
    client = _init_gemini()

    for article in articles:
        article_text = article._article_text or ""
        verification = _verify_with_gemini(
            client, article.headline, article_text,
        )

        article.verification_tag = str(verification["tag"])
        article.verification_reason = str(verification["reason"])
        article.evidence_links = [
            EvidenceLink(title=e["title"], url=e["url"])
            for e in verification.get("evidence", [])
            if isinstance(e, dict)
        ]
        article.search_entry_point = str(
            verification.get("search_entry_point", "")
        )

        logger.info(
            "검증 완료: %s → %s", article.headline[:40], article.verification_tag,
        )
        time.sleep(REQUEST_INTERVAL)

    logger.info("교차검증 완료: %d 기사", len(articles))
    return articles
