# 하모니시티 D-L1 — decision_record 스펙 v0 (T0 게이트 초안)

> 작성: oven, 2026-07-22. 페블 트랙B `harmonycity-injection-diff-v0.md` §4 D-L1 실행 스펙.
> 상위 정합: `decision-substrate-principles-v0.md §2/§3`(원자 단위·판단포획), `A-046 §7-4-5`, `video-studio-autonomy-pilot-setup-kit-v0.md B4`(모두 "오븐 M4 동형"으로 이 스펙을 앵커 삼음 — 재발명 아닌 이식이 되도록 필드를 canonical 스키마에서 그대로 가져옴).
> 게이트 경로: 이 스펙 → 페블 감수 → kee T0 판정 → 로컬 mock 검증 → (승인 시) 라이브 배포.

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
  "choice": "실제 선택/생성된 값 — 발화 내용, 또는 appraisal 판정",
  "outcome": {"relationships_delta": {"warmth": 0.01, "trust": -0.02}, "applied": true},
  "reversible": true,
  "cap_bound": "WARMTH_SOFT_CEILING",
  "gate_passed": true,
  "confidence": null,
  "provenance": {"replay_ref": "sha256(messages)[:12] 또는 record jsonl 오프셋"},
  "status": "applied",
  "links": {"data_dir": "...", "sim_log_line": 267310}
}
```

### 필드별 근거

| 필드 | canonical 출처 | harmonicity 적용 |
|---|---|---|
| `judgment_type` | §2/§4 | 현재 전부 **"분석"** — "미완성 자율 판단 보조, sim 테스트 통과+실측 신뢰도"가 정확히 하모니시티 그 자체. "감각"(A&R류 큐레이션)·"방향"(전략)은 해당 사항 없음 |
| `decider` | §2 (LEO\|위임에이전트\|정책\|게이트) | 캐릭터 LLM = "위임에이전트"로 매핑(재정의 아님, enum 값 재사용). `id`로 캐릭터명 구분 |
| `basis`/`alternatives_considered` | §2 | basis=필수. alternatives_considered=현재 자유생성(대화/독백)이라 대개 null — appraisal처럼 구조화 후보가 있는 판단유형만 채움. D-A2(폴백 태깅) 확장 시 후보목록이 생기면 채워짐 |
| `reversible`/`cap_bound` | §2/§7 안전레일 | 관계수치 변경은 대부분 감쇠형(true), cap_bound는 해당 soft-ceiling 상수명 참조(homeostasis.py WARMTH_SOFT_CEILING 등) — D-S1 킬스위치의 관측 대상이 될 필드 |
| `gate_passed` | §2 | **appraisal 파싱 성공 여부에 직결** — 실패 시 false+키워드폴백. D-A2("폴백을 자율실패 관측데이터로 태깅")가 이 필드 하나로 즉시 충족됨 |
| `confidence` | §2 | 현재 LLM이 명시적 confidence 미반환 → null 기본. 향후 세 다이얼(§4) 확장 시 채울 자리만 선점 |
| `provenance` | §2 | replay.py 레코드(옵트인)와 **교차조회용 참조만** 저장 — 병합 안 함(kee 승인사항) |
| `choice`/`outcome` | ★확장(페블 확인 요청) | D-L1 원 요구사항 충족용. 없으면 "무엇을 선택해서 뭐가 바뀌었는지"가 basis/status만으로 재구성 불가 |

## 3. 트랙 분리 원칙 (kee 승인사항 반영)

- **별도 모듈** `village/decision_log.py` — profiling.py/replay.py와 동일한 옵트인 패턴(env var 가드, 라이브 무영향 기본값).
- **replay와 병합 안 함**: replay는 "배치 비결정성 우회용 LLM I/O 원문 재생"이 목적, decision_record는 "구조화 판단 감사·재사용"이 목적. `provenance.replay_ref`로만 교차조회.
- 옵트인 가드: `HARMONICITY_DECISION_LOG=1` (미설정 시 기존 동작과 완전 동일 — 무영향 원칙, config.py 재현성 플래그·profiling과 동일 컨벤션).

## 4. MVP 계측 지점 (T0 범위)

현재 M1 기준 LLM이 실제로 "판단"하는 곳은 둘뿐 — 이 둘만 우선 계측한다(행위선택은 D-A1 몫, 아직 없음):

1. **대화/독백 생성** (`llm.chat` 호출 지점) — choice=생성문, alternatives_considered=null(자유생성), outcome=대화 로그 자체(직접적 세계상태 변화는 없음, status="applied").
2. **appraisal 판정** (`engine/appraisal.py run_appraisal`) — choice=파싱된 감정/델타, outcome=`apply_appraisal`이 반영한 실제 relationships 필드 변화, gate_passed=파싱 성공여부(이미 있는 정보를 구조화만 하면 됨).

## 5. 검증 계획 (로컬 mock, 라이브 무영향)

1. `HARMONICITY_DECISION_LOG=1` 없이 6틱 mock 스모크 — 해시 불변(기존 재현성 회귀 테스트 그대로) 확인.
2. `HARMONICITY_DECISION_LOG=1` 설정 후 6틱 mock — decision_record jsonl 생성 확인, 필드 전수 채움 확인(appraisal 파싱 성공/실패 케이스 각 1건 이상 포함되도록 시드 선택).
3. gate_passed=false(폴백) 케이스가 실제로 잡히는지 확인 — D-A2 선행 검증까지 겸함.

## 6. 페블 감수 요청 사항

- `choice`/`outcome` 필드 확장 승인 여부(canonical에 없는 추가).
- `judgment_type="분석"` 단일 고정이 맞는지(향후 "감각" 해당 판단유형이 하모니시티에 생길지 — 예: 캐릭터 간 미감 판단?).
- `decider.role="위임에이전트"` 매핑 적절성.
