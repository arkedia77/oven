"""LLM 구조화출력 기반 Appraisal 엔진 — 키워드 매칭 교체

OCC Appraisal 이론 기반: 대화 텍스트 → LLM이 구조화된 JSON으로
needs/beliefs/relationship/goal delta를 직접 산출.

기존 키워드 매칭 4곳을 통합 대체:
  - _adjust_relationship (conversation.py)
  - fulfill_needs_from_conversation (state.py)
  - _detected_belief_shift (conversation.py)
  - _update_goal_progress (conversation.py)
"""
import json
import re
from village.engine.llm import chat
from village.characters.state import CharacterState


APPRAISAL_SCHEMA = {
    "relationship": {
        "warmth_delta": "float [-0.1, 0.1]",
        "trust_delta": "float [-0.1, 0.1]",
        "tension_delta": "float [-0.1, 0.1]",
        "affection_delta": "float [-0.1, 0.1]",
    },
    "needs": {
        "belonging_delta": "float [-0.1, 0.1]",
        "purpose_delta": "float [-0.1, 0.1]",
        "security_delta": "float [-0.1, 0.1]",
        "recognition_delta": "float [-0.1, 0.1]",
        "autonomy_delta": "float [-0.1, 0.1]",
        "affection_delta": "float [-0.1, 0.1]",
    },
    "belief_shift": "bool",
    "goal_progress_delta": "float [-0.05, 0.05]",
    "emotional_valence": "str: 긍정/부정/혼합/중립",
    "reasoning": "str: 1문장 근거",
}


def build_appraisal_prompt(
    char: CharacterState,
    other: CharacterState,
    conversation_text: str,
    reflection_text: str,
    rel: dict,
) -> str:
    return f"""너는 사회 시뮬레이션의 심리 평가 엔진이다. 아래 대화와 반영문을 분석하여 캐릭터의 내면 상태 변화를 JSON으로 출력해.

== 평가 대상 캐릭터 ==
이름: {char.name}
역할: {char.role}
현재 감정: {char.emotional_state}
현재 욕구 수준: {json.dumps(char.needs, ensure_ascii=False)}
현재 신념: {json.dumps(char.beliefs, ensure_ascii=False)}
현재 목표: {char.goals[0]['description'] if char.goals else '없음'} (진행: {f"{char.goals[0]['progress']:.0%}" if char.goals else 'N/A'})

== 대화 상대 ==
이름: {other.name}
역할: {other.role}

== 현재 관계 ==
호감(warmth): {rel.get('warmth', 0.5):.2f}
신뢰(trust): {rel.get('trust', 0.5):.2f}
긴장(tension): {rel.get('tension', 0.3):.2f}
애정(affection): {rel.get('affection', 0.0):.2f}

== 대화 내용 ==
{conversation_text}

== {char.name}의 반영문 ==
{reflection_text}

== 출력 규칙 ==
- thinking 없이 바로 JSON만 출력. 설명 없이 순수 JSON.
- 모든 delta는 이 대화 한 건의 영향. 과하지 않게.
- 부정문/반어/비유를 정확히 해석해. "도움이 안 됐다"는 부정이다.
- 관계가 이미 극단(0.0 또는 1.0 근처)이면 delta 축소.
- 목표와 무관한 대화면 goal_progress_delta = 0.
- 혼합 감정도 가능. 한 대화에서 warmth_delta > 0이면서 tension_delta > 0일 수 있음.

```json
{{
  "relationship": {{
    "warmth_delta": 0.00,
    "trust_delta": 0.00,
    "tension_delta": 0.00,
    "affection_delta": 0.00
  }},
  "needs": {{
    "belonging_delta": 0.00,
    "purpose_delta": 0.00,
    "security_delta": 0.00,
    "recognition_delta": 0.00,
    "autonomy_delta": 0.00,
    "affection_delta": 0.00
  }},
  "belief_shift": false,
  "goal_progress_delta": 0.00,
  "emotional_valence": "중립",
  "gossip": {{
    "shared": false,
    "about": null,
    "valence": "중립"
  }},
  "reputation_update": {{
    "competence_delta": 0.00,
    "integrity_delta": 0.00
  }},
  "reasoning": "..."
}}
```

== gossip 필드 규칙 ==
- 대화 중 제3자에 대한 이야기가 오갔으면 shared=true, about=제3자 ID(영문), valence=긍정/부정/중립
- 제3자 이야기가 없었으면 shared=false, about=null
- 가능한 캐릭터 ID: seo_jin, aria, joon_ho, luna, min_ah, tae_sik, nexus, ha_yeon, sang_woo, ye_eun
== reputation_update 규칙 ==
- 이 대화를 통해 상대방의 능력(competence)이나 도덕성(integrity)에 대한 인상이 바뀌었으면 delta 기입
- 범위: [-0.05, 0.05]. 변화 없으면 0."""


def parse_appraisal_response(response: str) -> dict | None:
    json_match = re.search(r'\{[\s\S]*\}', response)
    if not json_match:
        return None
    try:
        data = json.loads(json_match.group())
        _validate_and_clamp(data)
        return data
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _validate_and_clamp(data: dict):
    for key in ("warmth_delta", "trust_delta", "tension_delta", "affection_delta"):
        val = data.get("relationship", {}).get(key, 0.0)
        data["relationship"][key] = max(-0.1, min(0.1, float(val)))

    for key in ("belonging_delta", "purpose_delta", "security_delta",
                "recognition_delta", "autonomy_delta", "affection_delta"):
        val = data.get("needs", {}).get(key, 0.0)
        data["needs"][key] = max(-0.1, min(0.1, float(val)))

    data["goal_progress_delta"] = max(-0.05, min(0.05, float(data.get("goal_progress_delta", 0.0))))
    data["belief_shift"] = bool(data.get("belief_shift", False))

    if "gossip" not in data:
        data["gossip"] = {"shared": False, "about": None, "valence": "중립"}
    else:
        g = data["gossip"]
        g["shared"] = bool(g.get("shared", False))
        g["about"] = g.get("about") or None
        g["valence"] = g.get("valence", "중립")

    if "reputation_update" not in data:
        data["reputation_update"] = {"competence_delta": 0.0, "integrity_delta": 0.0}
    else:
        ru = data["reputation_update"]
        ru["competence_delta"] = max(-0.05, min(0.05, float(ru.get("competence_delta", 0.0))))
        ru["integrity_delta"] = max(-0.05, min(0.05, float(ru.get("integrity_delta", 0.0))))


def run_appraisal(
    char: CharacterState,
    other: CharacterState,
    conversation_text: str,
    reflection_text: str,
    rel: dict,
) -> dict | None:
    prompt = build_appraisal_prompt(char, other, conversation_text, reflection_text, rel)
    messages = [{"role": "user", "content": prompt}]
    # max_tokens 2560 (kee 승인 2026-07-30). 제약이 2단으로 쌓여 있었다:
    #   ① llama-server 슬롯 컨텍스트(= ctx-size/parallel)가 2048이라 애초에 도달 불가
    #      → --parallel 4→2 로 슬롯 4096 확보(선행 조치)
    #   ② 그 위에서도 max_tokens 1536은 부족 — reasoning이 예산을 먹고 JSON이 중도 절단
    # 실측: mt=1536 → completion 1536 소진·PARSE FAIL / mt=3072 → finish=stop·completion 1363·PARSE OK
    # 2560 근거: 필요치 1363 + reasoning 변동폭(3,429~4,982자) 여유. 슬롯 예산 980+2560=3,540 < 4,096.
    # ※ 이 값을 올릴 때는 반드시 `프롬프트 + max_tokens < 슬롯 n_ctx`를 먼저 확인할 것(3072는 4,052로 밀착).
    response = chat(messages, max_tokens=2560, temperature=0.3)

    appraisal = parse_appraisal_response(response)
    if appraisal:
        print(f"    🧠 appraisal [{char.name}]: {appraisal.get('emotional_valence', '?')} "
              f"— {appraisal.get('reasoning', '')[:60]}")
    else:
        print(f"    ⚠️ appraisal 파싱 실패 [{char.name}], 키워드 fallback")

    return appraisal


def apply_appraisal(
    char: CharacterState,
    other: CharacterState,
    rel: dict,
    appraisal: dict,
    village_avg_tension: float = 0.4,
):
    from village.systems.homeostasis import get_tension_multipliers, apply_warmth_tension_constraint, apply_soft_ceiling

    interaction_count = rel.get("interaction_count", 0)
    # P2: 이중 감쇠 — 상호작용 횟수 + 현재 warmth 수준
    count_damp = 0.5 if interaction_count > 20 else 1.0
    warmth_level_damp = max(0.3, 1.0 - rel.get("warmth", 0.5))  # warmth 0.7 → 0.3배
    dampening = count_damp * warmth_level_damp

    inc_mult, dec_mult = get_tension_multipliers(village_avg_tension)

    rd = appraisal["relationship"]
    # P2: 양수 delta에만 dampening 적용, 음수 delta는 원래 속도 유지
    w_delta = rd["warmth_delta"]
    t_delta_trust = rd["trust_delta"]
    rel["warmth"] = max(0.0, min(1.0, rel["warmth"] + w_delta * (dampening if w_delta > 0 else count_damp)))
    rel["trust"] = max(0.0, min(1.0, rel["trust"] + t_delta_trust * (dampening if t_delta_trust > 0 else count_damp)))

    t_delta = rd["tension_delta"]
    if t_delta > 0:
        rel["tension"] = min(1.0, rel["tension"] + t_delta * inc_mult * dampening)
    else:
        rel["tension"] = max(0.0, rel["tension"] + t_delta * dec_mult)

    tension_dampen = max(0.1, 1.0 - rel["tension"])
    rel["affection"] = max(0.0, min(1.0, rel["affection"] + rd["affection_delta"] * tension_dampen * dampening))

    apply_warmth_tension_constraint(rel)
    apply_soft_ceiling(rel)

    nd = appraisal["needs"]
    need_map = {
        "belonging_delta": "belonging",
        "purpose_delta": "purpose",
        "security_delta": "security",
        "recognition_delta": "recognition",
        "autonomy_delta": "autonomy",
        "affection_delta": "affection",
    }
    for delta_key, need_key in need_map.items():
        if need_key in char.needs:
            char.needs[need_key] = max(0.0, min(1.0, char.needs[need_key] + nd[delta_key]))

    if appraisal["belief_shift"]:
        char.shift_belief_toward(other)

    goal_delta = appraisal["goal_progress_delta"]
    if goal_delta != 0 and char.goals:
        goal = char.top_goal()
        if goal:
            goal["progress"] = max(0.0, min(1.0, goal["progress"] + goal_delta))

    valence = appraisal.get("emotional_valence", "중립")
    positive = valence in ("긍정", "혼합")
    conflict = valence == "부정" and rd["tension_delta"] > 0
    return positive, conflict
