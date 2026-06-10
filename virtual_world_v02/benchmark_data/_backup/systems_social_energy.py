"""사회적 에너지 예산 시스템"""

ENERGY_BUDGET = {
    "seo_jin": 2.0,
    "nexus": 2.0,
    "joon_ho": 2.5,
    "sang_woo": 2.5,
    "aria": 3.0,
    "luna": 2.5,
    "min_ah": 3.0,
    "tae_sik": 3.0,
    "ha_yeon": 3.5,
    "ye_eun": 3.0,
}
DEFAULT_BUDGET = 3.0

CONVERSATION_COST = 0.5
MONOLOGUE_COST = 0.1
HIGH_TENSION_BONUS_COST = 0.3

MIN_ENERGY_FOR_CONVERSATION = 0.5


def get_daily_budget(char_id: str) -> float:
    return ENERGY_BUDGET.get(char_id, DEFAULT_BUDGET)


def spend_conversation(char, rel_tension: float = 0.0):
    cost = CONVERSATION_COST
    if rel_tension > 0.6:
        cost += HIGH_TENSION_BONUS_COST
    char.energy = max(0.0, char.energy - cost)


def spend_monologue(char):
    char.energy = max(0.0, char.energy - MONOLOGUE_COST)


def can_converse(char) -> bool:
    return char.energy >= MIN_ENERGY_FOR_CONVERSATION


def reset_daily_energy(char):
    char.energy = get_daily_budget(char.id)
