"""캐릭터 상태 관리 — #02 Ecosystem"""
import copy
from dataclasses import dataclass, field
from village.characters.definitions import CHARACTERS


@dataclass
class CharacterState:
    id: str
    name: str
    role: str
    age: str
    is_ai: bool
    persona: str
    speech_style: str
    stance_on_ai: str
    secret: str
    needs: dict
    beliefs: dict
    convictions: dict
    goals: list
    default_schedule: dict
    location: str = "residential"
    emotional_state: str = "평온"
    energy: float = 3.0
    today_interactions: list = field(default_factory=list)
    working_memory: list = field(default_factory=list)
    need_importance: dict = field(default_factory=dict)
    persona_addendum: str = ""

    @classmethod
    def from_definition(cls, char_id: str) -> "CharacterState":
        defn = CHARACTERS[char_id]
        needs = copy.deepcopy(defn["needs"])
        beliefs = copy.deepcopy(defn["beliefs"])
        convictions = {}
        for key in beliefs:
            val = abs(beliefs[key] - 0.5) * 2
            convictions[key] = max(0.3, min(0.9, 0.4 + val * 0.5))
        importance = {k: 1.0 for k in needs}
        return cls(
            id=char_id,
            name=defn["name"],
            role=defn["role"],
            age=str(defn["age"]),
            is_ai=defn["is_ai"],
            persona=defn["persona"],
            speech_style=defn["speech_style"],
            stance_on_ai=defn["stance_on_ai"],
            secret=defn["secret"],
            needs=needs,
            beliefs=beliefs,
            convictions=convictions,
            goals=copy.deepcopy(defn["goals"]),
            default_schedule=defn["default_schedule"],
            need_importance=importance,
        )

    def get_location(self, time_period: str) -> str:
        return self.default_schedule.get(time_period, "residential")

    def top_unmet_need(self) -> tuple:
        if not self.needs:
            return ("none", 1.0)
        importance = self.need_importance or {k: 1.0 for k in self.needs}
        return min(
            self.needs.items(),
            key=lambda x: x[1] / max(0.1, importance.get(x[0], 1.0)),
        )

    def top_goal(self) -> dict | None:
        if not self.goals:
            return None
        return min(self.goals, key=lambda g: g["progress"])

    def decay_needs(self, amount: float = 0.005):
        for key in self.needs:
            self.needs[key] = max(0.0, self.needs[key] - amount)

    def fulfill_needs_from_conversation(self, reflection: str, positive: bool):
        if positive:
            self.needs["belonging"] = min(1.0, self.needs["belonging"] + 0.05)
            self.needs["recognition"] = min(1.0, self.needs["recognition"] + 0.04)
            self.needs["affection"] = min(1.0, self.needs.get("affection", 0.5) + 0.04)
            self.needs["security"] = min(1.0, self.needs["security"] + 0.02)
        else:
            self.needs["belonging"] = min(1.0, self.needs["belonging"] + 0.02)
            self.needs["autonomy"] = min(1.0, self.needs["autonomy"] + 0.03)

        self.needs["purpose"] = min(1.0, self.needs["purpose"] + 0.02)

        conflict_words = ["분노", "짜증", "방해", "거부", "대립", "모독", "위협"]
        if any(w in reflection for w in conflict_words):
            self.needs["security"] = max(0.0, self.needs["security"] - 0.03)

        affection_words = ["사랑", "애정", "따뜻", "포옹", "보고싶", "그리", "설레"]
        if any(w in reflection for w in affection_words):
            self.needs["affection"] = min(1.0, self.needs.get("affection", 0.5) + 0.06)

    def fulfill_needs_from_monologue(self):
        self.needs["autonomy"] = min(1.0, self.needs["autonomy"] + 0.06)
        self.needs["purpose"] = min(1.0, self.needs["purpose"] + 0.03)

    def fulfill_needs_from_alone_time(self):
        self.needs["autonomy"] = min(1.0, self.needs["autonomy"] + 0.02)
        self.needs["security"] = min(1.0, self.needs["security"] + 0.01)

    def shift_belief_toward(self, other: "CharacterState"):
        for key in self.beliefs:
            if key not in other.beliefs:
                continue
            diff = abs(self.beliefs[key] - other.beliefs[key])
            if diff < 0.2:
                continue
            conviction = self.convictions.get(key, 0.5)
            actual_shift = 0.02 * (1.0 - conviction)
            direction = 1 if other.beliefs[key] > self.beliefs[key] else -1
            self.beliefs[key] = max(0.0, min(1.0, self.beliefs[key] + actual_shift * direction))
            self.convictions[key] = max(0.1, conviction - 0.005)

    def adapt_need_importance(self, recent_need_history: dict[str, list[float]]):
        for key in self.needs:
            history = recent_need_history.get(key, [])
            if len(history) < 10:
                continue
            avg = sum(history[-10:]) / 10
            imp = self.need_importance.get(key, 1.0)
            if avg > 0.7:
                self.need_importance[key] = max(0.3, imp * 0.9)
            elif avg < 0.3:
                self.need_importance[key] = min(2.0, imp * 1.1)

    def update_emotional_state(self):
        need_name, need_val = self.top_unmet_need()
        if need_val < 0.15:
            emotions = {
                "belonging": "외로움",
                "purpose": "공허함",
                "security": "불안",
                "recognition": "좌절",
                "autonomy": "답답함",
                "affection": "애정 결핍",
            }
            self.emotional_state = emotions.get(need_name, "불안정")
        elif need_val < 0.35:
            self.emotional_state = "약간 불만족"
        elif need_val > 0.7:
            self.emotional_state = "안정적"
        else:
            self.emotional_state = "평온"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "emotional_state": self.emotional_state,
            "energy": self.energy,
            "needs": self.needs,
            "beliefs": self.beliefs,
            "convictions": self.convictions,
            "goals": self.goals,
            "today_interactions": self.today_interactions,
            "working_memory": self.working_memory[-5:],
            "need_importance": self.need_importance,
            "persona_addendum": self.persona_addendum,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterState":
        char_id = data["id"]
        state = cls.from_definition(char_id)
        state.location = data.get("location", "residential")
        state.emotional_state = data.get("emotional_state", "평온")
        state.energy = data.get("energy", 3.0)
        state.needs = data.get("needs", state.needs)
        state.beliefs = data.get("beliefs", state.beliefs)
        state.convictions = data.get("convictions", state.convictions)
        state.goals = data.get("goals", state.goals)
        state.today_interactions = data.get("today_interactions", [])
        state.working_memory = data.get("working_memory", [])
        state.need_importance = data.get("need_importance", state.need_importance)
        state.persona_addendum = data.get("persona_addendum", "")
        return state
