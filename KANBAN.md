# 뮤직스코어 + 피아노 엔진 칸반
업데이트: 2026-03-09 (22시)

---

## 마지막 업데이트: 2026-03-09 세션 종료 (22시)

## ✅ DONE

- [x] PDMX 254,035개 MXL 수집 완료
- [x] GigaMIDI 3,409,419개 압축 해제 완료
- [x] Lakh MIDI 178,561개 압축 해제 완료
- [x] demucs / basic-pitch / pedalboard / pretty_midi 설치
- [x] utils.py 공통 유틸 추출 (02/03/04 스크립트 리팩토링)
- [x] 03_download_api.py — 브라우저 없는 MuseScore 다운로드 (curl_cffi)
- [x] 04_bitmidi.py — BitMIDI 113K 다운로더
- [x] launchd 자동화 — 새벽 2시 URL수집 + 3시 다운로드
- [x] 01_collect_urls.py — 최신순(date_added) 우선으로 쿼리 재정렬
- [x] monitor_bitmidi.py — 3시간마다 진행 체크 + agent-comm 리포트
- [x] agent-comm/musicscore/ 채널 생성
- [x] ENGINE_PLAN.md 작성 (v0.2)
- [x] 엔진 이름 확정: **Liszt** (Franz Liszt, 피아노의 신)
- [x] ASAP + aria-amt 다운로드 시작
- [x] MidiTok 설치 (MIDI 토큰화)
- [x] prepare_piano_data.py 작성 (5090 연결 시 즉시 실행)
- [x] README.md 전면 개편
- [x] 디버그/임시 파일 정리
- [x] **SQLite DB 구축** (build_dataset_db.py) — 875,690개 파일, 453MB
- [x] **venv 생성** + pretty_midi/fastapi/uvicorn/requests 설치
- [x] **대시보드 v1** (dashboard/server.py + index.html + landing.html)
  - 마일스톤 표시, 데이터셋 현황, 품질 분포, 칸반, 파일 뷰어
  - `/` → 공사중 랜딩 ("국산 음악 엔진 개발 중")
  - `/liszt/` → Liszt 대시보드
- [x] **뮤지션 협업 프레임워크** (MUSICIAN_COLLABORATION_GUIDE.md)
- [x] **키보디스트 인터뷰 가이드 v3** (KEYBOARDIST_INTERVIEW_v3.md)
  - MIDI 데이터 4축 기반 (타이밍/강약/음선택/음길이 + 맥락)
- [x] **YouTube 콘텐츠 기획** (YOUTUBE_CONTENT_PLAN.md)
- [x] **Google Drive 백업** — 1. work/claude/musicscore/
- [x] **MAESTRO v3 압축 해제** — 1,276곡 MIDI ✅ (2026-03-09)
- [x] **ATEPP v1.2 다운로드 + 압축 해제** — 12,142곡 MIDI ✅ (2026-03-09)
- [x] **ARIA-MIDI v1-ext 다운로드** — 7.9GB 완료 ✅ (2026-03-09)
- [x] **build_dataset_db.py 업데이트** — GigaMIDI 3개 서브폴더 분리 + MAESTRO 경로 수정 (2026-03-09)
- [x] **huggingface_hub + gdown** venv에 설치 (2026-03-09)

---

## 🔄 IN PROGRESS (백그라운드 실행 중)

- [ ] **DB 재스캔** — reklcli 실행 중 (290K/2.1M 처리, ~540K까지 중복 후 신규 삽입 시작)
  - 담당: reklcli (build_dataset_db.py, PID 43787)
  - 신규 추가 예상: GigaMIDI all-inst 274K + drums 2M + Lakh 나머지 ~100K + MAESTRO 1.2K
  - 로그: ~/musicscore/logs/build_db.log
- [ ] **ARIA-MIDI 압축 해제** — reklcli 백그라운드 (7.9GB tar.gz → /Volumes/data/score/aria-midi/)
  - 담당: reklcli (PID 79739)
  - 로그: ~/musicscore/logs/aria_midi_extract.log
- [ ] **BitMIDI 로컬 다운로드** — reklcli 실행 중 (8,951/113K, p600/7549)
  - 담당: reklcli (04_bitmidi.py, PID 14635)
  - 로그: ~/musicscore/logs/bitmidi.log
- [ ] **BitMIDI mukl 87K** — mukl에 Google Drive 업로드 요청 (agent-comm 태스크 전달)
  - 담당: mukl — 결과 미수신
- [ ] **대시보드 mukl 배포** — agent-comm 태스크 전달 완료, mukl 처리 대기
  - 담당: mukl — 결과 미수신
  - 도메인: musicscore.arkedia.work/liszt/
- [ ] MuseScore MXL 자동 수집 중 (매일 새벽 launchd)

---

## 📋 TODO — 데이터

- [ ] **DB 재스캔 후**: ARIA-MIDI + ATEPP + MAESTRO도 DB에 추가 (압축 해제 완료 후 build_dataset_db.py 재실행)
- [ ] Pop-K MIDI 305K 다운로드 (15개만 받음)
- [ ] MidiCaps 다운로드 (미시작)
- [ ] mukl BitMIDI 87K 수신 → DB 추가
- [ ] 전체 데이터 중복 제거 (MD5 해시 기반)
- [ ] 피아노 MIDI 추출 — ARIA-MIDI + MAESTRO + ATEPP + PDMX 피아노만
- [ ] 품질 필터링 (10초 미만, 손상 파일, 단음 제거)
- [ ] Leo 셀렉 수노 ~3,000곡 태깅 시스템 구축 (수노 DB 이전 후 — 이제 가능하나 직접 접근 불가)

---

## 📋 TODO — 피아노 엔진 (Phase 2)

- [ ] **RTX 5090 서버 환경 세팅** (내일 3/10 연결 예정)
  - CUDA, Python, PyTorch, Aria 라이브러리
- [ ] **Aria 모델 다운로드** (EleutherAI)
- [ ] **피아노 데이터 정제 스크립트** 실행 (prepare_piano_data.py)
- [ ] **Aria 파인튜닝** — ARIA-MIDI + MAESTRO + ATEPP
- [ ] 파인튜닝 결과 → pretty_midi로 MIDI 출력 테스트
- [ ] Pedalboard + 키스케이프 렌더링 파이프라인 구축
- [ ] Leo 직접 청취 퀄리티 평가

---

## 📋 TODO — 뮤지션 협업

- [ ] 피아니스트/키보디스트 인터뷰 진행 (가이드 v3 완성됨)
- [ ] 인터뷰 결과 → KEYBOARDIST_PROFILE.md 작성
- [ ] MIDI 레코딩 수집 (3곡 × 3버전)
- [ ] YouTube 촬영 일정 확정

---

## 📋 TODO — 이후 Phase

- [ ] Phase 3: 밴드 악기 확장 (기타/베이스/드럼)
- [ ] Phase 4: 뮤지션 협업 툴
- [ ] Phase 5: 트로트 전문 모델 (프로 협업)
- [ ] Phase 6: 악기 연습 서비스 (OSMD)
- [ ] Phase 7: 보컬 엔진 (Demucs + Basic Pitch 파이프라인)

---

## 🔗 주요 파일 경로

| 파일 | 경로 |
|------|------|
| 엔진 전체 계획 | `~/musicscore/ENGINE_PLAN.md` |
| 칸반 | `~/musicscore/KANBAN.md` |
| 대시보드 서버 | `~/musicscore/dashboard/server.py` |
| 대시보드 UI | `~/musicscore/dashboard/static/index.html` |
| 키보디스트 인터뷰 | `~/musicscore/KEYBOARDIST_INTERVIEW_v3.md` |
| 뮤지션 협업 가이드 | `~/musicscore/MUSICIAN_COLLABORATION_GUIDE.md` |
| YouTube 기획 | `~/musicscore/YOUTUBE_CONTENT_PLAN.md` |
| DB 구축 스크립트 | `~/musicscore/build_dataset_db.py` |
| 피아노 데이터 정제 | `~/musicscore/prepare_piano_data.py` |
| 데이터 저장 | `/Volumes/data/score/` |
| SQLite DB | `~/musicscore/data/musicscore.db` |
| Google Drive 백업 | `내 드라이브/1. work/claude/musicscore/` |
| agent-comm 채널 | `~/projects/agent-comm/musicscore/` |
