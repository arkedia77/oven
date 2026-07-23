"""D-C1 제도 슬롯 MVP — 고정 역할목록, 보상추적 전용 결정화. 옵트인(HARMONICITY_INSTITUTION=1).

§E-③(P5/P7) 반영: 역할 분류체계(ROLES)는 고정 큐레이션 — LLM이 새 역할을 발명하지 않는다.
배정(누가 어떤 역할인지)만 관계 데이터에서 규칙으로 도출(생성).
§E-②(신뢰가중치) 반영: 조건 미달 시 role=None으로 조용히 복귀 — 강등·페널티 이벤트 없음.
MEDIATOR는 갈등중재 이벤트 앵커 데이터 부재로 2차 라운드 보류(kee 게이트 동의).
"""
import os

ROLES = ("CONNECTOR", "SUPPORTER")

CONNECTOR_MIN_ACTIVE = 4
CONNECTOR_WARMTH_THRESHOLD = 0.6
SUPPORTER_WARMTH_THRESHOLD = 0.8
SUPPORTER_MIN_INTERACTIONS = 10


def enabled() -> bool:
    return os.environ.get("HARMONICITY_INSTITUTION") == "1"


def _character_relationships(char_id: str, relationships: dict):
    for key, rel in relationships.items():
        if char_id not in key:
            continue
        other_id = key[0] if key[1] == char_id else key[1]
        yield other_id, rel


def _derive_role(char_id: str, relationships: dict) -> str | None:
    rels = list(_character_relationships(char_id, relationships))
    connector_count = sum(1 for _, r in rels if r.get("warmth", 0) > CONNECTOR_WARMTH_THRESHOLD)
    if connector_count >= CONNECTOR_MIN_ACTIVE:
        return "CONNECTOR"
    for _, r in rels:
        if (r.get("warmth", 0) >= SUPPORTER_WARMTH_THRESHOLD
                and r.get("interaction_count", 0) >= SUPPORTER_MIN_INTERACTIONS):
            return "SUPPORTER"
    return None


def recompute_roles(characters: dict, relationships: dict, tick: int, interval: int = 24):
    """interval틱(기본 1일)마다 역할 재계산. 가드 미설정 또는 주기 아니면 무영향."""
    if not enabled():
        return
    if tick % interval != 0:
        return

    from village.persistence.save_load import save_institutions, load_institutions
    from village import decision_log

    data = load_institutions()
    for char_id in characters:
        role = _derive_role(char_id, relationships)
        prev = data.get(char_id)
        if prev != role:
            data[char_id] = role
            # §E-②: role=None 복귀도 강등이 아니라 조건 재평가 결과 — 페널티 필드 없음
            decision_log.record(
                tick=tick,
                decider_id="institution_rule",
                decider_role="정책",
                judgment_type=None,
                basis=f"{char_id} 관계데이터 재계산({interval}틱 주기)",
                choice=role or "None",
                outcome={"role_assigned": role, "previous": prev},
            )
    save_institutions(data)
