#!/usr/bin/env python3
"""하모니시티 관측·개입 API (Phase A-5).

파일 = 인터페이스: 엔진 프로세스와 IPC 없음. 세계 data dir의 JSON을 읽어 서빙하고,
개입은 DATA_DIR/interventions_inbox.json에 append(엔진이 HARMONICITY_ALLOW_INBOX=1로
떠 있으면 다음 틱에 소비). API는 상태 파일을 쓰지 않는다(inbox append 제외) — 세계의
단일 작성자는 엔진 하나라는 격리 원칙 유지. 락도 잡지 않는다.

실행:
  pip install fastapi uvicorn
  python api/server.py --port 8090
  또는  python -m uvicorn api.server:app --port 8090

세계 레지스트리: api/worlds.json  {"<별칭>": "<data dir 상대경로>"}
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path

from fastapi import FastAPI, HTTPException, Body

BASE = Path(__file__).parent.parent          # virtual_world_v02/
REGISTRY_PATH = Path(__file__).parent / "worlds.json"

sys.path.insert(0, str(BASE))
from village.metrics import extract_metrics   # noqa: E402
from village import intervention              # noqa: E402

app = FastAPI(title="Harmonicity Observation & Intervention API", version="1.0")


def _registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _world_dir(w: str) -> Path:
    reg = _registry()
    if w not in reg:
        raise HTTPException(404, f"world '{w}' 미등록 (등록: {sorted(reg)})")
    rel = reg[w]
    p = Path(rel)
    return p if p.is_absolute() else (BASE / rel)


def _read_json(path: Path, retries: int = 3, delay: float = 0.05):
    """부분 쓰기 방어: JSONDecodeError/FileNotFound 시 재시도. A-2 원자적 쓰기로 대부분 불필요하나
    미패치 세계(ogo 등) 대비 이중 방어."""
    if not path.exists():
        raise HTTPException(404, f"'{path.name}' 아직 저장 안 됨")
    last = None
    for _ in range(retries):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            last = e
            time.sleep(delay)
    raise HTTPException(503, f"'{path.name}' 읽기 실패(부분 쓰기 추정): {last}")


@app.get("/worlds")
def list_worlds():
    reg = _registry()
    out = {}
    for w, rel in reg.items():
        d = Path(rel) if Path(rel).is_absolute() else (BASE / rel)
        ws = d / "world_state.json"
        if ws.exists():
            try:
                s = json.loads(ws.read_text(encoding="utf-8"))
                out[w] = {"path": rel, "day": s.get("day"), "tick": s.get("tick"), "missing": False}
            except json.JSONDecodeError:
                out[w] = {"path": rel, "missing": False, "note": "쓰기 중"}
        else:
            out[w] = {"path": rel, "missing": True}
    return out


@app.get("/worlds/{w}/state")
def get_state(w: str):
    return _read_json(_world_dir(w) / "world_state.json")


@app.get("/worlds/{w}/relationships")
def get_relationships(w: str):
    return _read_json(_world_dir(w) / "relationships.json")


@app.get("/worlds/{w}/relationships/history")
def get_rel_history(w: str):
    return _read_json(_world_dir(w) / "relationship_history.json")


@app.get("/worlds/{w}/characters")
def list_characters(w: str):
    cdir = _world_dir(w) / "characters"
    if not cdir.exists():
        raise HTTPException(404, "characters 아직 저장 안 됨")
    out = []
    for p in sorted(cdir.glob("*.json")):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append({
            "id": c.get("id", p.stem),
            "name": c.get("name"),
            "location": c.get("location"),
            "emotional_state": c.get("emotional_state"),
        })
    return out


@app.get("/worlds/{w}/characters/{cid}")
def get_character(w: str, cid: str):
    return _read_json(_world_dir(w) / "characters" / f"{cid}.json")


@app.get("/worlds/{w}/reputation")
def get_reputation(w: str):
    return _read_json(_world_dir(w) / "reputation.json")


@app.get("/worlds/{w}/needs/history")
def get_need_history(w: str):
    return _read_json(_world_dir(w) / "need_history.json")


@app.get("/worlds/{w}/atmosphere")
def get_atmosphere(w: str):
    return _read_json(_world_dir(w) / "atmosphere.json")


@app.get("/worlds/{w}/metrics")
def get_metrics(w: str):
    d = _world_dir(w)
    if not (d / "relationships.json").exists():
        raise HTTPException(404, "relationships 아직 저장 안 됨")
    return extract_metrics(d)


@app.get("/worlds/{w}/conversations")
def get_conversations(w: str, day: int | None = None, limit: int = 20):
    conv_root = _world_dir(w) / "conversations"
    if not conv_root.exists():
        raise HTTPException(404, "conversations 아직 없음")
    if day is None:
        days = sorted(conv_root.glob("day*"))
        if not days:
            return {"day": None, "conversations": []}
        day_dir = days[-1]
        day = int(day_dir.name.replace("day", ""))
    else:
        day_dir = conv_root / f"day{day:03d}"
        if not day_dir.exists():
            raise HTTPException(404, f"day{day:03d} 대화 없음")
    files = sorted(day_dir.glob("*.json"))[-limit:]
    convs = []
    for p in files:
        try:
            convs.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return {"day": day, "count": len(convs), "conversations": convs}


@app.get("/worlds/{w}/interventions/applied")
def get_applied(w: str, limit: int = 50):
    p = _world_dir(w) / "interventions_applied.jsonl"
    if not p.exists():
        return {"applied": []}
    lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {"applied": [json.loads(l) for l in lines[-limit:]]}


@app.post("/worlds/{w}/interventions", status_code=202)
def post_intervention(w: str, body: dict = Body(...)):
    """개입 1건을 inbox에 큐잉. 검증 실패는 400. 적용은 엔진이 다음 틱에(ALLOW_INBOX=1 시)."""
    errs = intervention.validate_spec(body)
    if errs:
        raise HTTPException(400, {"errors": errs})
    d = _world_dir(w)
    if not d.exists():
        raise HTTPException(404, f"world dir 없음: {d}")
    inbox = d / "interventions_inbox.json"
    try:
        cur = json.loads(inbox.read_text(encoding="utf-8")) if inbox.exists() else []
        if not isinstance(cur, list):
            cur = [cur]
    except json.JSONDecodeError:
        cur = []
    cur.append(body)
    tmp = inbox.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, inbox)
    return {"queued": True, "queue_len": len(cur),
            "note": "엔진이 HARMONICITY_ALLOW_INBOX=1로 떠 있어야 다음 틱에 적용됨. "
                    "적용 확인은 GET .../interventions/applied"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    import uvicorn
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
