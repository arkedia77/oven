"""자생 이벤트 시스템 — 조건 기반 자동 발화"""
from village.characters.state import CharacterState
from village.world.state import WorldState
from village.systems.homeostasis import compute_village_tension


def check_events(
    world: WorldState,
    characters: dict[str, CharacterState],
    relationships: dict,
    need_history: dict[str, dict[str, list[float]]],
) -> list[dict]:
    events = []

    events.extend(_check_personal_crisis(characters, need_history))
    events.extend(_check_confrontation(relationships, world.day))
    events.extend(_check_stagnation(relationships, world))
    events.extend(_check_isolation(characters, world.day))
    events.extend(_check_goal_culmination(characters))

    for event in events:
        world.add_event(f"[Day {world.day}] {event['description']}")
        print(f"  🎯 이벤트: {event['description']}")

    return events


def _check_personal_crisis(
    characters: dict[str, CharacterState],
    need_history: dict[str, dict[str, list[float]]],
) -> list[dict]:
    events = []
    for char_id, char in characters.items():
        hist = need_history.get(char_id, {})
        for need_key, need_val in char.needs.items():
            if need_val >= 0.15:
                continue
            recent = hist.get(need_key, [])
            if len(recent) >= 3 and all(v < 0.15 for v in recent[-3:]):
                events.append({
                    "type": "personal_crisis",
                    "character": char_id,
                    "need": need_key,
                    "description": f"{char.name}: {need_key} 욕구 위기 (3일 연속 < 15%)",
                    "prompt_injection": f"오늘은 {need_key}에 대한 결핍이 극에 달했다. 뭔가 극적인 행동을 하고 싶다.",
                })
    return events


def _check_confrontation(relationships: dict, current_day: int) -> list[dict]:
    events = []
    for pair_key, rel in relationships.items():
        if rel.get("tension", 0) < 0.8:
            continue
        last_day = rel.get("last_interaction_day", 0)
        if current_day - last_day < 5:
            continue
        if isinstance(pair_key, tuple):
            a, b = pair_key
        else:
            a, b = pair_key.split("|")
        events.append({
            "type": "confrontation",
            "characters": [a, b],
            "description": f"{a} ↔ {b}: 장기 고긴장 대결 발생",
            "tension_release": 0.25,
        })
    return events


def _check_stagnation(relationships: dict, world: WorldState) -> list[dict]:
    avg_tension = compute_village_tension(relationships)
    if avg_tension >= 0.2:
        return []
    if not hasattr(world, "_low_tension_days"):
        world._low_tension_days = 0
    world._low_tension_days += 1
    if world._low_tension_days >= 3:
        world._low_tension_days = 0
        return [{
            "type": "stagnation_breaker",
            "description": "마을 분위기 정체 — 변화의 바람이 필요하다",
            "prompt_injection": "뭔가 변화를 만들고 싶다. 이대로는 재미없어.",
        }]
    return []


def _check_isolation(
    characters: dict[str, CharacterState],
    current_day: int,
) -> list[dict]:
    events = []
    for char_id, char in characters.items():
        unique_contacts = set()
        for interaction in char.today_interactions:
            other_id = interaction.split(" ")[0]
            unique_contacts.add(other_id)
        if len(unique_contacts) < 2 and current_day > 3:
            events.append({
                "type": "isolation_bridge",
                "character": char_id,
                "description": f"{char.name}: 사회적 고립 감지 — 새로운 만남 탐색",
            })
    return events


def _check_goal_culmination(characters: dict[str, CharacterState]) -> list[dict]:
    events = []
    for char_id, char in characters.items():
        for goal in char.goals:
            if goal["progress"] >= 0.9:
                events.append({
                    "type": "goal_culmination",
                    "character": char_id,
                    "description": f"{char.name}: '{goal['description']}' 목표 달성 임박",
                    "goal": goal,
                })
    return events
