# oven (Quincy/Liszt) KANBAN
업데이트: 2026-07-09 (하모니시티 Phase A 구현완료 + Krea2 #26 BASE 재검 착수·tick watchdog 무인다운로드)

---

## IN PROGRESS

- [ ] **하모니시티 확대 — Phase A 구현 완료** — oven — 2026-07-08 A-1~A-7 mock 검증 PASS
  - 설계: `HARMONICITY_EXPANSION_DESIGN.md`(6축) + `HARMONICITY_DETAILED_DESIGN_PHASE_A.md`(상세)
  - 구현: metrics.py/intervention.py/run_ab.py/api/server.py 신규 + save_load(원자적)/main(개입훅)/export(--ab) 수정
  - E1 관측·개입 API(FastAPI 17라우트) + E2 A/B paired 실험프레임(개입 4타입) 완성. 라이브 무영향 회귀 확인
  - 🔴 **real LLM 검증 대기**(젬마 복귀 후): run_ab real 효과리포트 / API 라이브 read-only 관측
  - 대기: Leo 결정 4건 (S2 선행 / V1 내부적용 / S4 정책 / ogo 배포 여부). 커밋 완료
  - 다음(Phase B): E6 도메인팩 / E3 서사기억 / config_set 개입(모듈참조 전환)

- [ ] **musicscore_data 백업** — oven — 2026-06-29~진행 중 (거의 완료)
  - cp -a 실행 중 (PID 62301), 대상 `/Volumes/LEO 1/musicscore_data` (exFAT)
  - 소스 637G. **대상 du=2.9T는 exFAT 1MB 클러스터 슬랙 + `._` 사이드카** 때문 (손상/중첩 아님, 7/3 재검증 완료)
  - PDMX/mxl 18샤드 중 **16/17 진행 중**(7/7 확인, 거의 완료). 16개 폴더 전부 존재
  - 공간 리스크 해소: 여유 520Gi로 충분 (실데이터 이미 소스와 일치)
  - cp 종료 감시 백그라운드(b6jhu69ah) → 종료 시 최종 파일수 검증 → Leo 보고 → leo_vst 삭제 가능
- [ ] **ogo GPU 독점 관리 체계** — oven — 2026-06-24 LEO 확정
  - ✅ 정책 확정 + admin/ari ACK
  - TODO: 예약 대시보드/로그 시스템 (필요 시)
- [ ] **하모니시티 라이브 시뮬 운용** — oven/ogo — ⏸ **정지 (Leo 지시: 젬마 신호 줄 때까지 down)**
  - **Leo 결정(7/4)**: ~2일간 GPU 이미지 생성 전념 → 젬마 down 유지, **Leo 신호 시에만 재기동**
  - 비활성화 task: `Gemma-AutoStart`, `Gemma-HealthCheck`, `HarmonicityHealthCheck` (리붓돼도 안 올라옴). 시뮬 `HarmonicityP11` End
  - 🔴 **재기동(Leo 신호 후)**: task 3개 `/ENABLE` + `schtasks /Run /TN Gemma-AutoStart` + `schtasks /Run /TN HarmonicityP11`(stale락 있으면 [[feedback_harmonicity_stale_lock]] 절차)
  - 참조 [[reference_ogo_autorestart]]. 7/4 stale락 복구 완료했었음 / T2 수정 적용 / rep_floor 검토 대기
- [ ] **하모니시티 재현성 트랙** — oven/ogo — ✅✅ 완전 완결
- [ ] **ACE-Step 1.5 LoKR 권PD 음원** — oven/leowin2 — 대기
  - **블로커**: leowin2 Tailscale 미접속
- [ ] **ACE Studio 자동화** — 3070 담당 (oven 이관 완료)
- [ ] **Krea2 이미지 캠페인 (hf-playground 협업)** — oven/ogo/hf-playground — 🟢 현재 큐 비어있음
  - 지금까지 종결 4건 총 318장(아이돌8+V2 10+소스100+여름100), 전부 실패0. archy AssetStore 적재
  - 워크플로 확립: gh api로 hf-playground 파일 회수→ogo 배포→SYSTEM schtask+run_*.bat 발사→회수 zip→통지
  - 🔴 **필수교훈**: Krea2 배치는 `--model 로컬` + LoRA 로컬(lora_v2) 명시 [[feedback_krea2_local_model]]. 젬마 down 상태 유지(VRAM독점)
  - 대기: hf 제안 baseline/강도스윕(LEO 판단), 추가 캠페인 요청
- [ ] **#26 비인물 clause Krea2 BASE 재검** — oven/hf-playground — 🟡 준비완료, 다운로드 진행중(느림)
  - ✅ 준비 100%: krea/Krea-2-Raw(비증류 BASE, is_distilled=false) 규명 / promptbank+corpus 배포(상대import→flat 패치) / gen provenance 동적패치(raw|turbo 자동) / bank 드라이런 50 jobs PASS
  - ⚙️ **ogo=원격서버라 물리 네트워크 조치 불가**(Leo 확인 7/8) → 원격전용 자동재시작으로 해결
  - 🟢 **tick watchdog**: schtask `Krea2NonhumanTick`(5분주기 SYSTEM, HarmonicityHealthCheck 패턴). `check_tick.ps1` 무상태 판단 = dl 살아있게+2tick(~10분)정지시 kill후 resume / 다운완료→50장 배치 자동 / 전부완료→무동작. hf_transfer로 resume 누적 → WiFi 드롭 무관 완주
  - **진행**: 7/8 17:20 기준 **19GB/33GB(~58%)**. 7/9 갈무리 시점 **ogo 오프라인(WiFi 드롭)** — 진행률 미확인. tick schtask는 재부팅·드롭 견디고 재접속 시 자동 resume(dl_krea2_raw.py hf_transfer가 .incomplete 이어받음)
  - **다음 세션 최우선**: ogo 복귀 확인 → `ssh ogo type C:\projects\krea2_test\tick.log`(진행) / `findstr DONE_NONHUMAN_RAW nonhuman_job.log`(배치완료). 완료면 nonhuman_raw_out 50장 회수(iCloud+NAS+README, 도메인폴더)+그리드+hf 회수대기 회신. 미완이면 tick watchdog이 계속 진행 중일 것(정지 시 `schtasks /Run /TN Krea2NonhumanTick`)
  - 준비물: promptbank+corpus(flat import 패치) 배포됨, gen provenance 동적패치(raw/turbo) 됨. hf 통지 3건 push(162012 확보경로/164455 블로커/172608 자동재시작정정) [[reference_ogo_network]]

---

## TODO

- [ ] **Quincy P3 학습 실행** — oven/5090 — Phase 2 완료, train_lora_p3.py 대기
- [ ] **venture-studio 실험 결과 보고** — T1/T6/T5 findings (LEO 결정 시)
- [ ] **ogo→leowin2 학습 인프라 이전** — leowin2 Tailscale 대기

---

## BLOCKED

- [ ] **diffsinger / stable-audio-open** — Leo — HF gated repo 접근 권한 필요
- [ ] **FLUX.2-dev** — Leo — HF gated repo 접근 승인 필요

---

## DONE (최근)

- [x] **Krea2 여름 리얼리즘 100장** — 2026-07-06~07 — 100/100, err 0, mean_gen 328s, vram_peak 51.7GB. realism-V2 LoRA w1.5, 전량 로컬로드(HF다운0). A_people 60/D_objects 20/E_bg 20. 회수 `~/oven/krea2_summer_results/`(zip 143MB+컨택트시트). hf 통지+Leo Preview 완료
- [x] **ogo 네트워크 진단** — 2026-07-06 — USB WiFi(DFS채널60) 간헐드롭이 원인(세션중 3회 오프라인). 신호100%·전원정상·직접P2P 13ms 정상. 유선/비-DFS채널 권장 Leo 전달 [[reference_ogo_network]]
- [x] **Krea2 소스셋 100장 캠페인** — 2026-07-06 — 100/100, err 0, mean_gen 297s, vram_peak 51.7GB(1344배경 포함). A36/B20/C12/D18/E14. 카테고리 하위폴더 저장. 회수 `~/oven/krea2_source_results/`(zip 121MB+컨택트시트). hf 완료통지. 최초분 --model 미지정 21h정지→수정 [[feedback_krea2_local_model]]
- [x] **Krea2 realism-V2 LoRA 10케이스** — 2026-07-05 — 10/10, err 0, vram_peak 35.7GB, weight1.5. 얼굴/조명/구성/텍스처/풍경 4축. LoRA 다운로드 정지→reklcli다운+scp+로컬로드 우회 [[feedback_krea2_local_model]]. 회수 `~/oven/krea2_realism_v2_results/`(+grid+zip). hf 통지+Leo Preview 완료
- [x] **Krea2 아이돌 공연 배치 8장** — 2026-07-04 — 8/8 성공, err 0, vram_peak 35.9GB. Realism LoRA 적용, 장당 ~4분(젬마다운 VRAM독점). 회수: `~/oven/krea2_idol_results/`(+idol_grid.png). Leo Preview 완료
- [x] **하모니시티 동시성 실증(A06) — venture 회신까지 완결** — 2026-06-19~21 (7/4 재확인)
  - 스윕 완료(ogo1, N=1~20, real, 2026-06-19). **SLA 허용 동시 세계 N≤12** (tick wall<200s, 실패 0). throughput 포화 N=4(~0.84 calls/s). VRAM 28.5GB 고정(모델공유) → 한계=VRAM 아닌 추론 throughput
  - venture-studio 회신 **이미 발송**: `venture-studio_oven_20260621_062000_동시성실측_A06승격.json` (A06 '추정'→'실측 N≤12' 승격). ⚠️ 7/3 메모리 TODO는 오등록, 중복발송 금지
  - 결과 로컬 회수: `virtual_world_v02/concurrency/ogo1_results/`. G2 GTM 원페이저 실측 확정(`concurrency/GTM_onepager_DRAFT.md`, 7/4)
- [x] **하모니시티 시뮬 stale락 복구** — 2026-07-04 — ogo 재부팅 후 재기동 실패 진단+복구 ([[feedback_harmonicity_stale_lock]])
- [x] **Krea2 커뮤니티 LoRA 테스트** — 2026-07-02~03
  - Realism LoRA (gokaygokay/Krea-2-Realism-LoRA) + Detail Slider (CivitAI alcaitiff) 테스트
  - 핵심 성과: 커뮤니티 LoRA 키 매핑 해결 (PEFT→diffusers, ComfyUI→diffusers 변환)
  - 결과: Realism은 구도/분위기 변화 뚜렷, Detail Slider는 미세 차이 (비추)
  - 비교 그리드: `krea2_test/community_results/comparison_grid.png`
- [x] **Krea2 루나바이브 아트워크 6장** — 2026-06-28
- [x] **Krea2 Turbo+LoRA 9종 스윕** — 2026-06-28 — 10/10 성공
  - enable_model_cpu_offload() 최적화: 장당 20분→4.5분, VRAM 60.9→37.8GB
- [x] **hf-playground Krea2 대행 벤치마크** — 2026-06-24~28 — 종결
- [x] **ogo GPU 관리 정책 수립** — 2026-06-24 — LEO 확정, admin+ari ACK
- [x] **T1/T6/T5 실험 스윕 전체 완료** — 2026-06-22
- [x] **PyTorch nightly cu128 설치** — 2026-06-27 — sm_120 지원 확인
