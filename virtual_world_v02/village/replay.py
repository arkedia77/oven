"""LLM record/replay — 배치 비결정성(⑤)을 우회한 완전 재현의 핵심.

문제: llama.cpp 단일요청은 seed로 결정적이나, 라이브 동시부하 시 배치 처리 부동소수점
비결정성으로 다중호출 시퀀스 재현이 깨짐(세션71 run_reproducible real 모드 FAIL로 실증).

해법: random은 seed로 재현 + LLM은 '출력을 기록(record) 후 재생(replay)'.
  - record: 실제 LLM 호출 결과 (messages, output, seed)를 jsonl에 순서대로 적재
  - replay: 기록을 순서대로 반환(서버 미사용) → 배치 비결정성 무관하게 동일 출력 보장

매칭: 순서 우선(random seed로 호출 순서 결정적) + messages 해시로 드리프트 감지 + 해시 폴백.
환경변수 가드(REPRO_RECORD/REPRO_REPLAY) — 라이브는 미설정이라 무영향.
"""
import hashlib
import json
import os
from pathlib import Path

_mode = None            # 'record' | 'replay' | None
_record_fh = None
_record_idx = 0
_replay_records = []     # [{idx, msg_hash, seed, output}, ...]
_replay_idx = 0
_replay_by_hash = {}     # msg_hash -> [output, ...] (순서 어긋날 때 폴백)
_stats = {"hits": 0, "hash_fallback": 0, "misses": 0}


def _msg_hash(messages: list) -> str:
    payload = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def init_record(path: str):
    global _mode, _record_fh, _record_idx
    _mode = "record"
    _record_idx = 0
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    _record_fh = open(p, "w", encoding="utf-8")


def init_replay(path: str):
    global _mode, _replay_records, _replay_idx, _replay_by_hash, _stats
    _mode = "replay"
    _replay_records = []
    _replay_by_hash = {}
    _replay_idx = 0
    _stats = {"hits": 0, "hash_fallback": 0, "misses": 0}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            _replay_records.append(rec)
            _replay_by_hash.setdefault(rec["msg_hash"], []).append(rec["output"])


def is_recording() -> bool:
    return _mode == "record"


def is_replaying() -> bool:
    return _mode == "replay"


def record_call(messages: list, output: str, seed) -> None:
    global _record_idx
    rec = {
        "idx": _record_idx,
        "msg_hash": _msg_hash(messages),
        "seed": seed,
        "output": output,
    }
    _record_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    _record_fh.flush()
    _record_idx += 1


def replay_call(messages: list) -> str:
    """기록된 출력 반환. 순서 우선 → 해시 폴백 → 미스 표시."""
    global _replay_idx
    h = _msg_hash(messages)
    # 1) 순서 매칭 (정상 경로)
    if _replay_idx < len(_replay_records) and _replay_records[_replay_idx]["msg_hash"] == h:
        out = _replay_records[_replay_idx]["output"]
        _replay_idx += 1
        _stats["hits"] += 1
        return out
    # 2) 해시 폴백 (순서 어긋남 — 같은 입력의 기록 출력 재사용)
    pool = _replay_by_hash.get(h)
    if pool:
        _stats["hash_fallback"] += 1
        return pool[0]
    # 3) 미스 — 로그에 없는 입력(로직 드리프트). 결정적 표식 반환(재현성 유지)
    _stats["misses"] += 1
    return f"[replay-miss:{h}]"


def close():
    global _record_fh
    if _record_fh:
        _record_fh.close()
        _record_fh = None


def stats() -> dict:
    return dict(_stats)
