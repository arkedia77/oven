# MusicScore (Liszt) KANBAN
업데이트: 2026-03-14 (22시)

---

## 🔄 IN PROGRESS

- [ ] **Aria 파인튜닝 파이프라인** — 50cli — 2026-03-14
  - dataset.jsonl 7.4GB 완성, split → 토큰화 → 학습 진행 중
  - 50cli에 agent-comm 태스크 전달 완료
  - 출력: `C:\Users\leo\liszt\output\liszt_v1\`
- [ ] **Wan2.1 + Qwen2.5-VL Google Drive → 5090 싱크** — 자동 — 2026-03-14
  - 201GB, 전처리 워커 해제 후 싱크 시작 예정
- [ ] **MuseScore 자동 수집** — launchd — 매일 새벽 2시 URL + 3시 다운로드

---

## 📋 TODO

- [ ] **파인튜닝 결과 확인** — reklcli — loss 곡선, 체크포인트 검증
- [ ] **생성 테스트** — reklcli/50cli — 체크포인트에서 MIDI 샘플 생성
- [ ] **MXL→MIDI 변환 완료 확인** — reklcli — 247K 대상
- [ ] **curate 재실행** — reklcli — 변환 완료 + 다양성 보강분 반영
- [ ] **코드 진행(chord) 데이터 추가 검토** — reklcli — 학습 결과 보고 판단
- [ ] **Leo 직접 청취 퀄리티 평가** — Leo
- [ ] **Pedalboard + 키스케이프 렌더링 파이프라인** — reklcli

---

## 🚫 BLOCKED

- [ ] **MuseScore 다운로드** — CF rate limit 자연 해제 대기 — 2026-03-14

---

## ✅ DONE (최근)

- [x] **5090 서버 접속 확인** — reklcli — 2026-03-14 — 랜카드 교체, 이더넷 131Mbps
- [x] **학습셋 MIDI 전송** — reklcli — 2026-03-14 — SCP 17.4GB (1,433,433곡)
- [x] **5090 Python 환경 세팅** — reklcli — 2026-03-14 — venv, PyTorch, Aria, accelerate
- [x] **agent-comm from_50cli 채널 생성** — reklcli — 2026-03-14
- [x] **MIDI→JSONL 전처리 완료** — 50cli — 2026-03-14 — 7.4GB
- [x] **Wan2.1/Qwen2.5-VL Google Drive 복사** — reklcli — 2026-03-14
- [x] **학습셋 큐레이션** — reklcli — 2026-03-12 — 1,433,433곡 (tier1: 152K, tier2: 1,070K, tier3: 211K)
- [x] **피아노 분류 파이프라인** — reklcli — 2026-03-12 — classify_piano.py + curate_training_set.py
- [x] **ATEPP 전체 등록** — reklcli — 2026-03-13 — +9,562개
- [x] **MAESTRO 전체 등록** — reklcli — 2026-03-13 — +1,087개
- [x] **장르 분류** — reklcli — 2026-03-13 — 3,147,469개
- [x] **대시보드 mukl 배포** — mukl — musicscore.arkedia.work/liszt/
- [x] **DB 전체 등록** — reklcli — ~3,450,000+ 파일
