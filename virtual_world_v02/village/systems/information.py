"""정보 비대칭 시스템 — 비밀/소문/관찰 추적 (P1 + P1.2)

각 캐릭터가 '아는 것'을 추적하고, 대화를 통해 정보가 전파됨.
truth_value는 전파될수록 감쇠 (전화기 효과).

P1.2: 소문 대상 분산 + 콘텐츠 다양성 강제.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import random


@dataclass
class InfoItem:
    id: str
    category: str              # "secret" | "observation" | "rumor" | "fact"
    subject: str               # 정보 대상 캐릭터 ID
    content: str
    truth_value: float = 1.0   # 0.0~1.0
    sensitivity: float = 0.5   # 0.0~1.0
    origin_day: int = 0
    source: str = "system"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "InfoItem":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# knowledge[char_id] → dict[info_id → InfoItem]
KnowledgeBase = dict[str, dict[str, InfoItem]]

# 전체 정보 등록소
InfoRegistry = dict[str, InfoItem]


def init_info_registry() -> InfoRegistry:
    """definitions.py의 secret 필드에서 초기 정보 생성."""
    from village.characters.definitions import CHARACTERS

    registry: InfoRegistry = {}
    for char_id, defn in CHARACTERS.items():
        secret = defn.get("secret", "")
        if secret:
            item = InfoItem(
                id=f"secret_{char_id}",
                category="secret",
                subject=char_id,
                content=secret,
                truth_value=1.0,
                sensitivity=_estimate_sensitivity(char_id),
                origin_day=0,
                source="system",
            )
            registry[item.id] = item
    return registry


def _estimate_sensitivity(char_id: str) -> float:
    high_sensitivity = {"tae_sik", "ha_yeon", "aria", "sang_woo", "ji_woo"}
    if char_id in high_sensitivity:
        return 0.9
    return 0.6


def init_knowledge_base(registry: InfoRegistry) -> KnowledgeBase:
    """각 캐릭터는 자기 비밀만 알고 시작."""
    from village.characters.definitions import CHARACTERS

    kb: KnowledgeBase = {}
    for char_id in CHARACTERS:
        kb[char_id] = {}
        secret_id = f"secret_{char_id}"
        if secret_id in registry:
            kb[char_id][secret_id] = registry[secret_id]
    return kb


def can_share(
    sharer: str,
    receiver: str,
    info: InfoItem,
    trust_level: float,
) -> bool:
    if info.subject == receiver:
        return False
    if info.sensitivity > 0.7 and trust_level < 0.8:
        return False
    if info.sensitivity > 0.4 and trust_level < 0.6:
        return False
    return True


def propagate_info(
    kb: KnowledgeBase,
    registry: InfoRegistry,
    sharer: str,
    receiver: str,
    info_id: str,
    day: int,
) -> InfoItem | None:
    original = kb.get(sharer, {}).get(info_id)
    if not original:
        return None

    if info_id in kb.get(receiver, {}):
        return None

    propagated = InfoItem(
        id=original.id,
        category="rumor" if original.category == "rumor" else original.category,
        subject=original.subject,
        content=original.content,
        truth_value=original.truth_value * 0.9,
        sensitivity=original.sensitivity,
        origin_day=day,
        source=sharer,
    )

    kb.setdefault(receiver, {})[info_id] = propagated
    return propagated


def try_observation(
    kb: KnowledgeBase,
    registry: InfoRegistry,
    observer: str,
    target: str,
    same_location: bool,
    day: int,
) -> InfoItem | None:
    if not same_location:
        return None

    secret_id = f"secret_{target}"
    if secret_id not in registry:
        return None
    if secret_id in kb.get(observer, {}):
        return None

    info = registry[secret_id]
    exposure_chance = info.sensitivity * 0.02
    if random.random() > exposure_chance:
        return None

    observed = InfoItem(
        id=secret_id,
        category="observation",
        subject=target,
        content=info.content,
        truth_value=0.7,
        sensitivity=info.sensitivity,
        origin_day=day,
        source=observer,
    )
    kb.setdefault(observer, {})[secret_id] = observed
    return observed


def select_shareable_info(
    kb: KnowledgeBase,
    sharer: str,
    receiver: str,
    trust_level: float,
    about: str | None = None,
) -> list[InfoItem]:
    sharer_knowledge = kb.get(sharer, {})
    shareable = []
    for info_id, info in sharer_knowledge.items():
        if info.subject == sharer:
            continue
        if about and info.subject != about:
            continue
        if can_share(sharer, receiver, info, trust_level):
            if info_id not in kb.get(receiver, {}):
                shareable.append(info)
    return shareable


def get_known_info_about(kb: KnowledgeBase, observer: str, target: str) -> list[InfoItem]:
    observer_knowledge = kb.get(observer, {})
    return [info for info in observer_knowledge.values() if info.subject == target]


def info_summary_for_prompt(kb: KnowledgeBase, observer: str, target: str) -> str:
    items = get_known_info_about(kb, observer, target)
    if not items:
        return ""
    lines = []
    for item in items:
        prefix = "확실히" if item.truth_value > 0.8 else "소문으로"
        lines.append(f"- {prefix} 알고 있음: {item.content}")
    return "\n".join(lines)


_rumor_counter: int = 0


def restore_rumor_counter(registry: InfoRegistry):
    """재시작 시 registry에서 최대 counter 값을 복원하여 ID 충돌 방지."""
    global _rumor_counter
    max_counter = 0
    for key in registry:
        if key.startswith("rumor_d"):
            parts = key.split("_")
            if len(parts) >= 3:
                try:
                    max_counter = max(max_counter, int(parts[-1]))
                except ValueError:
                    pass
    _rumor_counter = max_counter


_RUMOR_TEMPLATES = {
    "부정": [
        "{about}에 대해 좋지 않은 이야기가 돌고 있다",
        "{about}의 진정성에 의문을 제기하는 말이 나왔다",
        "{about}이(가) 신뢰를 저버린 행동을 했다는 이야기가 있다",
        "{about}에 대해 실망했다는 이야기를 들었다",
        "{about}의 최근 행동이 논란이 되고 있다",
        "{about}이(가) 약속을 지키지 않았다는 소문이 있다",
        "{about}에 대해 불편한 진실이 드러났다는 이야기를 들었다",
        "{about}이(가) 누군가에게 상처를 줬다는 말이 나왔다",
    ],
    "긍정": [
        "{about}에 대해 좋은 이야기를 들었다",
        "{about}이(가) 인상적인 모습을 보였다는 평가가 있다",
        "{about}의 능력을 칭찬하는 이야기를 들었다",
        "{about}이(가) 따뜻한 행동을 했다는 소문이 있다",
        "{about}에 대한 긍정적인 평판이 퍼지고 있다",
        "{about}이(가) 어려운 상황에서 도움을 줬다는 이야기가 있다",
        "{about}의 성실함에 대한 좋은 이야기를 들었다",
    ],
    "중립": [
        "{about}에 대한 이야기가 화제가 되었다",
        "{about}의 근황에 대해 이야기를 나눴다",
        "{about}에 대해 이런저런 이야기가 오갔다",
        "{about}이(가) 요즘 무엇을 하는지 이야기가 나왔다",
        "{about}에 대한 새로운 이야기를 들었다",
    ],
}

_DAILY_TARGET_CAP = 3
_TARGET_GAP_CAP = 20


def _count_rumors_by_target(registry: InfoRegistry) -> dict[str, int]:
    counts: dict[str, int] = {}
    for k, v in registry.items():
        if not k.startswith("rumor_"):
            continue
        subj = v.subject if isinstance(v, InfoItem) else v.get("subject", "")
        if subj:
            counts[subj] = counts.get(subj, 0) + 1
    return counts


def _count_daily_rumors_for_target(registry: InfoRegistry, day: int, target: str) -> int:
    prefix = f"rumor_d{day}_"
    count = 0
    for k, v in registry.items():
        if not k.startswith(prefix):
            continue
        subj = v.subject if isinstance(v, InfoItem) else v.get("subject", "")
        if subj == target:
            count += 1
    return count


def create_dynamic_rumor(
    kb: KnowledgeBase,
    registry: InfoRegistry,
    source_char: str,
    listener_char: str,
    about: str,
    valence: str,
    day: int,
) -> InfoItem | None:
    """대화에서 생성된 동적 소문을 knowledge base에 추가.

    P1.2: 대상별 일일 상한 + 누적 분산 유도 + 콘텐츠 다양화.
    """
    global _rumor_counter
    if about == source_char or about == listener_char:
        return None

    daily_count = _count_daily_rumors_for_target(registry, day, about)
    if daily_count >= _DAILY_TARGET_CAP:
        return None

    target_counts = _count_rumors_by_target(registry)
    about_total = target_counts.get(about, 0)
    if target_counts:
        min_count = min(target_counts.values())
        if about_total - min_count > _TARGET_GAP_CAP:
            return None

    _rumor_counter += 1
    rumor_id = f"rumor_d{day}_{_rumor_counter}"

    templates = _RUMOR_TEMPLATES.get(valence, _RUMOR_TEMPLATES["중립"])
    content = random.choice(templates).format(about=about)
    sensitivity = 0.7 if valence == "부정" else 0.3

    item = InfoItem(
        id=rumor_id,
        category="rumor",
        subject=about,
        content=content,
        truth_value=0.5,
        sensitivity=sensitivity,
        origin_day=day,
        source=source_char,
    )

    registry[rumor_id] = item
    kb.setdefault(source_char, {})[rumor_id] = item
    kb.setdefault(listener_char, {})[rumor_id] = item
    return item
