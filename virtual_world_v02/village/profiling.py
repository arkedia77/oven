"""경량 프로파일링 — 동시성 실측용. 옵트인(HARMONICITY_PROFILE=1)이며 미설정 시 무영향.

동시 N세계 가동 시 세계별 LLM latency·틱 wall-clock·throughput을 측정하기 위함.
각 세계(프로세스)는 자기 DATA_DIR에 profile_{pid}.jsonl을 적재 → 오케스트레이터가 집계.
replay.py와 동일한 env 가드 + lazy 패턴이라 라이브 경로 무영향.
"""
import json
import os
import time

_enabled = None          # 최초 호출 시 1회 캐시
_path = None
_llm_calls = 0           # 마지막 tick_snapshot 이후 LLM 호출 수
_llm_time = 0.0          # 마지막 tick_snapshot 이후 LLM 누적 latency(초)


def is_profiling() -> bool:
    global _enabled
    if _enabled is None:
        _enabled = os.environ.get("HARMONICITY_PROFILE") == "1"
    return _enabled


def _profile_path() -> str:
    global _path
    if _path is None:
        from village import config  # lazy — DATA_DIR 런타임 결정 반영
        _path = str(config.DATA_DIR / f"profile_{os.getpid()}.jsonl")
    return _path


def _append(rec: dict):
    try:
        with open(_profile_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 프로파일 기록 실패가 시뮬을 죽이면 안 됨


def record_llm(latency_s: float, prompt_tokens=None, gen_tokens=None, timings=None):
    """LLM 호출 1건 기록. llm.chat()에서 호출. 항상 카운터는 누적(틱 집계용)."""
    global _llm_calls, _llm_time
    _llm_calls += 1
    _llm_time += latency_s
    if not is_profiling():
        return
    _append({
        "t": "llm",
        "ts": time.time(),
        "latency_s": round(latency_s, 4),
        "prompt_tokens": prompt_tokens,
        "gen_tokens": gen_tokens,
        "timings": timings,
    })


def record_tick(tick: int, day: int, wall_s: float):
    """틱 1회 wall-clock + 그 틱에서 소비한 LLM 호출수/대기시간 기록. main 틱 루프에서 호출."""
    global _llm_calls, _llm_time
    n_calls, llm_time = _llm_calls, _llm_time
    _llm_calls, _llm_time = 0, 0.0  # 스냅샷 리셋
    if not is_profiling():
        return
    _append({
        "t": "tick",
        "ts": time.time(),
        "tick": tick,
        "day": day,
        "wall_s": round(wall_s, 4),
        "llm_calls": n_calls,
        "llm_wait_s": round(llm_time, 4),
        "engine_s": round(max(0.0, wall_s - llm_time), 4),
    })
