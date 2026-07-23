"""D-S1 안전레일 MVP — 임계치 기반 정지(킬스위치) + 상태 스냅샷/복원. 옵트인, 미설정 시 무영향.

포괄적 안전보장(행동기반 이상탐지 전반, D-G1 창발계측기 연동 등)은 별도 과제 — 이 모듈은
kee 승인 MVP 범위(임계 정지 + 스냅샷 복원)만 다룬다.

킬스위치 신호: LLM 호출 오류율 급증(예: llama-server 사망류 인프라 장애의 조기 감지 —
2026-07-22 14h 무인지 정지 사고가 계기). 오류가 아니라 "생성됨" 자체를 판단하는 지표라
appraisal 파싱 실패(fallback)와는 무관 — llm.chat() 자체가 예외를 삼키고 반환하는
"[오류: ...]" 문자열만 카운트한다.
"""
import os
import shutil
from pathlib import Path

_llm_calls_window = 0
_llm_errors_window = 0


class SafetyHalt(Exception):
    """킬스위치 발동 — 틱 루프가 이 예외를 잡아 그레이스풀하게 정지해야 함."""


def kill_switch_enabled() -> bool:
    return os.environ.get("HARMONICITY_KILL_SWITCH") == "1"


def snapshot_enabled() -> bool:
    return os.environ.get("HARMONICITY_SAFETY_SNAPSHOT") == "1"


def record_llm_result(is_error: bool):
    """llm.chat()에서 매 호출 후 기록. 가드 무관하게 카운트(경량 카운터, 파일기록 없음)."""
    global _llm_calls_window, _llm_errors_window
    _llm_calls_window += 1
    if is_error:
        _llm_errors_window += 1


def check_kill_switch(min_samples: int = 5, error_rate_threshold: float = 0.5):
    """LLM 오류율이 임계치를 넘으면 SafetyHalt. 가드 미설정 시 무영향(카운터만 계속 누적)."""
    if not kill_switch_enabled():
        return
    if _llm_calls_window < min_samples:
        return
    rate = _llm_errors_window / _llm_calls_window
    if rate >= error_rate_threshold:
        raise SafetyHalt(
            f"LLM 오류율 {rate:.0%} (임계 {error_rate_threshold:.0%}, 표본 {_llm_calls_window}건) "
            f"— 안전레일 발동, 틱 루프 정지"
        )


def reset_window():
    """윈도우 리셋 — main.py 틱 루프에서 매 틱 호출(가드 무관, 다음 판정을 위해 항상 리셋)."""
    global _llm_calls_window, _llm_errors_window
    _llm_calls_window = 0
    _llm_errors_window = 0


def maybe_snapshot(tick: int, interval: int = 24, keep: int = 5):
    """interval틱마다 DATA_DIR 상태 스냅샷(1일=24틱 기본). 가드 미설정 시 무영향."""
    if not snapshot_enabled():
        return
    if tick % interval != 0:
        return
    from village import config
    src = config.DATA_DIR
    dst = src.parent / "snapshots" / f"tick_{tick}"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("world_state.json", "relationships.json", "reputation.json",
                 "knowledge_base.json", "need_history.json", "belief_history.json",
                 "relationship_history.json", "atmosphere.json"):
        p = src / name
        if p.exists():
            shutil.copy2(p, dst / name)
    chars_src = src / "characters"
    if chars_src.exists():
        shutil.copytree(chars_src, dst / "characters", dirs_exist_ok=True)
    dst_root = dst.parent
    snaps = sorted(dst_root.glob("tick_*"), key=lambda p: p.stat().st_mtime)
    for old in snaps[:-keep]:
        shutil.rmtree(old, ignore_errors=True)


def restore_snapshot(data_dir, tick_label):
    """수동 복원 전용 — CLI에서만 호출(자동 호출 없음, 사람 판단 필요)."""
    data_dir = Path(data_dir)
    src = data_dir.parent / "snapshots" / f"tick_{tick_label}"
    if not src.exists():
        raise FileNotFoundError(f"스냅샷 없음: {src}")
    for item in src.iterdir():
        dst = data_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)
