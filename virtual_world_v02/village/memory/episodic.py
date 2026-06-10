"""L2 삽화기억 — append-only JSONL, 50개 롤링"""
import json
from pathlib import Path
from village.config import DATA_DIR, MAX_EPISODES


def get_episodes_path(char_id: str) -> Path:
    return DATA_DIR / "memories" / char_id / "episodes.jsonl"


def append_episode(char_id: str, episode: dict):
    path = get_episodes_path(char_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(episode, ensure_ascii=False) + "\n")
    _trim_episodes(path)


def _trim_episodes(path: Path):
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    if len(lines) > MAX_EPISODES:
        trimmed = lines[-MAX_EPISODES:]
        path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")


def get_recent_episodes(char_id: str, n: int = 10) -> list:
    path = get_episodes_path(char_id)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    episodes = []
    for line in lines[-n:]:
        if line.strip():
            episodes.append(json.loads(line))
    return episodes


def get_episodes_about(char_id: str, other_id: str, n: int = 3) -> list:
    all_eps = get_recent_episodes(char_id, 50)
    relevant = [e for e in all_eps if e.get("other") == other_id]
    return relevant[-n:]
