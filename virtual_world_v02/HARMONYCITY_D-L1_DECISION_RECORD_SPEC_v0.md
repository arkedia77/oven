# 하모니시티 D-L1 — decision_record 스펙 v0.1 (T0 게이트 PASS·조건반영)

> 작성: oven, 2026-07-22. 페블 트랙B `harmonycity-injection-diff-v0.md` §4 D-L1 실행 스펙.
> 상위 정합: `decision-substrate-principles-v0.md §2/§3`(원자 단위·판단포획), `A-046 §7-4-5`, `video-studio-autonomy-pilot-setup-kit-v0.md B4`(모두 "오븐 M4 동형"으로 이 스펙을 앵커 삼음 — 재발명 아닌 이식이 되도록 필드를 canonical 스키마에서 그대로 가져옴).
> 게이트 경로: 스펙 v0 → 페블 감수(조건부 PASS) → **kee T0 게이트 PASS(2026-07-22)** → 조건 3건 반영(v0.1, 본 개정) → 로컬 mock 검증 → (승인 시) 라이브 배포.
> ★choice/outcome 확장은 페블 소견상 canonical §2 잠재 갭으로 인정됨(4트랙 수렴) — 정식 canonical 승격은 페블 별도 트랙, 여기선 "승격 가정하고 정렬"만.

---

## 1. 목표

M4(로깅구조) 갭 — "에이전트 자체 판단을 decider+근거로 포획해 재사용 가능한 구조화 로그가 없음" — 을 해소한다. sim.log(자연어)·replay(LLM I/O 원문)와 별도 트랙으로, 매 에이전트 판단을 구조화 `decision_record`로 남긴다.

## 2. 스키마

`decision-substrate-principles-v0.md §2` 원자 스키마를 그대로 채택하고, 페블 D-L1 5필드 요구(`{decider, 근거, 선택지, 선택, 결과}`)를 만족시키기 위해 canonical에 없는 `choice`/`outcome` 2필드를 확장 제안한다(★페블 감수 시 확인 요청 — 임의 추가이므로).

```json
{
  "id": "dr_<sha256(payload)[:16]>",
  "tick": 10961,
  "world_id": "data 또는 격리 world dir명",
  "judgment_type": "분석",
  "decider": {"role": "위임에이전트", "id": "아리아"},
  "basis": "판단에 주어진 세계상태 관측 요약 — 프롬프트에 들어간 컨텍스트(상대 발화·관계수치·니즈·최근기억)",
  "alternatives_considered": null,
  "choice": "선택된 값의 참조/식별자 — 자유생성이라 후보목록이 없는 현 MVP에서는 생성된 값 자체가 곧 선택 식별자",
  "outcome": {"relationships_delta": {"warmth": 0.01, "trust": -0.02}, "realized": true},
  "reversible": true,
  "cap_bound": "WARMTH_SOFT_CEILING",
  "gate_passed": null,
  "interpretation_status": "parsed",
  "confidence": null,
  "provenance": {"replay_ref": "sha256(messages)[:12] 또는 record jsonl 오프셋"},
  "status": "open",
  "links": {"data_dir": "...", "sim_log_line": 267310}
}
```

### 필드별 근거

| 필드 | canonical 출처 | harmonicity 적용 |
|---|---|---|
| `judgment_type` | §2/§4 | 현재 전부 **"분석"** — "미완성 자율 판단 보조, sim 테스트 통과+실측 신뢰도"가 정확히 하모니시티 그 자체. "감각"(A&R류 큐레이션)·"방향"(전략)은 해당 사항 없음. ★고정이지만 태깅여지 남김 — 향후 캐릭터간 미감 판단류가 생기면 "감각"으로 재판정(kee 조건2) |
| `decider` | §2 (LEO\|위임에이전트\|정책\|게이트) | 캐릭터 LLM = "위임에이전트"로 매핑(재정의 아님, enum 값 재사용). `id`로 캐릭터명 구분 |
| `basis`/`alternatives_considered` | §2 | basis=필수. alternatives_considered=현재 자유생성(대화/독백)이라 대개 null — appraisal처럼 구조화 후보가 있는 판단유형만 채움. D-A2(폴백 태깅) 확장 시 후보목록이 생기면 채워짐 |
| `reversible`/`cap_bound` | §2/§7 안전레일 | 관계수치 변경은 대부분 감쇠형(true), cap_bound는 해당 soft-ceiling 상수명 참조(homeostasis.py WARMTH_SOFT_CEILING 등) — D-S1 킬스위치의 관측 대상이 될 필드 |
| `gate_passed` | §2 | **canonical 원래 의미(감사·승인 게이트 통과여부) 그대로 보존** — 현재 하모니시티엔 형식 게이트가 없어 기본 null. appraisal 파싱 성공여부와 **더 이상 혼입하지 않음**(kee 조건3) |
| `interpretation_status` | ★신규(kee 조건3 분리) | appraisal 파싱 성공="parsed" / 실패+키워드폴백="fallback". D-A2("폴백=자율실패 관측데이터화")는 이 필드로 충족, gate_passed와 별개 |
| `confidence` | §2 | 현재 LLM이 명시적 confidence 미반환 → null 기본. 향후 세 다이얼(§4) 확장 시 채울 자리만 선점 |
| `provenance` | §2 | replay.py 레코드(옵트인)와 **교차조회용 참조만** 저장 — 병합 안 함(kee 승인사항) |
| `choice` | ★확장(페블 조건부 승인) | 선택된 alternative의 참조·식별자(kee 조건1) — status(레코드 생애)나 outcome(세계효과)과 구분되는, "무엇이 선택됐나"만 가리키는 필드 |
| `outcome` | ★확장(페블 조건부 승인) | 실현된 결과·verdict(세계효과) — status와 구분(kee 조건1). "realized" bool + 실제 반영된 변화량 |
| `status` | §2, 의미 정정(kee 조건1) | **레코드 자체의 생애주기** — open(신규 기록)/promoted(코퍼스 등 승격)/rejected(무효 판정). 실행결과(적용/폴백 여부)는 outcome·interpretation_status가 담당하므로 status에 섞지 않음. MVP는 전부 "open" |

## 3. 트랙 분리 원칙 (kee 승인사항 반영)

- **별도 모듈** `village/decision_log.py` — profiling.py/replay.py와 동일한 옵트인 패턴(env var 가드, 라이브 무영향 기본값).
- **replay와 병합 안 함**: replay는 "배치 비결정성 우회용 LLM I/O 원문 재생"이 목적, decision_record는 "구조화 판단 감사·재사용"이 목적. `provenance.replay_ref`로만 교차조회.
- 옵트인 가드: `HARMONICITY_DECISION_LOG=1` (미설정 시 기존 동작과 완전 동일 — 무영향 원칙, config.py 재현성 플래그·profiling과 동일 컨벤션).

## 4. MVP 계측 지점 (T0 범위)

현재 M1 기준 LLM이 실제로 "판단"하는 곳은 둘뿐 — 이 둘만 우선 계측한다(행위선택은 D-A1 몫, 아직 없음):

1. **대화/독백 생성** (`llm.chat` 호출 지점) — choice=생성문(식별자 겸용), alternatives_considered=null(자유생성), outcome={"realized": true}(직접적 세계상태 변화 없음), status="open", interpretation_status 해당없음(null).
2. **appraisal 판정** (`engine/appraisal.py run_appraisal`) — choice=파싱된 감정/델타 식별자, outcome=`apply_appraisal`이 반영한 실제 relationships 필드 변화, interpretation_status=파싱 성공여부("parsed"/"fallback", 이미 있는 정보를 구조화만 하면 됨), status="open".

## 5. 검증 계획 (로컬 mock, 라이브 무영향)

1. `HARMONICITY_DECISION_LOG=1` 없이 6틱 mock 스모크 — 해시 불변(기존 재현성 회귀 테스트 그대로) 확인.
2. `HARMONICITY_DECISION_LOG=1` 설정 후 6틱 mock — decision_record jsonl 생성 확인, 필드 전수 채움 확인(appraisal 파싱 성공/실패 케이스 각 1건 이상 포함되도록 시드 선택).
3. `interpretation_status="fallback"`(appraisal 폴백) 케이스가 실제로 잡히는지 확인 — D-A2 선행 검증까지 겸함.

## 6. 게이트 이력

- **페블 감수**: 조건부 PASS(choice/outcome 확장 정합·5필드 중 decider/basis/alternatives 무손실 직매핑 확인). choice/outcome은 canonical §2 잠재 갭으로 인정(4트랙 수렴) — 정식 승격은 페블 별도 트랙.
- **kee T0 게이트**: PASS(조건부, 2026-07-22) — 적용조건 3건(①outcome≠status 구분 ②judgment_type 분석고정 유지 ③gate_passed/interpretation_status 오버로드 분리) 전부 본 개정(v0.1)에 반영 완료.
- 다음 게이트: 로컬 mock 구현·검증 완료 후 kee 보고 → D-S1(안전레일) 게이트로 진행.
