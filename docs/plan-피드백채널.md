# Plan — Google Form 피드백 채널 추가

**Date:** 2026-03-02

---

## 목적

홍보 글 게시 전에 유저 피드백 경로를 확보한다.
AI 검증 오류를 사용자가 알려줄 수 있는 통로가 없으면 이탈만 발생하고 개선 데이터를 얻지 못한다.

---

## 사전 준비 (수동)

Google Form을 직접 만들어야 합니다. 아래는 권장 구성:

**폼 제목:** 팩트렌즈 피드백

**질문 구성:**
1. 어떤 종류의 피드백인가요? (객관식)
   - 검증 태그가 잘못된 것 같아요
   - 요약이 이상해요
   - 기능 제안
   - 기타
2. 어떤 기사인가요? (단답형, 선택)
3. 자세히 알려주세요 (장문형, 필수)
4. 연락받을 이메일 (단답형, 선택)

폼을 만든 뒤 공유 URL을 알려주세요. 아래 구현에 반영합니다.

---

## 변경 대상

| 파일 | 변경 내용 |
|------|-----------|
| `templates/index.html.j2` | footer에 피드백 링크 추가 |
| `static/style.css` | `.feedback-link` 스타일 추가 |

---

## 변경 내용

### 1. `templates/index.html.j2` — footer 수정

**Before (118~123행):**
```html
<footer class="site-footer">
    <p class="disclaimer">AI 기반 자동 검증이며, 최종 판단은 독자의 몫입니다.</p>
    <a class="support-link" href="https://buymeacoffee.com/handaram" target="_blank" rel="noopener">
        가짜뉴스 없는 세상, 후원으로 함께 만들어주세요
    </a>
</footer>
```

**After:**
```html
<footer class="site-footer">
    <p class="disclaimer">AI 기반 자동 검증이며, 최종 판단은 독자의 몫입니다.</p>
    <div class="footer-actions">
        <a class="support-link" href="https://buymeacoffee.com/handaram" target="_blank" rel="noopener">
            가짜뉴스 없는 세상, 후원으로 함께 만들어주세요
        </a>
        <a class="feedback-link" href="{GOOGLE_FORM_URL}" target="_blank" rel="noopener"> //그러면 의견 보내기 버튼이 맨 밑에 있는거야? 그 방식이 최선일까? 계속 따라오게 하는건? 사용자 경험을 저해할까? 
            의견 보내기
        </a>
    </div>
</footer>
```

### 2. `static/style.css` — 스타일 추가

`.support-link:hover` 블록 뒤에 추가:

```css
.footer-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.feedback-link {
  display: inline-block;
  font-size: 0.85rem;
  color: #666;
  padding: 6px 14px;
  border: 1px solid #ccc;
  border-radius: 8px;
}

.feedback-link:hover {
  color: #333;
  border-color: #999;
  text-decoration: none;
}
```

---

## 변경하지 않는 것

- Python 코드 — 변경 없음
- 테스트 — HTML/CSS만 변경이라 기존 테스트에 영향 없음
- 후원 링크 — 기존 위치/스타일 유지, 감싸는 div만 추가

---

## 검증 방법

1. 기존 테스트 81개 통과 확인 (`pytest`)
2. `workflow_dispatch` 실행 → `dist/index.html`에 피드백 링크가 포함되는지 확인
3. 배포 후 링크 클릭 → Google Form으로 정상 이동하는지 확인
