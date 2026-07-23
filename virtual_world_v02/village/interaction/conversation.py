"""대화 실행 + 반영 처리 — #02 Ecosystem"""
import json
from datetime import datetime
from village.config import (
    DATA_DIR, EXCHANGES_PER_CONVERSATION,
    MAX_TOKENS_CONVERSATION, MAX_TOKENS_REFLECTION, MAX_TOKENS_MONOLOGUE,
)
from village.engine.llm import chat
from village.characters.state import CharacterState
from village.world.state import WorldState
from village.interaction.prompts import (
    build_conversation_prompt, build_reflection_prompt,
    build_monologue_prompt, build_opener_prompt,
)
from village.memory.episodic import append_episode
from village.memory.core import update_relationship_summary
from village.systems.homeostasis import (
    compute_village_tension, get_tension_multipliers,
    apply_warmth_tension_constraint, apply_soft_ceiling,
)
from village.systems.location_atmosphere import add_warmth, add_friction
from village.systems.social_energy import spend_conversation, spend_monologue
from village.engine.appraisal import run_appraisal, apply_appraisal
from village.systems.reputation import update_from_direct_interaction, ReputationMatrix

_reputation_matrix: ReputationMatrix | None = None


def set_conversation_reputation(matrix: ReputationMatrix):
    global _reputation_matrix
    _reputation_matrix = matrix


def run_conversation(
    char_a: CharacterState,
    char_b: CharacterState,
    relationships: dict,
    world: WorldState,
) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n  💬 {char_a.name} ↔ {char_b.name} @ {char_a.location}")

    sys_a = build_conversation_prompt(char_a, char_b, relationships, world)
    sys_b = build_conversation_prompt(char_b, char_a, relationships, world)

    history_a = [{"role": "system", "content": sys_a}]
    history_b = [{"role": "system", "content": sys_b}]

    opener_prompt = build_opener_prompt(char_a, char_b)
    history_a.append({"role": "user", "content": opener_prompt})
    greeting = chat(history_a, MAX_TOKENS_CONVERSATION)
    history_a.append({"role": "assistant", "content": greeting})
    print(f"    {char_a.name}: {greeting[:80]}...")

    exchanges = [{"speaker": char_a.id, "name": char_a.name, "text": greeting}]
    last_text = greeting

    for i in range(EXCHANGES_PER_CONVERSATION - 1):
        history_b.append({"role": "user", "content": f"[{char_a.name}]: {last_text}"})
        response_b = chat(history_b, MAX_TOKENS_CONVERSATION)
        history_b.append({"role": "assistant", "content": response_b})
        print(f"    {char_b.name}: {response_b[:80]}...")
        exchanges.append({"speaker": char_b.id, "name": char_b.name, "text": response_b})

        if i < EXCHANGES_PER_CONVERSATION - 2:
            history_a.append({"role": "user", "content": f"[{char_b.name}]: {response_b}"})
            response_a = chat(history_a, MAX_TOKENS_CONVERSATION)
            history_a.append({"role": "assistant", "content": response_a})
            print(f"    {char_a.name}: {response_a[:80]}...")
            exchanges.append({"speaker": char_a.id, "name": char_a.name, "text": response_a})
            last_text = response_a

    record = {
        "day": world.day,
        "hour": world.hour,
        "timestamp": timestamp,
        "location": char_a.location,
        "participants": [char_a.id, char_b.id],
        "exchanges": exchanges,
    }

    day_dir = DATA_DIR / "conversations" / f"day{world.day:03d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    log_path = day_dir / f"{char_a.id}_{char_b.id}_{timestamp}.json"
    log_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    char_a.today_interactions.append(f"{char_b.id} ({world.hour}:00)")
    char_b.today_interactions.append(f"{char_a.id} ({world.hour}:00)")

    rel_key = tuple(sorted([char_a.id, char_b.id]))
    rel = relationships.get(rel_key, {})
    rel_tension = rel.get("tension", 0.3)
    spend_conversation(char_a, rel_tension)
    spend_conversation(char_b, rel_tension)

    return record


def process_reflection(
    char: CharacterState,
    other: CharacterState,
    conv_record: dict,
    relationships: dict,
) -> dict | None:
    conv_text = "\n".join(
        f"{ex['name']}: {ex['text']}" for ex in conv_record["exchanges"]
    )
    prompt = build_reflection_prompt(char, other, conv_text)
    messages = [{"role": "user", "content": prompt}]
    reflection = chat(messages, MAX_TOKENS_REFLECTION)
    print(f"    💭 {char.name}: {reflection[:60]}...")

    episode = {
        "day": conv_record["day"],
        "hour": conv_record["hour"],
        "other": other.id,
        "other_name": other.name,
        "location": conv_record["location"],
        "summary": reflection,
    }
    append_episode(char.id, episode)
    char.working_memory.append(f"[{other.name}] {reflection[:200]}")
    if len(char.working_memory) > 5:
        char.working_memory = char.working_memory[-5:]

    rel_key = tuple(sorted([char.id, other.id]))
    rel = relationships.setdefault(rel_key, {
        "warmth": 0.5, "trust": 0.5, "tension": 0.3, "affection": 0.0,
        "salience": 0.3, "interaction_count": 0,
        "last_interaction_day": 0, "consecutive_conflicts": 0,
        "fatigue_cooldown": 0,
    })
    _ensure_rel_fields(rel)

    village_avg = compute_village_tension(relationships)

    rel_before = dict(rel)  # D-L1: outcome 산출용 스냅샷(가드 무관, 얕은 dict라 비용 무시)
    appraisal = run_appraisal(char, other, conv_text, reflection, rel)

    gossip_result = None
    if appraisal:
        positive, conflict = apply_appraisal(char, other, rel, appraisal, village_avg)
        gossip_result = appraisal.get("gossip")
        if _reputation_matrix:
            valence = appraisal.get("emotional_valence", "중립")
            rep_update = appraisal.get("reputation_update", {})
            update_from_direct_interaction(
                _reputation_matrix, char.id, other.id,
                valence, appraisal.get("relationship", {}),
                conv_record.get("day", 0),
            )
            entry = _reputation_matrix.get(char.id, {}).get(other.id)
            if entry and rep_update:
                entry.competence = max(0.0, min(1.0,
                    entry.competence + rep_update.get("competence_delta", 0.0)))
                entry.integrity = max(0.0, min(1.0,
                    entry.integrity + rep_update.get("integrity_delta", 0.0)))
    else:
        positive, conflict = _adjust_relationship(rel, reflection, village_avg)
        char.fulfill_needs_from_conversation(reflection, positive)
        if _detected_belief_shift(reflection):
            char.shift_belief_toward(other)
        _update_goal_progress(char, reflection)

    # D-L1 판단포획 (옵트인, 가드 미설정 시 decision_log.record 즉시 반환·무영향)
    from village import decision_log
    decision_log.record(
        tick=conv_record.get("day"),  # process_reflection엔 tick 미전달 — day로 근사(MVP)
        decider_id=char.id,
        basis=f"{other.id}와의 대화 반영: {reflection[:200]}",
        choice=appraisal.get("emotional_valence") if appraisal else "keyword_fallback",
        outcome={
            "relationships_delta": {
                k: round(rel.get(k, 0.0) - rel_before.get(k, 0.0), 4)
                for k in ("warmth", "trust", "tension", "affection")
            },
            "realized": True,
        },
        interpretation_status="parsed" if appraisal else "fallback",
        cap_bound="WARMTH_SOFT_CEILING" if appraisal else None,
    )

    # D-G2 경제슬롯 (옵트인, 가드 미설정 시 economy.grant_favor 즉시 반환·무영향)
    # warmth가 실제로 개선됐으면(char의 other에 대한 호감 상승) other가 호의를 준 것으로 관측
    if rel.get("warmth", 0.0) > rel_before.get("warmth", 0.0):
        from village.systems import economy
        economy.grant_favor(other.id, conv_record.get("day", 0))

    rel["salience"] = min(1.0, rel.get("salience", 0.3) + 0.1)
    rel["interaction_count"] = rel.get("interaction_count", 0) + 1
    rel["last_interaction_day"] = conv_record["day"]

    if conflict and rel["tension"] > 0.6:
        rel["consecutive_conflicts"] = rel.get("consecutive_conflicts", 0) + 1
        if rel["consecutive_conflicts"] >= 3:
            rel["salience"] = max(0.0, rel["salience"] - 0.3)
            rel["fatigue_cooldown"] = 5
            rel["consecutive_conflicts"] = 0
            print(f"    ⚡ {char.name} ↔ {other.name}: 피로 쿨다운 발동 (5틱)")
    else:
        rel["consecutive_conflicts"] = 0

    if positive:
        add_warmth(conv_record["location"])
    if conflict:
        add_friction(conv_record["location"])

    update_relationship_summary(char.id, other.id, reflection[:150])

    return gossip_result


def _ensure_rel_fields(rel: dict):
    defaults = {
        "affection": 0.0, "salience": 0.3, "interaction_count": 0,
        "last_interaction_day": 0, "consecutive_conflicts": 0,
        "fatigue_cooldown": 0,
    }
    for k, v in defaults.items():
        if k not in rel:
            rel[k] = v


def _adjust_relationship(rel: dict, reflection: str, village_avg_tension: float) -> tuple[bool, bool]:
    positive = any(w in reflection for w in [
        "도움", "고맙", "신뢰", "좋아", "동맹", "따뜻", "공감",
        "타협", "양보", "이해", "인정", "존중",
    ])
    negative = any(w in reflection for w in [
        "실망", "불신", "짜증", "방해", "거짓", "배신", "분노", "의심",
    ])
    conflict = any(w in reflection for w in [
        "충돌", "반박", "거부", "갈등", "대립", "논쟁",
    ])
    affectionate = any(w in reflection for w in [
        "사랑", "애정", "설레", "끌리", "그리움", "보고싶", "심장", "두근",
        "포옹", "가슴", "영혼", "동반자", "유대", "특별", "소중",
    ])

    inc_mult, dec_mult = get_tension_multipliers(village_avg_tension)

    interaction_count = rel.get("interaction_count", 0)
    # P2: 이중 감쇠 — 상호작용 횟수 + 현재 warmth 수준
    count_damp = 0.5 if interaction_count > 20 else 1.0
    warmth_level_damp = max(0.3, 1.0 - rel.get("warmth", 0.5))  # warmth 0.7 → 0.3배
    dampening = count_damp * warmth_level_damp

    if positive:
        rel["warmth"] = min(1.0, rel["warmth"] + 0.04 * dampening)
        rel["trust"] = min(1.0, rel["trust"] + 0.03 * dampening)
    if negative:
        # P2: 음수 변동은 count_damp만 적용 (하락은 빠르게 유지)
        rel["warmth"] = max(0.0, rel["warmth"] - 0.04 * count_damp)
        rel["trust"] = max(0.0, rel["trust"] - 0.04 * count_damp)

    if conflict:
        rel["tension"] = min(1.0, rel["tension"] + 0.05 * inc_mult * dampening)
    else:
        rel["tension"] = max(0.0, rel["tension"] - 0.03 * dec_mult)

    tension = rel.get("tension", 0.3)
    tension_dampen = max(0.1, 1.0 - tension)

    if affectionate:
        rel["affection"] = min(1.0, rel["affection"] + 0.08 * tension_dampen * dampening)
    elif positive:
        rel["affection"] = min(1.0, rel["affection"] + 0.02 * tension_dampen * dampening)
    if negative or conflict:
        rel["affection"] = max(0.0, rel["affection"] - 0.02)

    apply_soft_ceiling(rel)

    return positive, conflict


def _detected_belief_shift(reflection: str) -> bool:
    return any(w in reflection for w in [
        "생각해보니", "일리가", "인정할", "양보",
        "바꿔야", "다시 생각", "틀렸", "맞는 말",
    ])


def _update_goal_progress(char: CharacterState, reflection: str):
    goal = char.top_goal()
    if not goal:
        return
    progress_words = ["진전", "성공", "달성", "합의", "동의", "승인", "도움"]
    setback_words = ["실패", "거부", "좌절", "불가", "포기", "방해"]
    if any(w in reflection for w in progress_words):
        goal["progress"] = min(1.0, goal["progress"] + 0.03)
    if any(w in reflection for w in setback_words):
        goal["progress"] = max(0.0, goal["progress"] - 0.02)


def run_monologue(char: CharacterState, world: WorldState):
    prompt = build_monologue_prompt(char, world)
    messages = [{"role": "user", "content": prompt}]
    monologue = chat(messages, MAX_TOKENS_MONOLOGUE)
    print(f"  🧠 {char.name} (독백): {monologue[:80]}...")

    char.working_memory.append(f"[독백] {monologue[:200]}")
    if len(char.working_memory) > 5:
        char.working_memory = char.working_memory[-5:]

    episode = {
        "day": world.day,
        "hour": world.hour,
        "other": "self",
        "other_name": "내면",
        "location": char.location,
        "summary": monologue,
    }
    append_episode(char.id, episode)
    spend_monologue(char)
    char.fulfill_needs_from_monologue()
