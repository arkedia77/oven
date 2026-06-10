"""평판 시스템 — 삼자 사회 역학 (P1)

각 캐릭터가 다른 모든 캐릭터에 대해 독립적 평판을 갖는다.
관계(warmth/trust)와 달리 간접 정보(소문/목격)로도 형성됨.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class ReputationEntry:
    competence: float = 0.5
    integrity: float = 0.5
    warmth: float = 0.5
    influence: float = 0.5
    confidence: float = 0.3
    last_updated_day: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ReputationEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# reputation_matrix[observer_id][target_id] = ReputationEntry
ReputationMatrix = dict[str, dict[str, ReputationEntry]]


def init_reputation_matrix(char_ids: list[str]) -> ReputationMatrix:
    matrix = {}
    for observer in char_ids:
        matrix[observer] = {}
        for target in char_ids:
            if observer != target:
                matrix[observer][target] = ReputationEntry()
    return matrix


def update_from_direct_interaction(
    matrix: ReputationMatrix,
    observer: str,
    target: str,
    appraisal_valence: str,
    rel_delta: dict,
    day: int,
):
    entry = matrix.get(observer, {}).get(target)
    if not entry:
        return

    if appraisal_valence == "긍정":
        entry.warmth = min(1.0, entry.warmth + 0.03)
        entry.competence = min(1.0, entry.competence + 0.02)
    elif appraisal_valence == "부정":
        entry.warmth = max(0.0, entry.warmth - 0.03)
        entry.integrity = max(0.0, entry.integrity - 0.02)
    elif appraisal_valence == "혼합":
        entry.competence = min(1.0, entry.competence + 0.01)

    trust_delta = rel_delta.get("trust_delta", 0.0)
    if trust_delta > 0:
        entry.integrity = min(1.0, entry.integrity + trust_delta * 0.3)
    elif trust_delta < 0:
        entry.integrity = max(0.0, entry.integrity + trust_delta * 0.3)

    entry.confidence = min(1.0, entry.confidence + 0.05)
    entry.last_updated_day = day


def update_from_gossip(
    matrix: ReputationMatrix,
    receiver: str,
    about: str,
    gossip_valence: str,
    teller_integrity: float,
):
    entry = matrix.get(receiver, {}).get(about)
    if not entry:
        return

    weight = teller_integrity * 0.5
    confirmation_bias = 0.7

    if gossip_valence == "긍정":
        delta_w = 0.03 * weight
        delta_i = 0.02 * weight
        if entry.warmth > 0.6:
            delta_w *= (1.0 + confirmation_bias * 0.3)
        entry.warmth = min(1.0, entry.warmth + delta_w)
        entry.integrity = min(1.0, entry.integrity + delta_i)
    elif gossip_valence == "부정":
        delta_w = 0.03 * weight
        delta_i = 0.03 * weight
        if entry.warmth < 0.4:
            delta_w *= (1.0 + confirmation_bias * 0.3)
        entry.warmth = max(0.0, entry.warmth - delta_w)
        entry.integrity = max(0.0, entry.integrity - delta_i)

    entry.confidence = min(1.0, entry.confidence + 0.02)


def update_from_observation(
    matrix: ReputationMatrix,
    observer: str,
    target: str,
    observation_type: str,
    day: int,
):
    entry = matrix.get(observer, {}).get(target)
    if not entry:
        return

    if observation_type == "secret_exposed":
        entry.integrity = max(0.0, entry.integrity - 0.15)
    elif observation_type == "kind_act":
        entry.warmth = min(1.0, entry.warmth + 0.05)
    elif observation_type == "competent_act":
        entry.competence = min(1.0, entry.competence + 0.05)
    elif observation_type == "influential_act":
        entry.influence = min(1.0, entry.influence + 0.05)

    entry.confidence = min(1.0, entry.confidence + 0.08)
    entry.last_updated_day = day


def daily_decay(matrix: ReputationMatrix):
    for observer_reps in matrix.values():
        for entry in observer_reps.values():
            entry.confidence *= 0.99
            for attr in ("competence", "integrity", "warmth", "influence"):
                val = getattr(entry, attr)
                setattr(entry, attr, val + (0.5 - val) * 0.005)


def get_reputation_summary(matrix: ReputationMatrix, observer: str, target: str) -> str:
    entry = matrix.get(observer, {}).get(target)
    if not entry or entry.confidence < 0.2:
        return "잘 모르는 사람"

    parts = []
    if entry.competence > 0.7:
        parts.append("능력 있는")
    elif entry.competence < 0.3:
        parts.append("좀 미덥지 않은")

    if entry.integrity > 0.7:
        parts.append("믿을 수 있는")
    elif entry.integrity < 0.3:
        parts.append("좀 의심스러운")

    if entry.warmth > 0.7:
        parts.append("따뜻한")
    elif entry.warmth < 0.3:
        parts.append("차가운")

    if entry.influence > 0.7:
        parts.append("영향력 있는")

    if not parts:
        return "평범한 사람"
    return ", ".join(parts) + " 사람"
