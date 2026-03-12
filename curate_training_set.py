"""
Phase 2: 피아노 학습 데이터 큐레이션
- classify_piano.py 완료 후 실행
- 1단계: 피아노 곡 필터링 (piano_solo + piano_dominant)
- 2단계: 콘텐츠 기반 중복 제거 (content_fingerprint + MinHash/LSH)
- 3단계: 같은 곡 다른 연주 감지 (보존, 그룹핑)
- 4단계: 최종 학습셋 생성 (training_suitability 기준)
- 실행: nohup ./venv/bin/python3 curate_training_set.py > /dev/null 2>&1 &
- 모니터: tail ~/musicscore/logs/curate.log
"""

import os, sqlite3, json, hashlib
import numpy as np
from datetime import datetime
from collections import defaultdict
from datasketch import MinHash, MinHashLSH

BASE_DIR = os.path.expanduser("~/musicscore")
DB_PATH = f"{BASE_DIR}/data/musicscore.db"
LOG_FILE = f"{BASE_DIR}/logs/curate.log"
REPORT_FILE = f"{BASE_DIR}/data/curate_report.json"


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


def ensure_columns(conn):
    """큐레이션 컬럼 추가"""
    columns = {
        "dedup_group_id": "INTEGER",
        "dedup_status": "TEXT",        # unique, exact_dupe, near_dupe, same_piece_diff_perf
        "dedup_keep": "BOOLEAN",       # 그룹 내 대표 파일 여부
        "in_training_set": "BOOLEAN",  # 최종 학습셋 포함 여부
        "curated_at": "TIMESTAMP",
    }
    c = conn.cursor()
    c.execute("PRAGMA table_info(files)")
    existing = {row[1] for row in c.fetchall()}
    for col, dtype in columns.items():
        if col not in existing:
            c.execute(f"ALTER TABLE files ADD COLUMN {col} {dtype}")
            log(f"  컬럼 추가: {col} {dtype}")
    conn.commit()


def step1_filter_piano(conn):
    """1단계: 피아노 곡 필터링"""
    c = conn.cursor()

    c.execute("""
        SELECT COUNT(*) FROM files
        WHERE instrument_category IN ('piano_solo', 'piano_dominant')
        AND analyzed_at IS NOT NULL
    """)
    piano_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM files WHERE analyzed_at IS NOT NULL")
    total_analyzed = c.fetchone()[0]

    # 소스별 피아노 분포
    c.execute("""
        SELECT source, instrument_category, COUNT(*)
        FROM files
        WHERE analyzed_at IS NOT NULL
        GROUP BY source, instrument_category
        ORDER BY source, COUNT(*) DESC
    """)
    dist = c.fetchall()

    log(f"1단계: 피아노 필터링")
    log(f"  전체 분석 완료: {total_analyzed:,}")
    log(f"  피아노 곡 (solo+dominant): {piano_count:,} ({piano_count*100//max(total_analyzed,1)}%)")
    log(f"  소스별 분포:")
    for source, cat, cnt in dist:
        if cat in ('piano_solo', 'piano_dominant'):
            log(f"    {source}: {cat} = {cnt:,}")

    return piano_count


def step2_exact_dedup(conn):
    """2단계: content_fingerprint 기반 정확한 중복 제거"""
    c = conn.cursor()

    # 피아노 곡의 fingerprint 로드
    c.execute("""
        SELECT id, content_fingerprint, quality_score_v2, source
        FROM files
        WHERE instrument_category IN ('piano_solo', 'piano_dominant')
        AND content_fingerprint IS NOT NULL
        AND analyzed_at IS NOT NULL
    """)
    rows = c.fetchall()
    log(f"2단계: 콘텐츠 핑거프린트 중복 제거 (대상: {len(rows):,})")

    # fingerprint별 그룹핑
    fp_groups = defaultdict(list)
    for file_id, fp, quality, source in rows:
        fp_groups[fp].append((file_id, quality, source))

    unique_count = 0
    dupe_count = 0
    group_id = 0
    updates = []

    for fp, members in fp_groups.items():
        if len(members) == 1:
            # 유니크
            file_id = members[0][0]
            updates.append(("unique", None, True, file_id))
            unique_count += 1
        else:
            # 중복 그룹 — 품질 최고인 것을 keep
            group_id += 1
            members.sort(key=lambda x: x[1] or 0, reverse=True)
            for i, (file_id, quality, source) in enumerate(members):
                keep = (i == 0)  # 최고 품질만 keep
                updates.append(("exact_dupe", group_id, keep, file_id))
                dupe_count += 1

    # 배치 업데이트
    batch_size = 10000
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        c.executemany("""
            UPDATE files SET dedup_status=?, dedup_group_id=?, dedup_keep=?
            WHERE id=?
        """, batch)
        conn.commit()

    dupe_groups = group_id
    log(f"  유니크: {unique_count:,}")
    log(f"  중복 파일: {dupe_count:,} ({dupe_groups:,} 그룹)")
    log(f"  보존: {unique_count + dupe_groups:,}")

    return unique_count, dupe_count, dupe_groups


def step3_near_dedup_lsh(conn):
    """3단계: MinHash/LSH 기반 유사 중복 탐지"""
    c = conn.cursor()

    # dedup_keep=True 또는 unique인 피아노 곡만
    c.execute("""
        SELECT id, content_fingerprint
        FROM files
        WHERE instrument_category IN ('piano_solo', 'piano_dominant')
        AND (dedup_status = 'unique' OR dedup_keep = 1)
        AND content_fingerprint IS NOT NULL
    """)
    rows = c.fetchall()
    log(f"3단계: MinHash/LSH 유사 중복 탐지 (대상: {len(rows):,})")

    if len(rows) < 100:
        log("  파일 수 부족, 스킵")
        return 0

    # fingerprint를 n-gram으로 분해해서 MinHash 생성
    lsh = MinHashLSH(threshold=0.8, num_perm=128)
    minhashes = {}

    for i, (file_id, fp) in enumerate(rows):
        m = MinHash(num_perm=128)
        # fingerprint의 4-char n-grams
        for j in range(len(fp) - 3):
            m.update(fp[j:j+4].encode('utf8'))
        try:
            lsh.insert(file_id, m)
        except ValueError:
            pass  # 이미 존재 (동일 MinHash)
        minhashes[file_id] = m

        if (i + 1) % 50000 == 0:
            log(f"  LSH 인덱싱: {i+1:,}/{len(rows):,}")

    # 유사 그룹 탐지
    near_dupe_groups = []
    checked = set()

    for file_id, m in minhashes.items():
        if file_id in checked:
            continue
        result = lsh.query(m)
        if len(result) > 1:
            near_dupe_groups.append(result)
            checked.update(result)

    log(f"  유사 중복 그룹: {len(near_dupe_groups):,}")

    # DB 업데이트 — 유사 중복 그룹 내 최고 품질만 keep
    near_dupe_count = 0
    updates = []
    c2 = conn.cursor()

    for group in near_dupe_groups:
        # 그룹 내 품질 조회
        placeholders = ','.join('?' * len(group))
        c2.execute(f"""
            SELECT id, quality_score_v2 FROM files
            WHERE id IN ({placeholders})
            ORDER BY quality_score_v2 DESC
        """, list(group))
        members = c2.fetchall()

        if len(members) <= 1:
            continue

        for i, (fid, q) in enumerate(members):
            if i == 0:
                updates.append(("near_dupe", True, fid))
            else:
                updates.append(("near_dupe", False, fid))
                near_dupe_count += 1

    if updates:
        c.executemany("""
            UPDATE files SET dedup_status=?, dedup_keep=?
            WHERE id=?
        """, updates)
        conn.commit()

    log(f"  유사 중복으로 제거: {near_dupe_count:,}")
    return near_dupe_count


def step4_curate_training_set(conn):
    """4단계: 최종 학습셋 큐레이션"""
    c = conn.cursor()

    # 조건: 피아노 solo/dominant + 중복 아닌 것(keep) + 최소 품질
    MIN_SUITABILITY = 40.0  # training_suitability >= 40

    c.execute("""
        UPDATE files SET in_training_set = 0
        WHERE in_training_set IS NOT NULL
    """)

    c.execute("""
        UPDATE files SET in_training_set = 1, curated_at = ?
        WHERE instrument_category IN ('piano_solo', 'piano_dominant')
        AND (dedup_status = 'unique' OR dedup_keep = 1)
        AND training_suitability >= ?
        AND analyzed_at IS NOT NULL
    """, (datetime.now().isoformat(), MIN_SUITABILITY))
    conn.commit()

    c.execute("SELECT COUNT(*) FROM files WHERE in_training_set = 1")
    training_count = c.fetchone()[0]

    # 학습셋 통계
    c.execute("""
        SELECT source, COUNT(*),
               ROUND(AVG(training_suitability), 1),
               ROUND(AVG(quality_score_v2), 1)
        FROM files WHERE in_training_set = 1
        GROUP BY source ORDER BY COUNT(*) DESC
    """)
    by_source = c.fetchall()

    c.execute("""
        SELECT difficulty_label, COUNT(*)
        FROM files WHERE in_training_set = 1
        GROUP BY difficulty_label ORDER BY COUNT(*) DESC
    """)
    by_difficulty = c.fetchall()

    c.execute("""
        SELECT velocity_quality, COUNT(*)
        FROM files WHERE in_training_set = 1
        GROUP BY velocity_quality ORDER BY COUNT(*) DESC
    """)
    by_velocity = c.fetchall()

    c.execute("""
        SELECT timing_quality, COUNT(*)
        FROM files WHERE in_training_set = 1
        GROUP BY timing_quality ORDER BY COUNT(*) DESC
    """)
    by_timing = c.fetchall()

    c.execute("""
        SELECT pedal_type, COUNT(*)
        FROM files WHERE in_training_set = 1
        GROUP BY pedal_type ORDER BY COUNT(*) DESC
    """)
    by_pedal = c.fetchall()

    log(f"4단계: 최종 학습셋 큐레이션 (suitability >= {MIN_SUITABILITY})")
    log(f"  학습셋 크기: {training_count:,}")
    log(f"  소스별:")
    for source, cnt, avg_ts, avg_q in by_source:
        log(f"    {source}: {cnt:,} (avg suitability={avg_ts}, quality={avg_q})")
    log(f"  난이도별: {dict(by_difficulty)}")
    log(f"  Velocity: {dict(by_velocity)}")
    log(f"  Timing: {dict(by_timing)}")
    log(f"  Pedal: {dict(by_pedal)}")

    return {
        "training_set_size": training_count,
        "min_suitability": MIN_SUITABILITY,
        "by_source": [{"source": s, "count": c, "avg_suitability": t, "avg_quality": q}
                       for s, c, t, q in by_source],
        "by_difficulty": dict(by_difficulty),
        "by_velocity": dict(by_velocity),
        "by_timing": dict(by_timing),
        "by_pedal": dict(by_pedal),
    }


def main():
    log("=" * 60)
    log("Phase 2: 피아노 학습 데이터 큐레이션 시작")
    log("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)

    # 사전 검증: classify_piano.py 완료 확인
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM files WHERE analyzed_at IS NOT NULL")
    analyzed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM files")
    total = c.fetchone()[0]

    if analyzed == 0:
        log("❌ 분류가 완료되지 않았습니다. classify_piano.py를 먼저 실행하세요.")
        conn.close()
        return

    log(f"DB 현황: 전체 {total:,} / 분석 완료 {analyzed:,} ({analyzed*100//total}%)")

    # 1단계
    piano_count = step1_filter_piano(conn)

    if piano_count == 0:
        log("❌ 피아노 곡이 없습니다.")
        conn.close()
        return

    # 2단계
    unique, dupes, groups = step2_exact_dedup(conn)

    # 3단계
    near_dupes = step3_near_dedup_lsh(conn)

    # 4단계
    training_stats = step4_curate_training_set(conn)

    conn.close()

    # 최종 리포트
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_files": total,
        "analyzed": analyzed,
        "piano_count": piano_count,
        "exact_unique": unique,
        "exact_dupes": dupes,
        "exact_dupe_groups": groups,
        "near_dupes_removed": near_dupes,
        "training_set": training_stats,
    }
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log(f"\n{'='*60}")
    log(f"큐레이션 완료!")
    log(f"  전체: {total:,} → 피아노: {piano_count:,} → 중복제거: {unique + groups:,} → 학습셋: {training_stats['training_set_size']:,}")
    log(f"리포트: {REPORT_FILE}")
    log(f"{'='*60}")


if __name__ == "__main__":
    main()
