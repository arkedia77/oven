# 하모니시티 D-C1/D-G2 — 제도·경제 슬롯 MVP 스펙 v0 (제안, kee 게이트 대기)

> 작성: oven, 2026-07-23. kee 착수발주 — 페블 확정 주입순서(제도경제 1순위), §E 3원칙(A-058 GO)을 설계 정합 기준으로 반영.
> 게이트 경로: 이 스펙 → kee 게이트 → (승인 시) 로컬 구현+mock/격리world 검증 → kee 보고 (D-L1/D-S1 동일 절차).

---

## 1. §E 3원칙 적용

| 원칙 | 이 스펙에서의 적용 |
|---|---|
| ①S12(밴드+불변식, 차익차단) | 신설 자원("호의")에 **일일 상한**(밴드) — 캐릭터당 하루 누적 상한 초과 시 추가 발생 차단(enforce 선행 체크). 무한 축적(차익) 방지. |
| ②신뢰가중치(보상추적≠처벌추적) | 제도(역할) 결정화는 **긍정 상호작용 누적으로만** 발생 — 갈등·실패로 역할이 강등되지 않음. 교정이 필요하면 역할 **재배치**(다른 역할로 전환)이지 역할 박탈/수치 강등이 아님. |
| ③P5/P7(생성/고정 경계) | **역할 분류체계(taxonomy)는 고정**(사전 큐레이션된 소수 목록) — LLM이 임의로 새 역할을 발명하지 않음. **역할의 배정(누가 어떤 역할인지)은 생성**(기존 관계·상호작용 데이터에서 규칙으로 도출). |

## 2. 범위 — 왜 규칙기반인가(LLM 호출 추가 없음)

M2(발생기) 진단상 하모니시티 엔진은 이미 "규칙·인센티브 구동"이 확립돼 있다(homeostasis.py/reputation.py 패턴과 동일 계열). D-C1/D-G2는 자율(D-A1)이 아니라 **발생기·복리 축 보강**이므로, LLM 판단을 새로 추가하지 않고 **기존 데이터(relationships.json/reputation/appraisal 델타)에서 결정론적 규칙으로 도출**한다. 이렇게 하면:
- D-A2에서 겪은 "형식이탈/완주율" 리스크가 원천적으로 없음(LLM 호출 자체가 없으므로).
- 컴퓨트 예산(S12) 부담이 D-A1류보다 훨씬 낮음 — 순수 연산.

## 3. D-G2 — 경제 슬롯 MVP (`village/systems/economy.py`, 신설)

- **자원**: `favor`(호의) — 새 통화를 만들지 않고, **기존 appraisal 델타(warmth_delta>0)를 관측해 부여**. 대화에서 상대에게 순호감을 준 쪽이 호의 1점 획득(정수 카운터, 캐릭터별 `data/economy.json`에 저장).
- **밴드(①)**: 캐릭터당 **일일 획득 상한**(제안: 3점/일). 초과분은 버림(enforce 선행 — 카운터 증가 전에 오늘 누적치 체크).
- **소진**: MVP는 **관측만**(교환 행동에 아직 안 씀) — D-A1처럼 처음엔 관측 전용으로 시작해 후속 라운드에서 "호의를 자원 삼아 무언가 요청" 행동에 연결(범위 확대는 별도 게이트).
- 옵트인: `HARMONICITY_ECONOMY=1`. 미설정 시 무영향(관측 코드가 아예 안 돎).

## 4. D-C1 — 제도 슬롯 MVP (`village/systems/institution.py`, 신설)

- **고정 역할 목록(③)**: `CONNECTOR`(연결자 — 활성 관계 다수+평균 warmth 높음), `SUPPORTER`(지지자 — 특정 1인과 지속적 고warmth), `MEDIATOR`(중재자 — tension 높은 쌍과의 상호작용 이력, 향후 갈등중재 이벤트 연동 여지).
- **결정화 규칙(②, 보상추적 전용)**: 예시 —
  - CONNECTOR: `active_relationships(warmth>0.6) >= 4`
  - SUPPORTER: 특정 상대와 `warmth >= 0.8` AND `interaction_count >= 10`
  - MEDIATOR: (MVP는 보류 — 갈등중재 이벤트 자체가 아직 없어 앵커 데이터 부재. D-C1 2차 라운드 후보로 명시만.)
- **비처벌 원칙**: 조건 미달로 떨어지면 "역할 제거"가 아니라 **role=None(미배정)으로 조용히 복귀** — 강등 이벤트·페널티 없음. 조건 재충족 시 재획득.
- 매일(24틱) 1회 재계산, `data/institutions.json`에 캐릭터별 role 스냅샷 저장.
- 옵트인: `HARMONICITY_INSTITUTION=1`.

## 5. D-L1 연동

역할 배정/변경 이벤트는 decision_record로 기록 — `decider={"role": "정책", "id": "institution_rule"}`(LLM 판단이 아니므로 "위임에이전트" 아님, canonical의 "정책" 값 그대로 사용), `judgment_type`은 이 스키마 밖(규칙 기반이라 판단유형 다이얼 미해당 — 필드는 null 처리 제안, 페블 확인 요청).

## 6. 검증 계획

1. 가드 미설정 mock 6틱 — 해시 완전 동일(무영향, 기존과 동일 절차).
2. `HARMONICITY_ECONOMY=1` — 일일 상한 초과 시 실제로 차단되는지(합성으로 대량 positive appraisal 주입해 확인).
3. `HARMONICITY_INSTITUTION=1` — CONNECTOR/SUPPORTER 조건 충족/미충족 양쪽 확인, 조건 미달 시 역할이 조용히 사라지는지(페널티 로그 없음 확인).

## 7. kee 확인 요청

- D-G2 자원명("favor")·밴드값(3/일)이 합리적인지, 아니면 §E 예산 밴드와 스케일 정합이 필요한지.
- D-C1 MEDIATOR 보류(2차 라운드) 판단 동의 여부.
- decision_record의 judgment_type=null(규칙기반) 처리가 §2 canonical과 정합인지 페블 확인.

## 8. 구현+검증 결과 (2026-07-23, kee 게이트 GO 후)

### 구현
- `village/systems/economy.py`/`village/systems/institution.py` 신설. `save_load.py`에 save/load_economy·save/load_institutions 추가(기존 persistence 컨벤션 준수).
- `decision_log.py`에 `decider_role` 파라미터 추가(기본값 "위임에이전트" 유지, institution은 "정책"으로 호출) — 기존 D-L1/D-A1 호출부 무영향.
- `conversation.py`: warmth 실개선 관측 시 `economy.grant_favor(other.id, day)` 호출. `main.py`: 매 틱 `institution.recompute_roles()` 호출(24틱 주기 내부 처리).

### 검증 결과
| 항목 | 결과 |
|---|---|
| 무영향 회귀(가드 미설정) | PASS — mock 6틱 해시 완전 동일 |
| economy 일일상한(§E-①) | PASS — 동일 캐릭터 5회 시도 중 **3회만 성공**(4·5번째 차단), 다음날 카운터 리셋 확인 |
| institution 역할배정+비처벌 복귀(§E-②) | PASS — CONNECTOR 조건 충족 시 배정, 조건 미달 시 **"강등" 아니라 조용히 role=None**(decision_record에 페널티 필드 전혀 없음, `previous`만 기록) |
| 통합(main.py, 26틱 mock, 전 옵트인 동시 활성화) | 크래시 없음. economy.json은 이번 mock런에서 미생성됐는데, mock 응답 고정텍스트에 긍정 키워드가 없어 warmth가 애초에 안 올라가는 구조적 이유(appraisal도 fallback도 둘 다 mock고정텍스트론 positive 안 됨) — 버그 아님, grant_favor 자체는 단위테스트로 별도 검증 완료 |

MEDIATOR는 스펙대로 미구현(2차 라운드 보류, kee 동의 반영).
