"""L3 핵심기억 — 관계 요약, 신념 변화, 주요 사건"""
import json
from pathlib import Path
from village.config import DATA_DIR


def get_core_path(char_id: str) -> Path:
    return DATA_DIR / "memories" / char_id / "core.json"


def load_core(char_id: str) -> dict:
    path = get_core_path(char_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"relationship_summaries": {}, "key_events": [], "belief_shifts": []}


def save_core(char_id: str, core: dict):
    path = get_core_path(char_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(core, ensure_ascii=False, indent=2), encoding="utf-8")


def get_relationship_summary(char_id: str, other_id: str) -> str:
    core = load_core(char_id)
    return core.get("relationship_summaries", {}).get(other_id, "아직 잘 모르는 사이")


def update_relationship_summary(char_id: str, other_id: str, summary: str):
    core = load_core(char_id)
    if "relationship_summaries" not in core:
        core["relationship_summaries"] = {}
    core["relationship_summaries"][other_id] = summary
    save_core(char_id, core)


def add_key_event(char_id: str, event: str):
    core = load_core(char_id)
    core.setdefault("key_events", []).append(event)
    if len(core["key_events"]) > 20:
        core["key_events"] = core["key_events"][-20:]
    save_core(char_id, core)
