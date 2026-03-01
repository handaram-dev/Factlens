"""팩트렌즈 일일 브리핑 파이프라인.

python -m pipeline.main 으로 실행.
"""

import logging
import sys

from pipeline.collector import collect_news
from pipeline.filter import filter_and_select
from pipeline.renderer import build_briefing, render_html, save_json
from pipeline.summarizer import summarize_articles
from pipeline.verifier import verify_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    """일일 브리핑 파이프라인 전체 실행."""

    # 1. 수집 (3개 토픽 피드)
    logger.info("=== 1단계: 뉴스 수집 ===")
    feeds = collect_news()

    # 2. 필터링/선별 (라운드 로빈, 상위 15개)
    logger.info("=== 2단계: 필터링/선별 ===")
    articles = filter_and_select(feeds)
    if not articles:
        logger.error("선별된 기사가 없습니다. 파이프라인을 종료합니다.")
        sys.exit(1)
    logger.info("선별 완료: %d개 기사", len(articles))

    # 3. 요약 생성 (본문 스크래핑 + Gemini)
    logger.info("=== 3단계: 요약 생성 ===")
    articles = summarize_articles(articles)
    if not articles:
        logger.error("요약된 기사가 없습니다. 파이프라인을 종료합니다.")
        sys.exit(1)
    logger.info("요약 완료: %d개 기사", len(articles))

    # 4. 교차검증 + 태그 부여
    logger.info("=== 4단계: 교차검증 ===")
    articles = verify_articles(articles)
    logger.info("검증 완료: %d개 기사", len(articles))

    # 5. Briefing 객체 생성
    logger.info("=== 5단계: 브리핑 생성 ===")
    briefing = build_briefing(articles)

    # 6. JSON 저장 + HTML 렌더링
    logger.info("=== 6단계: 출력 ===")
    json_path = save_json(briefing)
    html_path = render_html(briefing)

    logger.info("파이프라인 완료!")
    logger.info("  JSON: %s", json_path)
    logger.info("  HTML: %s", html_path)


if __name__ == "__main__":
    run_pipeline()
