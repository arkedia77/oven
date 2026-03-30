# MusicScore (Liszt) KANBAN
업데이트: 2026-03-30 (세션 22 진행 중)

---

## IN PROGRESS

- [ ] **WAN 2.2 T2V 첫 영상 생성 (v4 재실행 중)** — 5090 schtasks WAN22MVTestV4 — 20:43 KST 시작, ~03:00 완료 예상
- [ ] **WAN 2.2 모델 E:→D: 복사** — robocopy 중단됨 (high_noise 완료, low_noise 2/6) — 재개 필요
- [ ] **MuseScore 수동 다운로드** — Leo — 매일 20개
- [ ] **키보디스트 인터뷰 v4 준비** — Leo — 이전 인터뷰 내용 공유 대기

---

## TODO

- [ ] **WAN 2.2 v4 영상 결과 확인 + Leo 공유** — reklcli
- [ ] **robocopy 재개 (E:→D: 모델 복사)** — reklcli — 완료 시 로딩 80분→~10분
- [ ] **v4 스크립트 D:경로 전환** — reklcli — robocopy 완료 후
- [ ] **FLUX 속도 최적화** — reklcli — fp8/해상도 조정 (현재 장당 34분 → 목표 5분)
- [ ] **WAN 2.2 I2V 모델 다운로드** — reklcli — E:\models\ 껍데기만 있음
- [ ] **웹툰/댄스 키프레임 생성** — reklcli — "반복되는 꿈", "이 초"
- [ ] **ACE-Step 1.5 5090 세팅** — reklcli — E:\models\ 존재, venv 필요
- [ ] **V8 청취 피드백** — Leo — V5 LoRA vs V7 Grid vs V8 Combined 비교
- [ ] **V9 방향 결정** — Leo/reklcli
- [ ] **NAS 백업 (V5~V8 체크포인트)** — reklcli
- [ ] **KR2 vs US 비교 → 노션 페이지** — reklcli — 노션 MCP 복구 후
- [ ] **Splice 다운로드** — Leo — Tier1+Tier2
- [ ] **NAS Gitea 설치** — reklcli

---

## BLOCKED

- [ ] **diffsinger / stable-audio-open 다운로드** — Leo — HuggingFace gated repo 접근 권한 신청 필요

---

## DONE (최근)

- [x] **WAN 2.2 v3 디퓨전 완료 + v4 버그픽스 재실행** — reklcli — 2026-03-30
  - v3: 40스텝 디퓨전 성공(5시간), save_video 버그로 결과 유실
  - v4: latents 즉시 저장 + manual fallback 추가, 재실행 중
- [x] **VAE decode 파이프라인 테스트 통과** — reklcli — 2026-03-30
- [x] **WAN 2.2 T2V-A14B 5090 파이프라인 구축** — reklcli — 2026-03-29
  - Sequential Load (T5→삭제→DiT bf16), SDPA 폴백 패치, offload 생성 성공
- [x] **FLUX MV 키프레임 7장 완성** — reklcli/5090 — 2026-03-29
  - "불 꺼진 화면" 01~07, 768×1360, 총 4시간 8분
- [x] **FLUX.1-dev 첫 이미지 생성 성공** — reklcli/5090 — 2026-03-28
- [x] **5090 부팅 정리** — reklcli — 2026-03-28
- [x] **MV/웹툰/댄스 테스트 플랜 + 후보곡 선정** — reklcli — 2026-03-28
- [x] **V8 Combined 학습 + eval + 대시보드 배포** — reklcli/5090 — 2026-03-25
