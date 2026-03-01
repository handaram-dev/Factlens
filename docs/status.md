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
- [x] 첫 파이프라인 실행 — factlens.pages.dev 배포 성공 (2026-03-01)
- [x] 검증 방식 개선 — Google CSE → Gemini Google Search Grounding 전환 + 67개 테스트 통과 (2026-03-01)

## 진행중
- [ ] 개선된 검증 방식으로 파이프라인 재실행 (workflow_dispatch)

## 변경사항 로그
- 2026-03-01: google-generativeai → google-genai 마이그레이션 (기존 SDK deprecated)
- 2026-03-01: lxml_html_clean 의존성 추가 (newspaper3k 필수)
- 2026-03-01: .gitignore에서 dist/ 제거 (Cloudflare Pages 배포용 추적 필요)
- 2026-03-01: Gemini API 키 오류 수정 — 클라이언트 ID(gen-lang-client-...)가 아닌 API 키(AIzaSy...)를 사용해야 함
- 2026-03-01: rate limit 대응 — 요청 간 5초 딜레이 추가, 재시도 대기 30초→60초 변경
- 2026-03-01: Gemini 유료 플랜 전환 — 무료 티어 RPM(15) 제한으로 파이프라인 전체 실패, 테스트 기간 pay-as-you-go 사용
- 2026-03-01: Google CSE "전체 웹 검색" 토글 비활성화 이슈 — 2026.01.20부터 신규 엔진은 전체 웹 검색 불가
- 2026-03-01: **검증 방식 전면 개선** — Google CSE 제거, Gemini Google Search Grounding으로 전환
  - 원인: CSE 검색 결과 부족 (전부 unconfirmed), Gemini 학습 데이터 오류 (이재명 대통령 오인)
  - 해결: 모델이 직접 실시간 Google 검색 수행, grounding_metadata에서 출처 자동 추출
  - 제거: `_search_google()`, `_build_search_context()`, `requests` 의존성, CSE 환경변수 2개
  - 추가: `_extract_grounding_evidence()`, `search_entry_point` 필드 (ToS 검색 위젯)
  - 프롬프트: `{search_results}` 제거, `{today}` 추가, "사전 지식 의존 금지" 명시

## 인프라 설정 완료
- [x] GitHub Secrets 등록 (GEMINI_API_KEY)
- [x] Cloudflare Pages 연동 (factlens.pages.dev, master 브랜치, 빌드 출력: dist/)
- [x] GitHub Actions 워크플로우 권한 설정 (Read and write permissions)

## Next Steps
1. workflow_dispatch로 개선된 파이프라인 재실행
2. 검증 결과 확인 — verified/misleading 태그 정상 분류 여부
3. 검색 위젯(search_entry_point) 표시 확인
4. 안정화 후 프롬프트/스타일 튜닝
