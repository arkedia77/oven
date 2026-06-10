"""동기 기반 프롬프트 빌더 — 소비자 리서치 도메인"""
from village.characters.state import CharacterState
from village.world.state import WorldState
from village.world.locations import LOCATIONS
from village.world.time_system import format_village_time
from village.memory.episodic import get_episodes_about
from village.memory.core import get_relationship_summary
from village.systems.location_atmosphere import get_atmosphere_text


def build_conversation_prompt(
    char: CharacterState,
    other: CharacterState,
    relationships: dict,
    world: WorldState,
) -> str:
    rel_key = tuple(sorted([char.id, other.id]))
    rel = relationships.get(rel_key, {"warmth": 0.5, "trust": 0.5, "tension": 0.3})

    past_episodes = get_episodes_about(char.id, other.id, n=3)
    past_summary = "\n".join(
        f"- {ep.get('summary', '')}" for ep in past_episodes
    ) if past_episodes else "(첫 대화)"

    rel_summary = get_relationship_summary(char.id, other.id)

    unmet_need, need_val = char.top_unmet_need()
    need_desc = {
        "belonging": "소속감 부족 — 동네에서 소외되는 느낌, 커뮤니티 유대 약화",
        "purpose": "소비 의미 부족 — 쇼핑이 공허함, 가치 있는 소비를 하고 싶음",
        "security": "경제적 불안 — 매출 감소, 일자리 위협, 재정 걱정",
        "recognition": "인정 부족 — 사회적 영향력/존재감이 줄어드는 느낌",
        "autonomy": "선택권 부족 — AI가 결정하는 대로 따라가는 느낌, 데이터 주권 불안",
        "affection": "유대 부족 — 동네 인간적 관계가 사라지고 있음, 단골 관계 그리움",
    }

    goal = char.top_goal()
    goal_text = ""
    if goal:
        is_ally = other.id in goal.get("allies", [])
        is_blocker = other.id in goal.get("blockers", [])
        goal_text = f"현재 목표: {goal['description']} (진행: {goal['progress']*100:.0f}%)"
        if is_ally:
            goal_text += f"\n→ {other.name}은(는) 이 목표의 잠재적 협력자"
        elif is_blocker:
            goal_text += f"\n→ {other.name}은(는) 이 목표의 방해 요소"

    belief_conflicts = []
    for key in char.beliefs:
        diff = abs(char.beliefs[key] - other.beliefs.get(key, 0.5))
        if diff > 0.4:
            belief_names = {
                "ai_consciousness": "AI 추천이 진정한 취향을 이해하는가",
                "ai_rights": "AI 서비스가 소비자 데이터를 쓸 권리",
                "human_uniqueness": "사람 대 사람 거래만의 가치",
                "progress_good": "기술 발전이 소비 생활을 개선하는가",
                "community_priority": "동네 상권/공동체 vs 개인 편의",
            }
            mine = "강하게 동의" if char.beliefs[key] > 0.6 else "회의적"
            belief_conflicts.append(f"'{belief_names.get(key, key)}' — 나는 {mine}")

    loc = LOCATIONS.get(char.location, {})
    loc_name = loc.get("name", char.location)
    atmosphere = get_atmosphere_text(char.location)

    persona = char.persona
    if hasattr(char, "persona_addendum") and char.persona_addendum:
        persona += f"\n(최근 변화: {char.persona_addendum})"

    return f"""너는 '{char.name}'이다. {persona}

== 말투 ==
{char.speech_style}

== 현재 상태 ==
감정: {char.emotional_state}
에너지: {char.energy:.1f}
고민: {need_desc.get(unmet_need, unmet_need)} (심각도: {1-need_val:.0%})
{goal_text}

== {other.name}과(와)의 관계 ==
신뢰: {rel.get('trust', 0.5)*10:.0f}/10 | 호감: {rel.get('warmth', 0.5)*10:.0f}/10 | 유대: {rel.get('affection', 0.0)*10:.0f}/10 | 긴장: {rel.get('tension', 0.3)*10:.0f}/10
내 인상: {rel_summary}
과거 대화:
{past_summary}

== 가치관 충돌 가능성 ==
{chr(10).join(belief_conflicts) if belief_conflicts else '(현재 뚜렷한 충돌 없음)'}

== 상황 ==
장소: {loc_name}, 시간: Day {world.day} {format_village_time(world.hour)}
{atmosphere}
최근 동네 소식: {'; '.join(world.recent_events(2)) if world.recent_events() else '특별한 소식 없음'}

== 규칙 ==
- 한국어 2-4문장. thinking 없이 바로 답해.
- 동네 주민답게 자연스럽게. 소비, 장사, 동네 생활 이야기가 자연스럽게 나와야 해.
- 동의하지 않으면 이유를 들어 반박해도 돼.
- 하지만 매번 싸울 필요는 없어. 현실처럼 행동해:
  타협, 주제 전환, 양보, 유머, 침묵, 수다도 자연스러운 선택이야.
- 긴장이 높으면(7/10 이상) 가끔은 한발 물러서봐.
  같은 동네에서 계속 만나야 하니까.
- 경제적 고민이 기분에 반영돼야 해.
- 과거 대화 내용을 참고해서 이어가.
- 반복되는 칭찬이나 빈말 금지. 구체적이고 진솔하게."""


def build_reflection_prompt(
    char: CharacterState,
    other: CharacterState,
    conversation_text: str,
) -> str:
    return f"""방금 {other.name}과(와) 나눈 대화야:

{conversation_text}

thinking 없이 바로 한국어로 답해. 아래 5가지를 각각 한 줄로:
1. 이 대화가 내 목표에 도움이 됐나 방해됐나?
2. {other.name}에 대한 신뢰/호감이 변했나? 어떤 방향?
3. 다음에 할 구체적 행동은? ("대화하기"가 아닌 실제 행동)
4. 지금 내 솔직한 기분은?
5. 이 사람과의 관계에서 내가 조금이라도 입장을 바꾼 부분이 있나?"""


def build_monologue_prompt(char: CharacterState, world: WorldState) -> str:
    unmet_need, need_val = char.top_unmet_need()
    goal = char.top_goal()

    return f"""너는 '{char.name}'이다. {char.persona}

지금은 Day {world.day} {format_village_time(world.hour)}. 혼자 있는 시간이야.

현재 감정: {char.emotional_state}
가장 부족한 것: {unmet_need} ({1-need_val:.0%} 결핍)
현재 고민: {goal['description'] if goal else '특별한 목표 없음'}

thinking 없이 한국어 2-3문장으로 내면 독백을 해.
- 소비자/상인/주민으로서의 속마음을 솔직하게. 불안, 질투, 후회, 그리움 뭐든.
- 다음에 뭘 해야 할지 혼잣말.
- 동네의 변화 속에서 나는 어디로 가고 있나."""


def build_opener_prompt(char: CharacterState, other: CharacterState) -> str:
    return (
        f"{other.name}을(를) 마주쳤어. "
        f"지금 네 감정과 상황에 맞게 자연스럽게 말을 걸어. "
        f"꼭 반갑게 인사할 필요 없어 — 기분이 안 좋으면 그것도 드러나도 돼."
    )
