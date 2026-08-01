# oven (Quincy/Liszt) KANBAN
업데이트: 2026-07-30

## 📦 캡슐 (세션 재개용 3줄)
① **마지막 완료**: **✅✅ appraisal 회귀 완전 수복(0% → 97%대) + D-L1 첫 정량 산출 + 게이트웨이 첫 완전 사이클**(07-30~08-01). 하모니시티 재기동 → D-트랙 배포 → 게이트 ON → **켜자마자 라이브 appraisal 파싱 98% 실패 포착** → 3라운드에 걸쳐 원인 규명·수복: ①mt 512→1536(무변화·**가설 기각**) ②진짜 원인=**슬롯 n_ctx 2048**(ctx-size/parallel) → parallel 4→2(슬롯 4096, 87.62%) ③**제약이 2단 적층**이라 A단계로 ctx 16384(슬롯 8192)+mt 3072 → **구간④ 중간 97.13%(507/15)**. 매 단계 사전등록·판정선 준수, **kee 개입 0회 자동 발효** 실증. 부산물: D-L1 1차 분석(n=709, ★내 가설 반증 자기정정·fallback 구간=「갈등이 기록되지 않는 세계」) + rep_floor 스펙 v0 저작(L2-003 완전 종결) + harmonicity.arkedia.work 복구.
① **(이전) 마지막 완료**: **✅ 하모니시티 라이브 재기동 + D-트랙 코드 배포**(07-30, LEO 승인). Sana 테스트 종료로 GPU 해제됨 → Day 565/Tick 13551에서 **무손실 재개**(정지=일시멈춤 확인). 재기동 전 **미배포 D-트랙 11파일 일괄 배포**(신규6: decision_log/safety_rail/autonomy/intervention/systems.economy/systems.institution + 수정5: main/conversation/encounter/llm/save_load) — 로컬 mock 3틱 PASS→ogo 백업(`code_backup/20260730_dtrack_deploy`)→scp→**해시 11/11 일치**+import PASS. **신규 기능 게이트는 전부 OFF 유지**(env 옵트인 9종 전수확인, 미설정 시 기존동작과 동일 = 정지점 "새 지시 없으면 홀드" 규칙 준수) → 활성화는 kee 게이트 대기. **harmonicity.arkedia.work 복구 200**(cloudflared 터널은 이 맥에서 계속 살아있었고, 죽어있던 건 ogo:8765 대시보드 → `HarmonicityDashboard` 태스크 기동으로 해결). watchdog 2종(HarmonicityHealthCheck/LlamaHealthCheck) ENABLE 복원. **kee 처분으로 관측·안전 3종(DECISION_LOG/KILL_SWITCH/SAFETY_SNAPSHOT) ON, 거동변경 3종 홀드** → 켜자마자 **라이브 appraisal 파싱 98% 실패** 포착(원인가설 max_tokens 512, kee 회부). 대조교훈: ogo PowerShell 파일목록은 **CRLF** 때문에 join/diff가 통째로 깨짐 — `tr -d '\r'` 필수.
① **(이전) 마지막 완료**: **✅ Sana+Krea2 LoRA 조사 전건 클로징**(07-29→30, hf-playground가 자기쪽에서 닫음, 오븐 큐 빔). Sana: 캐릭터일관성 FAIL(InsightFace B조건0.3983<문턱0.40)로 MV파이프 접목 보류. **부수 대발견 파장**: Krea2가 FLUX 아니라 자체 Krea2Pipeline(Qwen3VL) → LoRA 무효점검 확대 → **4종 중 정상은 공식krea LoRA 1종뿐**: detail_slider=확정무효, realism-V2=07-05원본도 픽셀대조(평균차0.2~0.5/255)로 무효였을 가능성 매우높음(육안대조 불요로 hf 동의), gokaygokay=매핑 미검증. **결론: 06-28 이후 Krea2 LoRA 캠페인 상당수가 사실상 base Turbo 출력**(품질 자체는 무관, 귀속만 재해석 필요). `get_list_adapters()` attach확인이 hf 표준절차로 등재됨. ogo 부수: C드라이브 2.7GB→30.2GB 정리, Krea2Pipeline VAE 하드크래시는 sequential_offload+fp32로 우회(근본원인 미확정, 재발시 이 메모 우선참조). 하모니시티는 정지 유지, GPU 자유.
② **다음 세션 할 일**: ①**3일 관찰 리포트(~08-03)는 4구간 비교로 확정** — ①고장 ②슬롯4096·mt1536 ③mt2560(87.62%) ④A단계(14004~), 구간별 관계지표 분리집계 + **①②구간에 「fallback=갈등 미기록」 캐비엇 필수** + `zero_relations`는 rep_floor 스펙 v0의 침식경로 한정 판독 규칙과 함께 인용 **<95%면 kee 재회부 없이 ②A단계 즉시 집행**(ctx 16384/parallel 2 + mt 3072, 사전승인 실물=`oven_kee_20260731_001500_...`), ≥95%면 현행 동결. 서버 미기동 시 즉시 롤백·보고 ①**하모니시티 3일 관찰(kee 지정, ~08-03)** — 전환 tick 13564 기준 전/후로 ①파싱 성공률 ②관계지표(rep_floor·포화율) 분리 보고(자연 A/B) — decision_records 적재율/틱당 오버헤드·KILL_SWITCH 오발동 0·스냅샷 회전·rep_floor 0.15 효과. 3일 후 kee 회신 필수 ②거동변경 게이트 3종(ECONOMY/INSTITUTION/AUTONOMY_LOCATION)은 **LEO 판단 대기** — 임의 활성화 금지 ③hf-playground/Leo 새 지시 대기(큐 비어있음). ari 커밋관례(author=oven, `-c user.name/email`) 계속 적용.
③ **상세**: [[project_harmonicity]](하모니시티 전체 이력+정지 상세) · [[project_ogo_gpu_management]] · [[feedback_llm_reasoning_token_budget]] · 본 파일 IN PROGRESS 섹션

---

## IN PROGRESS

- [ ] **하모니시티 라이브 재기동(2차) + D-트랙 배포** — oven/ogo — 2026-07-30 ✅ 기동완료, 관찰 진행중
  - LEO 승인(07-30) → 07-29 Sana건으로 내렸던 라이브 시뮬 재개. **Day 565 / Tick 13551에서 무손실 이어받음**(정지=일시멈춤 실증, 백업 `20260729_full_pre_sana` 사용 불요)
  - **선행 배포**: D-L1/S1/A1/C1/G2 + Phase A(intervention) 코드가 로컬 커밋만 되고 미배포 상태였음 → "다음 자연 재기동 시 배포" 계획대로 이번에 일괄 반영. 의존폐포 계산해 11파일 확정(main.py가 `intervention`을 무조건 import하므로 Phase A도 폐포에 포함됨)
  - 절차: 로컬 mock 3틱(`REPRO_MOCK_LLM=1`+격리 DATA_DIR, decision_records.jsonl 생성확인) → ogo 백업 → scp → **해시 11/11 일치 대조** → ogo import 무결성 PASS
  - **게이트 전량 OFF 유지**: 신규기능 9종 전부 env 옵트인(`HARMONICITY_DECISION_LOG`/`AUTONOMY_LOCATION`/`KILL_SWITCH`/`SAFETY_SNAPSHOT`/`ECONOMY`/`INSTITUTION` 등) 확인 → 미설정 = 기존 동작과 동일. 정지점 규칙("새 지시 없으면 홀드") 준수해 활성화는 **kee 게이트 회부 예정**
  - 기동 순서: LlamaHarmonicity(모델 로드 ~2분, GPU 26.1GB, health 200) → HarmonicityP11 → HarmonicityDashboard → watchdog 2종 ENABLE 복원
  - **harmonicity.arkedia.work 200 복구**(LEO 지시). 원인은 터널이 아니라 오리진: cloudflared(이 맥 launchd `com.cloudflared.harmonicity`, PID 1365)는 계속 살아있었고 ogo:8765 대시보드만 죽어 있었음. ⚠️ 호스트명은 harmoni**ci**ty(harmonycity는 미존재, 000)
  - ✅ **07-31 kee 게이트 처분 수령·즉시 반영**(kee 전결: env 플래그=가역·지출0이라 kee 범위, 단 세계 거동 변경은 LEO 내용결정이라 미승인)
    - **ON 3종**(관측·안전): `HARMONICITY_DECISION_LOG`(D-L1 판단포획, 세계 불변) · `HARMONICITY_KILL_SWITCH`(LLM 오류율 임계 정지) · `HARMONICITY_SAFETY_SNAPSHOT`(24틱 회전, keep 5)
    - **홀드 3종**(거동 변경): `HARMONICITY_ECONOMY`·`HARMONICITY_INSTITUTION`(LEO 여유 시 판단, 관측 3일 데이터 쌓인 뒤가 재료로도 나음) · `HARMONICITY_AUTONOMY_LOCATION`(최중량 — D-A2 max_tokens 1536 완주율 100% 전제 + 컴퓨트 여유 실측 동반 조건)
    - 반영: `launch_p11.bat`에 env 3줄 추가(홀드 3종은 주석으로 명시) → 백업 후 배포(해시 대조 fc82ebf) → HarmonicityP11 재기동, **Tick 13554 → 13555 무손실**
    - `launch_p11.bat`을 repo 정본으로 추적 시작(그동안 ogo에만 존재해 대조 불가였음 — 게이트 설정이 여기 있으니 추적 필요)
  - 🔴 **D-L1 첫 포착(07-30, 켠 지 몇 틱 만에)**: **라이브 appraisal 파싱 98% 실패** — sim.log 2000줄 창 `appraisal 파싱 실패` 163건 vs 대화 83건(기대 166회), decision_records 초기 4건 전부 `interpretation_status=fallback`/`choice=keyword_fallback`
    - 원인가설: `village/engine/appraisal.py:172` `chat(..., max_tokens=512)` — **D-A2가 45%로 실측한 바로 그 값**(reasoning_content가 예산 소진). 1536이면 100% 실증됨
    - 파장: 세션60(05-30) 도입 시 "파싱 100%"였으므로 **회귀**. 현 라이브는 appraisal이 아니라 **키워드 fallback으로 감정판정 중** → appraisal이 없애려던 '키워드 긍정편향 → 관계 포화 58%'가 되살아났을 개연성. **rep_floor/Ceiling 관찰 해석 시 교란요인으로 반드시 감안**
    - 512→1536 수정은 거동+컴퓨트 동시 변경이라 oven 단독처리 금지 → **kee 회부**(3일 기다리지 말고 선판단 권고 첨부). 상세 [[feedback_llm_reasoning_token_budget]]
    - ✅ **kee 전결 승인·즉시 집행(07-30 23:35)**: 성격이 "거동 신설"이 아니라 **회귀 수복**(세션60 파싱100%가 기준선, keyword_fallback이 고장상태)이라 경상 결재 범위로 판정. 정식 A/B는 **불요** — 현행 512 실측(98% fallback)과 세션60 100%가 이미 양끝을 잡아주므로 **전환 tick 마커 방식(자연 A/B)**으로 갈음
    - 집행: `appraisal.py` max_tokens 1536(커밋 **e4da25f**, ogo 해시 a70a817 대조 일치, 구버전 `*.bak512` 백업) → 재기동. **전환 마커: 저장상태 Tick 13563에서 재개 → 1536 첫 틱 13564**(중단 시점에 13564가 진행중이라 재실행됨, 데이터 손실 아님)
    - kee 조건 3건: ①집행실증(커밋해시+무손실+24h 내 파싱률 재실측 ≥95% 기대) 1회 보고 ②홀드 3종 합승 금지(불변) ③1536에서도 미회복이면 가설 기각 → 임의 추가상향 금지·재회부
  - 🔴🔴 **1536에서도 미회복(0%) → max_tokens 가설 기각. 진짜 원인 확정 = 슬롯당 n_ctx 2048** (07-30 재회부)
    - 읽기전용 진단(같은 프롬프트, max_tokens만 변경): mt=512→completion 512 / mt=1536→**1068** / mt=3072→**1068**(2배를 더 줘도 같은 자리에서 절단, content_len 전부 0)
    - 확정: llama-server `--ctx-size 8192 --parallel 4` → **슬롯당 n_ctx = 2048**(`/props` 실측 n_ctx=2048·total_slots=4). appraisal 프롬프트 1,926자(≈980토큰) + 생성 1068 ≈ 2048로 산술 일치
    - **정확한 규칙: `프롬프트토큰 + 필요생성토큰 < ctx-size/parallel`**. D-A2가 1536으로 풀린 건 그 프롬프트가 짧았기 때문일 뿐 — 판례 정정해 [[feedback_llm_reasoning_token_budget]]에 등재
    - 조치 후보 3안 회부(서버 재기동 필요): A)ctx 8192→16384/32768(VRAM 여유 4.3GB뿐이라 단계적) B)**parallel 4→2**(VRAM 증가 0, 동시성 절반 — oven 권고) C)프롬프트 축소. max_tokens 1536은 유지 권고(ctx 넓히면 필요해짐)
    - ✅ **kee 후보B 승인·집행 완료(07-30)**: `--parallel 4→2`(oven@a9603d8, ogo `D:\llama.cpp\start_gemma_harmonicity.bat`, 구버전 `.bak_parallel4` 보존, repo 정본 미러 추적 시작). `/props` 실측 **n_ctx 2048→4096 · total_slots 4→2**, VRAM 28,195→**27,507MiB(감소)**. 무손실 13566→13567. **새 자연A/B 마커 = Tick 13567**(13564는 폐기 — max_tokens 전환은 아무것도 못 바꿨음)
      - 안전순서 확립: 킬스위치 ON 상태에서 LLM 서버 교체 시 **watchdog 2종 DISABLE → 시뮬 정지 → 서버 교체 → health 200 → 시뮬 기동 → watchdog ENABLE**(안 그러면 오류율 임계로 SafetyHalt 위험)
      - 조건④ 틱 처리시간 전/후: 전(parallel4) 낮 82·100·117·139·107초 → 후(parallel2) 낮 127초 = **동시성 절반의 실비용 ≈ 0**(대화가 순차 처리라 슬롯 4개를 동시에 안 쓰고 있었음)
      - 🔴 **이전 보고 정정**: "틱 처리 8초/200초, 여유 24배"는 **심야 틱(대화 0건) 값**이었음. 낮 틱은 평균 ≈109초로 예산의 40~70%를 씀. 승인 근거로 쓰인 수치라 kee에 정정 보고함 — **향후 컴퓨트 판단은 낮 틱 기준**
    - 🔴🔴 **제약이 2단 적층이었음(B는 필요했으나 불충분)** — 슬롯 4096에서도 라이브 파싱 0%. 재진단: mt=512→completion 512 절단 / mt=1536→**completion 1536 소진, JSON 중도절단(content 182자)** / mt=3072→**finish=stop, completion 1363, content 766자, PARSE=OK** ✅
      - 필요 예산 ≈ 프롬프트 980 + 생성 1363 = **2,343토큰** → 옛 슬롯 2048로는 불가(B 필수) + max_tokens 1536으로도 불가(B만으론 불충분). 하나 풀면 다음 벽이 드러나는 구조
      - ✅ **kee 2560 승인·집행 완료(07-31 00:05 승인)**: `max_tokens 1536→2560`(oven@4bbc318, ogo 해시 a70f2d8 대조 일치, 구버전 `.bak1536` 보존) → 시뮬 재기동 → **✅ 파싱 회복 확인(성공 2 / 실패 0)**. **최종 자연A/B 마커 = Tick 13569**(13564 폐기, 13567은 "슬롯4096·파싱 여전히 0%" 중간 마커로만 존치)
      - 조건④ 낮 틱 proc 추이: 13567(mt1536) 127초 → 13568(mt1536) 146초 → **13569(mt2560) 163초 → 13570 153초 → 13572 152초**. 경보선 180초 미발동이나 예산 200초의 76~82%로 여유가 얇음 — 2560 실비용 ≈ +10~20초/틱. 180초 초과 시 즉시 kee 보고
      - ✅ **kee 판정(07-31 00:15): ③현행 유지 + ②A단계 조건부 사전 승인**
        - **★판정선(사전등록)**: 24h 정식 재실측(시간대 보정·최번시 기준) 결과 **파싱 <95% → ②집행 즉시 발효(추가 승인 불요, 그 메시지가 승인 실물)** / **≥95% → 현행 동결·관찰 완주(~08-03) 후 재판정**
        - **②발효 시 사양(그대로 집행)**: `--ctx-size 16384 --parallel 2`(슬롯 8192) + `appraisal.py` **max_tokens 3072** / watchdog 표준 순서 재사용 / **VRAM 미수용으로 서버 미기동 시 즉시 롤백 후 보고**(그 경우 ②폐기·재설계 회부) / 새 구간 마커 tick 기록(3→4구간 비교) / **proc>180초 즉시 보고 경보선 불변**
        - ①(2560→3072 단독)은 비채택 유지 — ②발효 시 3072가 함께 오므로 별도 트랙 아님
        - 지금 ②를 걸지 않는 이유(kee): VRAM 수용 미확정 + 틱 예산 이미 77~82% 사용 → **얇은 여유에서 변수 2개 동시 이동 금지**
        - ✅✅ **24h 정식 실측 완료(07-31 23:57, 마커 13569 → 14004 = 435틱 ≈ 24.2h)**: **최번시 성공률 87.62%(729/832)** — 전체구간도 동일(모든 appraisal이 proc>0 틱에서 발생). 교차검증 decision_records parsed율 84.28%(729/865, 회복 이전 구간 포함이라 낮게 나옴). proc>180 **0건**·최대 179초·평균 100.5초. 스냅샷 5개 정상 회전, halt 마커 없음
        - ✅✅ **판정선 적용 → A단계 발효·집행 완료**: 87.62% < 95%이므로 kee 조건부 사전승인 발효(추가 승인 불요). `--ctx-size 8192→16384`(슬롯 **8192**) + `max_tokens 2560→3072`, 커밋 **17c3e91**, ogo 해시 대조 일치(bat 7389d57 / appraisal 568f05d), 구버전 `.bak_ctx8192`·`.bak2560` 보존
          - **VRAM 수용 확인 — 롤백 불요**: 27,597 → 27,667MiB(KV 캐시 증가분 미미). `/props` 실측 **n_ctx=8192, total_slots=2**
          - watchdog 표준 순서 준수(DISABLE→시뮬정지→서버정지→배포→기동→health 200→`/props` 확인→시뮬기동→ENABLE)
          - **무손실 14003→14004**, **★새 자연A/B 마커 = Tick 14004**(4구간 비교: ①고장 ~13568 ②슬롯4096/mt1536 13567~13568 ③mt2560 13569~14003 ④A단계 14004~)
        - 📊 **중간 실측(07-31 15:52, 마커 이후 n=554)**: 파싱 **86.8%**(성공 481/실패 73) · **proc>180초 0건**(경보선 미발동, 최대 179초로 경계 밀착) · proc>0 평균 101초 · 스냅샷 5개 정상 회전(13752~13848) · decision_records 587건 · halt 마커 없음
    - ✅✅✅ **A단계 24h 재실측 = 97.26%(815/23, n=838, Tick 14004→14440 ≈24.2h) ≥ 95% → A단계 종결·관찰 모드 전환 확정(08-02)**. 추가 상향 없음. **관찰 기준선 고정: `--ctx-size 16384 --parallel 2`(슬롯 8192) + `max_tokens 3072`**
      - **회복 경로 완결**: ①고장 **0%** → ②슬롯4096·mt1536 **0%** → ③슬롯4096·mt2560 **87.62%** → ④슬롯8192·mt3072 **97.26%**
      - 교차검증 decision_records 누적 parsed율 90.66%(1544/1703, 회복 이전 구간 포함이라 낮음). proc **>180 0건**·최대 168초·평균 99.8초. 스냅샷 5개 회전, halt 없음, VRAM 27.8GB
      - 🔴 **★proc 감소 추정 철회(자기반증)**: 초기 n=3(평균 156→138)이 **창 노이즈**였음. 전체창 실측 = 틱평균 100.5→99.8초(**-0.70%**), **대화당 정규화 74.95→74.37초(-0.77%)**, 대화량 417 vs 420으로 거의 동일해 교란 없음 → **«품질·컴퓨트 동반 개선» 계상 금지, 이번 개선은 품질 단독**(컴퓨트 중립). 최대 proc 179→168 꼬리 축소는 관측 사실로만 두고 인과 미주장. **«뒤집히면 철회» 사전등록이 실제로 작동한 사례**
      - ✅ **kee 종결 발효 확인(08-02)**: 산술 대조 **7/7 PASS**(성공률·교차검증·합계·대화당 정규화 2건·차이·구간길이 전부 선언 일치). **kee 승인 0회로 판정선 자동 적용** — 07-31 87.62%엔 «발효», 08-02 97.26%엔 «종결»로 **같은 장치가 양방향 작동**한 것이 이번 사이클의 값. 기준선 고정 승인
      - ✅ **철회 접수 + ★대장 오염 0 확인**: kee 대장·캡슐·보드 전수 grep 결과 «proc 감소»·«동반 개선» 문자열 **0건** = **추정이 기록에 도달하기 전에 회수됨**. 계상은 **«품질 단독 개선·컴퓨트 중립»**으로 확정. kee 별도 계상 2건: ①추정 철회에서 멈추지 않고 **그 추정을 낳은 전제까지 되짚은 것** ②최악값 개선(179→168초)을 **관측 사실로만 두고 인과 미주장**한 처리
      - 📌 교훈 [[feedback_verify_before_report]]에 «사전등록» 규율로 확장 등재 — 사후 철회 결심과 사전 조건 등록은 다르며 **후자만 압력 아래서 버팀**
      - 🟡 **(경과) 부분 회복 중간값**: 성공 10 / 실패 3 = **77%**(n=13). decision_records에 `parsed`가 실제로 찍히기 시작(이전 전량 fallback) — D-L1이 진짜 판단을 포착하기 시작함. 잔여 실패는 reasoning 길이 변동(3,429~4,982자 실측)이 2560을 넘는 회차로 추정. 정식 수치는 24h 재실측(kee 조건②)
    - ⚠️ **관찰 영향**: 회복 완료 전까지 라이브는 keyword_fallback으로 감정판정 → 3일 관찰의 관계지표는 "appraisal 고장 상태" 데이터임을 리포트에 명기할 것

- [x] **D-L1 1차 분석 + rep_floor 스펙화(L2-003)** — oven/kee/SEAL — 2026-07-31 ✅ **게이트웨이 첫 완전 사이클 종결**
  - **D-L1 판단기록 1차 분석**(n=709, oven@e7d3f11 `HARMONYCITY_D-L1_FIRST_ANALYSIS_20260731.md` + 재현 스크립트): ①tension이 fallback 구간에서 사실상 죽어 있었음(+0.0001 vs +0.0181, 180배차) → **"갈등이 기록되지 않는 세계"**였을 개연성 ②🔴 **내 가설 반증** — warmth/trust 양수비율이 parsed(79.8/84.8%)가 fallback(64.6/70.7%)보다 높음. "키워드 긍정편향 부활" 주장은 데이터가 지지 안 함(kee 대장 인용 0건 확인, 반증 사실만 계상) ③Ceiling 포화 재발 0건 ④선택편향 한계 명기(fallback=긴 reasoning 회차 편중, 무작위 배정 아님)
  - **rep_floor = 부분 하한 발견 → L2-003 회부**: floor는 `homeostasis.py:142-143` 평판침식 경로에만 적용, 감쇠·갈등은 통과. 저작자 규명 회신(=oven 저작·LEO 7/19 직지시·**페블 무관이라 L1 직행 사유 없음**·설계 정본 부존재)
  - ✅ **L2-003 확정(SEAL 페블+solself 양측 대조)**: **② 침식 한정 유지 — 코드 무수정**. 전 경로 확장은 「관계가 완전히 식는 상태」를 세계에서 삭제하는 중대한 의미 변경이라 명시 승인 없이 불가. **LEO 명시 지시 시 재심**(solself 조건)
  - ✅ **발주 2건 이행·검수 통과(수정 불요)**: 스펙 저작 oven@**f26f86d** `HARMONYCITY_REP_FLOOR_SPEC_v0.md` + 0.0쌍 경량 규명
  - **★0.0쌍 규명 = 갈등 유래 확정, 버그 기각**(3근거): ①60일 warmth max 0.0~0.037 = 감쇠 아니라 애초에 안 오름(last_interaction 578~581로 활발) ②부정 판정 지배(ha_yeon|sang_woo 8건 중 부정 6 / 대조군 32건 중 양수 30) ③warmth 델타 0 = 이미 0 클램프지 계산 실패 아님. 한계=D-L1 켠 Day 566 이후 15일 창만 커버
  - 📌 **인용 의무(kee 지정)**: `zero_relations` 지표 정본은 **스펙 v0가 소유**(별도 정본 신설 불요, G-K4 단일기재). **3일 관찰 리포트(~08-03)와 SEAL 파일럿 롤업(08-14) 두 곳 모두에서 「침식 경로 하한 한정 판독」 규칙과 함께 인용할 것**
  - 별건 이월: ⓐ값 0.15 재조정(필요 시 재회부) ⓑ인과 설계(동일 대화 2경로)=A단계 안착 후 재론
    - 부수: decision_record `tick` 필드에 실제로는 **day**가 들어감(코드 주석에 MVP 근사 명시) — 적재율 정밀분석엔 tick 스레딩 필요
  - **관찰 3일(kee 지정 지표)**: ①decision_records.jsonl 적재율·틱당 오버헤드 ②KILL_SWITCH 오발동 0(발동 시 즉시 kee 통지) ③스냅샷 회전 정상·디스크 증가율 ④rep_floor 0.15 재개분(warmth/trust 하한·Ceiling 포화). 3일 후 kee 회신 → 거동변경 3종 상정 여부 판단

- [x] **하모니시티 재가동 + rep_floor 오버라이드(1차)** — oven/ogo — 2026-07-19 착수, 07-29 Sana건으로 관찰 중단
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
  - ✅ **08-01 귀속 확정(kimsecretary 질의 회신)**: **LoRA 미적재 확정** — ①`gen_krea2_source.py`의 `--lora-repo` 기본값 빈문자열 + `if args.lora_repo:` 가드 ②러너 4종(`run_retry60`/`run_mj_guarded`/`run_retry_final`/`run_retry_final2`) **전부 `--lora-*` 인자 0건** ③런타임 manifest **`lora_repo: null`·`lora_weight: null`·`errors: {}`**. → **귀속 = base Krea2-Raw(model_raw, 비증류 BASE — ★Turbo 아님)**, steps 32/guidance 3.5. hf 제안 1장 판별 절차는 **불요**(LoRA 물렸을 때만 하는 절차)
  - 🔴 **제 미발신 누락 확인**: 07-17 완주 후 hf-playground에만 회신하고 **kimsecretary에는 안 보냄** → LEO 보고가 지금껏 안 올라간 원인. 회신 유실 아님. 다행히 오귀속이 LEO 기록에 들어가기 전에 잡힘
  - ⚠️ **manifest 장수 ≠ 실물**(nonhuman assets 12 / mj 31 vs 실물 PNG 28 / 32) — 마지막 재발사분만 덮어쓴 결과. **완주 판정·인용은 실물 PNG 개수로 할 것**
  - ✅ **08-01 kimsecretary 접수·종결**: base=Turbo 정정 수용(«base Krea2-Raw(비증류, model_raw)·LoRA 미적재·steps 32·guidance 3.5»로 기록), manifest 대신 **실물 PNG 28+32=60장** 기준 채택. LEO 보고는 «정정»이 아니라 **«사전 차단»**으로 올라감(오귀속이 애초에 생길 여지 없었음) + 60장 결과 자체도 함께 보고
  - 🔴 **성문화된 규율(재발방지)**: **작업을 발주한 주체에게는 완료 회신을 반드시 1건, cc 아니라 to로** — 기술 협업 상대(hf)와 발주자(kimsecretary)가 다를 때 기술 쪽에만 회신하면 LEO 보고 라인이 통째로 끊김. 상세 [[reference_agent_comm]]
  - 별건 **보류(kimsecretary 판단)**: realism-V2 «거의 확실 무효 → 확정 무효» 승격 재검은 **지금 발주 안 함** — 어느 등급이든 안 쓰므로 의사결정이 안 바뀌고 GPU 슬롯 비용이 실익보다 큼. **LoRA 재도입 검토 시점에 gokaygokay 매핑 미검증 해소와 묶어 1슬롯으로 처리** 예정. LEO가 이미지 라인 재개 지시 시 kimsecretary가 재발주 — **oven이 먼저 움직이지 말 것**

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
  - ✅ **07-23 D-S1(안전레일) MVP 완료**: `village/safety_rail.py` 신규 — 킬스위치(LLM 오류율 임계50% 초과시 SafetyHalt로 그레이스풀 정지, appraisal파싱실패와 무관한 별개신호) + 스냅샷(24틱마다 회전보관 5개) + 수동복원. 검증 4종 전부 PASS(무영향회귀/스냅샷생성/킬스위치발동/복원). 스펙에 리스크 기록: 킬스위치 발동해도 기존 watchdog이 재기동시켜 halt-restart 반복 가능 — 후속과제로 명시. kee 조건부 게이트 PASS → D-A1 착수 GO
  - ✅ **07-23 D-A1(자율경계확장) MVP 구현+검증 완료**: `village/autonomy.py` 신규 — encounter.py의 위치배정 20%랜덤 ally방문 분기를 LLM 스캐폴딩 선택으로 대체(형식이탈시 기존스크립트 안전fallback, 관계수치로직 불가침). 검증(격리world 실LLM 20틱 N=37): 형식이탈율 46%(1차보고) / 판단분산·니즈상관 확인(목표명시 캐릭터는 그 장소로 일관수렴, affection우세시 cafe쏠림)
  - ✅ **07-23 halt-loop 가드 완료**(kee 선행필수 격상 지시): `safety_rail.record_halt_and_check_loop()`/`reset_halt_guard()` — 연속halt 3회/1h시 watchdog 자가DISABLE+`HALT_LOOP_GUARD_TRIGGERED.json` 마커(파일기반, 프로세스 재기동 넘어 누적). 검증 PASS(3회연속 킬스위치→3회째 정확 트리거+마커+리셋 확인). **oven 세션재개 루틴에 마커 점검 추가**(kee 지시, 완전자동통지는 YAGNI로 보류)
  - ✅✅ **07-23 D-A2 원인규명 완료 — 형식이탈46%는 모델한계 아닌 공학적 문제(토큰예산)**: 3변형 비교(N=20 each) — baseline(mt512)=45%, final-marker+추론허용(mt512)=**0%**(역설적 악화), baseline(mt1536, 토큰만 상향)=**100%**. "thinking 없이" 억제문구가 실제 유효함을 반증. `autonomy.py` max_tokens 512→1536 수정+재검증 10/10=100% 확인. kee 게이트 재판정 **통과**(모델한계 아님 확정) → D-A3 재개 GO
  - ✅ **07-23 D-A3 판단분산 본계측 완료**: ①자기 고유목표 반복(N=8)=거의 완전 결정론(entropy 0~0.54, 목표가 구체적이라 답이 하나뿐) ②동일 합성 니즈/목표 강제부여 후 5캐릭터 비교=페르소나별 체계적 차이 확인(luna/min_ah→plaza, tae_sik/aria→cafe) — "**개별 법의 존재**" 판정선 통과(입력이 애매할 때만 분산이 드러남). 컴퓨트예산 관측(kee 신설 게이트)은 새로 안 만들고 기존 `profiling.py`(HARMONICITY_PROFILE) 재사용으로 충분 확인. D-L1/S1/A1(A2/A3) 1차 사이클 완료
  - ✅ **07-23 A-058 §E 3원칙 GO(LEO 결재) → D-C1/D-G2(제도·경제 슬롯) 착수+완료**: `village/systems/economy.py`(favor 자원 관측, 일일상한3=§E-①S12 enforce)·`institution.py`(CONNECTOR/SUPPORTER 고정목록+규칙도출=§E-③P5/P7, 조건미달시 강등아닌 조용한 role=None복귀=§E-②신뢰가중치 비처벌) 신설. **규칙기반이라 LLM호출 추가 0건 — D-A2류 완주율리스크 원천배제**(kee 호평). 검증 전부 PASS(무영향회귀/일일상한 5회중3회만성공/역할배정+비처벌복귀 페널티필드 0건 확인/통합테스트). MEDIATOR는 갈등중재 앵커데이터 부재로 2차라운드 보류(kee 동의)
  - 다음: 라이브 배포는 다음 자연 재기동 시점(D-L1/S1/A1과 함께). 추가 지시 대기 — judgment_type=null의 canonical 정합은 페블 판단 계속 대기
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
