"""사회적 에너지 예산 시스템 — 기업 조직개발 도메인 (넥스트랩)"""

ENERGY_BUDGET = {
    "dong_hyun": 3.5,   # CEO — 고에너지, 회의/미팅 많음
    "hyun_woo": 2.0,    # CTO — 내향적, 코딩에 집중 선호
    "eun_bi": 3.0,      # HR — 사람 만나는 게 업무, 하지만 번아웃 주의
    "jae_won": 2.0,     # 시니어 엔지니어 — 과묵, 혼자 일하는 것 선호
    "min_jun": 3.0,     # 주니어 개발자 — 젊고 열정적, 적극적 네트워킹
    "da_hye": 2.5,      # PM — 회의 피로도 높지만 조율은 필수
    "sung_min": 3.5,    # 영업 디렉터 — 고에너지, 세일즈 DNA
    "yu_na": 2.5,       # 마케팅 리드 — 크리에이티브, 적당한 교류
    "ji_yeon": 2.5,     # AI 컨설턴트 — 분석적, 필요한 만남만 선별
    "so_young": 3.0,    # 총무 — 사교적, 모든 사람과 대화
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
