"""메트릭 추출/집계 공용 모듈 (Phase A-1).

run_reproducible.py의 _extract_metrics/_stats를 이관해 API 서버(api/server.py)와
A/B 실험(run_ab.py)이 재사용한다. 의도적으로 village.config를 import하지 않는다 —
임의 세계 data dir을 인자로 받아 동작해야 하므로(멀티월드 관측).
"""
import math
import statistics
from pathlib import Path
import json

METRIC_KEYS = [
    "avg_warmth", "avg_trust", "avg_tension",
    "ceiling", "affection_sat", "active_rels",
]


def extract_metrics(data_dir: Path) -> dict:
    """산출물 relationships.json에서 다회통계용 메트릭 추출.

    relationships.json이 없으면 빈 결과(모든 값 0, n_pairs 0)를 반환한다.
    """
    data_dir = Path(data_dir)
    rel_path = data_dir / "relationships.json"
    if not rel_path.exists():
        return {k: 0 for k in METRIC_KEYS} | {"n_pairs": 0}

    rel = json.loads(rel_path.read_text(encoding="utf-8"))
    pairs = list(rel.values()) if isinstance(rel, dict) else rel
    n = len(pairs) or 1

    def g(p, k):
        return p.get(k, 0) if isinstance(p, dict) else 0

    warmths = [g(p, "warmth") for p in pairs]
    trusts = [g(p, "trust") for p in pairs]
    tensions = [g(p, "tension") for p in pairs]
    return {
        "avg_warmth": round(sum(warmths) / n, 4),
        "avg_trust": round(sum(trusts) / n, 4),
        "avg_tension": round(sum(tensions) / n, 4),
        "ceiling": sum(1 for p in pairs if g(p, "warmth") >= 1.0 and g(p, "trust") >= 1.0),
        "affection_sat": sum(1 for p in pairs if g(p, "affection") >= 0.95),
        "active_rels": sum(1 for p in pairs if g(p, "interaction_count") > 0),
        "n_pairs": len(pairs),
    }


def stats(values: list) -> dict:
    """mean±std + 95% CI (정규근사). N<2면 CI=0(표기상 단일관측)."""
    n = len(values)
    m = statistics.mean(values) if n else 0.0
    sd = statistics.stdev(values) if n > 1 else 0.0
    ci = 1.96 * sd / math.sqrt(n) if n > 1 else 0.0
    return {"mean": round(m, 4), "std": round(sd, 4), "ci95": round(ci, 4), "n": n}
