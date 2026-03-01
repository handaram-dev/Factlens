# 프로젝트 진행 상황

## 완료
- [x] 프로젝트 초기화 — requirements.txt, .env.example, .gitignore, CLAUDE.md (2026-03-01)
- [x] 데이터 모델 정의 — pipeline/models.py (2026-03-01)
- [x] RSS 수집 모듈 — pipeline/collector.py + tests 16개 통과 (2026-03-01)
- [x] 필터링/선별 모듈 — pipeline/filter.py + tests 9개 통과 (2026-03-01)
- [x] AI 요약 모듈 — pipeline/summarizer.py + tests 10개 통과 (2026-03-01)
- [x] 교차검증 모듈 — pipeline/verifier.py + tests 18개 통과 (2026-03-01)
- [x] HTML 렌더링 모듈 — pipeline/renderer.py + templates + static + tests 13개 통과 (2026-03-01)
- [x] 파이프라인 통합 — pipeline/main.py + GitHub Actions 워크플로우 (2026-03-01)
- [x] 전체 테스트 — 66개 전부 통과 (2026-03-01)

## 진행중
- [ ] 첫 파이프라인 실행 테스트 (GitHub Actions workflow_dispatch 실행 중)

## 변경사항 로그
- 2026-03-01: google-generativeai → google-genai 마이그레이션 (기존 SDK deprecated)
- 2026-03-01: lxml_html_clean 의존성 추가 (newspaper3k 필수)
- 2026-03-01: .gitignore에서 dist/ 제거 (Cloudflare Pages 배포용 추적 필요)
- 2026-03-01: Gemini API 키 오류 수정 — 클라이언트 ID(gen-lang-client-...)가 아닌 API 키(AIzaSy...)를 사용해야 함
- 2026-03-01: rate limit 대응 — 요청 간 5초 딜레이 추가, 재시도 대기 30초→60초 변경
- 2026-03-01: Gemini 유료 플랜 전환 — 무료 티어 RPM(15) 제한으로 파이프라인 전체 실패, 테스트 기간 pay-as-you-go 사용
- 2026-03-01: Google CSE "전체 웹 검색" 토글 비활성화 이슈 — 2026.01.20부터 신규 엔진은 전체 웹 검색 불가. 주요 뉴스 사이트 16개 도메인 직접 등록으로 해결

## 인프라 설정 완료
- [x] GitHub Secrets 등록 (GEMINI_API_KEY, GOOGLE_CSE_API_KEY, GOOGLE_CSE_CX)
- [x] Google CSE 생성 (cx: 24a7d97e63c824af3, 한국 주요 뉴스 16개 도메인)
- [x] Cloudflare Pages 연동 (factlens.pages.dev, master 브랜치, 빌드 출력: dist/)

## Next Steps
1. 파이프라인 실행 결과 확인 (성공 시 factlens.pages.dev에서 확인)
2. 실제 출력물 확인 후 프롬프트/스타일 튜닝
3. 안정화 후 Gemini 무료 플랜으로 재전환 검토
