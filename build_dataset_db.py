"""
전체 데이터셋 SQLite DB 구축
- /Volumes/data/score/ 모든 소스 스캔
- 파일 메타 추출 (경로, 해시, 형식, 크기)
- MD5 중복 제거
- 품질 필터링
- 결과: ~/musicscore/data/musicscore.db
"""

import os, sqlite3, hashlib, json
from pathlib import Path
from datetime import datetime
import pretty_midi

BASE_DIR = os.path.expanduser("~/musicscore")
DATA_DIR = os.path.expanduser("/Volumes/data/score")
DB_PATH = f"{BASE_DIR}/data/musicscore.db"
LOG_FILE = f"{BASE_DIR}/logs/build_db.log"
REPORT_FILE = f"{BASE_DIR}/data/db_report.json"

# 데이터셋 소스 경로들
SOURCES = {
    "gigamidi-nodrums": f"{DATA_DIR}/gigamidi/Final_GigaMIDI_V1.1_Final/train/training-V1.1-80%/no-drums",
    "gigamidi-allinst": f"{DATA_DIR}/gigamidi/Final_GigaMIDI_V1.1_Final/train/training-V1.1-80%/all-instruments-with-drums",
    "gigamidi-drums": f"{DATA_DIR}/gigamidi/Final_GigaMIDI_V1.1_Final/train/training-V1.1-80%/drums-only",
    "lakh": f"{DATA_DIR}/lakh/lmd_full",
    "pdmx": f"{DATA_DIR}/PDMX",
    "aria-midi": f"{DATA_DIR}/aria-midi/aria-midi-v1-ext/data",
    "maestro": f"{DATA_DIR}/maestro/maestro-v3.0.0/maestro-v3.0.0",
    "atepp": f"{DATA_DIR}/atepp",
    "pop909": f"{DATA_DIR}/pop909",
    "pop-k-midi": f"{DATA_DIR}/pop-k-midi",
    "asap": f"{DATA_DIR}/asap",
    "bitmidi": f"{DATA_DIR}/bitmidi",
    "musescore": f"{DATA_DIR}/musescore",
}

def make_logger():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    return log

log = make_logger()

def file_md5(path):
    """파일 MD5 해시 계산"""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except:
        return None

def get_midi_metadata(path):
    """MIDI 파일 메타 추출 (길이, 음표 수)"""
    try:
        pm = pretty_midi.PrettyMIDI(path)
        duration = pm.get_end_time()
        note_count = sum(len(instr.notes) for instr in pm.instruments)
        return duration, note_count
    except:
        return None, None

def get_file_size(path):
    """파일 크기 바이트"""
    try:
        return os.path.getsize(path)
    except:
        return 0

def init_db():
    """DB 초기화"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            path TEXT UNIQUE,
            source TEXT,
            file_type TEXT,
            size_bytes INTEGER,
            hash TEXT UNIQUE,
            duration_sec FLOAT,
            note_count INTEGER,
            quality_score FLOAT,
            created_at TIMESTAMP,
            processed BOOLEAN DEFAULT 0
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_source ON files(source)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_hash ON files(hash)")
    conn.commit()
    conn.close()

def load_existing_paths():
    """DB에 이미 등록된 path 목록 로드 (스킵용)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT path FROM files")
    paths = set(row[0] for row in c.fetchall())
    conn.close()
    return paths

def scan_source(source_name, source_path, existing_paths):
    """데이터셋 소스 스캔 — 이미 DB에 있는 path는 제외"""
    if not os.path.exists(source_path):
        log(f"⚠️  {source_name} 경로 없음: {source_path}")
        return []

    files = []
    total = 0
    skipped = 0
    for root, dirs, filenames in os.walk(source_path):
        for fn in filenames:
            if fn.startswith('.'):
                continue

            path = os.path.join(root, fn)
            ext = Path(fn).suffix.lower()

            if ext in ['.mid', '.midi', '.mxl', '.xml']:
                total += 1
                if path in existing_paths:
                    skipped += 1
                    continue
                files.append({
                    'path': path,
                    'source': source_name,
                    'file_type': ext.lstrip('.')
                })
                if len(files) % 10000 == 0:
                    log(f"  {source_name}: {len(files)} 신규 발견 (스캔 {total})...")

    log(f"✅ {source_name}: 총 {total} 파일, 신규 {len(files)}, 기존 {skipped} 스킵")
    return files

def compute_quality_score(file_type, size_bytes, duration_sec, note_count):
    """품질 점수 계산"""
    score = 1.0

    if file_type in ['mid', 'midi']:
        if duration_sec is None or duration_sec < 10 or duration_sec > 600:
            score -= 0.8
        if note_count is None or note_count < 50 or note_count > 50000:
            score -= 0.7
        if size_bytes < 1000 or size_bytes > 5000000:
            score -= 0.3

    return max(0.0, score)

def insert_files(files):
    """DB에 파일 삽입 — 배치 커밋"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 현재 max id 번호 확인
    c.execute("SELECT COUNT(*) FROM files")
    id_offset = c.fetchone()[0]

    duplicates = 0
    invalid = 0
    inserted = 0

    for i, f in enumerate(files):
        path = f['path']

        size = get_file_size(path)
        file_hash = file_md5(path)

        duration = None
        note_count = None
        if f['file_type'] in ['mid', 'midi']:
            duration, note_count = get_midi_metadata(path)

        quality = compute_quality_score(f['file_type'], size, duration, note_count)
        file_id = f"{f['source']}_{id_offset + i}"

        try:
            c.execute("""
                INSERT INTO files
                (id, path, source, file_type, size_bytes, hash, duration_sec, note_count, quality_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, path, f['source'], f['file_type'],
                size, file_hash, duration, note_count, quality,
                datetime.now().isoformat()
            ))
            inserted += 1
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                duplicates += 1
            else:
                invalid += 1

        if (i + 1) % 10000 == 0:
            conn.commit()
            log(f"  진행: {i+1}/{len(files)} (삽입: {inserted}, 중복: {duplicates}, 오류: {invalid})")

    conn.commit()
    conn.close()

    log(f"📊 DB 삽입 완료: {inserted} 신규, {duplicates} 중복(해시), {invalid} 오류")
    return inserted, duplicates, invalid

def analyze_db():
    """DB 통계"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT source, COUNT(*), SUM(size_bytes)/1024/1024/1024 FROM files GROUP BY source ORDER BY COUNT(*) DESC")
    sources = c.fetchall()

    c.execute("SELECT COUNT(*) FROM files WHERE quality_score >= 0.7")
    high_quality = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM files WHERE quality_score < 0.7 AND quality_score > 0")
    med_quality = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM files WHERE quality_score <= 0")
    low_quality = c.fetchone()[0]

    c.execute("SELECT file_type, COUNT(*) FROM files GROUP BY file_type")
    formats = c.fetchall()

    c.execute("SELECT COUNT(*) FROM files")
    total = c.fetchone()[0]

    conn.close()

    stats = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "sources": [
            {"name": s[0], "count": s[1], "size_gb": round(s[2] or 0, 2)}
            for s in sources
        ],
        "quality": {
            "high (>=0.7)": high_quality,
            "medium (0-0.7)": med_quality,
            "low (<=0)": low_quality
        },
        "formats": {f[0]: f[1] for f in formats}
    }

    return stats

def main():
    log("=" * 60)
    log("🚀 MusicScore DB 2차 스캔 시작 (신규 파일만)")
    log("=" * 60)

    init_db()

    # 기존 등록 path 로드
    existing_paths = load_existing_paths()
    log(f"📂 기존 DB: {len(existing_paths):,} 파일 등록됨 → 스킵 대상")

    # 모든 소스 스캔 (신규만)
    all_files = []
    for source_name, source_path in SOURCES.items():
        files = scan_source(source_name, source_path, existing_paths)
        all_files.extend(files)

    if not all_files:
        log("✅ 신규 파일 없음. DB 최신 상태.")
    else:
        log(f"\n📦 신규 {len(all_files):,} 파일 발견, DB 삽입 시작...")
        inserted, duplicates, invalid = insert_files(all_files)

    # 통계
    log("\n📊 DB 분석 중...")
    stats = analyze_db()

    with open(REPORT_FILE, "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    log(f"\n✅ 리포트 저장: {REPORT_FILE}")
    log("\n" + json.dumps(stats, indent=2, ensure_ascii=False))
    log("=" * 60)

if __name__ == "__main__":
    main()
