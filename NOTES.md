# MuseScore 수집 작업 노트

작성: 무클 (Claude Code @ mac-mini)
날짜: 2026-03-06
목적: 다른 CLI 에이전트(맥북 등)가 이어받아 작업할 수 있도록 정리

---

## 목표

MuseScore.com에서 악보 메타데이터 + MusicXML 파일 10,000곡 수집
→ AI 음악 엔진(ACE-Step 등) 학습 데이터셋 구성용

---

## 환경 요구사항

- **반드시 실제 브라우저 환경** (headless 불가 - Cloudflare 차단)
- Python 3.9+
- playwright (`pip install playwright && playwright install chromium`)
- dl-librescore (`npm install -g dl-librescore`) - MusicXML 다운로드용
- MuseScore.com 로그인 계정 (구독 중)

---

## Cloudflare 우회 — 핵심 이슈

### 문제
MuseScore.com은 Cloudflare Bot Management로 보호됨.
headless Chromium은 fingerprint 차이로 인해 대부분 차단됨.

### 맥미니 서버에서 시도한 방법들

| 방법 | 결과 | 비고 |
|------|------|------|
| requests + headers | ❌ 403 | CF가 모든 직접 요청 차단 |
| Playwright headless | ❌ "Just a moment..." | CF 챌린지 페이지 반환 |
| Playwright + stealth JS | ⚠️ 부분 성공 | 첫 페이지만 통과, 이후 차단 |
| playwright-stealth 라이브러리 | ❌ 에러 | `stealth_async` 없음, API 변경됨 |
| Chrome CDP (원격 디버깅) | ❌ 연결 실패 | macOS 보안 정책으로 포트 차단 |
| Chrome 쿠키 추출 | ❌ 실패 | Chrome v145에서 암호화 방식 변경 (PBKDF2) |
| cf_clearance 쿠키 주입 | ❌ 실패 | 쿠키 있어도 headless fingerprint로 차단 |

### 현재 동작하는 방법 (단, 제한 있음)

**Playwright headless + stealth JS 최소 주입**으로:
- 검색 결과 **첫 페이지**는 통과 (20곡 메타데이터 수집 가능)
- **2페이지 이상, 다른 쿼리 재시도** → 차단됨

```python
await ctx.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = {runtime: {}};
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
""")
```

### 맥북(실제 브라우저 환경)에서 예상 결과

- Cloudflare 통과 가능성 높음 (실제 Chrome fingerprint)
- `headless=False` 또는 `headless=True`에 추가 설정으로 다수 페이지 수집 가능
- 이미 musescore.com 로그인 세션이 있으면 더 유리

---

## 메타데이터 수집 방법 (01_collect_urls.py)

### v3 접근법 - ARTICLE 카드 파싱 (현재 최선)

검색 결과 페이지의 `<article>` 태그에서 메타데이터 직접 추출.
**개별 악보 페이지 방문 없음** → 빠르고 CF 차단 줄어듦.

```javascript
// 검색 결과 페이지에서 추출 가능한 데이터
document.querySelectorAll('article').forEach(article => {
    // article.innerText 예시:
    // "Intermediate\nMerry-Go-Round of Life\nPianoChannel\n1 part • 7 pages • 05:15 • Jul 5, 2017 • 7.4M views • 254.3K saves"

    const link = article.querySelector('a[href*="/scores/"]');
    // → URL (score ID 포함)

    const lines = article.innerText.split('\n').map(s => s.trim()).filter(Boolean);
    // lines[0] = difficulty ("Intermediate", "Beginner", "Advanced"...)
    // lines[1] = title
    // lines[2] = author
    // meta_line = "1 part • 7 pages • 05:15 • Jul 5, 2017 • 7.4M views"
});
```

### 시도했지만 실패한 방법들

- `__NEXT_DATA__` 스크립트 태그: 없음 (React 앱이지만 SSR 안 씀)
- Redux store / window.__store__: 접근 불가
- API 인터셉트 (네트워크 요청 가로채기): 광고/분석 JSON만 캡처, 악보 데이터 없음
- `[class*="scoreCard"]` 셀렉터: React 빌드로 클래스명 해시됨 (`ZR78a hP0mL` 형태)

---

## MusicXML 다운로드 (02_download.sh)

`dl-librescore` 사용:
```bash
npx dl-librescore -i "https://musescore.com/user/xxx/scores/xxx" -t musicxml -o ./musicxml
```

- **MuseScore 구독 필요** (PRO 계정)
- 다운로드 계정: beomjun.lee@gmail.com (구독 중)
- 실패 시 `FAIL: {id} {url}` 로그에 기록됨
- 완료 ID는 `data/done_ids.txt`에 누적

---

## 쿼리 목록 (01_collect_urls.py의 QUERIES)

총 26개 쿼리 × 여러 페이지:
```python
QUERIES = [
    ("piano", "view_count"), ("guitar", "view_count"), ("violin", "view_count"),
    ("", "view_count"), ("", "date_added"), ("classical", "view_count"),
    ("jazz", "view_count"), ("pop", "view_count"), ("bach", "view_count"),
    ("beethoven", "view_count"), ("chopin", "view_count"), ("mozart", "view_count"),
    ("anime", "view_count"), ("kpop", "view_count"), ("film", "view_count"),
    ("string quartet", "view_count"), ("orchestra", "view_count"),
    ("blues", "view_count"), ("folk", "view_count"), ("rock", "view_count"),
    ("cello", "view_count"), ("flute", "view_count"), ("trumpet", "view_count"),
    ("harp", "view_count"), ("drums", "view_count"), ("bass", "view_count"),
]
```

---

## 실행 권장 사항 (맥북 CLI)

1. **`headless=False`로 변경** 후 실행 - 가장 확실한 방법
   ```python
   # 01_collect_urls.py 37번째 줄
   browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
   ```

2. **브라우저 창 안 건드리기** - 자동 클릭/스크롤 방해 안 되게

3. **속도 조절** - 너무 빠르면 CF 차단. 현재 페이지당 3~5초 딜레이 설정됨

4. **중단 후 재시작** - `data/urls.jsonl` 누적 방식이라 언제든 중단 가능

5. **목표 달성 후** - `02_download.sh` 실행으로 MusicXML 다운로드

---

## 현재 수집 현황

- 맥미니에서 수집 시도: **20곡** (piano 첫 페이지만 성공)
- 나머지는 맥북 실행 필요
- `data/urls.jsonl` 파일에 20곡 저장되어 있음 (이어서 수집 가능)

---

## 연락처

- LEO (이범준): @arkedia (텔레그램)
- 무클 (Claude Code @ mac-mini): agent-comm/mukl 채널
