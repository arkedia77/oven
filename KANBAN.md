# oven (Quincy/Liszt) KANBAN
업데이트: 2026-05-06 (세션 43)

---

## IN PROGRESS

- [ ] **로컬 LLM 비교 평가 및 운영** — oven/5090 — 2026-05-02
  - ✅ EXAONE 4.0 32B vs Qwen3.6-27B 비교 테스트 완료 (18항목)
  - ✅ Qwen3.6-27B-Q5_K_M 다운로드 완료 (19.5GB)
  - ✅ 노션 비교 리포트 업로드 완료
  - ✅ EXAONE 서버 복원 (현재 운영중)
  - **결론**: EXAONE 유지 권장 (안정성+한국어), Qwen은 thinking disable 후 코딩용 가능
  - **TODO**: Qwen thinking 비활성화 설정 테스트, gemma 요청 대응 (테스트 과정 공유)
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
- [ ] **Wan2.1 뮤직비디오 생성** — oven/5090 — 3개 에피소드
  - ✅ 모델 다운로드 완료
- [ ] **Suno 후처리 음질 향상 파이프라인** — oven — 2026-05-06
  - ✅ v5.0 vs v5.5 차이 분석 + 후처리 연구 완료
  - ✅ 노션 페이지 생성 (스템분리 포함/미포함 양쪽 파이프라인)
  - ✅ `suno_postprocess.py` 투 트랙 파이프라인 구축+테스트 완료 (2026-05-06)
  - ✅ matchering 2.0.6 설치, demucs htdemucs_ft 연동 확인
  - **대기**: hitmaking 오디오 분석 모듈 완성 수신
  - **TODO**: 실제 Suno WAV로 A/B 비교 청취, 레퍼런스 트랙 선정
- [ ] **키보디스트 인터뷰 v4 준비** — Leo

---

## TODO

- [ ] **Quincy P3 학습 실행** — oven/5090 — Phase 2 완료, train_lora_p3.py 대기
- [ ] **Quincy P3 eval** — oven/5090 — 학습 완료 후 gen_p3_eval.py
- [ ] **Quincy 대시보드 배포** — oven — oven.arkedia.work/quincy/
- [ ] **tempo 추정 재검토** — oven — Phase 1 결과 fast 144k/slow 1.2k 이상함
- [ ] **수집 데이터 QA + DB 등록** — oven — mukl 복구 후
- [ ] **ACE-Step 찬송가 LoRA** — ogo — 942곡
- [ ] **NAS 백업 (V5~P2 체크포인트)** — oven
- [ ] **RunPod HunyuanVideo 테스트** — oven

---

## BLOCKED

- [ ] **diffsinger / stable-audio-open** — Leo — HF gated repo 접근 권한 필요
- [ ] **FLUX.2-dev** — Leo — HF gated repo 접근 승인 필요
- [ ] **Wan2.1 영상 생성** — ACE-Step 완료 대기 중

---

## DONE (최근)

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
