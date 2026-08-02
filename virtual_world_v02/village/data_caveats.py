"""구간별 데이터 판독 캐비엇 — 기계 판독 헬퍼.

kee 지시(2026-08-02): «캐비엇을 문서가 아니라 데이터 산출물 자체에 기계적으로 붙일 것.
어느 방식이든 "사람이 문서를 읽어야 알 수 있는" 형태만 아니면 된다.»

정본: HARMONYCITY_DATA_CAVEATS.json (repo) / data/DATA_CAVEATS.json (라이브 배포본)

용법:
    from village import data_caveats
    data_caveats.warn(days=[556, 560])        # 해당 구간 캐비엇을 stderr로 출력
    for c in data_caveats.affecting(tick=9000): ...
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_CANDIDATES = [
    Path(os.environ["HARMONICITY_DATA_CAVEATS"]) if os.environ.get("HARMONICITY_DATA_CAVEATS") else None,
    _BASE / "data" / "DATA_CAVEATS.json",
    _BASE / "HARMONYCITY_DATA_CAVEATS.json",
]

_spec: dict | None = None


def load() -> dict:
    global _spec
    if _spec is None:
        for p in _CANDIDATES:
            if p and p.exists():
                _spec = json.loads(p.read_text(encoding="utf-8"))
                break
        else:
            _spec = {"segments": [], "reading_rules": []}
    return _spec


def day_from_tick(tick: int) -> int:
    return tick // 24 + 1


def affecting(tick: int | None = None, day: int | None = None,
              days: list[int] | None = None, ticks: list[int] | None = None) -> list[dict]:
    """주어진 tick/day(들)에 걸리는 캐비엇 구간을 돌려준다."""
    pts_day: list[int] = []
    if day is not None:
        pts_day.append(day)
    if days:
        pts_day.extend(days)
    if tick is not None:
        pts_day.append(day_from_tick(tick))
    if ticks:
        pts_day.extend(day_from_tick(t) for t in ticks)
    if not pts_day:
        return []
    hits = []
    for seg in load().get("segments", []):
        lo, hi = seg.get("day_from"), seg.get("day_to")
        if lo is None or hi is None:
            continue
        if any(lo <= d <= hi for d in pts_day):
            hits.append(seg)
    return hits


def reading_rule(field: str) -> dict | None:
    for r in load().get("reading_rules", []):
        if r.get("field") == field:
            return r
    return None


def format_block(segs: list[dict]) -> str:
    if not segs:
        return ""
    lines = ["", "=" * 72, "★ 데이터 판독 캐비엇 — 아래 구간이 이 집계에 포함되어 있습니다", "=" * 72]
    for s in segs:
        lines.append(f"[{s.get('severity', '?').upper()}] {s.get('label')}  "
                     f"(Day {s.get('day_from')}~{s.get('day_to')} / tick {s.get('tick_from')}~{s.get('tick_to')})")
        lines.append(f"  {s.get('caveat')}")
        ev = s.get("evidence") or {}
        for k, v in ev.items():
            lines.append(f"    - {k}: {v}")
        if s.get("cause_status"):
            lines.append(f"    - cause_status: {s['cause_status']}")
        lines.append(f"    출처: {s.get('source')}")
    lines.append("=" * 72)
    return "\n".join(lines)


def warn(tick: int | None = None, day: int | None = None,
         days: list[int] | None = None, ticks: list[int] | None = None,
         stream=None) -> list[dict]:
    """걸리는 캐비엇이 있으면 출력하고 목록을 돌려준다(없으면 조용히 빈 목록)."""
    segs = affecting(tick=tick, day=day, days=days, ticks=ticks)
    if segs:
        print(format_block(segs), file=stream or sys.stderr)
    return segs
