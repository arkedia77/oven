"""자생 이벤트 시스템 — 한남동 소비 생태계 조건 기반 자동 발화"""
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

    events.extend(_check_economic_crisis(characters, need_history))
    events.extend(_check_market_confrontation(relationships, world.day))
    events.extend(_check_market_stagnation(relationships, world))
    events.extend(_check_digital_exclusion(characters, world.day))
    events.extend(_check_goal_culmination(characters))

    for event in events:
        world.add_event(f"[Day {world.day}] {event['description']}")
        print(f"  🎯 이벤트: {event['description']}")

    return events


def _check_economic_crisis(
    characters: dict[str, CharacterState],
    need_history: dict[str, dict[str, list[float]]],
) -> list[dict]:
    """경제적 위기: 매출 급감, 해고 위기, 생활고 등으로 security/purpose가 바닥인 캐릭터 감지."""
    events = []
    for char_id, char in characters.items():
        hist = need_history.get(char_id, {})
        for need_key, need_val in char.needs.items():
            if need_val >= 0.15:
                continue
            recent = hist.get(need_key, [])
            if len(recent) >= 3 and all(v < 0.15 for v in recent[-3:]):
                need_labels = {
                    "belonging": "소속감",
                    "purpose": "삶의 의미",
                    "security": "경제적 안정",
                    "recognition": "사회적 인정",
                    "autonomy": "선택의 자유",
                    "affection": "인간적 유대",
                }
                label = need_labels.get(need_key, need_key)
                events.append({
                    "type": "economic_crisis",
                    "character": char_id,
                    "need": need_key,
                    "description": f"{char.name}: {label} 위기 (3일 연속 < 15%)",
                    "prompt_injection": (
                        f"오늘은 {label}에 대한 결핍이 극에 달했다. "
                        f"당장 뭔가 행동하지 않으면 무너질 것 같다."
                    ),
                })
    return events


def _check_market_confrontation(relationships: dict, current_day: int) -> list[dict]:
    """상권 충돌: 전통시장 vs AI마트 진영 사이의 고긴장 대결 발생."""
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
            "type": "market_confrontation",
            "characters": [a, b],
            "description": f"{a} ↔ {b}: 상권 갈등 폭발 — 공개적 대립 발생",
            "tension_release": 0.25,
        })
    return events


def _check_market_stagnation(relationships: dict, world: WorldState) -> list[dict]:
    """시장 정체: 전체 긴장도가 너무 낮아 소비 패턴이 고착된 상태."""
    avg_tension = compute_village_tension(relationships)
    if avg_tension >= 0.2:
        return []
    if not hasattr(world, "_low_tension_days"):
        world._low_tension_days = 0
    world._low_tension_days += 1
    if world._low_tension_days >= 3:
        world._low_tension_days = 0
        return [{
            "type": "market_stagnation",
            "description": "동네 상권 정체 — 새로운 변수가 필요하다 (팝업 행사, 가격 전쟁, 기사 노출 등)",
            "prompt_injection": "요즘 너무 조용하다. 뭔가 판을 흔들어야 할 것 같다.",
        }]
    return []


def _check_digital_exclusion(
    characters: dict[str, CharacterState],
    current_day: int,
) -> list[dict]:
    """디지털 소외: 시니어, 소상공인 등 디지털 접근이 어려운 캐릭터의 사회적 고립 감지."""
    events = []
    for char_id, char in characters.items():
        unique_contacts = set()
        for interaction in char.today_interactions:
            other_id = interaction.split(" ")[0]
            unique_contacts.add(other_id)
        if len(unique_contacts) < 2 and current_day > 3:
            events.append({
                "type": "digital_exclusion",
                "character": char_id,
                "description": f"{char.name}: 디지털 소외/사회적 고립 감지 — 도움의 손길 필요",
            })
    return events


def _check_goal_culmination(characters: dict[str, CharacterState]) -> list[dict]:
    """목표 달성 임박: 캐릭터의 개인 목표 진행도가 90% 이상."""
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
