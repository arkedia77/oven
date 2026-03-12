"""
BitMIDI 진행상황 모니터 (3시간마다 launchd 실행)
- bitmidi_done.txt 카운트 체크
- 3시간 전 대비 증가 없으면 → agent-comm에 재시작 태스크 push
- 정상이면 → 진행 리포트만 push
"""

import os, json, subprocess
from datetime import datetime

BASE_DIR    = os.path.expanduser("~/musicscore")
DONE_FILE   = f"{BASE_DIR}/data/bitmidi_done.txt"
STATE_FILE  = f"{BASE_DIR}/data/bitmidi_monitor_state.json"
AGENT_COMM  = os.path.expanduser("~/projects/agent-comm")
RESULTS_DIR = f"{AGENT_COMM}/musicscore/results"
TASKS_DIR   = f"{AGENT_COMM}/musicscore/tasks"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_count": 0, "last_check": ""}


def save_state(count):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_count": count, "last_check": datetime.now().isoformat()}, f)


def get_done_count():
    if not os.path.exists(DONE_FILE):
        return 0
    with open(DONE_FILE) as f:
        return sum(1 for line in f if line.strip())


def git_push(msg):
    subprocess.run(["git", "-C", AGENT_COMM, "pull", "--rebase"], check=True)
    subprocess.run(["git", "-C", AGENT_COMM, "add", "musicscore/"], check=True)
    result = subprocess.run(["git", "-C", AGENT_COMM, "diff", "--cached", "--quiet"])
    if result.returncode != 0:
        subprocess.run(["git", "-C", AGENT_COMM, "commit", "-m", msg], check=True)
        subprocess.run(["git", "-C", AGENT_COMM, "push"], check=True)


def push_report(count, last_count, stalled):
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    report = {
        "task_id": f"{ts}_bitmidi_monitor_report",
        "from": "reklcli",
        "to": "mukl",
        "created_at": now.isoformat(),
        "type": "monitor_report",
        "title": "BitMIDI 진행 모니터링",
        "current_count": count,
        "delta_3h": count - last_count,
        "stalled": stalled,
        "expected_total": 113229,
        "progress_pct": round(count / 113229 * 100, 2),
    }

    if stalled:
        report["action"] = "재시작 요청"
        report["instruction"] = "nohup python3 ~/musicscore/04_bitmidi.py >> ~/musicscore/logs/bitmidi.log 2>&1 &"

    path = f"{RESULTS_DIR}/{ts}_bitmidi_report.json"
    with open(path, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    status = "STALLED - 재시작 요청" if stalled else f"+{count - last_count}개 정상 진행"
    git_push(f"BitMIDI 모니터 [{count:,}/{113229:,}] {status}")
    print(f"[{now.strftime('%H:%M:%S')}] BitMIDI {count:,}개 | {status}")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    state = load_state()
    count = get_done_count()
    last_count = state["last_count"]

    stalled = (count - last_count) == 0 and count < 113229

    push_report(count, last_count, stalled)
    save_state(count)


main()
