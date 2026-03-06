# musicscore

MuseScore 대량 메타데이터 + MusicXML 수집기 (AI 학습용)

**목표**: 10,000곡 이상의 악보 메타데이터 + MusicXML 파일 수집

---

## 디렉토리 구조

```
musicscore/
├── 01_collect_urls.py   # Step 1: 검색 페이지에서 메타데이터 수집
├── 02_download.sh       # Step 2: MusicXML 파일 다운로드
├── NOTES.md             # 시도한 방법들 + 문제점 정리
├── data/
│   ├── urls.jsonl       # 수집된 메타데이터 (JSONL, 한 줄 = 한 곡)
│   └── done_ids.txt     # 다운로드 완료된 ID 목록
├── logs/
│   ├── collect.log      # 수집 로그
│   └── download.log     # 다운로드 로그
└── musicxml/            # 다운로드된 MusicXML 파일들
```

---

## 빠른 시작 (맥북 / Cloudflare 우회 가능한 환경)

### 1. 의존성 설치

```bash
pip install playwright
playwright install chromium
npm install -g dl-librescore
```

### 2. 메타데이터 수집 (Step 1)

```bash
python3 01_collect_urls.py
```

- `data/urls.jsonl`에 누적 저장 (중단 후 재시작 가능)
- 진행 상황: `tail -f logs/collect.log`

### 3. MusicXML 다운로드 (Step 2)

```bash
bash 02_download.sh
```

- `urls.jsonl`의 URL들을 `dl-librescore`로 다운로드
- 완료된 ID는 `data/done_ids.txt`에 기록 (재시작 안전)

---

## 수집 데이터 구조 (urls.jsonl 한 줄 예시)

```json
{
  "url": "https://musescore.com/user/16006641/scores/4197961",
  "id": "4197961",
  "title": "Merry-Go-Round of Life: Howl's Moving Castle Piano Tutorial",
  "author": "PianoChannel",
  "difficulty_label": "Intermediate",
  "difficulty": 3,
  "parts": 1,
  "pages": 7,
  "duration": "05:15",
  "date_added": "Jul 5, 2017",
  "views": 7400000,
  "saves": 254300,
  "collected_at": "2026-03-06T12:37:56.952076"
}
```

---

## 중요: NOTES.md 반드시 읽을 것

Cloudflare 우회 이슈, 시도한 방법들, 현재 동작하는 방법이 정리되어 있음.
