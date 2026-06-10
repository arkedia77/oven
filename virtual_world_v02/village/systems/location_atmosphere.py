"""장소 분위기 시스템 — 대화 결과가 공간에 축적"""
from village.world.locations import LOCATIONS

_atmosphere: dict[str, dict] = {}


def _ensure_init():
    global _atmosphere
    if not _atmosphere:
        for loc_id in LOCATIONS:
            _atmosphere[loc_id] = {"warmth": 0.0, "friction": 0.0}


def add_warmth(location: str, amount: float = 0.1):
    _ensure_init()
    if location in _atmosphere:
        _atmosphere[location]["warmth"] = min(3.0, _atmosphere[location]["warmth"] + amount)


def add_friction(location: str, amount: float = 0.1):
    _ensure_init()
    if location in _atmosphere:
        _atmosphere[location]["friction"] = min(3.0, _atmosphere[location]["friction"] + amount)


def decay_all():
    _ensure_init()
    for atm in _atmosphere.values():
        atm["warmth"] *= 0.95
        atm["friction"] *= 0.95


def get_atmosphere_text(location: str) -> str:
    _ensure_init()
    atm = _atmosphere.get(location)
    if not atm:
        return ""
    diff = atm["warmth"] - atm["friction"]
    if diff > 0.3:
        return "이 장소는 최근 따뜻하고 편안한 분위기다."
    elif diff < -0.3:
        return "이 장소는 최근 긴장되고 불편한 분위기다."
    return ""


def get_state() -> dict:
    _ensure_init()
    return {k: dict(v) for k, v in _atmosphere.items()}


def load_state(state: dict):
    global _atmosphere
    _atmosphere = {k: dict(v) for k, v in state.items()}
