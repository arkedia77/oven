"""D-L1 판단포획 — 구조화 decision_record 기록. 옵트인(HARMONICITY_DECISION_LOG=1)이며 미설정 시 무영향.

decision-substrate-principles-v0.md §2 canonical 스키마 채택(+choice/outcome 확장, kee T0 게이트 PASS 2026-07-22).
sim.log(자연어)·replay.py(LLM I/O 원문)와 별도 트랙 — provenance로만 교차조회, 병합하지 않음.
스펙: HARMONYCITY_D-L1_DECISION_RECORD_SPEC_v0.md 참조.
"""
import hashlib
import json
import os
import time

_enabled = None  # 최초 호출 시 1회 캐시
_path = None


def is_enabled() -> bool:
    global _enabled
    if _enabled is None:
        _enabled = os.environ.get("HARMONICITY_DECISION_LOG") == "1"
    return _enabled


def _log_path() -> str:
    global _path
    if _path is None:
        from village import config  # lazy — DATA_DIR 런타임 결정 반영
        _path = str(config.DATA_DIR / "decision_records.jsonl")
    return _path


def _make_id(payload: dict) -> str:
    h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return f"dr_{h[:16]}"


def record(
    tick: int,
    decider_id: str,
    basis: str,
    choice,
    outcome: dict,
    judgment_type: str | None = "분석",
    decider_role: str = "위임에이전트",
    alternatives_considered=None,
    reversible: bool = True,
    cap_bound: str | None = None,
    gate_passed=None,
    interpretation_status: str | None = None,
    confidence=None,
    provenance: dict | None = None,
    sim_log_line: int | None = None,
):
    """decision_record 1건 기록. 가드 미설정 시 즉시 반환(무영향).

    decider_role: canonical §2 enum(LEO|위임에이전트|정책|게이트) — 규칙기반 결정(D-C1 등)은
    "정책"으로 호출. judgment_type=None은 규칙도출(rule derivation)이라 판단유형 다이얼
    미해당(D-C1/D-G2, 페블 canonical 확인 대기 — kee 165359).
    """
    if not is_enabled():
        return
    from village import config
    payload = {
        "tick": tick,
        "world_id": str(config.DATA_DIR),
        "judgment_type": judgment_type,
        "decider": {"role": decider_role, "id": decider_id},
        "basis": basis,
        "alternatives_considered": alternatives_considered,
        "choice": choice,
        "outcome": outcome,
        "reversible": reversible,
        "cap_bound": cap_bound,
        "gate_passed": gate_passed,
        "interpretation_status": interpretation_status,
        "confidence": confidence,
        "provenance": provenance or {},
        "status": "open",
        "links": {"sim_log_line": sim_log_line},
    }
    rec = {"id": _make_id(payload), "ts": time.time(), **payload}
    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 판단포획 기록 실패가 시뮬을 죽이면 안 됨
