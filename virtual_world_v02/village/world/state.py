"""월드 상태 관리"""
from dataclasses import dataclass, field


@dataclass
class WorldState:
    day: int = 1
    hour: int = 6
    tick: int = 0
    community_events: list = field(default_factory=list)
    pending_decisions: list = field(default_factory=lambda: [
        "시의회 AI 사업 허가 조례 표결 (5일차 예정)"
    ])
    low_tension_days: int = 0

    def advance_tick(self):
        self.tick += 1
        self.hour = (self.hour + 1) % 24
        if self.hour == 6:
            self.day += 1

    def is_end_of_day(self) -> bool:
        return self.hour == 5  # 05:00 = just before new day starts at 06:00

    def add_event(self, event: str):
        self.community_events.append(f"[Day {self.day}] {event}")
        if len(self.community_events) > 20:
            self.community_events = self.community_events[-20:]

    def recent_events(self, n: int = 3) -> list:
        return self.community_events[-n:] if self.community_events else []

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "hour": self.hour,
            "tick": self.tick,
            "community_events": self.community_events,
            "pending_decisions": self.pending_decisions,
            "low_tension_days": self.low_tension_days,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldState":
        ws = cls()
        ws.day = data.get("day", 1)
        ws.hour = data.get("hour", 6)
        ws.tick = data.get("tick", 0)
        ws.community_events = data.get("community_events", [])
        ws.pending_decisions = data.get("pending_decisions", ws.pending_decisions)
        ws.low_tension_days = data.get("low_tension_days", 0)
        return ws
