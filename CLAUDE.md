# FactLens (팩트렌즈)

## 프로젝트 개요
AI가 뉴스를 쉬운 말로 요약하고, 팩트체크 검증 태그를 붙여주며, 같은 사건에 대한 다양한 언론사 원문을 나란히 보여주는 중립적 뉴스 브리핑 서비스.

## 기술 스택
- Python 3.12
- feedparser (RSS 파싱)
- google-generativeai (Gemini Flash API)
- newspaper3k (기사 본문 추출)
- requests (Google Custom Search)
- Jinja2 (HTML 템플릿 렌더링)
- pytest (테스트)
- GitHub Actions (스케줄 실행)
- Cloudflare Pages (호스팅)

## 컨벤션
- type hint 필수, any/Unknown 금지
- dataclass 사용 (Pydantic 미사용)
- 모듈별 단일 책임: collector, filter, summarizer, verifier, renderer
- 테스트: pytest, 외부 API 호출은 mock
- 개별 기사 실패가 전체 파이프라인을 중단시키지 않도록 처리
- 환경변수: os.environ으로 직접 접근
- 커밋: Conventional Commits (feat:, fix:, docs: 등)
- Jinja2: 시맨틱 HTML, 접근성 고려
