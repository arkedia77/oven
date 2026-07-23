"""하모니 시티 #02 Ecosystem — 메인 루프"""
import sys
import time
from datetime import datetime
from collections import defaultdict

from village.config import (
    TICK_SECONDS, TICKS_PER_DAY, SOLO_MONOLOGUES_PER_TICK,
    RETROSPECTIVE_INTERVAL_DAYS, MAX_TOKENS_RETROSPECTIVE,
)
from village.safety_rail import SafetyHalt  # D-S1: except 절에서 필요, 최상단 임포트
from village.characters.definitions import CHARACTERS
from village.characters.state import CharacterState
from village.world.state import WorldState
from village.world.time_system import format_village_time, village_hour_to_period
from village.world.locations import LOCATIONS
from village.interaction.encounter import (
    determine_locations, select_encounters, select_solo_characters,
    set_encounter_context,
)
from village.interaction.conversation import (
    run_conversation, process_reflection, run_monologue,
    set_conversation_reputation,
)
from village.interaction.prompts import set_social_context
from village.persistence.save_load import (
    save_all, load_world_state, load_character_state, load_relationships,
    save_need_history, load_need_history,
    save_belief_history, load_belief_history,
    save_relationship_history, load_relationship_history,
    save_atmosphere, load_atmosphere,
    save_reputation, load_reputation,
    save_knowledge_base, load_knowledge_base,
)
from village.systems.homeostasis import (
    decay_relationships, apply_reputation_to_relationships,
)
from village.systems.social_energy import reset_daily_energy
from village.systems.location_atmosphere import decay_all as decay_atmosphere, get_state as get_atm_state, load_state as load_atm_state
from village.systems.events import check_events
from village.systems.reputation import (
    init_reputation_matrix, daily_decay as reputation_daily_decay,
    update_from_direct_interaction, update_from_gossip, update_from_observation,
    ReputationMatrix,
)
from village.systems.information import (
    init_info_registry, init_knowledge_base,
    propagate_info, try_observation, select_shareable_info,
    create_dynamic_rumor, restore_rumor_counter,
    KnowledgeBase, InfoRegistry,
)
from village.engine.llm import chat


need_history: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
belief_history: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
relationship_history: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

reputation_matrix: ReputationMatrix = {}
knowledge_base: KnowledgeBase = {}
info_registry: InfoRegistry = {}


def initialize_or_resume() -> tuple:
    global need_history, reputation_matrix, knowledge_base, info_registry

    world = load_world_state()
    relationships = load_relationships()

    characters = {}
    for char_id in CHARACTERS:
        loaded = load_character_state(char_id)
        if loaded:
            characters[char_id] = loaded
        else:
            characters[char_id] = CharacterState.from_definition(char_id)

    for rel in relationships.values():
        defaults = {
            "affection": 0.0, "salience": 0.3, "interaction_count": 0,
            "last_interaction_day": 0, "consecutive_conflicts": 0,
            "fatigue_cooldown": 0,
        }
        for k, v in defaults.items():
            if k not in rel:
                rel[k] = v

    saved_history = load_need_history()
    if saved_history:
        for char_id, needs_dict in saved_history.items():
            for need_key, values in needs_dict.items():
                need_history[char_id][need_key] = values

    saved_belief_hist = load_belief_history()
    if saved_belief_hist:
        for char_id, beliefs_dict in saved_belief_hist.items():
            for bkey, values in beliefs_dict.items():
                belief_history[char_id][bkey] = values

    saved_rel_hist = load_relationship_history()
    if saved_rel_hist:
        for pair_key, metrics_dict in saved_rel_hist.items():
            for mkey, values in metrics_dict.items():
                relationship_history[pair_key][mkey] = values

    saved_atm = load_atmosphere()
    if saved_atm:
        load_atm_state(saved_atm)

    # P1: 평판/정보 시스템 로드 또는 초기화
    saved_rep = load_reputation()
    if saved_rep:
        reputation_matrix.update(saved_rep)
    else:
        reputation_matrix.update(init_reputation_matrix(list(CHARACTERS.keys())))

    saved_kb = load_knowledge_base()
    if saved_kb:
        kb, reg = saved_kb
        knowledge_base.update(kb)
        info_registry.update(reg)
    else:
        info_registry.update(init_info_registry())
        knowledge_base.update(init_knowledge_base(info_registry))

    restore_rumor_counter(info_registry)

    # 신규 캐릭터 자동 통합 (기존 세이브에 없는 캐릭터 감지)
    all_ids = list(CHARACTERS.keys())
    _integrate_new_characters(all_ids, characters, relationships,
                              reputation_matrix, knowledge_base, info_registry)

    # 컨텍스트 주입
    set_social_context(reputation_matrix, knowledge_base)
    set_encounter_context(reputation_matrix, knowledge_base)
    set_conversation_reputation(reputation_matrix)

    return world, characters, relationships


def _integrate_new_characters(
    all_ids: list[str],
    characters: dict,
    relationships: dict,
    reputation_matrix: dict,
    knowledge_base: dict,
    info_registry: dict,
):
    """기존 세이브에 없는 신규 캐릭터를 관계/평판/정보 시스템에 통합."""
    from village.systems.reputation import ReputationEntry
    from village.systems.information import InfoItem, _estimate_sensitivity

    new_chars = []
    for cid in all_ids:
        if cid not in reputation_matrix:
            new_chars.append(cid)

    if not new_chars:
        return

    for new_id in new_chars:
        print(f"  🆕 신규 캐릭터 감지: {CHARACTERS[new_id]['name']} ({new_id})")

        # 1) 관계: 모든 기존+신규 캐릭터와 초기 관계 생성
        for other_id in all_ids:
            if other_id == new_id:
                continue
            pair = tuple(sorted([new_id, other_id]))
            if pair not in relationships:
                relationships[pair] = {
                    "warmth": 0.3, "trust": 0.3, "tension": 0.1,
                    "affection": 0.0, "salience": 0.5,
                    "interaction_count": 0, "last_interaction_day": 0,
                    "consecutive_conflicts": 0, "fatigue_cooldown": 0,
                }

        # 2) 평판: 신규→기존, 기존→신규 엔트리 생성
        reputation_matrix[new_id] = {}
        for other_id in all_ids:
            if other_id == new_id:
                continue
            reputation_matrix[new_id][other_id] = ReputationEntry()
            if other_id in reputation_matrix:
                reputation_matrix[other_id][new_id] = ReputationEntry()

        # 3) 정보: 신규 캐릭터의 비밀을 레지스트리에 추가
        secret = CHARACTERS[new_id].get("secret", "")
        if secret:
            secret_id = f"secret_{new_id}"
            if secret_id not in info_registry:
                item = InfoItem(
                    id=secret_id,
                    category="secret",
                    subject=new_id,
                    content=secret,
                    truth_value=1.0,
                    sensitivity=_estimate_sensitivity(new_id),
                    origin_day=0,
                    source="system",
                )
                info_registry[secret_id] = item

        # 4) 지식: 신규 캐릭터는 자기 비밀만 알고 시작
        if new_id not in knowledge_base:
            knowledge_base[new_id] = {}
            secret_id = f"secret_{new_id}"
            if secret_id in info_registry:
                knowledge_base[new_id][secret_id] = info_registry[secret_id]

    print(f"  ✅ {len(new_chars)}명 통합 완료")


def run_tick(world: WorldState, characters: dict, relationships: dict):
    period = village_hour_to_period(world.hour)
    print(f"\n{'='*60}")
    print(f"  Day {world.day} | {format_village_time(world.hour)} | Tick {world.tick}")
    print(f"{'='*60}")

    determine_locations(characters, world.hour, tick=world.tick)
    loc_summary = {}
    for cid, char in characters.items():
        loc_summary.setdefault(char.location, []).append(char.name)
    for loc, names in loc_summary.items():
        if loc != "residential" and names:
            loc_name = LOCATIONS.get(loc, {}).get("name", loc)
            print(f"  📍 {loc_name}: {', '.join(names)}")

    # P1: 같은 장소에서 관찰 기회
    _process_observations(characters, world)

    encounters = select_encounters(characters, relationships, world.hour, world.day)
    encounter_participants = set()

    for char_a_id, char_b_id in encounters:
        char_a = characters[char_a_id]
        char_b = characters[char_b_id]
        encounter_participants.update([char_a_id, char_b_id])

        conv = run_conversation(char_a, char_b, relationships, world)
        gossip_a = process_reflection(char_a, char_b, conv, relationships)
        gossip_b = process_reflection(char_b, char_a, conv, relationships)

        _process_post_conversation(
            char_a_id, char_b_id, relationships, world.day,
            gossip_a, gossip_b,
        )

    if period not in ("late_night",):
        solo_ids = select_solo_characters(characters, encounter_participants, SOLO_MONOLOGUES_PER_TICK)
        for solo_id in solo_ids:
            run_monologue(characters[solo_id], world)

    for char in characters.values():
        char.decay_needs(0.005)
        if char.location == "residential":
            char.fulfill_needs_from_alone_time()
        char.update_emotional_state()

    decay_relationships(relationships)
    apply_reputation_to_relationships(relationships, reputation_matrix)
    decay_atmosphere()

    if world.is_end_of_day():
        _end_of_day(world, characters, relationships)

    save_all(world, characters, relationships)
    save_atmosphere(get_atm_state())
    save_reputation(reputation_matrix)
    save_knowledge_base(knowledge_base, info_registry)


def _process_observations(characters: dict, world: WorldState):
    loc_groups: dict[str, list[str]] = {}
    for cid, char in characters.items():
        if char.location != "residential":
            loc_groups.setdefault(char.location, []).append(cid)

    for loc, char_ids in loc_groups.items():
        if len(char_ids) < 2:
            continue
        for i in range(len(char_ids)):
            for j in range(len(char_ids)):
                if i == j:
                    continue
                observed = try_observation(
                    knowledge_base, info_registry,
                    char_ids[i], char_ids[j],
                    same_location=True, day=world.day,
                )
                if observed:
                    print(f"  👁️ {characters[char_ids[i]].name}이(가) "
                          f"{characters[char_ids[j]].name}에 대해 무언가 발견!")
                    update_from_observation(
                        reputation_matrix, char_ids[i], char_ids[j],
                        "secret_exposed", world.day,
                    )


def _process_post_conversation(
    char_a_id: str, char_b_id: str,
    relationships: dict, day: int,
    gossip_a: dict | None = None,
    gossip_b: dict | None = None,
):
    import random
    from village.characters.definitions import CHARACTERS as CHAR_DEFS

    rel_key = tuple(sorted([char_a_id, char_b_id]))
    rel = relationships.get(rel_key, {})
    trust_ab = rel.get("trust", 0.5)

    # P1.1: 동적 소문 생성 (appraisal gossip 활용)
    for gossip, speaker, listener in [
        (gossip_a, char_a_id, char_b_id),
        (gossip_b, char_b_id, char_a_id),
    ]:
        if not gossip or not gossip.get("shared") or not gossip.get("about"):
            continue
        about = gossip["about"]
        valence = gossip.get("valence", "중립")
        if about not in CHAR_DEFS:
            continue
        rumor = create_dynamic_rumor(
            knowledge_base, info_registry,
            speaker, listener, about, valence, day,
        )
        if rumor:
            teller_entry = reputation_matrix.get(listener, {}).get(speaker, None)
            teller_int = teller_entry.integrity if teller_entry else 0.5
            update_from_gossip(
                reputation_matrix, listener, about, valence, teller_int,
            )
            update_from_gossip(
                reputation_matrix, speaker, about, valence, 0.7,
            )
            subject_name = CHAR_DEFS.get(about, {}).get("name", about)
            print(f"  💬🗣️ 동적소문: {speaker}↔{listener}가 {subject_name}에 대해 {valence} 이야기")

    # 기존 비밀/정보 전파 (A→B, B→A)
    for sharer, receiver in [(char_a_id, char_b_id), (char_b_id, char_a_id)]:
        shareable = select_shareable_info(knowledge_base, sharer, receiver, trust_ab)
        if not shareable:
            continue
        share_chance = trust_ab * 0.3
        if random.random() >= share_chance:
            continue
        info = random.choice(shareable)
        propagated = propagate_info(
            knowledge_base, info_registry,
            sharer, receiver, info.id, day,
        )
        if not propagated:
            continue
        teller_entry = reputation_matrix.get(receiver, {}).get(sharer, None)
        teller_int = teller_entry.integrity if teller_entry else 0.5
        valence = info_registry.get(info.id, info)
        gossip_valence = "부정" if info.sensitivity > 0.7 else "중립"
        update_from_gossip(
            reputation_matrix, receiver, info.subject,
            gossip_valence, teller_int,
        )
        subject_name = CHAR_DEFS.get(info.subject, {}).get("name", info.subject)
        print(f"  🗣️ 소문 전파: → {receiver}가 {subject_name}에 대해 들음")


def _end_of_day(world: WorldState, characters: dict, relationships: dict):
    print(f"\n  🌙 Day {world.day} 종료 — 기억 통합 중...")

    for char_id, char in characters.items():
        for key, val in char.needs.items():
            need_history[char_id][key].append(val)
            if len(need_history[char_id][key]) > 60:
                need_history[char_id][key] = need_history[char_id][key][-60:]
        if char.beliefs:
            for bkey, bval in char.beliefs.items():
                belief_history[char_id][bkey].append(bval)
                if len(belief_history[char_id][bkey]) > 60:
                    belief_history[char_id][bkey] = belief_history[char_id][bkey][-60:]

    for pair_key, rel in relationships.items():
        str_key = f"{pair_key[0]}|{pair_key[1]}" if isinstance(pair_key, tuple) else pair_key
        for mkey in ("warmth", "trust", "tension", "affection"):
            relationship_history[str_key][mkey].append(rel.get(mkey, 0.0))
            if len(relationship_history[str_key][mkey]) > 60:
                relationship_history[str_key][mkey] = relationship_history[str_key][mkey][-60:]

    events = check_events(world, characters, relationships, need_history)

    for char in characters.values():
        char.today_interactions = []
        defn = CHARACTERS[char.id]
        for key in char.needs:
            floor = defn["needs"].get(key, 0.5) * 0.4
            char.needs[key] = max(char.needs[key], floor)
            char.needs[key] = min(1.0, char.needs[key] + 0.08)
        reset_daily_energy(char)

    for event in events:
        if event["type"] == "confrontation":
            for pair_key, rel in relationships.items():
                chars = event.get("characters", [])
                if isinstance(pair_key, tuple):
                    a, b = pair_key
                else:
                    a, b = pair_key.split("|")
                if set([a, b]) == set(chars):
                    rel["tension"] = max(0.0, rel["tension"] - event.get("tension_release", 0.25))

        injection = event.get("prompt_injection")
        if injection:
            target_id = event.get("character")
            if target_id and target_id in characters:
                targets = [characters[target_id]]
            elif not target_id:
                targets = list(characters.values())
            else:
                targets = []
            for char in targets:
                char.working_memory.append(f"[내면] {injection}")
                if len(char.working_memory) > 5:
                    char.working_memory = char.working_memory[-5:]

    if world.day % RETROSPECTIVE_INTERVAL_DAYS == 0:
        _run_retrospectives(characters, world)

    if world.day % 10 == 0:
        for char in characters.values():
            char.adapt_need_importance(dict(need_history.get(char.id, {})))

    # P1: 평판 일일 감쇠
    reputation_daily_decay(reputation_matrix)

    save_need_history(dict(need_history))
    save_belief_history(dict(belief_history))
    save_relationship_history(dict(relationship_history))

    print(f"  ✓ Day {world.day + 1} 시작 준비 완료")


def _run_retrospectives(characters: dict, world: WorldState):
    print(f"\n  📝 {RETROSPECTIVE_INTERVAL_DAYS}일 회고 세션...")
    for char in characters.values():
        recent_memories = "\n".join(char.working_memory[-5:]) if char.working_memory else "(기억 없음)"
        prompt = (
            f"너는 '{char.name}'이다. {char.persona}\n\n"
            f"지난 {RETROSPECTIVE_INTERVAL_DAYS}일을 돌아봐.\n"
            f"최근 기억:\n{recent_memories}\n\n"
            f"thinking 없이 한국어 2-3문장으로 답해:\n"
            f"- 나는 어떻게 변했나?\n"
            f"- 가장 인상적이었던 사람이나 사건은?\n"
            f"- 앞으로의 나는 어떤 사람이 되고 싶은가?"
        )
        messages = [{"role": "user", "content": prompt}]
        retrospective = chat(messages, MAX_TOKENS_RETROSPECTIVE)
        char.persona_addendum = retrospective[:200]
        print(f"    📖 {char.name}: {retrospective[:60]}...")


def _save_full(world, characters, relationships):
    """전체 상태 영속화 — KeyboardInterrupt/검증런 종료 시 공통 사용."""
    save_all(world, characters, relationships)
    save_need_history(dict(need_history))
    save_atmosphere(get_atm_state())
    save_reputation(reputation_matrix)
    save_knowledge_base(knowledge_base, info_registry)


def main(max_ticks: int = None, fast: bool = False):
    """라이브: main()  — 무한루프 + 실시간 틱 대기.
    검증런: main(max_ticks=N, fast=True) — N틱 실행 후 저장·종료, 틱 대기 생략."""
    print("=" * 60)
    print("🏙️  하모니 시티 #02 Ecosystem + P1.3 (외부인 실험)")
    print(f"   주민: {len(CHARACTERS)}명")
    print(f"   시간 압축: 실시간 {TICK_SECONDS}초 = 마을 1시간")
    print(f"   틱/일: {TICKS_PER_DAY}")
    if max_ticks is not None:
        print(f"   [검증런] max_ticks={max_ticks}, fast={fast}")
    print(f"   시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    world, characters, relationships = initialize_or_resume()
    print(f"   상태: Day {world.day}, {format_village_time(world.hour)}, Tick {world.tick}")
    print(f"   P1: 평판 매트릭스 {len(reputation_matrix)}명, "
          f"정보 {sum(len(v) for v in knowledge_base.values())}건 로드")

    # A-4: 개입 파이프 초기화 (spec/inbox 미설정 시 no-op → 라이브 무영향)
    from village import config, intervention
    intervention.init(config.DATA_DIR)

    ticks_done = 0
    try:
        while True:
            tick_start = time.time()
            world.advance_tick()
            # A-4: 개입 적용(예약 spec + inbox) — run_tick 앞이라 이번 틱 encounter/대화에 즉시 반영
            n_iv = intervention.apply_pending(
                world, characters, relationships,
                reputation_matrix, knowledge_base, info_registry,
            )
            if n_iv:
                print(f"  ⚡ 개입 {n_iv}건 적용 (tick {world.tick})")
            run_tick(world, characters, relationships)
            ticks_done += 1
            # 동시성 실측: 틱 wall-clock + LLM 대기/엔진 분리 기록(옵트인, 무영향)
            from village import profiling
            profiling.record_tick(world.tick, world.day, time.time() - tick_start)

            # D-S1 안전레일: 킬스위치 판정(가드 무관 무영향, 발동은 옵트인) + 스냅샷(옵트인)
            from village import safety_rail
            safety_rail.check_kill_switch()  # 임계 초과 시 SafetyHalt — 아래 except에서 처리
            safety_rail.reset_window()
            safety_rail.maybe_snapshot(world.tick)

            if max_ticks is not None and ticks_done >= max_ticks:
                print(f"\n  [검증런] {ticks_done}틱 완료 — 상태 저장 후 종료")
                _save_full(world, characters, relationships)
                return

            if fast:
                continue  # 검증런: 틱 대기 생략

            elapsed = time.time() - tick_start
            wait = max(0, TICK_SECONDS - elapsed)
            if wait > 0:
                print(f"\n  ⏱️ 다음 틱까지 {wait:.0f}초 대기...", flush=True)
                deadline = time.time() + wait
                while time.time() < deadline:
                    time.sleep(min(10, deadline - time.time()))
    except KeyboardInterrupt:
        print("\n\n🛑 시뮬레이션 중단 — 상태 저장 중...")
        _save_full(world, characters, relationships)
        print("✓ 저장 완료. 재시작하면 이어서 진행됩니다.")
        sys.exit(0)
    except SafetyHalt as e:
        print(f"\n\n🔴 안전레일 발동 — {e}\n   상태 저장 중...")
        _save_full(world, characters, relationships)
        print("✓ 저장 완료. 원인 확인 후 수동 재기동 필요(watchdog 자동재기동은 그대로 걸림 — 필요시 task DISABLE).")
        sys.exit(1)


if __name__ == "__main__":
    main()
