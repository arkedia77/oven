# 하모니시티 Phase A 상세설계서 (Detailed Design v1.0)

작성: oven, 2026-07-07 / **구현 완료: 2026-07-08 (A-1~A-7 전부, mock 검증 PASS)**
상위 문서: `HARMONICITY_EXPANSION_DESIGN.md` (확대 설계 v1.0)
범위: **Phase A = E1 관측·개입 API + E2 A/B 개입 실험 프레임**

> **구현 상태 (2026-07-08):** A-1~A-7 전부 구현·mock 검증 완료. 신규
> `village/metrics.py`·`village/intervention.py`·`run_ab.py`·`api/server.py`·`specs/smoke_tension.json`,
> 수정 `save_load.py`(원자적)·`main.py`(개입 훅)·`run_reproducible.py`(metrics import)·`export_report.py`(--ab).
> 무영향 회귀 확인(spec 없을 때 mock 해시 불변 `081b56bad12840dd`). **real LLM 검증은 젬마 복귀 후**(§7 체크리스트).

---

## 0. 범위와 비목표

### 포함 (내일 구현 대상, 순서대로)
| # | 컴포넌트 | 신규/수정 | 파일 |
|---|----------|----------|------|
| A-1 | 메트릭 공용 모듈 | 신규+수정 | `village/metrics.py` (신규), `run_reproducible.py` (import 전환) |
| A-2 | 원자적 저장 | 수정 | `village/persistence/save_load.py` |
| A-3 | 개입 파이프 | 신규 | `village/intervention.py` |
| A-4 | 엔진 훅 | 수정(2곳) | `village/main.py` |
| A-5 | 관측·개입 API 서버 | 신규 | `api/server.py`, `api/worlds.json` |
| A-6 | A/B 실험 오케스트레이터 | 신규 | `run_ab.py` |
| A-7 | A/B 리포트 export | 수정 | `export_report.py` |

### 비목표 (Phase B 이후)
- E3 서사 계층, E4 SQLite, E5 테넌트 매니저, E6 도메인 팩 규격
- 웹 대시보드 UI / SSE 실시간 피드 (Phase A는 폴링 GET으로 충분)
- 인증/권한 (tailnet 내부 사용 전제)
- `config_set` 개입 타입 (§3.3.5의 함정 때문에 보류 — 사유 명시)
- 라이브(ogo) 배포 — Phase A는 **로컬 canonical에서만** 개발·검증. ogo 배포는 별도 Leo 결정

### 개발 환경 전제
- 젬마 DOWN 상태(Leo 지시 7/4)와 충돌 없음: 전 태스크 `REPRO_MOCK_LLM=1`로 개발·검증
- real LLM 검증(§6.3)은 젬마 복귀 후 별도 체크리스트로 실행
- 신규 의존성: `fastapi`, `uvicorn` (A-5에서만, `pip install fastapi uvicorn`)

---

## 1. 설계 원칙 (재현성 트랙에서 검증된 패턴 승계)

1. **옵트인 = 미설정 시 무영향.** 모든 신규 동작은 환경변수/파일 존재로 게이트. 라이브 경로의
   기본 동작 변경은 A-2(원자적 쓰기 — 순수 안전성 개선) 하나뿐.
2. **파일 = 인터페이스.** 엔진↔API 서버 간 IPC 없음. API는 data dir의 JSON을 읽고,
   개입은 inbox 파일로 전달. 엔진은 틱 경계에서만 파일을 읽는다 (기존 save 시점과 대칭).
3. **기존 함수 재사용.** `_spawn`/`_extract_metrics`/`_stats`(run_reproducible.py)와
   `_integrate_new_characters`(main.py)를 그대로 사용. 신규 로직 최소화.
4. **모든 개입은 감사 로그에 남는다.** 재현성 담보: "어느 틱에 무엇이 주입됐나"가 기록되어야
   record/replay·논문 export와 정합.

---

## 2. A-1 — `village/metrics.py` (메트릭 공용화)

**동기**: `_extract_metrics`가 run_reproducible.py에 갇혀 있어 API(A-5)와 A/B(A-6)가 재사용 불가.

```python
# village/metrics.py (신규)
def extract_metrics(data_dir: Path) -> dict
    # run_reproducible._extract_metrics(176-196행) 본문 그대로 이관.
    # 반환 키: avg_warmth, avg_trust, avg_tension, ceiling, affection_sat, active_rels, n_pairs

def stats(values: list) -> dict
    # run_reproducible._stats(199-205행) 이관. {mean, std, ci95, n}

METRIC_KEYS = ["avg_warmth", "avg_trust", "avg_tension", "ceiling", "affection_sat", "active_rels"]
```

**run_reproducible.py 수정**: `_extract_metrics`/`_stats` 본문 삭제 →
`from village.metrics import extract_metrics as _extract_metrics, stats as _stats` (호출부 무수정).
주의: metrics.py는 `village.config`를 import하지 않는다(data_dir 인자만) — API 서버가
임의 세계 dir에 쓸 수 있어야 하므로.

**검증**: `python run_reproducible.py --multiseed 2 --ticks 2 --mock` → 기존과 동일한 리포트 출력.

---

## 3. A-2 — 원자적 저장 (`save_load.py`)

**동기**: 현재 전부 `path.write_text(...)` 직접 쓰기(save_load.py:10 등 12곳). API 서버가
저장 도중 읽으면 부분 파일 → JSONDecodeError. 라이브에서도 크래시 시 파일 파손 리스크.

```python
def _atomic_write(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)   # POSIX/Windows 모두 원자적
```

- save_load.py 내 모든 `path.write_text(json.dumps(...))` 호출을 `_atomic_write(path, json.dumps(...))`로 치환 (12곳).
- **동작 변경 없음** (같은 내용, 같은 경로) — 재현성 해시 비교(`_hash_dir`)에 영향 없음.
- API 서버 쪽에도 방어적 재시도(§5)를 두어 이중 안전.

**검증**: ① mock 4틱 정상 저장 ② mock 시뮬 + 병렬 무한 read 루프(0.01s 간격) 동시 실행 →
JSONDecodeError 0건 ③ `run_reproducible.py --mock` PASS 유지(해시 불변 확인).

---

## 4. A-3/A-4 — 개입 파이프 (`village/intervention.py` + main.py 훅)

E1(외부 개입)과 E2(실험 조건 주입)가 **같은 모듈**을 쓴다. 개입 출처 2종:

| 출처 | 게이트 | 용도 |
|------|--------|------|
| **spec 파일** | env `HARMONICITY_INTERVENTION=<spec.json 경로>` | 배치 실험(A/B). 틱 예약형 |
| **inbox 파일** | env `HARMONICITY_ALLOW_INBOX=1` **and** `DATA_DIR/interventions_inbox.json` 존재 | API POST 경유 라이브/관전형 주입 |

둘 다 미설정이면 훅은 no-op — 라이브 무영향 원칙 충족.

### 4.1 개입 spec 스키마 (`specs/*.json`)

```json
{
  "version": 1,
  "name": "tension_shock_test",
  "interventions": [
    {"id": "i1", "at_tick": 12, "type": "prompt_injection",
     "target": "all",                      // "all" 또는 char_id
     "text": "마을 광장에 'AI 주민 투표권' 공지가 붙었다."},
    {"id": "i2", "at_tick": 24, "type": "relationship_delta",
     "pair": ["min_ah", "tae_sik"],
     "delta": {"tension": 0.2, "trust": -0.1}},
    {"id": "i3", "at_tick": 24, "type": "need_delta",
     "character": "ha_yeon", "delta": {"belonging": -0.3}},
    {"id": "i4", "at_tick": 48, "type": "character_add", "character": "ji_woo"}
  ]
}
```

- `at_tick`: `world.advance_tick()` 직후의 `world.tick` 절대값과 비교. 신규 실험 dir은 tick 0부터
  시작하므로 실험에서는 사실상 상대 틱. (재개된 세계에 spec을 걸 때는 절대 틱임을 문서화)
- 검증 규칙: type enum 검사, char_id는 `CHARACTERS`에 존재해야 함, delta 키는
  relationship: {warmth,trust,tension,affection} / need: 캐릭터 needs 키. 값 적용 후 `0.0~1.0` clamp.

### 4.2 개입 타입별 적용 로직 (`apply_one`)

| type | 구현 | 근거 코드 |
|------|------|----------|
| `prompt_injection` | 대상 캐릭터 `working_memory.append(f"[외부사건] {text}")`, 5개 초과 시 뒤 5개 유지 | `_end_of_day`의 event injection 패턴(main.py:408-420)과 동일 |
| `relationship_delta` | `key = tuple(sorted(pair))`; 관계 없으면 표준 초기값(`_REL_DEFAULT`)으로 **lazy 생성** 후 `clamp(v + delta)` — **메모리 내 키는 튜플**(save_load.py 직렬화 시 `"a\|b"`) | main.py:167-174 초기 관계 dict |
| `need_delta` | `characters[cid].needs[k] = clamp(...)` | CharacterState.needs |
| `character_add` | `_integrate_new_characters([cid], ...)` 호출 | main.py:140-209 |

**🔴 구현일(7/8) 발견 — 설계 대비 2건 조정:**
1. **관계 lazy 생성**: 신규 실험 dir은 관계쌍이 대화로 점진 생성되므로 초기엔 비어 있다(라이브는
   280일+라 55쌍 존재). `relationship_delta`가 미존재 쌍을 대상으로 하면 KeyError → **없으면
   `_REL_DEFAULT`(warmth/trust 0.3, tension 0.1 …)로 생성 후 델타 적용**으로 변경. "두 사람 사이에
   긴장을 심는다"는 개입 의미에도 부합. ⚠️ 부작용: treat가 ctrl에 없는 쌍을 생성하면 avg 메트릭의
   분모(n_pairs)가 조건 간 달라짐 — 실측에서 확인됨(smoke treat n_pairs=15 vs ctrl~12). 효과는
   여전히 정직하게 검출되나, 리포트 해석 시 유의. 분모 영향을 피하려면 이미 존재가 보장된 쌍
   또는 prompt_injection 사용 권장.
2. **`character_add` 한계**: definitions.py의 전 캐릭터가 기동 시 로드되므로, 이미 로스터에 있는
   캐릭터(ji_woo 포함)를 add하면 `_integrate_new_characters`가 "신규 아님"으로 판단해 **no-op**.
   이 경로는 "definitions에 뒤늦게 추가된 캐릭터를 이미 돌던 세계에 통합"하는 역사적 용도(ji_woo)엔
   정상이나, 신규 실험 dir에선 의미 없음. 실험에서 "외부인 투입"을 원하면 Phase B에서 로스터
   서브셋 기동(부분 로드) 지원 필요 — 현재는 문서화만.

**결정성 주의**: `apply_one`은 random/LLM을 호출하지 않는다 (전 타입 순수 상태 변경) —
같은 seed + 같은 spec = 동일 궤적 보장. 이것이 A/B 프레임의 재현성 근거.

### 4.3 모듈 구조

```python
# village/intervention.py (신규)
_queue: list = []          # 로드된 spec 개입 (틱 예약)
_applied_log_path = None   # DATA_DIR / "interventions_applied.jsonl"

def init(data_dir: Path):
    """main()에서 1회 호출. env 게이트 검사 + spec 로드 + 검증.
    spec 오류는 기동 시점에 즉시 raise (틱 도중 실패 방지)."""

def validate_spec(spec: dict) -> list[str]:  # 오류 목록 반환 (API에서도 재사용)

def apply_pending(world, characters, relationships,
                  reputation_matrix, knowledge_base, info_registry) -> int:
    """매 틱 호출. ① _queue에서 at_tick <= world.tick 인 미적용 건 적용
    ② ALLOW_INBOX면 inbox 파일 소비(읽기→큐 편입→파일을 빈 리스트로 원자적 재작성.
       inbox 건은 at_tick 없으면 현재 틱 즉시 적용)
    ③ 적용 건마다 interventions_applied.jsonl에 append:
       {"tick","day","intervention",<원본>,"ok":bool,"error":str|None}
    반환: 적용 건수."""
```

### 4.4 main.py 훅 (수정 2곳 — 침습 최소)

```python
# main() 내 initialize_or_resume() 다음 (main.py:480 부근):
from village import intervention
intervention.init(config.DATA_DIR)

# 루프 내 world.advance_tick() 직후, run_tick() 직전 (main.py:489-490 사이):
n = intervention.apply_pending(world, characters, relationships,
                               reputation_matrix, knowledge_base, info_registry)
if n:
    print(f"  ⚡ 개입 {n}건 적용 (tick {world.tick})")
```

훅 위치를 run_tick **앞**에 두는 이유: 개입 결과가 같은 틱의 encounter 선택·대화에 즉시 반영 —
"tick T에 개입"의 의미가 명확해짐 (감사 로그·논문 기술과 일치).

### 4.5 🔴 `config_set` 보류 사유 (구현 시 함정 — 반드시 숙지)

main.py는 config를 **값으로 import**한다 (main.py:7-10 `from village.config import TICK_SECONDS, ...`).
따라서 `setattr(village.config, "SOLO_MONOLOGUES_PER_TICK", 2)`는 main.py 네임스페이스에 이미
바인딩된 값에 **전파되지 않는다**. llm.py만 모듈 참조(`from village import config`) 패턴이라 런타임
변경이 먹힌다(재현성 ①에서 의도적으로 전환한 것). config_set을 지원하려면 encounter/conversation/
main의 소비부를 모듈 참조로 전환해야 함 → 엔진 침습이라 **Phase A 제외, Phase B 후보**.
"조정값 학습" 실험은 당분간 프로세스 재기동 단위(스윕)로 수행 — run_experiments.py의 config
override 방식이 이미 존재.

**검증(A-3/A-4)**: §6.1 시나리오 V3.

---

## 5. A-5 — 관측·개입 API 서버 (`api/server.py`)

FastAPI 단일 파일. 실행: `python -m uvicorn api.server:app --port 8090` 또는
`python api/server.py --port 8090` (uvicorn.run 내장).

### 5.1 세계 레지스트리 (`api/worlds.json`)

```json
{"live": "data", "repro_s1": "repro_runs/multiseed_s1"}
```
- 상대경로는 `virtual_world_v02/` 기준. 서버 기동 시 로드, `GET /worlds`로 노출.
- 존재하지 않는 dir은 목록에서 `"missing": true`로 표기 (실험 dir은 생성/삭제가 잦음).

### 5.2 읽기 유틸 (부분 쓰기 방어)

```python
def read_json(path, retries=3, delay=0.05):
    # JSONDecodeError/FileNotFoundError 시 delay 후 재시도, 소진하면 503
```
A-2 원자적 쓰기로 대부분 불필요해지지만 이중 방어로 유지 (ogo 등 미패치 세계 대비).

### 5.3 엔드포인트 명세

| 메서드/경로 | 반환 | 소스 파일 |
|-------------|------|----------|
| `GET /worlds` | 레지스트리 + 각 세계 `{day, tick}` 요약 | world_state.json |
| `GET /worlds/{w}/state` | world_state 원문 | world_state.json |
| `GET /worlds/{w}/relationships` | `{"a\|b": {warmth,trust,tension,affection,salience,interaction_count,...}}` 원문 | relationships.json |
| `GET /worlds/{w}/relationships/history` | 4축 시계열 (일 단위, 최근 60일) | relationship_history.json |
| `GET /worlds/{w}/characters` | `[{id, name, role, location, emotional_state}]` 요약 리스트 | characters/*.json |
| `GET /worlds/{w}/characters/{cid}` | 캐릭터 상태 원문 (needs/beliefs/goals/working_memory 포함) | characters/{cid}.json |
| `GET /worlds/{w}/reputation` | 관찰자별 평판 행렬 원문 | reputation.json |
| `GET /worlds/{w}/metrics` | `village.metrics.extract_metrics` 결과 (A-1 재사용) | relationships.json |
| `GET /worlds/{w}/needs/history` | 욕구 시계열 | need_history.json |
| `GET /worlds/{w}/conversations?day=N&limit=20` | 대화 파일 목록+내용 (day 미지정 시 최신 day) | conversations/day{N:03d}/*.json |
| `GET /worlds/{w}/atmosphere` | 장소 분위기 | atmosphere.json |
| `GET /worlds/{w}/interventions/applied?limit=50` | 감사 로그 tail | interventions_applied.jsonl |
| `POST /worlds/{w}/interventions` | §5.4 | interventions_inbox.json |

에러 규약: 미등록 world=404, 파일 부재=404(`{"detail": "not saved yet"}`), 읽기 실패=503.

### 5.4 개입 POST 흐름

```
POST /worlds/{w}/interventions   body = 개입 객체 1건 (스키마 §4.1과 동일, at_tick 생략 가능)
 → intervention.validate_spec으로 검증 (400 + 오류 목록)
 → DATA_DIR/interventions_inbox.json 에 append (원자적 재작성)
 → 202 {"queued": true, "note": "엔진이 HARMONICITY_ALLOW_INBOX=1로 떠 있어야 다음 틱에 적용됨"}
```
적용 확인은 `GET .../interventions/applied` 폴링으로. (동기 적용 아님 — 엔진과 무IPC 원칙)

### 5.5 conversations 디렉토리 규약 확인 사항
구현 시 실제 파일명 패턴(`conversations/day{NNN}/{a}_{b}_{timestamp}.json`) 을 ls로 확인 후
글롭 패턴 확정할 것 (탐색 보고 기준이며 코드 재확인 필요 — 구현일 첫 확인 항목).

---

## 6. A-6/A-7 — A/B 개입 실험 프레임 (`run_ab.py` + export)

### 6.1 설계: 시드 짝지은(paired) 2조건 비교

```
for seed in seeds:
    ctrl  = ab_runs/{name}/s{seed}_ctrl   ← _spawn(seed, ticks, dir)                      # 개입 없음
    treat = ab_runs/{name}/s{seed}_treat  ← _spawn(seed, ticks, dir, {"HARMONICITY_INTERVENTION": spec})
# 같은 seed의 ctrl/treat은 첫 개입 틱까지 동일 궤적 (§4.2 결정성) → paired design 성립
diff[metric][seed] = treat_metrics[metric] - ctrl_metrics[metric]
summary[metric] = stats(diff)   # 짝지은 차이의 mean±std+95%CI = 개입 효과 추정치
```

paired 설계가 핵심: 시드 간 분산(N=30 실측에서 std 0.009~0.011)이 차이 계산에서 상쇄되어
같은 N으로 훨씬 좁은 CI → 적은 GPU로 유의한 효과 검출.

### 6.2 `run_ab.py` 구조

```python
# run_reproducible에서 재사용: _spawn, REPRO_ROOT 패턴
# village.metrics에서: extract_metrics, stats, METRIC_KEYS

def orchestrate_ab(spec_path, seeds, ticks, mock=False, record=True) -> dict:
    # 1) spec 로드 + intervention.validate_spec — 실패 시 즉시 종료
    # 2) 시드별 ctrl/treat 순차 실행 (mock이면 REPRO_MOCK_LLM=1,
    #    record면 조건별 REPRO_RECORD=ab_runs/{name}/s{seed}_{cond}_llm.jsonl)
    # 3) 시드별/조건별 metrics + paired diff
    # 4) 리포트 ab_runs/{name}/ab_report.json:
    #    {spec: {...원본+sha256}, seeds, ticks, mode,
    #     per_seed: {seed: {ctrl: {...}, treat: {...}, diff: {...}}},
    #     summary: {ctrl: {metric: stats}, treat: {...}, effect: {metric: stats(diffs)}}}

# CLI:
#   python run_ab.py --spec specs/tension_shock.json --seeds 5 --ticks 24 [--mock] [--no-record]
#   실패 시드는 multiseed와 동일하게 "제외+경고" 정책
```

실행 형태는 순차(기존 multiseed와 동일). 동시 실행 최적화(동시성 실측 N≤12 활용)는
ogo에서 real 실행할 때 concurrency/run_concurrency.py 패턴 이식 — Phase A 범위 밖(문서화만).

### 6.3 A-7 export (`export_report.py` 확장)

- `python export_report.py --ab ab_runs/{name}/ab_report.json` 분기 추가
- 산출: `ab_summary.md` (표 3개: ctrl 요약 / treat 요약 / **effect** mean±std+95%CI+시드별 diff raw)
  + `ab_summary.csv` + `REPRODUCE.md` (spec 전문 + sha256 + 시드/틱/모델/record 로그 경로 매니페스트)
- effect 표에 각 메트릭의 CI가 0을 포함하는지 표기 (`sig` 컬럼: CI가 0 제외 시 ★) —
  검정이 아닌 CI 기반 표기(과대해석 방지, 기존 정직성 원칙)

---

## 7. 구현 순서 (2026-07-08) — 태스크 체크리스트

의존성 순. 각 태스크는 "검증 통과" 후 다음으로.

1. **[A-1] metrics.py 이관** → 검증: `--multiseed 2 --ticks 2 --mock` 기존 동일 출력
2. **[A-2] 원자적 쓰기** → 검증: mock 4틱 + 병렬 리더 + `--mock` 해시 PASS 유지
3. **[A-3] intervention.py** (spec 로드/검증/apply_one/감사로그) — 이 시점엔 훅 없이 단위 검증:
   mock 세계 저장물 로드 후 apply_one 4타입 각각 → 상태 변화 assert
4. **[A-4] main.py 훅 2곳** → 검증 V3: spec(tick 2에 relationship_delta) + mock 4틱 →
   ① applied.jsonl 1건 ② relationships.json 반영 ③ **spec 없는 런은 산출물 해시가 훅 추가 전과 동일**
   (무영향 회귀 — `--mock` orchestrate PASS)
5. **[A-6] run_ab.py** → 검증: `--spec specs/smoke.json --seeds 3 --ticks 8 --mock` —
   tension 주입 spec에서 effect.avg_tension > 0 검출, ctrl/treat 첫 개입 틱 전 상태 동일 확인
6. **[A-7] export --ab** → 검증: 5번 리포트로 md/csv/REPRODUCE 생성, 표 수치 대조
7. **[A-5] api/server.py** → 검증: repro_runs 세계 등록 후 전 엔드포인트 curl 200 +
   POST 개입 → inbox 생성 → `HARMONICITY_ALLOW_INBOX=1` mock 런에서 적용 확인
8. **갈무리**: KANBAN + project_harmonicity.md 갱신, oven 커밋

예상 규모: 신규 ~600줄 + 수정 ~60줄. 전부 mock 기반이라 GPU 불요.

### 젬마 복귀 후 real 검증 체크리스트 (별도 세션)
- [ ] run_ab real: `--spec tension_shock --seeds 5 --ticks 24` (record) — 효과 리포트 실증
- [ ] record 로그로 treat 1개 replay → 비트단위 재현 확인 (개입+replay 정합)
- [ ] API를 라이브 세계(read-only)에 붙여 관측 스모크 — **inbox 게이트는 라이브에서 미설정 유지**
- [ ] (Leo/venture 판단 시) 효과 리포트 venture-studio 공유 — "개입 효과 실측" 신규 GTM 자산

---

## 8. 리스크와 주의사항

1. **conversations 파일명 패턴 미확정** (§5.5) — 구현일 최우선 확인.
2. **inbox와 라이브**: `HARMONICITY_ALLOW_INBOX`를 라이브 기동 스크립트에 절대 넣지 않는다.
   ogo 배포 자체가 Phase A 범위 밖이므로 현실 리스크 낮음. 배포하게 될 경우 llm.py↔replay.py
   동반배포 교훈(ImportError 사고 예방)처럼 **intervention.py는 main.py와 반드시 동반배포**.
3. **API 서버는 쓰기 금지** (inbox append 제외) — 세계 상태의 단일 작성자는 엔진 프로세스
   하나라는 기존 격리 원칙(dir-scoped lock) 유지. API는 락을 잡지 않는다.
4. **`at_tick` 절대값 의미** — 재개된 세계에 spec을 걸 때 tick이 이미 수천일 수 있음.
   실험은 항상 새 dir에서 tick 0부터 (run_ab가 보장).
5. **paired 설계의 한계 정직 표기**: 첫 개입 틱 이후 궤적 분기는 LLM 배치 비결정성(⑤)의 영향을
   ctrl/treat이 다르게 받을 수 있음(real 모드). record 로그 보관으로 사후 감사 가능 — 리포트에
   mode(mock/real)와 함께 명시. mock에서는 완전 결정적이므로 프레임 자체 검증은 mock으로 완결.

---

## 9. Phase B 이후 개략 (참고 — 이번 구현 범위 아님)

- **config_set 개입** — 소비부 모듈참조 전환 후 (§4.5)
- **SSE/대시보드** — dashboard.py를 API 소비자로 이관
- **E6 도메인 팩 manifest** — spec/팩/세계를 하나의 실험 정의로 묶는 상위 포맷
- **동시 실행 run_ab** — concurrency 인프라 이식으로 N시드×2조건 병렬 (5090 1대 = 12세계 실측)
- **E3 L2.5 요약 기억** — 상위 문서 참조
