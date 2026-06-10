"""자생 이벤트 시스템 — 기업 조직개발 도메인 (넥스트랩)"""
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
    """번아웃 위기 — 특정 욕구가 3일 연속 임계치 이하일 때 발동."""
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
                    "description": f"{char.name}: {need_key} 번아웃 위기 (3일 연속 < 15%)",
                    "prompt_injection": f"오늘은 {need_key}에 대한 결핍이 한계에 달했다. 퇴사를 고민하거나, 폭발적 행동을 하고 싶다.",
                })
    return events


def _check_confrontation(relationships: dict, current_day: int) -> list[dict]:
    """부서 간 대결 — 고긴장 관계가 장기간 해소되지 않을 때 발동."""
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
            "description": f"{a} ↔ {b}: 장기 갈등 폭발 — 부서 간 대결 발생",
            "tension_release": 0.25,
        })
    return events


def _check_stagnation(relationships: dict, world: WorldState) -> list[dict]:
    """조직 정체 — 전체 긴장도가 낮은 상태가 지속되면 변화 촉발."""
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
            "description": "조직 분위기 정체 — 누군가 변화를 시도해야 할 때",
            "prompt_injection": "회사가 너무 정체되어 있다. 뭔가 새로운 시도를 하거나, 숨겨왔던 불만을 꺼내고 싶다.",
        }]
    return []


def _check_isolation(
    characters: dict[str, CharacterState],
    current_day: int,
) -> list[dict]:
    """사일로 고립 — 특정 구성원이 소수와만 교류할 때 발동."""
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
                "description": f"{char.name}: 사일로 고립 감지 — 타 부서 교류 필요",
            })
    return events


def _check_goal_culmination(characters: dict[str, CharacterState]) -> list[dict]:
    """프로젝트 마일스톤 — 개인 목표 달성이 임박할 때 발동."""
    events = []
    for char_id, char in characters.items():
        for goal in char.goals:
            if goal["progress"] >= 0.9:
                events.append({
                    "type": "goal_culmination",
                    "character": char_id,
                    "description": f"{char.name}: '{goal['description']}' 마일스톤 달성 임박",
                    "goal": goal,
                })
    return events
