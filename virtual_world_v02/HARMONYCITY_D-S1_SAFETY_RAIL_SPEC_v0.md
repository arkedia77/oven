# 하모니시티 D-S1 — 안전레일 MVP 스펙 v0

> 작성: oven, 2026-07-23. 페블 트랙B `harmonycity-injection-diff-v0.md` §5 D-S1 실행 스펙.
> kee 승인 범위(2026-07-22): save_load.py 원자적쓰기 활용·개입시스템 재사용·**MVP=임계 정지+스냅샷 복원**만, 포괄 안전보장(행동기반 이상탐지 전반, D-G1 창발계측기 연동)은 별도 과제.
> 계기: 2026-07-22 ogo llama-server 14h 무인지 정지 사고 — 프로세스 존재가 아니라 "실작업 신호"를 봐야 한다는 governance 원칙(kee↔admin SOP 수렴)의 실물 구현.

## 1. 범위 (MVP만)

1. **킬스위치**: LLM 호출 오류율이 임계치를 넘으면 틱 루프를 그레이스풀 정지.
2. **스냅샷/복원**: 주기적으로 상태 스냅샷 보관, 필요 시 수동 복원.

행위기반 이상탐지(D-G1 창발카운터 연동, D-A3 판단분산 등)는 계측기 단계(주입순서 5번) 몫 — 여기선 다루지 않는다.

## 2. 구현 (`village/safety_rail.py`)

- **킬스위치**: `llm.chat()`이 성공/오류 결과를 `safety_rail.record_llm_result(is_error)`로 매 호출 보고 → 메인 틱 루프가 매 틱 `check_kill_switch()` 호출. 오류율(기본 표본≥5, 임계 50%) 초과 시 `SafetyHalt` 예외 → `main()`이 잡아서 `_save_full()` 후 정상 종료(exit 1).
  - 오류 판정 기준 = `llm.chat()`이 예외를 삼키고 반환하는 `"[오류: ...]"` 문자열 여부. **appraisal 파싱 실패(fallback)와는 무관**한 별개 신호 — D-L1의 `interpretation_status`와 혼동하지 않도록 분리.
  - 이 임계치가 발동했다면 = llama-server 사망류 인프라 장애의 조기 감지(7/22 사고를 실시간 감지했을 신호).
- **스냅샷**: `maybe_snapshot(tick)` — 기본 24틱(1일)마다 DATA_DIR의 JSON 8종 + characters/ 를 `{DATA_DIR}/../snapshots/tick_{N}/`에 복사, 최근 5개만 보관(회전).
- **복원**: `restore_snapshot(data_dir, tick_label)` — 수동 호출 전용(자동 롤백 없음, MVP는 사람 판단 후 실행).
- 전부 옵트인 — `HARMONICITY_KILL_SWITCH=1`(정지) / `HARMONICITY_SAFETY_SNAPSHOT=1`(스냅샷). 미설정 시 카운터만 누적, 파일 I/O·예외 없음.

## 3. 검증 (로컬, 라이브 무영향)

1. 가드 미설정 mock 6틱 — 해시 완전 동일(무영향 확정, run_reproducible.py --mock).
2. `HARMONICITY_SAFETY_SNAPSHOT=1` mock 26틱 — tick_24 스냅샷 생성 확인(8개 JSON + characters/ 전부).
3. `HARMONICITY_KILL_SWITCH=1` + 의도적 불통 API_URL — 오류율 100%(표본17) 감지, SafetyHalt 발동, 상태 저장 후 정상 종료 확인.
4. restore_snapshot — 스냅샷에서 별도 디렉토리로 전체 복원 확인.

전부 PASS.

## 4. 라이브 적용 시 주의

- 킬스위치 발동 시 프로세스가 exit(1)로 종료됨 — `HarmonicityHealthCheck` watchdog이 python.exe 부재를 감지해 **자동 재기동**시킬 것(현재 watchdog 설계상). 즉 킬스위치 원인(예: llama-server 사망)이 해소 안 된 채면 재기동 후 곧바로 다시 오류율 임계 도달 → 재정지, 반복될 수 있음. **원인 해소 전 무한 재시도 방지가 필요하면 후속 과제**(예: 연속 halt N회 시 watchdog 자체를 임시 DISABLE하는 로직) — MVP 범위 밖으로 명시.
- 라이브 배포는 다른 옵트인 모듈과 동일하게 안전(env 미설정 시 무해) — 다음 재기동 시점에 D-L1과 함께 배포 예정.
