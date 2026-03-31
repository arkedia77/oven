# MusicScore (Liszt) KANBAN
업데이트: 2026-03-31 (세션 22 종료)

---

## IN PROGRESS

- [ ] **Liszt V9 LoRA 학습 (실행 중)** — 5090 schtasks LisztV9Train — E0 loss 1.54↓, ~2시간 후 완료 예상
- [ ] **WAN 2.2 모델 E:→D: 복사** — robocopy 중단됨 (high_noise 완료, low_noise 2/6)
- [ ] **MuseScore 수동 다운로드** — Leo — 매일 20개
- [ ] **키보디스트 인터뷰 v4 준비** — Leo

---

## TODO

- [ ] **V9 학습 결과 확인 + eval** — reklcli — val_loss, 프리픽스별 MIDI 생성
- [ ] **V9 대시보드 배포** — reklcli — pop/classical/jazz/composer 비교
- [ ] **WAN I2V 모델 다운로드** — Leo/reklcli — ~110GB, 외장하드 경유
- [ ] **robocopy 재개** — reklcli — 완료 시 WAN 로딩 80분→~10분
- [ ] **FLUX 속도 최적화** — reklcli — fp8/해상도 (장당 34분 → 5분)
- [ ] **ACE-Step 1.5 5090 세팅** — reklcli
- [ ] **V10 form 라벨링** — reklcli — 임베딩 클러스터 기반 자동 분류
- [ ] **NAS 백업 (V5~V9 체크포인트)** — reklcli
- [ ] **KR2 vs US 비교 → 노션** — reklcli
- [ ] **Splice 다운로드** — Leo
- [ ] **NAS Gitea 설치** — reklcli

---

## BLOCKED

- [ ] **diffsinger / stable-audio-open** — Leo — HF gated repo 접근 권한 필요

---

## DONE (최근)

- [x] **Liszt V9 프리픽스 확장 파이프라인 구축** — reklcli — 2026-03-31
  - config 수정 (form 8개 교체 + pop 추가), vocab 리매핑, 데이터 5928+312 준비
  - LoRA + modules_to_save로 새 토큰 임베딩 학습 가능하게 설계
- [x] **WAN 2.2 v4 첫 영상 성공** — reklcli — 2026-03-31
  - 01_intro_theater.mp4 (1.6MB), latents.pt 정상 저장
- [x] **WAN 2.2 v3→v4 버그픽스** — reklcli — 2026-03-30
- [x] **WAN 2.2 T2V 파이프라인 구축** — reklcli — 2026-03-29
- [x] **FLUX MV 키프레임 7장 완성** — reklcli/5090 — 2026-03-29
- [x] **V8 Combined 학습 + 대시보드** — reklcli/5090 — 2026-03-25
