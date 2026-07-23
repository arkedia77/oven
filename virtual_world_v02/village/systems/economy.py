"""D-G2 경제 슬롯 MVP — 관측전용 'favor'(호의) 자원. 옵트인(HARMONICITY_ECONOMY=1), 미설정 시 무영향.

§E-①(S12) 반영: 캐릭터당 일일 획득 상한(DAILY_CAP) enforce — 초과분은 버림(무한축적/차익 차단).
새 통화를 만들지 않고 기존 appraisal warmth_delta>0 관측만으로 부여한다(conversation.py에서 호출).
MVP는 관측만 — 소진(교환행동 연결)은 별도 게이트에서 확대.
"""
import os

DAILY_CAP = 3


def enabled() -> bool:
    return os.environ.get("HARMONICITY_ECONOMY") == "1"


def grant_favor(char_id: str, day: int) -> bool:
    """긍정 상호작용 관측 시 호의 1점 부여 시도. 일일상한 도달 시 차단(§E-① S12).
    반환값: 실제로 부여됐는지(관측·검증용)."""
    if not enabled():
        return False
    from village.persistence.save_load import save_economy, load_economy
    data = load_economy()
    entry = data.setdefault(char_id, {"total": 0, "daily": {}})
    today_key = str(day)
    today = entry["daily"].get(today_key, 0)
    if today >= DAILY_CAP:
        return False  # 밴드 초과 — 차단(enforce)
    entry["daily"][today_key] = today + 1
    entry["total"] = entry.get("total", 0) + 1
    save_economy(data)
    return True
