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
- [x] 검증 재실행 — 7개 기사 중 6개 verified, 1개 unconfirmed (JSON 파싱 오류) (2026-03-01)
- [x] UI/UX 개선 + 파싱 품질 강화 — 77개 테스트 통과 (2026-03-01)

## 진행중
- [ ] UI/UX 개선 파이프라인 재실행 (workflow_dispatch)

## 변경사항 로그
- 2026-03-01: google-generativeai → google-genai 마이그레이션 (기존 SDK deprecated)
- 2026-03-01: lxml_html_clean 의존성 추가 (newspaper3k 필수)
- 2026-03-01: .gitignore에서 dist/ 제거 (Cloudflare Pages 배포용 추적 필요)
- 2026-03-01: Gemini API 키 오류 수정 — 클라이언트 ID가 아닌 API 키 사용
- 2026-03-01: rate limit 대응 — 요청 간 5초 딜레이, 재시도 대기 60초
- 2026-03-01: Gemini 유료 플랜 전환 — 무료 티어 RPM 제한, pay-as-you-go 사용
- 2026-03-01: **검증 방식 전면 개선** — Google CSE → Gemini Google Search Grounding
- 2026-03-01: **UI/UX 개선 + 파싱 품질 강화**
  - 출처 토글: `<details>/<summary>`로 기본 접힌 상태, 건수 표시
  - 후원 문구: "가짜뉴스 없는 세상, 후원으로 함께 만들어주세요"
  - 요약 가독성: 프롬프트에 문단 분리 지시, 템플릿에서 `\n\n` → `<p>` 변환
  - 검색 위젯: 토글 내부 배치, `overflow-x: auto` 가로 스크롤
  - unconfirmed 출처 숨김: 확인 못 한 기사에서 출처 링크 미표시
  - 파서 체인: newspaper3k → trafilatura 폴백, 면책 키워드 필터로 잘못된 파싱 감지

## 인프라 설정 완료
- [x] GitHub Secrets 등록 (GEMINI_API_KEY)
- [x] Cloudflare Pages 연동 (factlens.pages.dev, master 브랜치, 빌드 출력: dist/)
- [x] GitHub Actions 워크플로우 권한 설정 (Read and write permissions)

## Next Steps
1. UI/UX 개선 파이프라인 재실행 결과 확인
2. factlens.pages.dev에서 토글, 문단 분리, 후원 문구 확인
3. 파서 체인 작동 확인 (채널A 등 이전 실패 사이트)
4. 안정화 후 추가 튜닝
