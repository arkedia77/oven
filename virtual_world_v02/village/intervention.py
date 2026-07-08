"""개입 파이프 (Phase A-3) — 외부 이벤트/실험 조건을 시뮬에 주입.

출처 2종 (둘 다 미설정이면 no-op → 라이브 무영향):
  1) spec 파일:  env HARMONICITY_INTERVENTION=<spec.json>  — 배치 실험(A/B). 틱 예약형.
  2) inbox 파일: env HARMONICITY_ALLOW_INBOX=1 + DATA_DIR/interventions_inbox.json — API POST 경유.

개입 타입(전부 순수 상태 변경 — random/LLM 미호출 → 같은 seed+spec = 동일 궤적):
  - prompt_injection   : 대상 working_memory에 외부사건 주입
  - relationship_delta : 관계 4축(warmth/trust/tension/affection) 가감 + clamp
  - need_delta         : 캐릭터 욕구 가감 + clamp
  - character_add      : definitions.py에 정의된 신규 캐릭터 통합

모든 적용은 DATA_DIR/interventions_applied.jsonl에 감사 로그로 남는다(재현성/논문 정합).
"""
import os
import json
from pathlib import Path

REL_KEYS = {"warmth", "trust", "tension", "affection"}
_VALID_TYPES = {"prompt_injection", "relationship_delta", "need_delta", "character_add"}

# 관계 lazy 생성 시 초기값 — main._integrate_new_characters(main.py)와 동일하게 유지.
# 신규 실험 dir은 관계가 점진 생성되므로, 아직 없는 쌍에 델타를 걸면 이 기본값 위에 적용한다.
_REL_DEFAULT = {
    "warmth": 0.3, "trust": 0.3, "tension": 0.1, "affection": 0.0,
    "salience": 0.5, "interaction_count": 0, "last_interaction_day": 0,
    "consecutive_conflicts": 0, "fatigue_cooldown": 0,
}

_queue: list = []              # spec에서 로드된 미적용 개입 (틱 예약)
_applied_log_path = None       # DATA_DIR / "interventions_applied.jsonl"
_inbox_path = None             # DATA_DIR / "interventions_inbox.json"
_allow_inbox = False


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def validate_spec(spec: dict) -> list[str]:
    """spec(dict) 또는 개입 리스트를 검증. 오류 메시지 목록 반환(빈 리스트=정상).
    API POST(개입 1건)와 배치 spec 양쪽에서 재사용."""
    from village.characters.definitions import CHARACTERS

    errors = []
    if isinstance(spec, dict) and "interventions" in spec:
        items = spec["interventions"]
    elif isinstance(spec, list):
        items = spec
    elif isinstance(spec, dict):
        items = [spec]  # 개입 1건
    else:
        return ["spec은 dict 또는 list여야 함"]

    for i, iv in enumerate(items):
        tag = f"[{i}]"
        if not isinstance(iv, dict):
            errors.append(f"{tag} 개입은 객체여야 함")
            continue
        t = iv.get("type")
        if t not in _VALID_TYPES:
            errors.append(f"{tag} 알 수 없는 type: {t} (허용: {sorted(_VALID_TYPES)})")
            continue
        if "at_tick" in iv and not isinstance(iv["at_tick"], int):
            errors.append(f"{tag} at_tick은 정수여야 함")

        if t == "prompt_injection":
            if not iv.get("text"):
                errors.append(f"{tag} prompt_injection은 text 필요")
            tgt = iv.get("target", "all")
            if tgt != "all" and tgt not in CHARACTERS:
                errors.append(f"{tag} target 미존재 캐릭터: {tgt}")
        elif t == "relationship_delta":
            pair = iv.get("pair")
            if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
                errors.append(f"{tag} pair는 [id, id] 형식")
            else:
                for cid in pair:
                    if cid not in CHARACTERS:
                        errors.append(f"{tag} pair 미존재 캐릭터: {cid}")
            delta = iv.get("delta", {})
            if not delta:
                errors.append(f"{tag} delta 필요")
            for k in delta:
                if k not in REL_KEYS:
                    errors.append(f"{tag} 관계 delta 키 오류: {k} (허용: {sorted(REL_KEYS)})")
        elif t == "need_delta":
            cid = iv.get("character")
            if cid not in CHARACTERS:
                errors.append(f"{tag} character 미존재: {cid}")
            if not iv.get("delta"):
                errors.append(f"{tag} delta 필요")
        elif t == "character_add":
            cid = iv.get("character")
            if cid not in CHARACTERS:
                errors.append(f"{tag} character_add 대상이 definitions.py에 없음: {cid}")
    return errors


def init(data_dir: Path):
    """main()에서 1회 호출. env 게이트 검사 + spec 로드/검증.
    spec 오류는 기동 시점에 즉시 raise(틱 도중 실패 방지)."""
    global _queue, _applied_log_path, _inbox_path, _allow_inbox
    data_dir = Path(data_dir)
    _queue = []
    _applied_log_path = data_dir / "interventions_applied.jsonl"
    _inbox_path = data_dir / "interventions_inbox.json"
    _allow_inbox = os.environ.get("HARMONICITY_ALLOW_INBOX") == "1"

    spec_path = os.environ.get("HARMONICITY_INTERVENTION")
    if spec_path:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        errs = validate_spec(spec)
        if errs:
            raise ValueError(f"개입 spec 검증 실패({spec_path}):\n  " + "\n  ".join(errs))
        items = spec["interventions"] if isinstance(spec, dict) and "interventions" in spec else spec
        _queue = [dict(x) for x in items]
        print(f"  ⚡ 개입 spec 로드: {len(_queue)}건 ({Path(spec_path).name})")

    if _allow_inbox:
        print(f"  📮 inbox 개입 수신 활성화: {_inbox_path.name}")


def _log_applied(world, iv: dict, ok: bool, error: str | None):
    rec = {
        "tick": world.tick, "day": world.day,
        "intervention": iv, "ok": ok, "error": error,
    }
    with open(_applied_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def apply_one(iv: dict, world, characters, relationships,
              reputation_matrix, knowledge_base, info_registry):
    """개입 1건 적용. 예외는 호출자(apply_pending)가 잡아 감사 로그에 기록."""
    t = iv["type"]
    if t == "prompt_injection":
        text = iv["text"]
        target = iv.get("target", "all")
        targets = list(characters.values()) if target == "all" else [characters[target]]
        for ch in targets:
            ch.working_memory.append(f"[외부사건] {text}")
            if len(ch.working_memory) > 5:
                ch.working_memory = ch.working_memory[-5:]

    elif t == "relationship_delta":
        key = tuple(sorted(iv["pair"]))
        rel = relationships.get(key)
        if rel is None:  # 관계 lazy 생성: 아직 없는 쌍이면 표준 초기값으로 생성 후 델타 적용
            rel = dict(_REL_DEFAULT)
            relationships[key] = rel
        for k, dv in iv["delta"].items():
            rel[k] = _clamp(rel.get(k, 0.0) + dv)

    elif t == "need_delta":
        ch = characters[iv["character"]]
        for k, dv in iv["delta"].items():
            if k not in ch.needs:
                raise KeyError(f"욕구 키 미존재: {k} ({ch.id})")
            ch.needs[k] = _clamp(ch.needs[k] + dv)

    elif t == "character_add":
        from village.characters.definitions import CHARACTERS
        from village.characters.state import CharacterState
        from village.main import _integrate_new_characters
        cid = iv["character"]
        if cid not in characters:
            characters[cid] = CharacterState.from_definition(cid)
        _integrate_new_characters(
            list(CHARACTERS.keys()), characters, relationships,
            reputation_matrix, knowledge_base, info_registry,
        )
    else:
        raise ValueError(f"알 수 없는 type: {t}")


def _consume_inbox() -> list:
    """inbox 파일을 읽어 개입 목록 반환 + 파일을 빈 리스트로 원자적 재작성."""
    if not (_allow_inbox and _inbox_path.exists()):
        return []
    try:
        items = json.loads(_inbox_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(items, list):
        items = [items]
    # 원자적으로 비우기 (동시 POST와의 race 최소화 — 소비 즉시 클리어)
    tmp = _inbox_path.with_suffix(".json.tmp")
    tmp.write_text("[]", encoding="utf-8")
    os.replace(tmp, _inbox_path)
    return items


def apply_pending(world, characters, relationships,
                  reputation_matrix, knowledge_base, info_registry) -> int:
    """매 틱 호출. 예약(spec) + inbox 개입 중 이번 틱에 적용할 건들을 적용.
    적용 건마다 감사 로그 append. 반환: 적용 건수."""
    if _applied_log_path is None:
        return 0

    # inbox 개입을 큐에 편입 (at_tick 없으면 이번 틱 즉시)
    for iv in _consume_inbox():
        errs = validate_spec(iv)
        if errs:
            _log_applied(world, iv, False, "inbox 검증 실패: " + "; ".join(errs))
            continue
        if "at_tick" not in iv:
            iv = dict(iv, at_tick=world.tick)
        _queue.append(iv)

    applied = 0
    remaining = []
    for iv in _queue:
        if iv.get("at_tick", world.tick) <= world.tick:
            try:
                apply_one(iv, world, characters, relationships,
                          reputation_matrix, knowledge_base, info_registry)
                _log_applied(world, iv, True, None)
                applied += 1
            except Exception as e:
                _log_applied(world, iv, False, f"{type(e).__name__}: {e}")
        else:
            remaining.append(iv)
    _queue[:] = remaining
    return applied
