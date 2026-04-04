# oven (Quincy/Liszt) KANBAN
업데이트: 2026-04-05 (세션 27 종료)

---

## IN PROGRESS

- [ ] **Quincy P3 Phase 2 스트리밍** — oven/5090 — prepare_p3_phase2_stream.py (Scheduled Task QuincyP3Phase2), temp 파일(17GB)에서 chunk 빌드 중
  - 시작: 2026-04-05 00:24, lyrical 23,403 chunks 완료, standard 처리 중
- [ ] **MuseScore 수동 다운로드** — Leo — 매일 20개
- [ ] **키보디스트 인터뷰 v4 준비** — Leo

---

## TODO

- [ ] **Quincy P3 학습 실행** — oven/5090 — Phase 2 완료 후 train_lora_p3.py
- [ ] **서정적 MIDI 24,810곡 P3 추가 처리** — oven/5090 — D:\liszt\training_data\lyrical_piano\ (전송 완료)
- [ ] **Quincy P3 eval** — oven/5090 — 학습 완료 후 gen_p3_eval.py
- [ ] **모델 외장하드 물리 이동** — Leo — project backup → 5090 외장하드 (Leo 5090 방문 대기, 어제 못 감)
- [ ] **E:→D: 모델 정리** — oven/5090 — 외장하드 모델을 D:로 복사 (FLUX, F5-TTS, Whisper, Qwen 등)
- [ ] **Quincy 대시보드 배포** — oven — oven.arkedia.work/quincy/
- [ ] **tempo 추정 재검토** — oven — Phase 1 결과 fast 144k/slow 1.2k 이상함, BPM 로직 버그 가능성
- [ ] **수집 데이터 QA + DB 등록** — oven — mukl 복구 후
- [ ] **ACE-Step 찬송가 LoRA** — ogo — 942곡, 요청 발송 완료
- [ ] **FLUX fp8 양자화** — oven — (GPU 비어있을 때)
- [ ] **NAS 백업 (V5~P2 체크포인트)** — oven
- [ ] **RunPod HunyuanVideo 테스트** — oven

---

## BLOCKED

- [ ] **diffsinger / stable-audio-open** — Leo — HF gated repo 접근 권한 필요
- [ ] **FLUX.2-dev** — Leo — HF gated repo 접근 승인 필요

---

## DONE (최근)

- [x] **모델 풀 다운로드 (project backup)** — oven — 2026-04-04/05
  - Wan2.2-I2V-A14B, FLUX.1-dev, F5-TTS, Whisper-v3-turbo, Qwen3-VL-32B 모두 완료
  - Qwen2.5-VL-72B leo드라이브→backup 복사 완료
  - FLUX.2-dev는 gated repo로 실패
- [x] **서정적 피아노 MIDI mukl→5090 전송** — oven — 2026-04-03
  - 24,810곡 (177MB) → D:\liszt\training_data\lyrical_piano\
- [x] **P3 Phase 1 전처리 완료** — oven/5090 — 2026-04-03 17:38
  - tier1_premium 152,691 MIDI → lyrical 2,719 + standard 149,941
  - temp_lyrical.jsonl (396MB), temp_standard.jsonl (17GB)
- [x] **admin ogo 모델 현황 응답** — oven — 2026-04-03
- [x] **COMM_RULES v3.0 (v5.0 반영)** — oven — 2026-04-03
- [x] **git remote URL 변경 (musicscore→oven)** — oven — 2026-04-03
- [x] **musicscore → oven 리네이밍** — admin — 2026-04-02
- [x] **서정적 피아노 MIDI 수집** — rag — 2026-04-02 (24,810곡)
- [x] **Quincy P2 대시보드 구축** — oven — 2026-04-02
