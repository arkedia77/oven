"""MusicScore 대시보드 서버"""

import os, sqlite3, json, re
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse

app = FastAPI(title="MusicScore Dashboard")

BASE_DIR = os.path.expanduser("~/musicscore")
DATA_DIR = "/Volumes/data/score"
DB_PATH = f"{BASE_DIR}/data/musicscore.db"

# 목표 수량 (데이터셋별)
TARGETS = {
    "gigamidi": 3_409_419,
    "lakh": 178_561,
    "pdmx": 254_035,
    "aria-midi": 1_186_253,
    "maestro": 1_276,
    "atepp": 11_742,
    "pop909": 909,
    "pop-k-midi": 305_815,
    "bitmidi": 113_229,
    "musescore": 999_999,  # 무한 수집
    "asap": 565,
    "midicaps": 10_000,
}


def query_db(sql, params=()):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        cols = [d[0] for d in c.description]
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        return [{"error": str(e)}]


@app.get("/api/stats")
def get_stats():
    """DB 전체 통계"""
    sources = query_db("""
        SELECT source, COUNT(*) as count,
               COALESCE(SUM(size_bytes), 0) / 1024 / 1024 / 1024 as size_gb,
               COALESCE(AVG(quality_score), 0) as avg_quality
        FROM files GROUP BY source ORDER BY count DESC
    """)

    quality = query_db("""
        SELECT
            SUM(CASE WHEN quality_score >= 0.7 THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN quality_score > 0 AND quality_score < 0.7 THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN quality_score <= 0 THEN 1 ELSE 0 END) as low,
            COUNT(*) as total
        FROM files
    """)

    formats = query_db("SELECT file_type, COUNT(*) as count FROM files GROUP BY file_type")

    # 목표 대비 진행률 추가
    for s in sources:
        target = TARGETS.get(s["source"], 0)
        s["target"] = target
        s["progress_pct"] = round(s["count"] / target * 100, 1) if target > 0 else 0
        s["size_gb"] = round(s["size_gb"], 2)
        s["avg_quality"] = round(s["avg_quality"], 2)

    return {
        "sources": sources,
        "quality": quality[0] if quality else {},
        "formats": formats,
        "db_size_mb": round(os.path.getsize(DB_PATH) / 1024 / 1024, 1) if os.path.exists(DB_PATH) else 0,
        "updated_at": datetime.now().isoformat()
    }


@app.get("/api/downloads")
def get_downloads():
    """진행 중인 다운로드 상태"""
    results = {}

    # BitMIDI 진행
    bitmidi_done = f"{BASE_DIR}/data/bitmidi_done.txt"
    if os.path.exists(bitmidi_done):
        with open(bitmidi_done) as f:
            count = len(f.read().splitlines())
        results["bitmidi"] = {
            "done": count,
            "target": 113_229,
            "pct": round(count / 113_229 * 100, 1)
        }

    # MuseScore 진행
    musescore_dir = f"{DATA_DIR}/musescore"
    if os.path.exists(musescore_dir):
        count = sum(1 for f in Path(musescore_dir).rglob("*.mxl"))
        results["musescore"] = {
            "done": count,
            "target": "∞ (매일 수집)",
            "pct": None
        }

    # BitMIDI 로그 최신 라인
    bitmidi_log = f"{BASE_DIR}/logs/bitmidi.log"
    if os.path.exists(bitmidi_log):
        with open(bitmidi_log) as f:
            lines = f.readlines()
            results["bitmidi_log"] = lines[-3:] if len(lines) >= 3 else lines

    return results


@app.get("/api/kanban")
def get_kanban():
    """KANBAN.md 파싱"""
    kanban_path = f"{BASE_DIR}/KANBAN.md"
    if not os.path.exists(kanban_path):
        return {"error": "KANBAN.md not found"}

    with open(kanban_path) as f:
        content = f.read()

    sections = {"done": [], "in_progress": [], "todo_data": [], "todo_engine": [], "todo_later": []}
    current = None

    for line in content.split("\n"):
        if "## ✅ DONE" in line:
            current = "done"
        elif "## 🔄 IN PROGRESS" in line:
            current = "in_progress"
        elif "## 📋 TODO — 데이터" in line:
            current = "todo_data"
        elif "## 📋 TODO — 피아노 엔진" in line:
            current = "todo_engine"
        elif "## 📋 TODO — 이후" in line:
            current = "todo_later"
        elif "## 🔗" in line:
            current = None
        elif current and line.strip().startswith("- ["):
            checked = "[x]" in line
            text = re.sub(r"- \[.\]\s*", "", line.strip())
            sections[current].append({"text": text, "done": checked})

    return sections


@app.get("/api/files")
def get_files():
    """프로젝트 관련 파일 목록"""
    files = []
    important = [
        ("KANBAN.md", "칸반 보드"),
        ("ENGINE_PLAN.md", "엔진 설계 로드맵"),
        ("KEYBOARDIST_INTERVIEW_v3.md", "키보디스트 인터뷰 가이드"),
        ("MUSICIAN_COLLABORATION_GUIDE.md", "뮤지션 협업 프레임워크"),
        ("YOUTUBE_CONTENT_PLAN.md", "YouTube 콘텐츠 기획"),
        ("prepare_piano_data.py", "피아노 데이터 정제 스크립트"),
        ("build_dataset_db.py", "DB 구축 스크립트"),
        ("README.md", "프로젝트 소개"),
    ]

    for fname, desc in important:
        fpath = os.path.join(BASE_DIR, fname)
        exists = os.path.exists(fpath)
        size = os.path.getsize(fpath) if exists else 0
        files.append({
            "name": fname,
            "description": desc,
            "exists": exists,
            "size_kb": round(size / 1024, 1),
        })

    return files


@app.get("/api/file/{filename:path}")
def read_file(filename: str):
    """파일 내용 읽기"""
    fpath = os.path.join(BASE_DIR, filename)
    if not os.path.exists(fpath):
        return PlainTextResponse("File not found", status_code=404)
    if not fpath.startswith(BASE_DIR):
        return PlainTextResponse("Access denied", status_code=403)
    with open(fpath) as f:
        return PlainTextResponse(f.read())


@app.get("/api/disk")
def get_disk():
    """디스크 사용량"""
    result = {}
    for name in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, name)
        if os.path.isdir(path):
            total = sum(
                f.stat().st_size
                for f in Path(path).rglob("*")
                if f.is_file()
            ) if os.path.exists(path) else 0
            result[name] = round(total / 1024 / 1024 / 1024, 2)
    return result


# Landing page (공사중)
@app.get("/")
def landing():
    return FileResponse(f"{BASE_DIR}/dashboard/static/landing.html")


# Liszt dashboard
@app.get("/liszt")
def liszt_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/liszt/")


@app.get("/liszt/")
def liszt_dashboard():
    return FileResponse(f"{BASE_DIR}/dashboard/static/index.html")


# Quincy P2 dashboard
@app.get("/quincy")
def quincy_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/quincy/")


@app.get("/quincy/")
def quincy_dashboard():
    return FileResponse(f"{BASE_DIR}/dashboard/quincy.html")


@app.get("/quincy/midi/{path:path}")
def quincy_midi(path: str):
    fpath = os.path.join(BASE_DIR, "eval", "quincy_p2_eval", "midi", path)
    if not os.path.exists(fpath):
        return PlainTextResponse("Not found", status_code=404)
    from fastapi.responses import Response
    with open(fpath, "rb") as f:
        return Response(content=f.read(), media_type="audio/midi")
