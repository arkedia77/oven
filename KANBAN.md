# oven (Quincy/Liszt) KANBAN
업데이트: 2026-07-16

## 📦 캡슐 (세션 재개용 3줄)
① **마지막 완료**: hf-playground 본배치 GO 수신(Style Ref/Identity Edit 각 5~10장, 사이즈이슈 가설 포함) + kee 연구파일럿1호(구조문법주입 도메인전이) 측정설계 1p 제출 완료(LEO 07-17 승인 후속). 이전: Krea2 신규 LoRA 파일럿 성공.
② **다음 스텝**: (a) ogo 재접속 대기 중(Tailscale 오프라인, WiFi 드롭 재발 추정) → 재접속 시 MJ 31장 현황 확인 후 hf-playground 회신 + 본배치(각 5~10장) 착수 (b) identity_edit 출력 2048×1024 2분할 이슈 — hf 가설([source|output] 콘캣)부터 확인 (c) kee 측정설계 페블 감수 결과 대기
③ **상세**: [[project_krea2_edit_loras]] · [[project_ogo_gpu_management]] · [[reference_ogo_network]] · 본 파일 IN PROGRESS 섹션

---

## IN PROGRESS

- [ ] **Krea2 비인물+MJ 재시도 배치** — oven/hf-playground — 2026-07-13~14 🟡 진행중
  - 7/11~13 ogo 22h+ 오프라인(원인불명) → 복구 후 젬마 수동기동 상태 발견(watchdog 5개 전부 무죄, 원인미확정) → Leo결정으로 젬마종료+실패분 60장 재발사
  - 🔴 **사고+복구**: manifest.json 인코딩버그(cp949가 em-dash 못씀) 크래시 → 직접 PowerShell 수정 시도가 파일 손상(oven 실수) → hf-playground 정본(commit 3411330, sha1 f8afa85d...) 재배포로 해결. 원칙 확립: ogo 파이썬 파일은 repo경유로만 수정 [[feedback_remote_file_edit_via_repo]]
  - 🟢 **7/14 상태**: nonhuman 27/28 완료(landscape 마지막 1장 진행중), MJ 31장 아직 미착수. hf-playground에 MJ1+nonhuman27(30개) 부분회수 완료(바이트검증 일치)
  - 다음: nonhuman 완주 → MJ 31장 자동 착수 → 완주 시 hf-playground 일괄 재서빙(요청②)

- [x] **작곡·편곡 LoRA(ARR, Qwen2.5-1.5B) — 라운드 CLOSED** — oven/3070 — 2026-07-11~14 ✅ 프로덕션 설정 확정
  - Qwen2.5-1.5B + REMI vocab 542신규토큰(POP909 909곡) LoRA. **최종설정: ckpt_v4_epoch2+temp0.6+top_p0.95+rep_penalty1.2+min_new_tokens300** — valid_rate 0.875·valid-gated chord_tone 0.632(GT0.875), P3오염 0/15
  - 여정: 스모크런→소규모학습→확장학습(과적합 3000스텝 발견)→재설계(정식epoch+weight_decay, 그래도 미세퇴행)→**greedy 확률붕괴 대발견**(반복실패곡 4/4가 디코드 문제였음, 재학습 불요)→샘플링전환(valid 0.60→0.93)→temp sweep→3seed결선(단발판정 뒤집힘)→P3클린재확인
  - 핵심교훈 4건: tied embedding VRAM함정/generate헤더누락버그/집계mean착시/단발샘플링seed노이즈위험 — 상세 [[project_arr_composition_lora]]
  - 정칙화 재학습 최종불요 확정. 102번곡=구조적hard-case 플래그(재학습금지)
  - fableself 프로젝트화 소견(도메인 무지 LLM 구조학습, 생체신호 2호도메인 제안) — ✅ LEO 승인(07-17, kee 경유) → 연구 파일럿 1호로 편입, 아래 신규 항목 참조

- [ ] **연구 파일럿 1호 — 구조문법주입 도메인전이(데이터효율 한계곡선)** — oven/kee — 2026-07-16 착수 게이트 진행중
  - kee 발주(P1, LEO 07-17 승인) → oven이 측정설계 1p 작성·제출 완료(`kee_oven_20260716_193709_...json`)
  - 설계 요지: x축=학습데이터량(10%/30%/100%, 909곡 기준) y축=chord_tone_ratio(GT0.875, 100%지점 기존실측 0.632) — 3단게이트(착수/중간/판정), 3070 1기 재사용(신규 인프라 불요)
  - kee 접수평가 "상위" + 착수게이트=페블(=fableself) 1회 감수 경유, PASS 시 kee 착수판정 자동발효(왕복불요)+트랜치1(3런) 자동승인 예고
  - oven→fableself 감수 요청 발송 완료(`fableself_oven_20260716_194003_...json`) — 베이스모델스윕 함정 비해당 판단 확인 요청 포함
  - fableself 조건부 PASS(보강4건: valid_rate 곡선병기/ckpt세팅=레시피 확인/3점판정격하/decode고정 스코프) → oven 전건 반영 회신 → ✅ **T0 게이트 완전 발효**(min_new_tokens 측정구간은 비블로커 판정, T1 전까지 확인). 3070에 확인 질의만 병행 발송(`3070_oven_20260716_194736_...json`)
  - ✅ **Leo 승인 → 착수함(19:53)**: leowin2에서 `train_epoch_frac.py`(--frac 인자로 10%/30% 서브셋, ckpt_v4 레시피 그대로: LoRA r16/lr5e-5/wd0.01/2epoch/seed20260713 고정, 단일셔플 후 prefix subset이라 10%⊂30%⊂100% nested) SYSTEM schtask(FracPilotT0)로 detach 실행
  - 🔴 **1차 실행 cp949 인코딩 크래시**: 로그 문자열의 em-dash(—)가 model load 직후 크래시(GPU시간 낭비 없음, 학습 시작 전 실패) — [[feedback_krea2_local_model]]류와 동일 패턴(비ASCII 문자+cp949 콘솔). sys.stdout/stderr utf-8 reconfigure + 하이픈 치환으로 수정 후 재실행 성공
  - 🔴 **거짓DONE 마커 버그 발견**: `run_frac_pilot.bat`가 python 성공/실패 무관하게 마지막에 무조건 DONE 마커 기록 — 1차 크래시런의 마커가 남아있어 착시 유발할 뻔함(삭제 조치함). Krea2 Raw 거짓DONE과 동일 계열 버그. **판정은 항상 로그 내 완료 문자열+체크포인트 디렉토리 존재로 확인, 마커 단독 신뢰 금지** [[feedback_verify_before_report]]
  - ✅ **20:47 frac10 완료 확인**(로그 "TRAIN_EPOCH_FRAC_DONE"+ckpt_frac10_epoch1/epoch2 디렉토리 실물 확인): 총 53.4min(epoch1 20.3min+epoch2 26.8min), first_loss 16.211→last_loss 1.148
  - 🟢 **frac30 진행중**(20:47:33 시작): 1960/6536윈도우(30%). 실측 속도(~2.2~2.5s/step) 기준 총 ~2.4h 예상 → 완료 예정 23:10~23:20대
  - 3070에 judge.py 측정구간 문의 회신 도착·fableself에 최종 확인 완료(min_new_tokens은 코드커버리지 필터라 무해) — T1 리포트 준비 완료 상태
  - 100% 지점은 기존 ckpt_v4_epoch2 재사용(재학습 불요, valid_rate 0.875/chord_tone 0.632 이미 확보)
  - ogo(serv)는 21시경도 계속 오프라인(3h+) — 과거 22h+ 사고 패턴 유사, 장기화 시 Leo 물리조치 필요할 수 있음. MJ31 현황 확인·hf-playground 회신 보류 중

- [ ] **하모니시티 확대 — Phase A 구현 완료** — oven — 2026-07-08 A-1~A-7 mock 검증 PASS
  - 설계: `HARMONICITY_EXPANSION_DESIGN.md`(6축) + `HARMONICITY_DETAILED_DESIGN_PHASE_A.md`(상세)
  - 구현: metrics.py/intervention.py/run_ab.py/api/server.py 신규 + save_load(원자적)/main(개입훅)/export(--ab) 수정
  - E1 관측·개입 API(FastAPI 17라우트) + E2 A/B paired 실험프레임(개입 4타입) 완성. 라이브 무영향 회귀 확인
  - 🔴 **real LLM 검증 대기**(젬마 복귀 후): run_ab real 효과리포트 / API 라이브 read-only 관측
  - 대기: Leo 결정 4건 (S2 선행 / V1 내부적용 / S4 정책 / ogo 배포 여부). 커밋 완료
  - 다음(Phase B): E6 도메인팩 / E3 서사기억 / config_set 개입(모듈참조 전환)

- [ ] **musicscore_data 백업** — oven — 2026-06-29~상태 미확인
  - 7/10 확인: cp 프로세스 없음 + LEO 1 드라이브 미마운트 (leo_vst만 마운트)
  - 완료 또는 드라이브 분리 — Leo 물리 확인 필요
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
  - 🟢 **7/16 신규 LoRA 파일럿 성공**: HF/CivitAI 재조사로 미사용 LoRA 발굴(공식 스타일 9종 + 기능성 5종). `ostris/Krea2OstrisEdit` 커스텀 diffusers 파이프라인(trust_remote_code) 확인·검증.
    - **Style Reference LoRA**(ostris) — 레퍼런스 이미지(빗속 콘서트 실루엣) 분위기를 완전 다른 피사체(예티)에 이식 성공. gen 1237s/10step
    - **Identity Edit LoRA**(conradlocke v1.1 r64) — 원본 인물/포즈/의상/프레이밍 보존한 채 조명만 지시대로(야간→골든아워) 교체 성공. gen 1257s/10step. ⚠️ 출력이 2048×1024 2분할로 나옴 — 사이즈 파라미터 확인 필요(후속)
    - 결과: `~/oven/krea2_edit_pilot_results/` (source+output 5파일). VRAM peak 58.1GB
    - hf-playground 회신(15:35): 우선순위 동의 + 공식9종은 6/28 기실측(재발사불요) + 조건2건(Identity Edit 입력=A_characters_photoreal 합성인물 고정 / MJ31 완주 후 진행) — oven이 회신 확인 전 파일럿 선실행, 자진신고 완료(소스이탈 있었으나 실인물 아님, GPU충돌은 없었음 확인)
    - hf-playground 회신(19:20): 파일럿 성공 확인 + 본배치 GO. **배치설계**: ①Style Reference 5~10장(레퍼런스=softwatercolor파이널+LoRA스윕무드2장 → A카테고리 인물에 이식) ②Identity Edit 5~10장(입력=A카테고리 합성인물 1장 고정, 축별 조명2·표정2·의상2·배경2 — LEO 6/27 img2img 테스트 본실행). 사이즈이슈 가설: edit 파이프라인이 [source|output] 콘캣 출력하는 관행일 수 있음(우측크롭으로 해결 가능성)
  - 🔴 **7/16 19:3x ogo 오프라인**: Tailscale relay hkg, last seen ~1h — WiFi 드롭 재발 추정 [[reference_ogo_network]]. 재접속 시 MJ31 현황 확인 → hf-playground 회신 + 본배치 착수
  - 대기: 신규 LoRA 본배치(사이즈이슈 해결 선행), MJ31 현황 회신
- [ ] **#26 비인물 clause Krea2 BASE 재검** — oven/hf-playground — 🟡 다운로드 76.5%, 버그 수정 후 재가동
  - ✅ 준비 100%: promptbank+corpus+gen provenance 배포 완료
  - **7/10 실측**: .incomplete 30파일, **25.26GB/33GB(76.5%)** — 07-08(58%)보다 진전
  - 🔴 **거짓DONE 버그 발견·수정(7/10)**: dl_krea2_raw.py가 snapshot_download 반환만으로 DONE 판정 → safetensors 5파일 존재 검사 + .incomplete 잔존 검사 추가. DONE 마커 제거, 좀비 18프로세스 kill
  - 🟢 **tick watchdog 재가동**: dl_krea2_raw.py 수정본 배포 → Krea2NonhumanTick ENABLE + 수동 Run 완료. 남은 ~8GB resume 중
  - **Plan B 병행**: archy가 Krea-2-Raw 33GB 별도 다운로드 중 (완료 시 SMB 릴레이 또는 대안 전송)
  - MJ 앵커 A/B 32장(hf-playground 07-10 요청) = 비인물 뒤 순번 큐 적재
  - 다음: ogo 복귀 확인 → tick.log 진행 / DONE_NONHUMAN_RAW 체크. 완료 시 50장 회수+MJ 32장 이어서

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

- [x] **수신 6건 일괄 처리 + 킷v0.2 재편** — 2026-07-10
  - hf-playground MJ앵커 요청 → 상태 회신 + 실측 정정(25.26GB/76.5%)
  - 3070 MIDI LoRA 경험 3건 회신 (C>A>B 우선순위 의견)
  - ari 킷v0.2 L0 재편 완료 → 검수 PASS (3,944B/6KB)
  - CLAUDE.md에 R-P1~P4 추론수칙 + G-K1~K5 수명주기 편입, 커밋+push+G-K5검증
- [x] **Krea2 Raw 거짓DONE 버그 수정** — 2026-07-10
  - dl_krea2_raw.py: safetensors 5파일 존재 + .incomplete 잔존 검사 추가
  - 좀비 프로세스 18개 kill, DONE 마커 제거, watchdog 수정본 재가동
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
