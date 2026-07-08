"""상태 저장/복구 — #02 Ecosystem"""
import os
import json
from pathlib import Path
from village.config import DATA_DIR
from village.characters.state import CharacterState
from village.world.state import WorldState


def _atomic_write(path: Path, text: str):
    """원자적 쓰기(A-2): tmp 파일에 쓴 뒤 os.replace로 교체.

    관측 API(api/server.py)가 저장 도중 읽어도 부분 파일을 보지 않게 하고,
    크래시 시 파일 파손을 방지한다. 내용/경로는 기존과 동일 → 재현성 해시 불변.
    """
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def save_world_state(world: WorldState):
    path = DATA_DIR / "world_state.json"
    _atomic_write(path, json.dumps(world.to_dict(), ensure_ascii=False, indent=2))


def load_world_state() -> WorldState:
    path = DATA_DIR / "world_state.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return WorldState.from_dict(data)
    return WorldState()


def save_character_state(char: CharacterState):
    path = DATA_DIR / "characters" / f"{char.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, json.dumps(char.to_dict(), ensure_ascii=False, indent=2))


def load_character_state(char_id: str) -> CharacterState | None:
    path = DATA_DIR / "characters" / f"{char_id}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return CharacterState.from_dict(data)
    return None


def save_relationships(relationships: dict):
    serializable = {}
    for key, val in relationships.items():
        str_key = f"{key[0]}|{key[1]}"
        serializable[str_key] = val
    path = DATA_DIR / "relationships.json"
    _atomic_write(path, json.dumps(serializable, ensure_ascii=False, indent=2))


def load_relationships() -> dict:
    path = DATA_DIR / "relationships.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    relationships = {}
    for str_key, val in data.items():
        parts = str_key.split("|")
        if len(parts) == 2:
            relationships[tuple(parts)] = val
    return relationships


def save_need_history(history: dict):
    path = DATA_DIR / "need_history.json"
    _atomic_write(path, json.dumps(history, ensure_ascii=False, indent=2))


def load_need_history() -> dict | None:
    path = DATA_DIR / "need_history.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_belief_history(history: dict):
    path = DATA_DIR / "belief_history.json"
    _atomic_write(path, json.dumps(history, ensure_ascii=False, indent=2))


def load_belief_history() -> dict | None:
    path = DATA_DIR / "belief_history.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_relationship_history(history: dict):
    path = DATA_DIR / "relationship_history.json"
    _atomic_write(path, json.dumps(history, ensure_ascii=False, indent=2))


def load_relationship_history() -> dict | None:
    path = DATA_DIR / "relationship_history.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_atmosphere(state: dict):
    path = DATA_DIR / "atmosphere.json"
    _atomic_write(path, json.dumps(state, ensure_ascii=False, indent=2))


def load_atmosphere() -> dict | None:
    path = DATA_DIR / "atmosphere.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_reputation(matrix: dict):
    from village.systems.reputation import ReputationEntry
    serializable = {}
    for observer, targets in matrix.items():
        serializable[observer] = {}
        for target, entry in targets.items():
            serializable[observer][target] = entry.to_dict()
    path = DATA_DIR / "reputation.json"
    _atomic_write(path, json.dumps(serializable, ensure_ascii=False, indent=2))


def load_reputation() -> dict | None:
    from village.systems.reputation import ReputationEntry
    path = DATA_DIR / "reputation.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    matrix = {}
    for observer, targets in data.items():
        matrix[observer] = {}
        for target, entry_data in targets.items():
            matrix[observer][target] = ReputationEntry.from_dict(entry_data)
    return matrix


def save_knowledge_base(kb: dict, registry: dict):
    from village.systems.information import InfoItem
    kb_serial = {}
    for char_id, items in kb.items():
        kb_serial[char_id] = {iid: item.to_dict() for iid, item in items.items()}
    reg_serial = {iid: item.to_dict() for iid, item in registry.items()}
    path = DATA_DIR / "knowledge_base.json"
    _atomic_write(path, json.dumps({"kb": kb_serial, "registry": reg_serial}, ensure_ascii=False, indent=2))


def load_knowledge_base() -> tuple[dict, dict] | None:
    from village.systems.information import InfoItem
    path = DATA_DIR / "knowledge_base.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    kb = {}
    for char_id, items in data.get("kb", {}).items():
        kb[char_id] = {iid: InfoItem.from_dict(d) for iid, d in items.items()}
    registry = {iid: InfoItem.from_dict(d) for iid, d in data.get("registry", {}).items()}
    return kb, registry


def save_all(world: WorldState, characters: dict[str, CharacterState], relationships: dict):
    save_world_state(world)
    for char in characters.values():
        save_character_state(char)
    save_relationships(relationships)
