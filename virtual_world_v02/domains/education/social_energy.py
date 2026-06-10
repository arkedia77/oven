"""사회적 에너지 예산 시스템 — 한빛고등학교"""

ENERGY_BUDGET = {
    "kim_teacher": 2.5,       # 담임교사 — 수업으로 에너지 소모, 중간 수준
    "principal_oh": 2.5,      # 교장 — 권위적이라 대화보다 지시, 중간
    "ai_tutor": 3.0,          # AI 튜터 — 피로 없이 상호작용 가능, 높음
    "top_student_minji": 2.0, # 우등생 — 학습에 집중, 사교 에너지 적음
    "loner_eunsoo": 1.5,      # 은따 학생 — 사회적 접촉 극도로 제한
    "class_pres_yuna": 3.5,   # 반장 — 가장 활발한 사교 활동
    "rebel_doha": 2.0,        # 문제아 — 선택적으로만 대화, 에너지 적음
    "parent_rep_shin": 2.5,   # 학부모 대표 — 목적 지향적 소통
    "counselor_park": 3.0,    # 상담교사 — 전문적 대화, 높은 에너지
    "coder_jihoon": 3.0,      # 코딩부장 — 기술 이야기엔 에너지 무한, 활발
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
