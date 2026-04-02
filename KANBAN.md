# MusicScore (Quincy/Liszt) KANBAN
업데이트: 2026-04-02 (세션 26 종료)

---

## IN PROGRESS

- [ ] **Quincy P3 데이터 준비 실행 중** — reklcli/5090 — prepare_p3_data.py 실행 중 (PID 7228), tier1_premium 15만 MIDI 토크나이징
- [ ] **서정적 피아노 MIDI 수집** — rag — 사카모토/이루마/에이나우디/히사이시/닐스프람, 요청 전송 완료
- [ ] **musicscore → oven 리네이밍** — admin 승인 대기
- [ ] **MuseScore 수동 다운로드** — Leo — 매일 20개
- [ ] **키보디스트 인터뷰 v4 준비** — Leo
- [ ] **mukl 서버 다운 복구** — admin — SSH 접속 불가, 보고 완료

---

## TODO

- [ ] **Quincy P3 학습 실행** — reklcli/5090 — prepare 완료 후 train_lora_p3.py 실행
- [ ] **Quincy P3 eval** — reklcli/5090 — 학습 완료 후 gen_p3_eval.py (P2 비교 포함)
- [ ] **Quincy 대시보드 배포** — reklcli — mukl 복구 후 musicscore.arkedia.work/quincy/
- [ ] **수집 데이터 QA + DB 등록** — reklcli — rag 수집 완료 후
- [ ] **tempo B안(BPM 10단위) 또는 포기 결정** — reklcli — P3 결과 후 재검토
- [ ] **WAN I2V 모델 다운로드** — Leo/reklcli — ~110GB
- [ ] **FLUX fp8 양자화** — reklcli — (GPU 비어있을 때)
- [ ] **ACE-Step 1.5 5090 세팅** — reklcli
- [ ] **NAS 백업 (V5~P2 체크포인트)** — reklcli
- [ ] **RunPod HunyuanVideo 테스트** — reklcli

---

## BLOCKED

- [ ] **diffsinger / stable-audio-open** — Leo — HF gated repo 접근 권한 필요

---

## DONE (최근)

- [x] **Quincy P2 대시보드 구축** — reklcli — 2026-04-02
  - dashboard/quincy.html + server.py /quincy/ 라우트, MIDI 재생, 히트맵, tempo 분석
- [x] **P3 학습 파이프라인 준비** — reklcli — 2026-04-02
  - prepare_p3_data.py, train_lora_p3.py, gen_p3_eval.py 작성 + 5090 전송
  - tier1_premium 1.3GB 5090 전송 + 압축해제 (152,691 MIDI)
  - P3 전략: MAESTRO/ATEPP/ASAP 8x 업샘플, jazz 필터링, cosine LR
- [x] **mukl 서버 다운 보고** — reklcli — 2026-04-02
- [x] **P2 eval WAV 75개 변환 + 청취** — reklcli — 2026-04-01
  - tempo A안 실패 확정, 재즈 화성 과다 → 서정적 데이터 보강 결정
- [x] **rag MIDI 수집 요청** — reklcli — 2026-04-01
- [x] **Quincy P2 학습 완료** — reklcli/5090 — 2026-04-01
- [x] **P2 eval 72 MIDI 생성** — reklcli/5090 — 2026-04-01
- [x] **Quincy P1 학습 + eval** — reklcli/5090 — 2026-03-31
