"""D-A1 자율경계 확장 MVP — 위치/방문 선택을 LLM 판단으로. 옵트인(HARMONICITY_AUTONOMY_LOCATION=1),
미설정 시 encounter.py의 기존 20% 랜덤 분기가 그대로 동작(무영향).

스캐폴딩 원칙(kee 게이트 승인): 컨트롤러는 니즈·목표·후보 장소만 관측 가능하게 제공 — 실제 선택은 LLM.
형식이탈(유효 장소 밖 응답) 시 안전 fallback = 기존 스크립트 로직 그대로(kee 게이트 조건1).
관계수치 변경 로직은 이 모듈이 건드리지 않는다(kee 게이트 조건2, encounter.py의 위치 배정에만 관여).
"""
import os
import re

from village.world.locations import LOCATIONS


def autonomy_enabled() -> bool:
    return os.environ.get("HARMONICITY_AUTONOMY_LOCATION") == "1"


def _build_prompt(char, characters, period) -> str:
    need_id, need_val = char.top_unmet_need()
    goal = char.top_goal()
    goal_desc = goal["description"] if goal else "없음"
    allies = goal.get("allies", []) if goal else []

    loc_lines = []
    for loc_id, info in LOCATIONS.items():
        if loc_id == "residential":
            continue
        likely_there = [
            characters[a].name for a in allies
            if a in characters and characters[a].get_location(period) == loc_id
        ]
        extra = f" (거기 있을 것 같은 사람: {', '.join(likely_there)})" if likely_there else ""
        loc_lines.append(f"- {loc_id}: {info['name']} — {info['vibe']}{extra}")

    return f"""너는 {char.name}({char.role})다. 지금 이 시간대에 어디로 갈지 스스로 정해.

너의 현재 상태:
- 가장 채워지지 않은 욕구: {need_id} ({need_val:.2f})
- 목표: {goal_desc}

갈 수 있는 곳:
{chr(10).join(loc_lines)}
- residential: 집 — 혼자 쉬거나 성찰

너의 성격과 목표, 욕구를 고려해서 지금 어디로 가고 싶은지 정해. thinking 없이 바로 장소 id 하나만 출력해(예: plaza)."""


def choose_location(char, characters, period, fallback_fn):
    """LLM에게 위치 선택을 맡긴다. 형식이탈 시 fallback_fn()으로 안전 복귀(kee 게이트 조건1).

    fallback_fn: () -> str|None — 기존 스크립트 로직(20% 랜덤 ally 방문)을 그대로 호출하는 콜백.
    반환: (location, decision_meta) — decision_meta는 decision_log 기록용 dict.
    """
    from village.engine.llm import chat

    need_id, need_val = char.top_unmet_need()
    goal = char.top_goal()
    valid_ids = set(LOCATIONS.keys())

    prompt = _build_prompt(char, characters, period)
    # max_tokens=512: 이 모델은 "thinking 없이" 지시에도 reasoning_content를 먼저 채우는
    # 경향이 있어(appraisal.py와 동일 현상), 짧은 예산은 finish_reason=length로 content
    # 공백을 유발한다(실측: 20~1024 전부 실패, "thinking 없이" 문구+512 조합에서 성공).
    response = chat([{"role": "user", "content": prompt}], max_tokens=512, temperature=0.7)
    candidate = re.sub(r"[^a-z_]", "", response.strip().lower())

    if candidate in valid_ids:
        return candidate, {
            "basis": f"top_unmet_need={need_id}({need_val:.2f}), goal={goal['description'] if goal else None}",
            "alternatives_considered": sorted(valid_ids),
            "choice": candidate,
            "interpretation_status": "parsed",
        }

    fallback_loc = fallback_fn()
    return fallback_loc, {
        "basis": f"LLM 응답 형식이탈(안전 fallback 발동): {response[:50]!r}",
        "alternatives_considered": sorted(valid_ids),
        "choice": "format_deviation_fallback",
        "interpretation_status": "fallback",
    }
