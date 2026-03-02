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
- [x] 가독성 전면 개선 + 기사 수 확대 — 디자인 구현, 77개 테스트 통과 (2026-03-01)

- [x] 파싱 실패 감지 강화 — 3층 방어 구현, 81개 테스트 통과 (2026-03-01)
- [x] 광고 플랫폼 도입 — 카카오 AdFit 배너 1개 (7번째 기사 뒤), 81개 테스트 통과 (2026-03-01)
- [x] 론칭 준비 — 파비콘, OG 태그, GA4, Clarity, sitemap.xml, robots.txt (2026-03-02)
- [x] 프롬프트 개선 — 냉철한 톤, 존칭 금지, 직접 인용(""), 숫자 정확 표기, 검증 reason 해요체 통일, 81개 테스트 통과 (2026-03-02)
- [x] 서치 콘솔 등록 — 구글 서치 콘솔 + 네이버 서치어드바이저 인증 완료, 사이트맵 제출 (2026-03-02)
- [x] Buy Me a Coffee 연결 — buymeacoffee.com/handaram 후원 링크 반영 (2026-03-02)
- [x] 프롬프트 재설계 — 쉬움+냉철함 균형, 괄호 설명 의무화, 인용 15자 제한, 숫자 선별, 81개 테스트 통과 (2026-03-02)
- [x] 출처 링크 이모지 제거 — CSS에서 깨진 유니코드(\U0001F4CE) 제거, 클린 리스트로 변경 (2026-03-02)

## 진행중
- [ ] 카카오 AdFit 매체 심사 대기 중 (승인 후 광고 노출)

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
- 2026-03-01: **가독성 전면 개선 + 기사 수 확대**
  - CSS: 배경 #f0f0f0, 카드 radius 16px/border 추가, headline 1.25rem/800, 본문 1rem/#222
  - 섹션 구분선: 요약↔검증, 검증↔원문보기 사이 border-top
  - 태그: pill shape (radius 20px), 색상 강화, misleading에 border 추가
  - word-break: keep-all (한글 어절 단위 줄바꿈)
  - 모바일: padding 16px, 카드 20px/12px, headline 1.125rem
  - 후원 배너: 3번째 기사 뒤 중간 삽입 + footer 유지
  - 기사 수: filter max_count 10 → 15
  - 완료된 research/plan 파일 → docs/archive/ 이동
- 2026-03-01: **파싱 실패 감지 강화** — 3층 방어 전략
  - Layer 1: 키워드 `"재배포 금지"` → `"재배포"` 교체 (변형 매칭)
  - Layer 2: MIN_ARTICLE_LENGTH=200 최소 길이 체크
  - Layer 3: Gemini 프롬프트에 `[[INVALID]]` 반환 규칙 + 감지 처리
- 2026-03-01: **광고 플랫폼 도입** — 카카오 AdFit
  - 7번째 기사 뒤에 320x100 모바일 배너 1개 배치
  - AdFit SDK 스크립트 `<head>`에 추가
- 2026-03-02: **론칭 준비**
  - 파비콘: SVG (돋보기+체크마크)
  - OG 태그: og:title, og:description, og:type, og:url, og:locale, twitter:card
  - GA4 (G-RYQSQF9486) + Microsoft Clarity (vp0n1nogns)
  - sitemap.xml + robots.txt 자동 생성 (renderer.py)
- 2026-03-02: **프롬프트 개선**
  - 요약: 페르소나 "냉철한 작가", 존칭 금지, 중립 동사("말했다"), 직접 인용(""), 숫자 정확 표기
  - 검증: reason 해요체 통일 + 구체적 사실/수치 근거 제시 규칙
- 2026-03-02: **서치 콘솔 + BMC 연결**
  - Google Search Console 인증 (VnZBNB4M...) + 사이트맵 제출
  - Naver Search Advisor 인증 (e956417c...) + 사이트맵 제출
  - Buy Me a Coffee 후원 링크: buymeacoffee.com/handaram
- 2026-03-02: **요약 난이도 리서치** — `docs/research-요약난이도.md`
  - 문제 진단: "정보 압축 vs 정보 번역" — 현재 프롬프트가 신문 기사를 압축만 하고 번역(쉽게 풀어쓰기)을 안 함
  - 5대 원인: 직접 인용 과다, 숫자 전량 포함, 페르소나가 풀어쓰기 억압, 규칙 우선순위 부재, 전문용어 풀이 미실행
  - 벤치마크: 뉴닉/어피티/토스 분석 → "쉬움과 냉철함은 양립 가능"
  - 다음 단계: `plan-프롬프트재설계.md` 작성 → 승인 후 구현
- 2026-03-02: **프롬프트 재설계** — `docs/plan-프롬프트재설계.md`
  - 페르소나: "건조하게 전달" → "쉬운 말로 전달, 감정/의견 금지"
  - 우선순위 명시: 쉬움 > 정확성 > 중립성
  - 인용: 핵심 15자만 직접 인용, 나머지 간접 인용
  - 숫자: 핵심 1~2개만, 나머지 정성적 표현
  - 전문용어: 괄호 설명 의무화 (스드메, 의협, 혁명수비대, 바우처 등 반영 확인)
  - 인물/기관: 2~3명만 이름, 나머지 역할 표기
  - 출력 검증: 9개 기사 모두 규칙 준수 확인
- 2026-03-02: **출처 링크 이모지 제거**
  - CSS `.evidence-list li::before`에서 `\U0001F4CE`(📎) 제거
  - 원인: Python 유니코드 이스케이프가 CSS에서 미지원 → 텍스트 깨짐
  - OS/브라우저별 렌더링 차이 방지 + 토글 내부 시각적 노이즈 감소

## 인프라 설정 완료
- [x] GitHub Secrets 등록 (GEMINI_API_KEY)
- [x] Cloudflare Pages 연동 (factlens.pages.dev, master 브랜치, 빌드 출력: dist/)
- [x] GitHub Actions 워크플로우 권한 설정 (Read and write permissions)

## Next Steps — 론칭 전 필수

1. ~~프롬프트 개선~~ ✅
2. ~~파비콘 제작~~ ✅
3. ~~Open Graph 태그~~ ✅
4. ~~Buy Me a Coffee 연결~~ ✅
5. ~~애널리틱스 설치~~ ✅
6. ~~서치 콘솔 등록~~ ✅
7. ~~속도 점검~~ ✅

## Next Steps — 론칭 후 / 보류

1. Gemini 무료 버전으로 전환 (현재 pay-as-you-go 유료 플랜)
2. AdFit 매체 심사 승인 후 광고 노출 확인
3. PRD 수락 기준 검증 (4.4 체크리스트 점검)
4. 랜딩페이지 제작 — 고민 중
5. 유저 피드백 채널 — 카카오 오픈톡방 버튼
6. 재방문(Sticky) 성장 전략