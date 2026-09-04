"""항상성 컨트롤러 — 마을 전체 tension 자기조절"""

TARGET_TENSION = 0.4
HIGH_THRESHOLD = 0.5
LOW_THRESHOLD = 0.3


def compute_village_tension(relationships: dict) -> float:
    tensions = [r.get("tension", 0.3) for r in relationships.values()]
    if not tensions:
        return TARGET_TENSION
    return sum(tensions) / len(tensions)


def get_tension_multipliers(village_avg: float) -> tuple[float, float]:
    """Returns (increase_mult, decrease_mult) for homeostatic adjustment."""
    if village_avg > HIGH_THRESHOLD:
        overshoot = min(1.0, (village_avg - HIGH_THRESHOLD) / 0.3)
        return 1.0 - overshoot * 0.5, 1.0 + overshoot * 0.5
    elif village_avg < LOW_THRESHOLD:
        undershoot = min(1.0, (LOW_THRESHOLD - village_avg) / 0.2)
        return 1.0 + undershoot * 0.5, 1.0 - undershoot * 0.5
    return 1.0, 1.0


def apply_warmth_tension_constraint(rel: dict):
    """warmth가 높으면 tension 상한 제한 (P1.1: 완화)."""
    warmth = rel.get("warmth", 0.5)
    if warmth > 0.7:
        max_tension = 0.5 + (1.0 - warmth) * 0.5
        rel["tension"] = min(rel["tension"], max_tension)


WARMTH_SOFT_CEILING = 0.85   # P2: 특별 이벤트 없이 도달 가능한 상한
TRUST_SOFT_CEILING = 0.85


def decay_relationships(relationships: dict):
    """매 틱 자연 감쇠 (P2: warmth/trust 자연 감쇠 추가)."""
    for rel in relationships.values():
        rel["tension"] = max(0.0, rel["tension"] - 0.002)
        rel["salience"] = max(0.0, rel.get("salience", 0.3) - 0.01)

        # P2: warmth 자연 감쇠 — 0.5(기준선) 이상일수록 강하게 끌어내림
        warmth = rel.get("warmth", 0.5)
        if warmth > 0.5:
            excess = warmth - 0.5
            rel["warmth"] = max(0.5, warmth - excess * 0.008)

        # P2: trust 자연 감쇠 — warmth와 동일 로직, 약간 느리게
        trust = rel.get("trust", 0.5)
        if trust > 0.5:
            excess = trust - 0.5
            rel["trust"] = max(0.5, trust - excess * 0.006)

        cooldown = rel.get("fatigue_cooldown", 0)
        if cooldown > 0:
            rel["fatigue_cooldown"] = cooldown - 1


def apply_soft_ceiling(rel: dict):
    """P2: warmth/trust에 소프트 실링 적용.

    SOFT_CEILING(0.85) 초과 시 초과분을 30%로 압축.
    예: 실링=0.85, 현재=0.90 → 0.85 + 0.05*0.3 = 0.865
    특별 이벤트(affection > 0.5 등)는 실링을 완화.
    """
    affection = rel.get("affection", 0.0)
    # 깊은 애정 관계는 실링 완화 (최대 0.95)
    warmth_ceil = min(0.95, WARMTH_SOFT_CEILING + affection * 0.2)
    trust_ceil = min(0.95, TRUST_SOFT_CEILING + affection * 0.2)

    warmth = rel.get("warmth", 0.5)
    if warmth > warmth_ceil:
        excess = warmth - warmth_ceil
        rel["warmth"] = warmth_ceil + excess * 0.3

    trust = rel.get("trust", 0.5)
    if trust > trust_ceil:
        excess = trust - trust_ceil
        rel["trust"] = trust_ceil + excess * 0.3


def apply_reputation_to_relationships(relationships: dict, reputation_matrix: dict):
    """P1.2: 평판(integrity)이 낮으면 관계(warmth/trust) 점진 하락.

    양방향 검사: A→B, B→A 중 더 낮은 integrity 기준으로 침식.
    confidence < 0.3이면 무시 (불확실한 평판은 영향 없음).
    """
    for pair_key, rel in relationships.items():
        if isinstance(pair_key, tuple):
            a, b = pair_key
        else:
            parts = pair_key.split("|")
            if len(parts) != 2:
                continue
            a, b = parts

        worst_integrity = 1.0

        for observer, target in [(a, b), (b, a)]:
            entry = reputation_matrix.get(observer, {}).get(target)
            if not entry:
                continue
            confidence = entry.confidence if hasattr(entry, 'confidence') else 0.3
            if confidence < 0.3:
                continue
            integrity = entry.integrity if hasattr(entry, 'integrity') else 0.5
            if integrity < worst_integrity:
                worst_integrity = integrity

        if worst_integrity >= 0.5:
            continue

        if worst_integrity < 0.1:
            erosion_w, erosion_t = 0.003, 0.004
        elif worst_integrity < 0.3:
            erosion_w, erosion_t = 0.002, 0.003
        else:
            erosion_w, erosion_t = 0.001, 0.001

        rel["warmth"] = max(0.0, rel["warmth"] - erosion_w)
        rel["trust"] = max(0.0, rel["trust"] - erosion_t)
