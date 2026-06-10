"""장소 기반 만남 선택 시스템 — #02 Ecosystem"""
import random
from village.characters.state import CharacterState
from village.world.time_system import village_hour_to_period
from village.config import MAX_CONVERSATIONS_PER_TICK
from village.systems.social_energy import can_converse
from village.systems.reputation import ReputationMatrix
from village.systems.information import KnowledgeBase

_reputation_matrix: ReputationMatrix | None = None
_knowledge_base: KnowledgeBase | None = None


def set_encounter_context(reputation_matrix: ReputationMatrix, knowledge_base: KnowledgeBase):
    global _reputation_matrix, _knowledge_base
    _reputation_matrix = reputation_matrix
    _knowledge_base = knowledge_base


def determine_locations(characters: dict[str, CharacterState], hour: int):
    period = village_hour_to_period(hour)
    for char in characters.values():
        if not can_converse(char) and period not in ("late_night", "early_morning"):
            char.location = "residential"
            continue

        base_location = char.get_location(period)
        if random.random() < 0.2 and char.top_goal():
            goal = char.top_goal()
            allies = goal.get("allies", [])
            if allies:
                target_ally = random.choice(allies)
                if target_ally in characters:
                    target_loc = characters[target_ally].get_location(period)
                    if target_loc != "residential":
                        char.location = target_loc
                        continue
        char.location = base_location


def select_encounters(
    characters: dict[str, CharacterState],
    relationships: dict,
    hour: int,
    world_day: int = 1,
) -> list[tuple[str, str]]:
    period = village_hour_to_period(hour)

    if period in ("late_night", "early_morning"):
        return []

    location_groups: dict[str, list[str]] = {}
    for char_id, char in characters.items():
        loc = char.location
        if loc == "residential":
            continue
        if not can_converse(char):
            continue
        location_groups.setdefault(loc, []).append(char_id)

    possible_pairs = []
    for loc, char_ids in location_groups.items():
        if len(char_ids) < 2:
            continue
        for i in range(len(char_ids)):
            for j in range(i + 1, len(char_ids)):
                a, b = char_ids[i], char_ids[j]

                # P2: 하루 1회 제한 — 이미 오늘 대화한 쌍은 제외
                a_talked_to_b = any(b in entry for entry in characters[a].today_interactions)
                if a_talked_to_b:
                    continue

                priority = _calculate_encounter_priority(
                    a, b, characters, relationships, world_day,
                )
                possible_pairs.append((priority, a, b))

    possible_pairs.sort(key=lambda x: -x[0])

    selected = []
    used_chars = set()
    for priority, a, b in possible_pairs:
        if len(selected) >= MAX_CONVERSATIONS_PER_TICK:
            break
        if a in used_chars or b in used_chars:
            continue
        selected.append((a, b))
        used_chars.add(a)
        used_chars.add(b)

    return selected


def _calculate_encounter_priority(
    a: str, b: str,
    characters: dict[str, CharacterState],
    relationships: dict,
    world_day: int = 1,
) -> float:
    rel_key = tuple(sorted([a, b]))
    rel = relationships.get(rel_key, {
        "warmth": 0.5, "trust": 0.5, "tension": 0.3,
        "salience": 0.3, "interaction_count": 0,
        "last_interaction_day": 0, "fatigue_cooldown": 0,
    })

    if rel.get("fatigue_cooldown", 0) > 0:
        return -10.0

    score = 0.5

    score += rel.get("salience", 0.3) * 1.5

    score += _compute_needs_alignment(a, b, characters) * 1.0

    char_a = characters[a]
    char_b = characters[b]
    goal_a = char_a.top_goal()
    goal_b = char_b.top_goal()
    if goal_a and (b in goal_a.get("allies", []) or b in goal_a.get("blockers", [])):
        score += 1.0
    if goal_b and (a in goal_b.get("allies", []) or a in goal_b.get("blockers", [])):
        score += 1.0

    days_since = world_day - rel.get("last_interaction_day", 0)
    if days_since >= 5:
        score += min(2.0, days_since * 0.3)

    if rel.get("interaction_count", 0) < 3:
        score += 2.0

    recent_a = [i for i in char_a.today_interactions if b in i]
    if not recent_a:
        score += 0.5

    if _reputation_matrix:
        entry_a = _reputation_matrix.get(a, {}).get(b)
        entry_b = _reputation_matrix.get(b, {}).get(a)
        if entry_a and entry_a.integrity < 0.3 and entry_a.confidence > 0.4:
            score -= 1.0
        if entry_b and entry_b.integrity < 0.3 and entry_b.confidence > 0.4:
            score -= 1.0
        if entry_a and entry_a.integrity > 0.7:
            score += 0.3

    if _knowledge_base:
        a_knows_about_b = [i for i in _knowledge_base.get(a, {}).values() if i.subject == b]
        if a_knows_about_b:
            score += 0.5

    score += random.uniform(0, 0.5)

    return score


def _compute_needs_alignment(a: str, b: str, characters: dict) -> float:
    char_a = characters[a]
    char_b = characters[b]
    need_a, val_a = char_a.top_unmet_need()
    need_b, val_b = char_b.top_unmet_need()

    alignment = 0.0
    if need_a == "belonging" or need_b == "belonging":
        alignment += 0.3
    if need_a == "recognition" and char_b.is_ai != char_a.is_ai:
        alignment += 0.2
    if need_a == "affection" or need_b == "affection":
        alignment += 0.2
    urgency = max(0.0, 1.0 - min(val_a, val_b))
    alignment += urgency * 0.3
    return min(1.0, alignment)


def select_solo_characters(
    characters: dict[str, CharacterState],
    encounter_participants: set[str],
    n: int = 1,
) -> list[str]:
    available = [
        cid for cid in characters
        if cid not in encounter_participants and characters[cid].location != "residential"
    ]
    if not available:
        available = [cid for cid in characters if cid not in encounter_participants]
    return random.sample(available, min(n, len(available)))
