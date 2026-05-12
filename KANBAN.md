# oven (Quincy/Liszt) KANBAN
업데이트: 2026-05-12 (세션 48)

---

## IN PROGRESS

- [ ] **하모니 시티 가상 마을 시뮬레이션** — oven — 2026-05-12
  - ✅ 프로토타입 v1 (4인, 23라운드) 완료 — 반복 문제 확인
  - ✅ v2 설계+구현 완료 (10인, 7장소, 욕구/신념/목표 시스템)
  - ✅ v3 수정 완료 (욕구 고갈 버그, affection 추가, tension 감쇠)
  - ✅ 세션 47 결과 노션 보고서 업로드 완료
  - ✅ 백그라운드 실행 중 (PID 65240, Day 33+ Tick 769+)
  - **TODO**: security/autonomy 균형 확인, affection 분포 검증, 장기 서사 분석
- [x] **Gemma 4 MTP 속도 향상** — oven/5090 — 2026-05-09 **BLOCKED→보류**
  - ✅ atomic-llama-cpp-turboquant 포크 CUDA 13.x + 12.8 양쪽 빌드 완료
  - ✅ drafter 모델 다운로드 완료 (gemma-4-26B-A4B-it-assistant Q4_K_M, 310MB)
  - ✅ 공식 최신 llama.cpp 빌드 완료 (MTP 미지원 확인)
  - ❌ CUDA 13.x: MTP+FA on 크래시 / MTP+FA off 속도향상 없음 (181.9 tok/s)
  - ❌ CUDA 12.8: MTP+FA on/off 모두 추론 크래시 (더 불안정)
  - **결론**: atomic fork MTP 구현이 Blackwell SM120 비호환. 공식 llama.cpp MTP PR 머지 대기
- [ ] **Gemma 4 리서치 오케스트레이터 개선** — oven — 2026-05-09
  - ✅ 검색 보강 v3 실행 → leomusic-base 평가 4.5/10 (v1 대비 +1.5)
  - ✅ Wikipedia User-Agent 버그 수정
  - ✅ Semantic Scholar 재시도 로직 추가
  - TODO: instruction following 강화, RAG 소스 고급화, 자기비평 루프
- [ ] **Gemma 4 루틴 업무 테스트** — oven — 2026-05-09 완료
  - ✅ 8가지 테스트 (데이터처리/웹추출/판단) → 7/8 (87%) 통과
  - 약점: 다중 제약 최적화 (HA + 자원 할당 동시 처리)
- [ ] **ACE-Step 피아노 LoRA v6 음질 개선 — AudioSR 후처리** — oven — 2026-04-21
  - AudioSR 그리드 테스트 완료, **대기**: Leo 최적 설정 선택 → 디노이즈 추가 검토
  - **노션 업로드 미완료** (Leo 요청)
- [ ] **ACE Studio 자동화 (MCP + GUI)** — oven — 2026-05-05
  - ✅ Phase 1-9 완료: core/import/instrument/vocal/export/UI전체매핑 검증
  - ✅ MCP 71개 도구 풀 워크플로우 테스트 완료 (2026-05-05)
  - ✅ hitmaking + 3070에 MCP 테스트 결과 agent-comm 전달 완료
  - ✅ 노션 ACE Studio 연구 페이지에 MCP 섹션 추가 완료
  - MCP 불가: Import/Export/Save/Render → GUI 자동화 유지
  - **TODO**: 배치 파이프라인 MCP+GUI 하이브리드 통합 테스트
- [ ] **Suno 후처리 음질 향상 파이프라인** — oven — 2026-05-06
  - ✅ v5.0 vs v5.5 차이 분석 + 후처리 연구 완료
  - ✅ 노션 페이지 생성 (스템분리 포함/미포함 양쪽 파이프라인)
  - ✅ `suno_postprocess.py` 투 트랙 파이프라인 구축+테스트 완료 (2026-05-06)
  - ✅ matchering 2.0.6 설치, demucs htdemucs_ft 연동 확인
  - **대기**: hitmaking 오디오 분석 모듈 완성 수신
  - **TODO**: 실제 Suno WAV로 A/B 비교 청취, 레퍼런스 트랙 선정


---

## TODO

- [ ] **Quincy P3 학습 실행** — oven/5090 — Phase 2 완료, train_lora_p3.py 대기
- [ ] **Quincy P3 eval** — oven/5090 — 학습 완료 후 gen_p3_eval.py
- [ ] **Quincy 대시보드 배포** — oven — oven.arkedia.work/quincy/
- [ ] **tempo 추정 재검토** — oven — Phase 1 결과 fast 144k/slow 1.2k 이상함
- [ ] **수집 데이터 QA + DB 등록** — oven — mukl 복구 후
- [ ] **ACE-Step 찬송가 LoRA** — ogo — 942곡
- [ ] **NAS 백업 (V5~P2 체크포인트)** — oven
- [x] ~~**RunPod HunyuanVideo 테스트** — 폐기 (2026-05-08)~~

---

## BLOCKED

- [ ] **diffsinger / stable-audio-open** — Leo — HF gated repo 접근 권한 필요
- [ ] **FLUX.2-dev** — Leo — HF gated repo 접근 승인 필요
- [x] ~~**Wan2.1 영상 생성** — 폐기 (2026-05-08)~~

---

## DONE (최근)

- [x] **Gemma 4 26B 레오패밀리 통합 서빙** — oven/5090 — 2026-05-08
  - EXAONE → Gemma 4 26B-A4B Q8_0 교체 (174 tok/s, 3배 향상)
  - 11개 역할별 테스트 전항목 PASS, Open WebUI 기동, agent-comm 공지
- [x] **Gemma 4 26B + Open WebUI 통합 서빙** — oven/5090 — 2026-05-08
  - Open WebUI v0.9.2 기동 (http://100.107.229.5:3000, 인증 없음)
  - cp949 인코딩 에러 해결, 포트 3000, WMI 독립 프로세스
  - 한국어 채팅 테스트 정상, agent-comm 전체 공지 완료
- [x] **ACE-Step LoRA v6 연구 보고서** — oven — 2026-05-08
  - `research/ACE-Step_Piano_LoRA_v6_Report.md` — v1~v6 진화, AudioSR, 후처리, 결론
- [x] **대시보드 멀티페이즈 확장** — oven — 2026-04-24
  - Quincy: P2 전용 → P1/P1x/P2 phase tabs 분리, MIDI 엔드포인트 분리
  - Liszt: Engine Lab 리디자인 (MIDI 재생+FluidSynth 통합)
  - 커밋 0554fec (크래쉬 세션 복구)
- [x] **ACE-Step 베이스 모델 EP/밴드 아티팩트 비교** — oven/5090 — 2026-04-24
  - EP 3종(rhodes, wurlitzer, epiano) + 밴드 3종(rock, jazz, postrock) 생성 및 청취
  - 결론: 치치치 아티팩트 없으나 음질 자체가 다름, ACE-Step 아키텍처 한계 재확인
- [x] **ACE-Step v6 LoRA 학습 + 샘플 평가** — oven/5090 — 2026-04-18
  - 파이프라인: aria-midi → VirtuosoNet(velocity+pedal) → tempo fix → Piano V3 render → 486 segments
  - 학습: 300ep, rank 64, lr 1.5e-4, cosine, loss 0.2737
  - 평가: v6 LoRA / base model / HQ prompt / 다른 악기 비교 청취 완료
  - 결론: 음악적 품질 양호, 오디오 품질(축음기 느낌)은 ACE-Step 한계
- [x] **ACE-Step 피아노 LoRA v2 파이프라인 (데이터→학습→추론→HTML)** — oven/5090 — 2026-04-13 23:00
  - yt-dlp 6곡 (4.75GB) → segment_piano.py 120개 30s clips → ACE-Step preprocess → 29분 학습 → Base+5ckpt×6프롬프트 추론 → scp → 6열 HTML
  - 총 파이프라인 시간 ~1시간 (다운로드 제외)
- [x] **hitmaking 팝 샘플 전달** — oven — 2026-04-13 21:50
  - mxl 19개 + meta 19개 + urls_pop.jsonl 4,228개 + DOWNLOAD_GUIDE.md
  - `~/projects/agent-comm/projects/hitmaking/input/musescore_pop/`
- [x] **5090 FFmpeg 7.1 + torchcodec 설치** — oven — 2026-04-10
  - 원인: ACE-Step 전처리가 `load_with_torchcodec` 사용 → torchcodec 0.11은 FFmpeg 4~7 shared DLL 필요
  - 해결: BtbN n7.1 shared build (`C:\Users\leo\ffmpeg\bin`) + User PATH + 배치 내 명시 set PATH
  - 주의: BtbN `latest` 태그는 FFmpeg 8(avcodec-62)라 torchcodec 비호환 → n7.1 태그 지정 필수
- [x] **ACE-Step 배치 버그 수정** — oven — 2026-04-10
  - `train.py fixed --yes` → `train.py --yes fixed` (글로벌 옵션 위치 오류)
  - SSH `Start-Process`는 세션 종료 시 자식 프로세스 동반 사망 → schtasks S4U로 독립 실행
- [x] **Freesound 피아노 수집 완료** — oven/5090 — 2026-04-09
  - 최종 1,296개 (CC0/CC-BY), 배치 스크립트 준비 완료
- [x] **ACE-Step 학습 스케줄 등록→취소** — oven — 2026-04-09
  - schtasks S4U 모드로 등록 성공 (Interactive 모드는 콘솔 로그인 필요 → S4U 필요)
  - Leo 요청으로 취소, 내일 재실행
- [x] **5090 재부팅 + Freesound 수집 시작** — oven — 2026-04-09
  - Freesound API key 발급
  - Wan2.1 transformer/VAE 다운로드 완료
- [x] **NAS musicscore_data 전송** — oven — 2026-04-08
  - 4,972,264 파일 전송 검증 완료 (aria-midi, bitmidi, PDMX, aria-amt, asap, atepp, gigamidi)
  - NAS 경로: `/volume1/music/musicscore_data/`
- [x] **Wan2.2-T2V-A14B 모델 다운로드** — oven/5090 — 2026-04-06
- [x] **Quincy P3 Phase 1+2 전처리 완료** — oven/5090 — 2026-04-05
- [x] **Quincy 대시보드 멀티페이즈 확장** — oven — 2026-04-06
- [x] **서정적 피아노 MIDI mukl→5090 전송** — oven — 2026-04-03
