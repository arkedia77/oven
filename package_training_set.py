"""
학습셋 패키징: DB에서 in_training_set=1인 파일들을 tar.gz로 묶기
- 티어별 분리: tier1(80+), tier2(60-79), tier3(40-59)
- 실행: ./venv/bin/python3 package_training_set.py
- 모니터: tail ~/musicscore/logs/package.log
"""

import os, sqlite3, tarfile, json
from datetime import datetime

BASE_DIR = os.path.expanduser("~/musicscore")
DB_PATH = f"{BASE_DIR}/data/musicscore.db"
OUT_DIR = f"{BASE_DIR}/data/training_packages"
LOG_FILE = f"{BASE_DIR}/logs/package.log"
GDRIVE_DIR = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-beomjun.lee@gmail.com/내 드라이브/1. work/claude/musicscore/50cli/training_data"
)

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def package_tier(conn, tier_name, condition):
    c = conn.cursor()
    c.execute(f"""
        SELECT path, source, training_suitability
        FROM files WHERE in_training_set=1 AND {condition}
        ORDER BY training_suitability DESC
    """)
    rows = c.fetchall()
    if not rows:
        log(f"  {tier_name}: 0곡, 스킵")
        return 0

    tar_path = f"{OUT_DIR}/liszt_{tier_name}.tar.gz"
    log(f"  {tier_name}: {len(rows):,}곡 → {tar_path}")

    missing = 0
    packed = 0
    with tarfile.open(tar_path, "w:gz") as tar:
        for i, (path, source, ts) in enumerate(rows):
            if not os.path.exists(path):
                missing += 1
                continue
            # tar 내부 경로: tier/source/filename
            basename = os.path.basename(path)
            arcname = f"{tier_name}/{source}/{basename}"
            tar.add(path, arcname=arcname)
            packed += 1
            if (i + 1) % 50000 == 0:
                log(f"    진행: {i+1:,}/{len(rows):,}")

    size_gb = os.path.getsize(tar_path) / 1e9
    log(f"    완료: {packed:,}곡 패킹, {missing:,} 누락, {size_gb:.1f} GB")
    return packed


def main():
    log("=" * 60)
    log("학습셋 패키징 시작")
    log("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    tiers = [
        ("tier1_premium", "training_suitability >= 80"),
        ("tier2_good", "training_suitability >= 60 AND training_suitability < 80"),
        ("tier3_basic", "training_suitability >= 40 AND training_suitability < 60"),
    ]

    total = 0
    for tier_name, condition in tiers:
        total += package_tier(conn, tier_name, condition)

    conn.close()

    # Google Drive로 복사 (마운트 되어 있으면)
    if os.path.exists(os.path.dirname(GDRIVE_DIR)):
        os.makedirs(GDRIVE_DIR, exist_ok=True)
        log(f"\nGoogle Drive 복사 시작: {GDRIVE_DIR}")
        for f in os.listdir(OUT_DIR):
            if f.endswith(".tar.gz"):
                src = f"{OUT_DIR}/{f}"
                dst = f"{GDRIVE_DIR}/{f}"
                log(f"  복사: {f} ({os.path.getsize(src)/1e9:.1f} GB)")
                import shutil
                shutil.copy2(src, dst)
        log("Google Drive 복사 완료")
    else:
        log("Google Drive 미마운트 — 수동 복사 필요")

    log(f"\n패키징 완료: 총 {total:,}곡")


if __name__ == "__main__":
    main()
