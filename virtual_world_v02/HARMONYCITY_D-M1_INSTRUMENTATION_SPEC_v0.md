# 하모니시티 D-M1 — 계측기 슬롯 MVP 스펙 v0

> 작성: oven, 2026-07-24. kee 게이트: Q1(주입순서 설계)에서 "중앙 설계 없음 — oven 자율판단"으로 회신(2026-07-24 172730) → 오븐 자체 판단으로 착수. 비가역/형식이탈 없는 순수 읽기전용 집계라 사전 게이트 불요 판단(완료 후 진행보고).

## 0. 배경 — 왜 이 항목인가

fableself 원 주입순서(kee 라우팅, 2026-07-22): `D-L1 판단포획 → D-S1 안전레일 → D-A1 자율경계확장 → D-C1/D-G2 제도·경제 → 5)계측기(창발·폴백·판단분산·기억영속)`. 07-23 갈무리 시점 계측기 슬롯만 남고 전부 종료 — "정지점"으로 명시된 게 바로 이 항목이다. 07-24 역할 리셋(중앙PM 폐기) 이후 kee가 "다음 페이즈는 네 판단"이라 회신했지만, 원 설계 순서상 계측기가 유일하게 남은 예정 항목이라 **새 확장(자율지점 추가) 대신 계측기를 우선 선택**함 — 원 계획 이행이 임의 확장보다 스코프가 명확하고, D-C1/D-G2가 이미 "규칙기반=LLM호출 0건" 패턴으로 완주율 리스크를 피했듯, 계측기도 **순수 읽기전용 집계**라면 같은 원칙으로 가장 안전하게 확장 가능.

## 1. 핵심 설계 결정 — 런타임 훅 아님, 오프라인 집계기

D-L1/S1/A1/C1/G2는 전부 `main.py`/`conversation.py`/`encounter.py` 등 시뮬 루프 안에 옵트인 훅을 심는 방식이었다. D-M1은 다르다 — **이미 쌓인 옵트인 로그를 읽기만 하는 오프라인 분석기**로 설계한다.

**Why:** 4개 하위 계측(창발·폴백·판단분산·기억영속) 전부 기존 옵트인 산출물(`decision_records.jsonl`/`profile_*.jsonl`/`relationships.json`/`institutions.json`/`memories/*/`)만으로 계산 가능 — 시뮬 루프에 새 코드를 넣을 이유가 없다. 런타임 훅을 안 심으면: ①라이브 무영향이 설계상 자명(옵트인 가드조차 불필요) ②D-A2가 발견한 "완주율 리스크"(LLM 호출 추가→형식이탈)가 원천 배제 ③`analyze_p11.py`와 같은 계열의 독립 분석 스크립트라 배포 리스크도 없음(다음 자연 재기동을 기다릴 필요조차 없이 로컬에서 바로 실행·검증 가능).

## 2. 구현 (`village/instrumentation.py` + `run_instrumentation.py`)

### 2.1 폴백 계측 (기존 D-A1/D-L1 신호의 재사용·formalize)

- 입력: `decision_records.jsonl`의 `interpretation_status` 필드.
- `fallback_rate(data_dir, window=None) -> dict`: 전체 및 `decider_id`별 parsed/fallback/None 카운트+비율. D-A1이 1회성 스크립트로 계산했던 46%를 재사용 가능한 함수로 승격.
- 창(window) 인자로 최근 N건만 볼 수 있게(추세 관찰용) — 한 세션 스냅샷이 아니라 지속 관측 가능하게.

### 2.2 판단분산 계측 (D-A3 방법론의 재사용·formalize)

- 입력: `decision_records.jsonl`의 `decider_id`/`basis`/`choice`.
- `judgment_entropy(data_dir, group_by="decider_id") -> dict`: 그룹별 `choice` 분포의 Shannon entropy. D-A3가 수작업으로 계산했던 것과 동일 정의, 그룹 키를 인자화해 재사용.
- 참고: D-A3 소견대로 "입력이 결정을 완전히 결정짓지 않을 때"만 분산이 드러난다 — 낮은 entropy 자체는 이상신호가 아니라 목표가 구체적이라는 신호일 수 있음(해석 시 이 소견 인용 필수, 스펙 §5에 재기재).

### 2.3 창발 계측 (신규)

정의: "명시적으로 프로그램되지 않은 구조가 관계/제도 데이터에서 관찰되는가."

- 입력: `institutions.json`(역할 배정: CONNECTOR/SUPPORTER/None), `relationships.json`.
- `role_emergence(data_dir) -> dict`: 역할 분포(CONNECTOR/SUPPORTER/None 캐릭터 수)+비균등도(entropy 또는 최다역할 캐릭터 집중도). "역할이 규칙으로 도출되긴 하지만 어떤 캐릭터가 어떤 역할을 얻는지는 관계 형성 결과다" — 이게 창발 신호.
- `interaction_concentration(data_dir) -> dict`: 캐릭터별 활성 관계쌍 수(`interaction_count>0`)의 Gini 계수 — 특정 캐릭터가 "허브"로 자연 발생했는지(균등분포면 창발 없음, 쏠리면 구조 형성).
- 스냅샷 1회로는 "창발"을 주장할 수 없음 — 시계열 비교(재기동 전후 또는 일자별 institutions.json 스냅샷)가 필요. MVP는 **단일 시점 구조 측정 함수만 제공**, 시계열 비교는 스코프 밖(§6 향후 과제).

### 2.4 기억영속 계측 (신규)

- 입력: `memories/{char_id}/core.json`(relationship_summaries/key_events/belief_shifts), `memories/{char_id}/episodes.jsonl`(50개 롤링).
- `memory_persistence(data_dir) -> dict`: 캐릭터별 ① `relationship_summaries` 커버리지(요약 있는 관계쌍 수 / 활성 관계쌍 수) ② `key_events` 적재 수(상한 20) ③ `episodes.jsonl` 라인 수(상한 50, 롤링 트림 여부) ④ `belief_shifts` 존재 여부.
- 낮은 커버리지 자체가 버그는 아님(요약은 conversation.py 특정 분기에서만 갱신되는 것으로 추정 — MVP는 측정만, 갱신 로직 원인 조사는 스코프 밖).

## 3. 산출물

`run_instrumentation.py --data-dir DIR [--json|--md]`: 위 4항목을 한 번에 계산해 리포트 출력. `export_report.py`(D-재현성 트랙)와 동일하게 md 요약 + json raw 두 포맷 지원.

## 4. 검증 계획

- 로컬 canonical에서 mock 6틱 스모크 → 산출물 없거나 0건이어도 크래시 없이 빈 리포트 반환(로그 부재 방어).
- 격리 world(`HARMONICITY_DATA_DIR` 분리) + 기존 D-L1/A1/C1 옵트인 로그가 쌓인 상태에서 4항목 전부 0 아닌 값 산출 확인.
- **라이브 데이터 대상 read-only 실행 1회**(라이브 `data/` 디렉토리를 인자로, 쓰기 없음) — 현재 축적된 decision_records/institutions 스냅샷으로 실측 리포트 산출.

## 5. 해석 시 주의(D-A3 교훈 인용)

판단분산 낮음 ≠ 자율성 부재. 창발 신호는 단일 스냅샷만으로 "발생했다"고 단정 불가(시계열 필요, §6). 폴백율은 D-A2가 이미 "모델한계 아닌 토큰예산 문제"로 원인규명한 이력이 있으므로, 새로운 폴백율 상승 관측 시 먼저 max_tokens 설정부터 재확인.

## 6. 스코프 밖 (향후 과제)

- 창발의 시계열 추적(일자별 스냅샷 비교, 역할 churn rate)
- 기억영속의 "왜 커버리지가 낮은가" 원인 조사(Phase B E3 장기서사 설계와 연결 가능)
- API 서버(api/server.py) 라우트로 노출(현재는 CLI 산출물만)

## 7. 라이브 적용

읽기전용 오프라인 분석기라 "배포"라는 개념 자체가 약함 — 로컬 canonical에 두고 언제든 라이브 `data/`를 인자로 실행 가능. ogo에 별도 배포할지는 실행 편의성 문제일 뿐 리스크 문제가 아님(코드가 시뮬 프로세스에 로드되지 않음).
