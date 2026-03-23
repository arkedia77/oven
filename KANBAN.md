# MusicScore (Liszt) KANBAN
업데이트: 2026-03-23 (세션 15 완료)

---

## IN PROGRESS

- [ ] **MuseScore 수동 다운로드** — Leo — 매일 20개

---

## TODO

- [ ] **V7 청취 피드백** — Leo — V5 LoRA vs V7 Grid 비교, 멜로디-반주 동기화
- [ ] **NAS 백업 (V5 Pop + V5 LoRA + V6 + V7)** — reklcli
- [ ] **WAN 2.2 / Qwen 다운로드 완료 확인** — reklcli
- [ ] **V8 방향 결정** — Leo/reklcli — V7 피드백 기반
- [ ] **5090 모델 테스트** — reklcli — Wan2.2, FLUX, F5-TTS, Whisper 등
- [ ] **Splice 다운로드** — Leo — Tier1+Tier2 (~1,200개 WAV)
- [ ] **NAS Gitea 설치** — reklcli — DS420+

---

## BLOCKED

(없음)

---

## DONE (최근)

- [x] **V7 Grid 학습 + eval + 대시보드** — reklcli/5090 — 2026-03-23
  - val_loss 1.7322, rep% 0~1.3% (반복 사실상 해결)
  - unique_pitches 60~73, 7 스타일 × 3 = 21 MIDI
- [x] **V7 학습 스크립트 작성 + 시작** — reklcli — 2026-03-23
- [x] **onset quantization 후처리 스크립트** — reklcli — 2026-03-23
  - quantize_onsets.py, V5 LoRA nocturne/classical/waltz에 적용
- [x] **대시보드 대규모 업데이트** — reklcli — 2026-03-23
  - V5 Pop 23 + V5 LoRA 21 + V6 Tempo 30 + Q16 9 + V7 Grid 21 = 104개 MIDI
  - V5 LoRA "실패"->"성공", V6/Q16/V7 탭 추가
- [x] **V6 Tempo 학습 완료** — 5090 — 2026-03-23
- [x] **V5 LoRA 학습 완료** — 5090 — 2026-03-22
- [x] **V5 Pop 학습 완료** — 5090 — 2026-03-21
