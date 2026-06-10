#!/usr/bin/env python3
"""하모니 시티 라이브 대시보드 서버"""
import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA_DIR = Path(__file__).parent / "data"
LOG_FILE = Path(__file__).parent / "village_output_v3.log"
PORT = 8765

CHAR_NAMES = {
    "aria": "아리아", "luna": "루나", "nexus": "넥서스",
    "seo_jin": "윤서진", "joon_ho": "박준호", "tae_sik": "강태식",
    "sang_woo": "류상우", "ye_eun": "송예은", "min_ah": "최민아",
    "ha_yeon": "임하연",
}

LOCATION_NAMES = {
    "plaza": "하모니 광장", "cafe": "민아 카페 '온기'",
    "studio": "루나 스튜디오", "lab": "융합연구실",
    "council": "시의회 사무실", "community_center": "하모니 커뮤니티 센터",
    "residential": "주거 구역",
}


def get_state():
    try:
        return json.loads((DATA_DIR / "world_state.json").read_text(encoding="utf-8"))
    except:
        return {"day": 0, "hour": 0, "tick": 0}


def get_characters():
    chars = []
    for f in sorted((DATA_DIR / "characters").glob("*.json")):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
            c["display_name"] = CHAR_NAMES.get(c["id"], c.get("name", c["id"]))
            c["location_name"] = LOCATION_NAMES.get(c.get("location", ""), c.get("location", ""))
            chars.append(c)
        except:
            pass
    return chars


def get_relationships():
    try:
        return json.loads((DATA_DIR / "relationships.json").read_text(encoding="utf-8"))
    except:
        return {}


def get_conversations(day=None, limit=50):
    if day is None:
        state = get_state()
        day = state.get("day", 0)
    convs = []
    for d in range(day, max(day - 3, 0), -1):
        conv_dir = DATA_DIR / "conversations" / f"day{d:03d}"
        if conv_dir.exists():
            for f in sorted(conv_dir.glob("*.json"), key=lambda p: p.name, reverse=True):
                try:
                    c = json.loads(f.read_text(encoding="utf-8"))
                    c["_day"] = d
                    convs.append(c)
                except:
                    pass
        if len(convs) >= limit:
            break
    return convs[:limit]


def get_memories(char_id):
    mem_dir = DATA_DIR / "memories" / char_id
    mems = []
    if not mem_dir.exists():
        return mems
    jsonl = mem_dir / "episodes.jsonl"
    if jsonl.exists():
        try:
            lines = jsonl.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines[-20:]):
                try:
                    mems.append(json.loads(line))
                except:
                    pass
        except:
            pass
    if not mems:
        for f in sorted(mem_dir.glob("*.json"), reverse=True)[:10]:
            try:
                mems.append(json.loads(f.read_text(encoding="utf-8")))
            except:
                pass
    return mems[:10]


def get_history():
    result = {"needs": {}, "beliefs": {}, "relationships": {}}
    for name, key in [("needs", "need_history.json"), ("beliefs", "belief_history.json"), ("relationships", "relationship_history.json")]:
        path = DATA_DIR / key
        if path.exists():
            try:
                result[name] = json.loads(path.read_text(encoding="utf-8"))
            except:
                pass
    return result


def get_log_tail(n=80):
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-n:])
    except:
        return ""


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._json_response(get_state())
        elif parsed.path == "/api/characters":
            self._json_response(get_characters())
        elif parsed.path == "/api/relationships":
            self._json_response(get_relationships())
        elif parsed.path == "/api/conversations":
            qs = parse_qs(parsed.query)
            day = int(qs["day"][0]) if "day" in qs else None
            self._json_response(get_conversations(day))
        elif parsed.path == "/api/memories":
            qs = parse_qs(parsed.query)
            cid = qs.get("id", ["aria"])[0]
            self._json_response(get_memories(cid))
        elif parsed.path == "/api/log":
            self._json_response({"log": get_log_tail()})
        elif parsed.path == "/api/history":
            self._json_response(get_history())
        elif parsed.path == "/api/all":
            self._json_response({
                "state": get_state(),
                "characters": get_characters(),
                "relationships": get_relationships(),
                "conversations": get_conversations(limit=30),
            })
        elif parsed.path == "/" or parsed.path == "/index.html":
            self._serve_html()
        else:
            self.send_error(404)

    def _json_response(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        html_path = Path(__file__).parent / "dashboard.html"
        body = html_path.read_text(encoding="utf-8").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"하모니 시티 대시보드: http://localhost:{PORT}")
    server.serve_forever()
