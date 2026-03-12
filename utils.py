"""공유 유틸리티 — 02, 03, 04 스크립트에서 공통 사용"""

import json, os
from datetime import datetime, date

BASE_DIR  = os.path.expanduser("~/musicscore")
URLS_FILE = f"{BASE_DIR}/data/urls.jsonl"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"


def make_logger(log_file):
    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        with open(log_file, "a") as f:
            f.write(line + "\n")
    return log


def load_done(done_file):
    if os.path.exists(done_file):
        with open(done_file) as f:
            return set(f.read().splitlines())
    return set()


def mark_done(done_file, item_id):
    with open(done_file, "a") as f:
        f.write(str(item_id) + "\n")


def load_daily(daily_file):
    today = str(date.today())
    if os.path.exists(daily_file):
        with open(daily_file) as f:
            d = json.load(f)
        if d.get("date") == today:
            return d.get("count", 0)
    return 0


def save_daily(daily_file, count):
    with open(daily_file, "w") as f:
        json.dump({"date": str(date.today()), "count": count}, f)


def iter_pending_urls(urls_file, done_ids, limit=None):
    """urls.jsonl에서 미완료 항목을 제너레이터로 반환 (메모리 절약)"""
    count = 0
    with open(urls_file) as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("id") and d["id"] not in done_ids:
                yield d
                count += 1
                if limit and count >= limit:
                    return
