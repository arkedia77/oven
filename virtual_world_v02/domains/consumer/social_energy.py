"""사회적 에너지 예산 시스템 — 한남동 소비 생태계"""

ENERGY_BUDGET = {
    "dong_hyun": 3.0,       # 얼리어답터: 외향적, 활발한 소통
    "sang_chul": 2.5,       # 전통시장 사장: 체력 있지만 지쳐감
    "soo_yeon": 3.5,        # 인플루언서: 소셜 에너지 최상위
    "mi_jung": 2.5,         # 알뜰 주부: 실속형, 필요한 만큼만 소통
    "nuri": 2.5,            # AI 쇼핑 어시스턴트: 안정적이지만 감정 대화에 소모
    "hae_won": 2.0,         # 환경운동가: 열정적이지만 에너지 소모가 큼
    "young_sook": 2.0,      # 시니어: 체력 한계, 느린 소통
    "jun_seo": 2.0,         # 배달기사: 과로 상태, 소통 여력 최소
    "eun_bi": 3.0,          # 카페 사장: 손님 응대로 소통 익숙
    "ji_won": 2.5,          # 구청 담당자: 업무적 소통은 많지만 개인적 교류는 적음
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
