# oven (Quincy/Liszt) KANBAN
업데이트: 2026-07-19

## 📦 캡슐 (세션 재개용 3줄)
① **마지막 완료**: **Krea2 3기법쌍비교 12/12 완료→hf-playground 회수완료(13/13 바이트일치)**. **연구파일럿1호 트랜치3(frac50/70%) 완주**→3070에 생성+채점 착수 확인(ACK, ~3h 예상). ogo에서 **LoRA 본배치 재개**(잔여13장, resume 스크립트로 1/14 스킵 확인·정상 진행 재시작). 도중 leowin2 schtask 재발화 사고(8h+ 정체) 완전 해소, [[feedback_schtask_onetime_refire]] 등재. **(7/19 추가) Leo 지시로 Krea2 이미지 캠페인 중단→하모니시티 재가동 + rep_floor(0.15) 오버라이드 배포 완료**, Day 457/Tick 10961+ 정상 진행 확인.
② **다음 세션 할 일**: (a) 본배치(잔여13장, ~4~5h) 완주 대기 → hf-playground 통지+서빙 (b) 3070 채점 회신(~3h 내) 대기 → 사전등록 기준(valid_rate 0.65/0.79, chord_tone 비단조)으로 판정 → **T3 게이트 리포트**(kee cc fableself) 작성 (c) hf-playground 프롬프트벤치v1(48장, 정본 준비완료 `krea2_prompt_formula_promptbank.py`)은 (a)(b) 완료 후 3번째 순번 (d) **하모니시티 3일 가동 관찰**(rep_floor 효과) → 종료 시 Krea2 배치 재개
③ **상세**: [[project_krea2_edit_loras]] · [[project_ogo_gpu_management]] · [[reference_ogo_network]] · [[feedback_schtask_onetime_refire]] · [[project_harmonicity]] · 본 파일 IN PROGRESS 섹션

---

## IN PROGRESS

- [ ] **하모니시티 재가동 + rep_floor 오버라이드** — oven/ogo — 2026-07-19 착수
  - Leo 지시(7/19): Krea2 이미지 캠페인(gen_edit_main_batch.py, PID 3228, GPU 32GB 점유) 중단 → 하모니시티 3일 재가동 + rep_floor 오버라이드 완성
  - `homeostasis.py`에 `HARMONICITY_CONFIG_OVERRIDES`(env JSON) 파라미터화 추가: WARMTH/TRUST_SOFT_CEILING·WARMTH/TRUST_DECAY_RATE·REP_EROSION_MULT·REP_WARMTH_FLOOR. 로컬 mock 스모크+floor 유닛테스트 PASS, 라이브 미설정 시 기존값과 완전 동일(무영향) 확인
  - **API_URL도 `HARMONICITY_API_URL` env override로 전환**(config.py) → "config.py 머신별 분기·동기화 예외" 문제 해소, `launch_p11.bat`에서 `localhost` 지정(ogo 네트워크 불안정 tailnet 의존 제거)
  - 배포: config.py/run_village.py(mutex dir-scoped)/llm.py(profiling 연동)/homeostasis.py 4파일 ogo 배포(백업 `code_backup/20260719_010706_rep_floor_deploy`, 해시검증+import무결성 PASS)
  - **REP_WARMTH_FLOOR=0.15 적용**(메모리 권장범위 0.15~0.20 중 하한값 우선 적용, Leo 조정 가능)
  - Krea2 배치 중단(resume 매니페스트 있어 재개 가능) → llama-server(LlamaHarmonicity) 재기동 → HarmonicityP11 재기동(stale lock 자동탈취 정상) → HarmonicityHealthCheck watchdog 재활성화. Day 457/Tick 10959→10961+ 정상 진행 확인, 신규 crash 없음
  - ⚠️ SSH known_hosts 이슈 발견+해결: ogo 호스트키가 `serv` 별칭으로만 등록돼 `ogo`/IP 접속이 거부됨 — 동일 키 확인 후 재등록(보안이슈 아님, alias 누락)
  - 다음: 3일 가동 관찰(rep_floor 효과=warmth/trust 하한 유지 여부) → 필요시 Leo와 floor값 조정 → 종료 시 Krea2 배치 재개(run_main_batch.bat, resume 확인됨)

- [x] **Krea2 비인물+MJ 재시도 배치** — oven/hf-playground — 2026-07-13~17 ✅ 완주 확인
  - 7/11~13 ogo 22h+ 오프라인(원인불명) → 복구 후 젬마 수동기동 상태 발견(watchdog 5개 전부 무죄, 원인미확정) → Leo결정으로 젬마종료+실패분 60장 재발사
  - 🔴 **사고+복구**: manifest.json 인코딩버그(cp949가 em-dash 못씀) 크래시 → 직접 PowerShell 수정 시도가 파일 손상(oven 실수) → hf-playground 정본(commit 3411330, sha1 f8afa85d...) 재배포로 해결. 원칙 확립: ogo 파이썬 파일은 repo경유로만 수정 [[feedback_remote_file_edit_via_repo]]
  - 🔴 **7/16 18:3x~7/17 13:4x ogo 재차 19h 오프라인**(2번째 장기사고) — 원인 여전히 불명, 복구 경위도 불명(자동복구 추정, Leo 물리조치 요청은 해뒀으나 확인 못함)
  - ✅ **7/17 13:47 복귀 후 완주 확인**: MJ patterns 31/31(manifest+실물PNG32개 대조), nonhuman_retry28 28/28(실물 대조) — hf-playground에 회신, 재서빙 방식 문의 중
  - 다음: hf-playground 회신 오면 일괄 재서빙

- [x] **작곡·편곡 LoRA(ARR, Qwen2.5-1.5B) — 라운드 CLOSED** — oven/3070 — 2026-07-11~14 ✅ 프로덕션 설정 확정
  - Qwen2.5-1.5B + REMI vocab 542신규토큰(POP909 909곡) LoRA. **최종설정: ckpt_v4_epoch2+temp0.6+top_p0.95+rep_penalty1.2+min_new_tokens300** — valid_rate 0.875·valid-gated chord_tone 0.632(GT0.875), P3오염 0/15
  - 여정: 스모크런→소규모학습→확장학습(과적합 3000스텝 발견)→재설계(정식epoch+weight_decay, 그래도 미세퇴행)→**greedy 확률붕괴 대발견**(반복실패곡 4/4가 디코드 문제였음, 재학습 불요)→샘플링전환(valid 0.60→0.93)→temp sweep→3seed결선(단발판정 뒤집힘)→P3클린재확인
  - 핵심교훈 4건: tied embedding VRAM함정/generate헤더누락버그/집계mean착시/단발샘플링seed노이즈위험 — 상세 [[project_arr_composition_lora]]
  - 정칙화 재학습 최종불요 확정. 102번곡=구조적hard-case 플래그(재학습금지)
  - fableself 프로젝트화 소견(도메인 무지 LLM 구조학습, 생체신호 2호도메인 제안) — ✅ LEO 승인(07-17, kee 경유) → 연구 파일럿 1호로 편입, 아래 신규 항목 참조

- [x] **연구 파일럿 1호(정본코드 A-042 과제①) — 구조문법주입 도메인전이(데이터효율 한계곡선)** — oven/kee — 2026-07-16~21 ✅✅ LEO 종결승인, AGENDA 반영완료
  - **07-21 종결**: LEO 최종 승인(07-21) → kee AGENDA 반영 완료. 코퍼스 승격 GO(범위: TRANCHE1~3 judged JSON+사전등록 프로토콜+decode고정설정+ckpt_v4_epoch2만, 중간 25ckpt는 코드+seed 재현가능이라 제외)
  - 후속 연구는 A-042 프레임(3단게이트·트랜치·출구) 내 신규 트랜치로 별도 상정 예정
  - kee 발주(P1, LEO 07-17 승인) → oven이 측정설계 1p 작성·제출 완료(`kee_oven_20260716_193709_...json`)
  - 설계 요지: x축=학습데이터량(10%/30%/100%, 909곡 기준) y축=chord_tone_ratio(GT0.875, 100%지점 기존실측 0.632) — 3단게이트(착수/중간/판정), 3070 1기 재사용(신규 인프라 불요)
  - kee 접수평가 "상위" + 착수게이트=페블(=fableself) 1회 감수 경유, PASS 시 kee 착수판정 자동발효(왕복불요)+트랜치1(3런) 자동승인 예고
  - oven→fableself 감수 요청 발송 완료(`fableself_oven_20260716_194003_...json`) — 베이스모델스윕 함정 비해당 판단 확인 요청 포함
  - fableself 조건부 PASS(보강4건: valid_rate 곡선병기/ckpt세팅=레시피 확인/3점판정격하/decode고정 스코프) → oven 전건 반영 회신 → ✅ **T0 게이트 완전 발효**(min_new_tokens 측정구간은 비블로커 판정, T1 전까지 확인). 3070에 확인 질의만 병행 발송(`3070_oven_20260716_194736_...json`)
  - ✅ **Leo 승인 → 착수함(19:53)**: leowin2에서 `train_epoch_frac.py`(--frac 인자로 10%/30% 서브셋, ckpt_v4 레시피 그대로: LoRA r16/lr5e-5/wd0.01/2epoch/seed20260713 고정, 단일셔플 후 prefix subset이라 10%⊂30%⊂100% nested) SYSTEM schtask(FracPilotT0)로 detach 실행
  - 🔴 **1차 실행 cp949 인코딩 크래시**: 로그 문자열의 em-dash(—)가 model load 직후 크래시(GPU시간 낭비 없음, 학습 시작 전 실패) — [[feedback_krea2_local_model]]류와 동일 패턴(비ASCII 문자+cp949 콘솔). sys.stdout/stderr utf-8 reconfigure + 하이픈 치환으로 수정 후 재실행 성공
  - 🔴 **거짓DONE 마커 버그 발견**: `run_frac_pilot.bat`가 python 성공/실패 무관하게 마지막에 무조건 DONE 마커 기록 — 1차 크래시런의 마커가 남아있어 착시 유발할 뻔함(삭제 조치함). Krea2 Raw 거짓DONE과 동일 계열 버그. **판정은 항상 로그 내 완료 문자열+체크포인트 디렉토리 존재로 확인, 마커 단독 신뢰 금지** [[feedback_verify_before_report]]
  - ✅ **20:47 frac10 완료 확인**(로그 "TRAIN_EPOCH_FRAC_DONE"+ckpt_frac10_epoch1/epoch2 디렉토리 실물 확인): 총 53.4min(epoch1 20.3min+epoch2 26.8min), first_loss 16.211→last_loss 1.148
  - ✅ **07-17 03:06:05 frac30도 완료 확인**(로그 "TRAIN_EPOCH_FRAC_DONE"+"FRAC30 DONE"+ckpt_frac30_epoch1/epoch2 디렉토리 실물, GPU 유휴 복귀 확인): 총 2h18m(epoch1 70min+epoch2 68min), first_loss 16.189→last_loss 1.209
  - 3070에 judge.py 측정구간 문의 회신 도착·fableself에 최종 확인 완료(min_new_tokens은 코드커버리지 필터라 무해)
  - 100% 지점은 기존 ckpt_v4_epoch2 재사용(재학습 불요, valid_rate 0.875/chord_tone 0.632 이미 확보)
  - ✅ **09:41 3070에 채점 요청 발송**(`3070_oven_20260717_094119_...json`) → **10:23 회신 도착**: 10%(valid 0.800/ct_valid 0.4315) 30%(valid 0.667/ct_valid 0.4111) 100%(valid 0.875/ct_valid 0.632, 기존). frac30 무효5/15(empty4곡+폴리포니클러스터1곡)
  - 🟡 **비단조 관측**: 10%→30% 구간 역전(둘 다 소폭 하락), 30%→100% 구간 급상승(ct_valid +0.221). n=15 단발시드라 저구간 역전은 ARR temp-sweep 때와 같은 seed noise 함정 가능성 — **확정 판정 보류**, 다음 트랜치(다seed 재검증 or 중간점 50%/70% 추가)는 제안만 하고 Leo/kee 판단 대기
  - ✅ **10:24 T1 리포트 발송**(`kee_oven_20260717_102412_...json`, cc fableself) — 3점 데이터+비단조 해석유보+다음 트랜치 제안 포함
  - ✅ **T1 게이트 PASS 확정**: fableself 재감수(방법론 정합 확인+"valid_rate 동반하락은 완전 노이즈 배제 금지"+문턱가설 제기) + kee 공식 PASS 판정. **트랜치2 승인**: (a) 10%/30% 각 +2seed 다seed재검증 먼저(노이즈 vs 실재 가름) → (b) 중간점 50/70%는 트랜치3 후보로 보류. 3070 GPU슬롯=kee가 3070에 직접 발주(동시발신), oven은 확인회신 후 착수
  - ✅ **트랜치2 사전준비 완료**: `train_epoch_frac.py`에 `--seed` 인자 추가(데이터서브셋 셔플+torch dropout 랜덤성 모두 시딩), 4런 배치(`run_frac_tranche2.bat`: frac10/frac30 × seed7/seed13) + SYSTEM task(FracTranche2) 등록까지 완료, 트리거만 대기(거짓DONE 마커 안 씀 — 로그+ckpt디렉토리로만 판정)
  - kee에 확인 회신 발송(`kee_oven_20260717_102729_...json`)
  - ✅ **10:51 kee GO**(`3070 유휴실측 57MiB/8GB·0%util·46°C`, 지금부터 무기한 OK) — 조건 2건: ①220W 전력제한 유지(건드리지 말것) ②학습중 ACE-Step 인퍼런스 병행금지(OOM기교훈, 필요시 3070이 직접 조율). 3070 실측 소요: frac10 2ep≈45min/런, frac30 2ep≈2.2h/런, 4런 직렬≈6h
  - ✅ **10:55:45 FracTranche2 착수**: frac10 seed7부터 시작, GPU 정상 점유 확인, seed 인자 정상 동작(cp949 인코딩버그 재발 없음)
  - ✅ **11:24 frac10 seed7 완주**(ckpt_frac10_seed7_epoch1/epoch2 실물 확인)
  - ✅ **12:00 frac10 seed13 완주**(ckpt_frac10_seed13_epoch1/epoch2 실물 확인)
  - 🟢 **12:40 frac30 seed7 epoch1 완료**(ckpt_frac30_seed7_epoch1 실물 확인) → epoch2 13:11 기준 step1540/1960, 완료 임박(13:26대 예상). 이후 마지막 1런(frac30 seed13, ~1.3h) 남음
  - ✅ **15:06 frac30 seed13 완주** — 4런 전부 완료(3070이 15:35 leowin2 실측으로 재확인: 4개 ckpt 전량 실물+GPU유휴 확인)
  - ✅ **15:39 3070에 생성+채점 요청 발송**(`3070_oven_20260717_153919_...json`) — heldout 15곡×4런, P3 동일 decode, seed별 분리 산출 요청. 회신 대기
  - ✅ **17:11 3070 채점완료 회신**: 3seed 결과표 — 10%(valid 0.800/0.800/0.867, ct_valid 0.4315/0.4752/0.3932) 30%(valid 0.667/0.667/0.533, ct_valid 0.4111/0.4639/0.4435) 100%(valid 0.875, ct_valid 0.632 GT동일). **판정1**: T1의 10→30 ct역전은 노이즈 확정(mean차 0.006 < seed spread), 30→100 급개선(+0.19) 견고 재확인 — 문턱은 30% 위. **판정2(신규)**: valid_rate가 30% 구간서 3seed 전부 하락(pooled 0.822→0.622, z=2.17≈2.2σ) — 단정 금지, 후보 등재
  - ✅ **17:12 T2 게이트 리포트 발송**(`kee_oven_20260717_171239_...json`, cc fableself) — 트랜치3(50/70% 중간점) 제안만 하고 판정은 kee/Leo 대기
  - ✅ **17:14 kee T2 게이트 PASS** — 30→100 급개선 "연구1호 첫 견고 발견"으로 기록. 트랜치3 GO(설계는 페블 감수 경유 조건부)
  - ✅ **17:16~17:20 설계 확정**: oven이 1seed선행(vs 3seed일괄) 제안 → fableself 조건부PASS(ⓐ에스컬레이션 수치 사전등록: valid_rate 0.72↑회복/0.65↓딥연속/0.65~0.79 애매=자동+2seed, chord_tone 비단조시 자동보강 / ⓑ50·70%가 기존 30%의 슈퍼셋=nested 추출 의무) → kee 최종 확정(1seed×2런, ~8.5h) + 교란변수 질의(10↔30 nested여부)
  - ✅ **17:17 교란변수 회신**: train_epoch_frac.py 코드 근거(L34/80/83, 단일셔플+prefix슬라이스)로 nested 확정 회신
  - ✅ **17:18:37 FracTranche3 착수**(frac50 3268윈도우 시작) — 착수 후 fableself 조건부PASS 회신 도착(메시지 교차), 결과 미생성 시점이라 사전등록 취지 훼손없음 판단하고 ⓐⓑ 반영한 시작통지 발송(17:19)+3070 착수통지(17:20)
  - 🔴 **17:21 kee 경계중첩 적발**: 사전등록 기준 "0.72 상방/하방" vs "0.65~0.79 애매구간"이 0.72~0.79에서 자기모순 → oven이 "0.72는 fableself 원문의 설명적 참고점, 실경계는 명시된 0.65/0.79뿐"로 정정 회신(17:23, 결과 미생성 시점 유지)
  - ✅ **재고정 최종기준**: valid_rate ≤0.65=딥연속 / 0.65~0.79=애매(자동+2seed) / ≥0.79=회복. chord_tone(30%mean 0.4395 대비 비단조=자동보강)은 변경없음
  - fableself가 별도로 시작통지(ⓐⓑ) 자체는 수용 회신(17:21:30, kee의 경계지적과 시간상 교차) — nested확인으로 T2 valid_rate딥의 '구성효과' 교란변수 해소, '중간데이터량 불안정' 가설 후보등재 성립 확정
  - ✅ **21:01 frac50 완주**(ckpt_frac50_epoch2 실물 확인, adapter 5.6GB) — **frac70 착수**(4575윈도우, epoch1 시작). 예상 소요 frac50 대비 1.4배(~4.7h)
  - ✅ **23:53 frac70 epoch1 완료**(ckpt_frac70_epoch1 실물 확인) → epoch2 진행중. 완료 시 트랜치3 전체(50%+70%) 완주
  - 🔴 **07-18 11:03 정체 발견**: epoch2 step425/4575(05:10 로그)에서 5h52m 무갱신, 프로세스는 생존(25%util·7942MiB, 정상시 100%util). wmic 확인 결과 leowin2에 python.exe 3쌍(venv+system 중복카운트) 동시실행 — ①제 frac70(정상) ②`train_epoch_frac.py --frac 0.1 --seed 13`(frac10_seed13 재학습, 07-17 12:00에 이미 완료된 ckpt 중복) ③`generate_and_decode.py ckpt_frac10_seed13_epoch2`(07-17에 이미 채점완료분 중복 재생성) — ②③가 GPU 나눠쓰며 frac70을 굶긴 것으로 추정
  - ✅ **11:03 kee(cc 3070)에 긴급 진단 발송**: 10분 무회신 시 ②③ 프로세스 종료하고 frac70 단독 재개 예고
  - ✅ **11:06~11:08 해소 완료**: kee 즉시승인(조건3건: 종료전로그·재스폰감시·재개확인) → oven 재확인 시점엔 이미 ②③ 소멸(3070이 선조치, kill 불요) → 3070 경위회신(자기 One-Time schtasks가 예약시각에 재발화한 운영실수, 원인 차단+재발방지 등재 완료) → oven 독자 재확인(GPU 100%util 복귀)으로 조건3건 전부 충족·종결
  - ✅ **07-18 13:58 frac70 완주**(로그 "TRAIN_EPOCH_FRAC_DONE"+"TRANCHE3 ALL RUNS FINISHED"+ckpt_frac70_epoch2 실물 확인) — **트랜치3(50%+70%) 전체 완주**
  - ✅ **07-19 00:45 3070에 생성+채점 요청 발송**(`3070_oven_20260719_004503_...json`) — 사전등록 기준(0.65/0.79) 적용해 T3 판정 예정. 회신 대기
  - ✅ **ogo(serv) 07-17 13:47 복구 완료**(19h 오프라인 후) — 상세는 Krea2 이미지 캠페인 섹션 참조
  - 🟡 **07-19 01:34 T3 1차판정**: frac70 1seed 0.667=애매밴드(자동+2seed 트리거) / frac50 1seed 0.467=딥연속 후보. oven이 frac70(자동트리거)+frac50(딥형태 확인용, oven 재량) 둘다 +2seed GO
  - ✅ **07-19 10:35 frac70 3seed 회복 확정**: pooled 0.800(≥0.79)="회복" — 어제 1seed 0.667은 저운 draw로 판명, 다seed 원칙이 오판 실제로 방지
  - 🔴 **07-19 14:38 디스크풀 인시던트**: leowin2 C: 여유 4.3GB로 frac50 재실행 ckpt 저장 실패(os112, 파일럿 누적 164GB). oven 안A(구세대 smoke ckpt 삭제, 31.8GB확보) GO → 3070 즉시 집행(여유 35.6GB)+재실행, 재발방지로 사전 여유공간체크 추가
  - ✅ **07-19 21:29 frac50 3seed 최종**: s7/s13 둘다 0.933 — '딥=50' 가설 기각, 딥은 **30%에 잔존**(pooled 0.622) 확정
  - ✅✅ **07-21 11:24 T3 최종 게이트 PASS**(`kee_oven_20260721_112400_...json`, cc fableself/3070) — **데이터효율 한계곡선 완성**: valid_rate 10%0.822→30%0.622(딥)→50%0.778→70%0.800(회복)→100%0.875 / ct_valid 0.4333→0.4395→0.4672→0.526→0.632(30%이후 단조상승, 급개선 50~70%구간). 핵심소견: ①다seed 원칙이 딥위치 오판(50→30 정정) 실제로 방지 ②구조습득(ct)과 표면유효성(valid_rate)이 분리되는 현상 발견(30%에서 ct는 이미 상승중인데 valid만 일시하락) ③급개선 임계점 ≈50~70% 데이터량
  - 다음(Leo/kee 판단 대기): fableself 최종종합/논문화, Leo결재용 1p 요약 필요시 작성, 3070 GPU 유휴 — 후속라운드(시드확대 CI축소, 타도메인 확장) 여부

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
- [x] **하모니시티 라이브 시뮬 운용 — 재가동+rep_floor** — oven/ogo — 2026-07-19 재기동, 관찰중
  - **Leo 결정(7/19)**: Krea2 이미지 캠페인(gen_edit_main_batch.py) 중단 → 하모니시티 3일 재가동 + rep_floor 오버라이드 완성. 상세는 위쪽 하모니시티 섹션/[[project_harmonicity]] 참조
  - REP_WARMTH_FLOOR=0.15 적용, LlamaHarmonicity+HarmonicityP11+HarmonicityHealthCheck 전부 재기동, Day 457/Tick 10961+ 정상 확인
  - 다음: 3일 관찰(7/22 전후) 종료 후 Krea2 배치 재개 여부 Leo와 조율
  - 🆕 **07-21 kee 요청**: LEO 지시(7/20)로 페블(fableself) '세계문법·자율' 개념을 하모니시티에 처음부터 주입 검토 — oven이 M1~M5 현황 스냅샷 회신 완료(`kee_oven_20260721_113000_...json`). 핵심 갭: **에이전트 판단을 decider+근거로 구조화 로깅하는 체계 부재** — 주입 diff의 핵심 손볼 지점으로 소견 전달. 페블 트랙B 산출 대기
  - ✅ **07-22 페블 트랙B diff 수령+D-L1 T0게이트 PASS**: 5축 판정(발생기SET/복리SET/자율PARTIAL/판단포획최대갭/안전레일부분), 주입순서 D-L1→D-S1→D-A1→D-C1/G2→계측기 확정. D-L1(판단포획) decision_record 스펙 v0 작성→페블감수 조건부PASS→kee T0게이트 PASS(조건3건: status≠outcome 분리/judgment_type 분석고정/gate_passed·interpretation_status 오버로드분리)
  - ✅ **07-22 D-L1 MVP 로컬구현+검증 완료**: `village/decision_log.py` 신규(profiling/replay 동일 옵트인 패턴), conversation.py appraisal분기 연동. mock무영향회귀PASS+mock필드검증PASS+격리world 실LLM검증PASS. 라이브 배포는 다음 재기동시점까지 보류(직후 사고 복구라 신중)
  - 🔴 **07-22 llama-server 14h 무인지 정지 사고 발견+복구**: D-L1 실LLM검증 중 ogo llama-server(:8080) 사망 발견 — sim.log가 당일 01:04부터 약 14시간 정지. 원인: HarmonicityHealthCheck watchdog이 python.exe(run_village) 프로세스 개수만 감시해 llama 자체 사망을 못 잡음(launch_p11.bat이 헬스체크 대기루프에서 정상 대기 중이라 watchdog 관점에선 안 죽은 것처럼 보임). 로그부재로 llama 사망 원인 자체는 불명. LlamaHarmonicity 수동재기동으로 즉시 복구(Day 511/Tick 12255+ 재개, 데이터손실 0)
  - ✅ **재발방지**: `LlamaHealthCheck` watchdog 신설(ogo, 5분 간격 SYSTEM, `llama_healthcheck.ps1` — localhost:8080/health 실패 시 LlamaHarmonicity 자동재기동). 기존 watchdog과 상보적. D-S1(안전레일) 설계에 실측 입력으로 kee에 전달
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
  - 🔴 **7/16 18:3x~7/17 13:47 ogo 19h 오프라인**(2번째 장기사고, 원인·복구경위 불명) [[reference_ogo_network]] → 복구 후 MJ31(31/31)+nonhuman(28/28) 완주 확인, hf-playground 재서빙(62/62 바이트일치 회수완료), 서버 종료
  - ✅ **7/17 14:01 사이즈이슈 원인 규명**: `[source|output] 콘캣` 가설 아니었음 — pipeline.py에 concat/paste 로직 없음(코드 확인), 원인은 단순히 `pipe()` 호출 시 height/width 미지정. 명시적으로 height=1024/width=1024 지정 시 정확히 (1024,1024) 단일 이미지 출력 확인(steps=4 축소테스트)
  - ✅ **Leo 승인 → 본배치 착수(14:XX)**: `gen_edit_main_batch.py` 작성(height/width=1024 명시 반영) — Style Reference 6장(softwatercolor/rainywindow/vintagetarot × kr_woman/kr_man 프롬프트 2종, 소스=lora_out 9종스윕) + Identity Edit 8장(고정소스=A_characters_photoreal/kr_young_woman_casual_seed42.png, 축별 조명2·표정2·의상2·배경2). SYSTEM task(Krea2EditMainBatch) detach 실행, 정상 시작 확인(모델로드 5.7s)
  - 다음: 14장 완주 대기(~4~5h 예상, 장당 ~20min) → hf-playground 회신·회수
  - ✅ **15:00 LEO 신규지시(hf경유) — 3기법 쌍비교 12장**: "플레인/앵커/앵커+락 다시 2개씩 비교, 인물은 락 걸리면 좋겠다". 구성: fashion_editorial(1024)+street_film(1344) × plain/anchor(기존 promptbank, Krea-2-Raw 32step guidance3.5)/anchor_lock(Krea2OstrisEdit+Identity Edit LoRA, 고정정체성=kr_young_woman_casual_seed42, 프롬프트접두 "Place this exact person...") × 시드42/123 = 12장
  - `gen_3technique_comparison.py` 작성 완료, SYSTEM task(Krea23TechCompare) 등록(트리거는 본배치 완료 후로 대기) — 동시 GPU 로드 시 OOM위험 판단, 순차실행 결정하고 hf에 근거+우선순위 재확인 발송
  - ✅ **15:2x LEO 확정 "비교 먼저"** → oven이 본배치 프로세스 안전종료(1/14 style_softwatercolor_kr_woman만 완료, manifest 보존) → **Krea23TechCompare 즉시 트리거**, Krea-2-Raw 로드+32step 생성 시작 확인(15:39)
  - ✅ **07-18 새벽 완료 확인(로그 "TECHNIQUE_COMPARE_DONE")**: 10/12 성공, 2건 실패 — street_film_anchor_lock seed42/123 둘 다 CUDA OOM(23.09GB 요청, PyTorch에 이미 49.47GB 할당된 상태 — Raw파이프라인 `del`+`empty_cache()`가 불충분했던 것으로 추정, fashion_editorial(1024) edit은 성공했으나 street_film(1344) edit만 실패)
  - ✅ **11:04 재시도 착수**: `retry_streetfilm_anchorlock.py`(Raw 파이프라인 없이 edit 파이프라인만 단독 로드하는 클린 프로세스) — SYSTEM task(Krea2RetryStreetfilm)로 실행, 정상 로드 확인(8.2s)
  - 🔴 **1차 재시도도 동일 OOM 재현**(49.47GB 동일 수치) — 클린 프로세스에서도 재현되어 "잔여물" 가설 기각, **1344 해상도 identity-edit 자체가 32GB 카드 용량 초과하는 진짜 한계**로 확정. hf스펙("1024 또는 1344") 범위 내에서 1024로 낮춰 2차 재시도 → 성공
  - 🔴 **원샷 schtask 재발화 위험 직접 경험**: Krea2RetryStreetfilm이 생성 직후 확인해보니 Next Run Time이 당일 오후로 무장돼 있어 실행중이던 재시도와 충돌 직전(3070의 leowin2 사고와 동일 계열) — 즉시 삭제로 회피, 이후 모든 원샷 task는 트리거 확인 직후 즉시 삭제로 전환 [[feedback_schtask_onetime_refire]]
  - ✅ **07-19 00:44 12/12 전량 완료 확인**(재시도 로그 "STREETFILM_RETRY_DONE"+manifest count 12/errors 0) — files.txt(13항목) 생성+8899 서빙 재기동+hf-playground 통지 완료
  - ✅ **00:55 hf-playground 회수완료**(13/13 바이트일치) + 본배치재개 GO → 서버 종료(PID 4164 kill, 재기동 위험한 스트레이 task도 정리) → **본배치 재개 착수**: `gen_edit_main_batch.py`에 resume 로직 추가(기존 manifest 로드해 완료된 tag 스킵) → 정상 재개 확인(style_softwatercolor_kr_woman 스킵, 다음 항목 진행)
  - 다음: 잔여 13장(style_reference 5+identity_edit 8) 완주 대기 → hf-playground 통지+서빙
  - 다음: 3기법비교 12장 완주 대기(소요 재추정중) → 서빙+hf통지 → 본배치 재개(잔여 13장, style_reference 5장+identity_edit 8장)
  - 📋 **21:34 hf-playground 큐 예약(회신불요)**: "프롬프트 공식 벤치 v1"(Krea-2-Raw 32step guidance3.5, 3모델레그×8브리프×2시드=48장) — 순번 3번째(3기법비교→본배치재개→이것)
  - ✅ **22:05 자료 준비 완료(회신불요)**: promptbank 정본 커밋됨(hf-playground repo `pipeline/krea2_prompt_formula_promptbank.py`, standalone·JSON의존없음), 드라이런 PASS. **실행 커맨드**(순번 되면): `gen_krea2_source.py --bank krea2_prompt_formula_promptbank --model C:\projects\krea2_test\model_raw --steps 32 --guidance 3.5 --out C:\projects\krea2_test\prompt_formula_out`. 파일명에 key(브리프id__레그)+seed 보존 필요
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
