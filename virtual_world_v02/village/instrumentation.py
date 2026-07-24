"""D-M1 계측기 슬롯 — 창발·폴백·판단분산·기억영속. 읽기전용 오프라인 집계.

기존 옵트인 로그(decision_records.jsonl/institutions.json/relationships.json/memories/*)만
읽는다. 시뮬 루프에 훅을 심지 않으므로 라이브 무영향이 설계상 자명하다(가드조차 불요).
스펙: HARMONYCITY_D-M1_INSTRUMENTATION_SPEC_v0.md 참조.

village.config를 import하지 않는다 — metrics.py와 동일하게 임의 data dir을 인자로 받는다.
"""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def _read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _entropy(counts) -> float:
    """Shannon entropy(bits). 단일 카테고리(분산 0)면 0.0."""
    total = sum(counts)
    if total == 0 or len(counts) <= 1:
        return 0.0
    h = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return round(h, 4)


def _gini(values) -> float:
    """Gini 계수(0=완전균등, 1=완전쏠림). 값 전부 0이면 0.0."""
    vals = sorted(v for v in values if v >= 0)
    n = len(vals)
    total = sum(vals)
    if n == 0 or total == 0:
        return 0.0
    cum = 0
    weighted = 0
    for i, v in enumerate(vals, start=1):
        cum += v
        weighted += i * v
    gini = (2 * weighted) / (n * total) - (n + 1) / n
    return round(gini, 4)


def fallback_rate(data_dir, window: int | None = None) -> dict:
    """decision_records.jsonl의 interpretation_status 분포 — 전체 + decider_id별.

    window: 최근 N건만 집계(추세 관찰). None이면 전체.
    """
    records = _read_jsonl(Path(data_dir) / "decision_records.jsonl")
    if window:
        records = records[-window:]
    if not records:
        return {"n": 0, "overall": {}, "by_decider": {}}

    overall = Counter(r.get("interpretation_status") for r in records)
    by_decider = defaultdict(Counter)
    for r in records:
        decider_id = (r.get("decider") or {}).get("id", "unknown")
        by_decider[decider_id][r.get("interpretation_status")] += 1

    def _summarize(counter: Counter) -> dict:
        total = sum(counter.values())
        fb = counter.get("fallback", 0)
        return {
            "n": total,
            "fallback": fb,
            "fallback_rate": round(fb / total, 4) if total else 0.0,
            "distribution": dict(counter),
        }

    return {
        "n": len(records),
        "overall": _summarize(overall),
        "by_decider": {k: _summarize(v) for k, v in by_decider.items()},
    }


def judgment_entropy(data_dir, group_by: str = "decider_id", window: int | None = None) -> dict:
    """decision_records.jsonl의 choice 분포 entropy. group_by: decider_id | basis.

    D-A3 소견 인용: 낮은 entropy는 자율성 부재가 아니라 입력이 답을 사실상
    결정짓는 경우일 수 있다 — 단독 해석 금지, fallback_rate/원본 basis와 함께 볼 것.
    """
    records = _read_jsonl(Path(data_dir) / "decision_records.jsonl")
    if window:
        records = records[-window:]
    parsed = [r for r in records if r.get("interpretation_status") != "fallback"]
    if not parsed:
        return {"n": 0, "groups": {}}

    def _key(r):
        if group_by == "basis":
            return r.get("basis", "unknown")
        return (r.get("decider") or {}).get("id", "unknown")

    groups = defaultdict(Counter)
    for r in parsed:
        choice = r.get("choice")
        if isinstance(choice, (dict, list)):
            choice = json.dumps(choice, sort_keys=True, ensure_ascii=False)
        groups[_key(r)][choice] += 1

    out = {}
    for k, counter in groups.items():
        out[k] = {
            "n": sum(counter.values()),
            "n_distinct_choices": len(counter),
            "entropy_bits": _entropy(list(counter.values())),
            "distribution": dict(counter),
        }
    return {"n": len(parsed), "groups": out}


def role_emergence(data_dir) -> dict:
    """institutions.json 역할 분포 — 단일 시점 스냅샷(시계열 비교는 스코프 밖, §6)."""
    institutions = _read_json(Path(data_dir) / "institutions.json", {})
    roles = institutions.get("roles", institutions) if isinstance(institutions, dict) else {}
    if not isinstance(roles, dict) or not roles:
        return {"n_characters": 0, "distribution": {}, "role_entropy_bits": 0.0}

    counter = Counter(v if v else "None" for v in roles.values())
    return {
        "n_characters": len(roles),
        "distribution": dict(counter),
        "role_entropy_bits": _entropy(list(counter.values())),
    }


def interaction_concentration(data_dir) -> dict:
    """캐릭터별 활성 관계쌍 수의 Gini 계수 — 허브 캐릭터 자연발생 여부."""
    relationships = _read_json(Path(data_dir) / "relationships.json", {})
    pairs = relationships.values() if isinstance(relationships, dict) else relationships
    per_char = Counter()
    for key, rel in (relationships.items() if isinstance(relationships, dict) else []):
        if not isinstance(rel, dict) or rel.get("interaction_count", 0) <= 0:
            continue
        a, b = key.split("|") if "|" in key else (key, "")
        per_char[a] += 1
        if b:
            per_char[b] += 1

    return {
        "n_characters": len(per_char),
        "active_pairs_per_character": dict(per_char),
        "gini": _gini(list(per_char.values())),
    }


def memory_persistence(data_dir) -> dict:
    """캐릭터별 L2(episodes)/L3(core) 기억 적재 현황 + 관계요약 커버리지."""
    data_dir = Path(data_dir)
    mem_root = data_dir / "memories"
    relationships = _read_json(data_dir / "relationships.json", {})
    active_pairs = defaultdict(set)
    for key, rel in (relationships.items() if isinstance(relationships, dict) else []):
        if not isinstance(rel, dict) or rel.get("interaction_count", 0) <= 0:
            continue
        if "|" not in key:
            continue
        a, b = key.split("|")
        active_pairs[a].add(b)
        active_pairs[b].add(a)

    if not mem_root.exists():
        return {"n_characters": 0, "characters": {}}

    out = {}
    for char_dir in sorted(p for p in mem_root.iterdir() if p.is_dir()):
        char_id = char_dir.name
        core = _read_json(char_dir / "core.json", {})
        episodes = _read_jsonl(char_dir / "episodes.jsonl")
        summaries = core.get("relationship_summaries", {}) if isinstance(core, dict) else {}
        active = active_pairs.get(char_id, set())
        coverage = round(len(set(summaries) & active) / len(active), 4) if active else None
        out[char_id] = {
            "relationship_summary_coverage": coverage,
            "n_summaries": len(summaries),
            "n_active_relationships": len(active),
            "n_key_events": len(core.get("key_events", [])) if isinstance(core, dict) else 0,
            "n_belief_shifts": len(core.get("belief_shifts", [])) if isinstance(core, dict) else 0,
            "n_episodes": len(episodes),
            "episodes_at_cap": len(episodes) >= 50,
        }
    return {"n_characters": len(out), "characters": out}


def full_report(data_dir) -> dict:
    """4항목 전부 한 번에 계산."""
    return {
        "data_dir": str(data_dir),
        "fallback": fallback_rate(data_dir),
        "judgment_dispersion": judgment_entropy(data_dir),
        "emergence": {
            "role_emergence": role_emergence(data_dir),
            "interaction_concentration": interaction_concentration(data_dir),
        },
        "memory_persistence": memory_persistence(data_dir),
    }
