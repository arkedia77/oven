"""
Phase 1: 피아노 분류 + 품질 분석
- symusic (Rust) 기반 고속 스캔
- DB files 테이블에 분류 컬럼 추가 후 업데이트
- 실행: nohup ./venv/bin/python3 classify_piano.py > /dev/null 2>&1 &
- 모니터: tail ~/musicscore/logs/classify.log
"""

import os, sqlite3, json, hashlib, traceback, gc
import multiprocessing as mp
import numpy as np
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.expanduser("~/musicscore")
DB_PATH = f"{BASE_DIR}/data/musicscore.db"
LOG_FILE = f"{BASE_DIR}/logs/classify.log"
REPORT_FILE = f"{BASE_DIR}/data/classify_report.json"
BATCH_SIZE = 1000  # 16GB RAM 대응: 5000→1000

# symusic import
import symusic

PIANO_PROGRAMS = set(range(0, 8))  # GM piano family


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
    """분류 컬럼 추가 (없으면)"""
    columns = {
        "instrument_category": "TEXT",      # piano_solo, piano_dominant, piano_mixed, has_piano, no_piano
        "piano_ratio": "FLOAT",
        "num_instruments": "INTEGER",
        "has_drums": "BOOLEAN",
        "velocity_mean": "FLOAT",
        "velocity_std": "FLOAT",
        "velocity_quality": "TEXT",         # flat, step_quantized, low_expression, moderate_expression, high_expression
        "timing_deviation_mean": "FLOAT",
        "timing_quality": "TEXT",           # perfectly_quantized, lightly_humanized, human_performance, loose_timing
        "has_pedal": "BOOLEAN",
        "pedal_type": "TEXT",               # none, binary, continuous
        "pedal_event_count": "INTEGER",
        "pitch_range": "INTEGER",
        "avg_notes_per_second": "FLOAT",
        "avg_polyphony": "FLOAT",
        "pitch_entropy": "FLOAT",
        "avg_tempo": "FLOAT",
        "tempo_changes": "INTEGER",
        "difficulty_level": "INTEGER",      # 1-10
        "difficulty_label": "TEXT",
        "content_fingerprint": "TEXT",
        "quality_score_v2": "FLOAT",        # 0-100 comprehensive
        "training_suitability": "FLOAT",    # 0-100 piano AI training
        "analyzed_at": "TIMESTAMP",
    }
    c = conn.cursor()
    c.execute("PRAGMA table_info(files)")
    existing = {row[1] for row in c.fetchall()}

    for col, dtype in columns.items():
        if col not in existing:
            c.execute(f"ALTER TABLE files ADD COLUMN {col} {dtype}")
            log(f"  컬럼 추가: {col} {dtype}")

    # 인덱스
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_instrument_category ON files(instrument_category)",
        "CREATE INDEX IF NOT EXISTS idx_quality_v2 ON files(quality_score_v2)",
        "CREATE INDEX IF NOT EXISTS idx_training ON files(training_suitability)",
        "CREATE INDEX IF NOT EXISTS idx_fingerprint ON files(content_fingerprint)",
        "CREATE INDEX IF NOT EXISTS idx_difficulty ON files(difficulty_level)",
    ]
    for idx in indexes:
        c.execute(idx)
    conn.commit()


def analyze_file(path):
    """symusic으로 단일 파일 분석 — 모든 지표 추출"""
    try:
        return _analyze_file_inner(path)
    except Exception:
        return None


def _analyze_file_inner(path):
    try:
        s = symusic.Score(path)
    except:
        return None

    # --- 악기 분류 ---
    non_drum_tracks = [t for t in s.tracks if not t.is_drum and len(t.notes) > 0]
    drum_tracks = [t for t in s.tracks if t.is_drum and len(t.notes) > 0]

    if not non_drum_tracks:
        return None

    piano_notes = 0
    non_piano_notes = 0
    for t in non_drum_tracks:
        n = len(t.notes)
        if t.program in PIANO_PROGRAMS:
            piano_notes += n
        else:
            non_piano_notes += n
    drum_notes = sum(len(t.notes) for t in drum_tracks)

    total_melodic = piano_notes + non_piano_notes
    if total_melodic == 0:
        return None

    piano_ratio = piano_notes / total_melodic

    if piano_ratio >= 0.95 and non_piano_notes < 10 and drum_notes < 10:
        instrument_category = "piano_solo"
    elif piano_ratio >= 0.80:
        instrument_category = "piano_dominant"
    elif piano_ratio >= 0.30:
        instrument_category = "piano_mixed"
    elif piano_ratio > 0:
        instrument_category = "has_piano"
    else:
        instrument_category = "no_piano"

    has_drums = len(drum_tracks) > 0
    num_instruments = len(non_drum_tracks)

    # --- 초 단위 변환 ---
    s_sec = s.to("second")

    # 피아노 트랙 노트 수집 (초 단위)
    piano_track_indices = [i for i, t in enumerate(s.tracks)
                          if not t.is_drum and len(t.notes) > 0 and t.program in PIANO_PROGRAMS]
    all_notes = []
    for i in piano_track_indices:
        all_notes.extend(s_sec.tracks[i].notes)

    if not all_notes:
        # 피아노 트랙 없으면 모든 비드럼 트랙
        for i, t in enumerate(s_sec.tracks):
            if not s.tracks[i].is_drum and len(t.notes) > 0:
                all_notes.extend(t.notes)

    if len(all_notes) < 5:
        return None

    duration_sec = s_sec.end()
    if duration_sec <= 0:
        return None

    # --- Velocity 분석 ---
    velocities = [n.velocity for n in all_notes]
    vel_mean = float(np.mean(velocities))
    vel_std = float(np.std(velocities))

    if vel_std < 2.0:
        velocity_quality = "flat"
    elif vel_std < 8.0:
        velocity_quality = "low_expression"
    elif vel_std < 20.0:
        velocity_quality = "moderate_expression"
    else:
        velocity_quality = "high_expression"

    # step_quantized 체크
    unique_vel = set(velocities)
    if len(unique_vel) <= 5 and vel_std >= 2.0:
        velocity_quality = "step_quantized"

    # --- Timing 분석 (16분음표 그리드 기준) ---
    tempo_list = s.tempos if s.tempos else []
    avg_tempo_bpm = float(np.mean([t.qpm for t in tempo_list])) if tempo_list else 120.0
    beat_dur = 60.0 / avg_tempo_bpm
    grid_16th = beat_dur / 4

    onsets_sec = sorted([n.time for n in all_notes[:2000]])  # 이미 초 단위
    deviations = []
    for onset in onsets_sec:
        nearest = round(onset / grid_16th) * grid_16th
        deviations.append(abs(onset - nearest))

    timing_dev_mean = float(np.mean(deviations)) if deviations else 0.0

    if timing_dev_mean < 0.005:
        timing_quality = "perfectly_quantized"
    elif timing_dev_mean < 0.015:
        timing_quality = "lightly_humanized"
    elif timing_dev_mean < 0.040:
        timing_quality = "human_performance"
    else:
        timing_quality = "loose_timing"

    # --- 페달 분석 ---
    pedal_events = 0
    pedal_type = "none"
    has_pedal = False

    # 원본(tick) 트랙에서 CC 분석
    piano_tracks_orig = [s.tracks[i] for i in piano_track_indices] if piano_track_indices else non_drum_tracks
    for t in piano_tracks_orig:
        # CC64 = sustain pedal
        cc64 = [c for c in t.controls if c.number == 64]
        pedal_events += len(cc64)
        if cc64:
            has_pedal = True
            vals = set(c.value for c in cc64)
            if vals - {0, 127}:
                pedal_type = "continuous"
            elif pedal_type != "continuous":
                pedal_type = "binary"

    # --- 피치 분석 ---
    pitches = [n.pitch for n in all_notes]
    pitch_range = max(pitches) - min(pitches)

    pitch_classes = [p % 12 for p in pitches]
    pitch_hist = np.bincount(pitch_classes, minlength=12).astype(float)
    pitch_hist /= pitch_hist.sum() + 1e-9
    pitch_entropy = float(-np.sum(pitch_hist * np.log2(pitch_hist + 1e-9)))

    # --- 밀도/폴리포니 ---
    avg_nps = len(all_notes) / duration_sec

    # 폴리포니: 50ms 윈도우로 그룹핑 (초 단위)
    onset_groups = defaultdict(int)
    for n in all_notes:
        q = round(n.time * 20)  # 50ms 퀀타이즈
        onset_groups[q] += 1
    avg_polyphony = float(np.mean(list(onset_groups.values()))) if onset_groups else 1.0

    # --- 템포 ---
    tempo_changes = len(s.tempos)

    # --- 난이도 ---
    diff = 1.0
    diff += min(avg_nps / 3, 2.0)
    # peak density (1초 윈도우)
    sec_groups = defaultdict(int)
    for n in all_notes:
        sec_groups[int(n.time)] += 1
    if sec_groups:
        peak_nps = max(sec_groups.values())
        diff += min(peak_nps / 15, 2.0)
    # fast passages (초 단위, 100ms 미만)
    sorted_onsets = sorted(n.time for n in all_notes)
    if len(sorted_onsets) > 1:
        iois = np.diff(sorted_onsets)
        fast_ratio = float(np.sum(iois < 0.1) / len(iois))
        diff += min(fast_ratio * 3, 1.5)
    # pitch range
    diff += min(pitch_range / 60, 1.5)

    difficulty_level = max(1, min(10, int(round(diff))))
    diff_labels = {
        1: "beginner", 2: "beginner", 3: "elementary",
        4: "intermediate", 5: "intermediate", 6: "upper_intermediate",
        7: "advanced", 8: "advanced", 9: "virtuoso", 10: "virtuoso"
    }
    difficulty_label = diff_labels.get(difficulty_level, "unknown")

    # --- 콘텐츠 핑거프린트 ---
    sorted_notes = sorted(all_notes, key=lambda n: (n.time, n.pitch))
    intervals = []
    for i in range(1, min(len(sorted_notes), 500)):
        intervals.append(sorted_notes[i].pitch - sorted_notes[i-1].pitch)
    fp_str = ",".join(str(iv) for iv in intervals)
    content_fingerprint = hashlib.sha256(fp_str.encode()).hexdigest()[:32]

    # --- 종합 품질 (0-100) ---
    q = 0.0
    # duration (0-10)
    if 30 <= duration_sec <= 600:
        q += 10
    elif 10 <= duration_sec <= 30 or 600 < duration_sec <= 1200:
        q += 5
    else:
        q += 1
    # note count (0-10)
    nc = len(all_notes)
    if nc >= 200:
        q += 10
    elif nc >= 50:
        q += 5
    else:
        q += 2
    # velocity (0-20)
    vel_scores = {"flat": 0, "step_quantized": 2, "low_expression": 8,
                  "moderate_expression": 15, "high_expression": 20}
    q += vel_scores.get(velocity_quality, 0)
    # timing (0-20)
    tim_scores = {"perfectly_quantized": 2, "lightly_humanized": 10,
                  "human_performance": 20, "loose_timing": 12}
    q += tim_scores.get(timing_quality, 0)
    # pedal (0-15)
    if pedal_type == "continuous":
        q += 15
    elif pedal_type == "binary":
        q += 10
    # pitch range (0-10)
    if pitch_range >= 60:
        q += 10
    elif pitch_range >= 36:
        q += 7
    else:
        q += 3
    # metadata (0-10)
    if s.time_signatures:
        q += 5
    if s.key_signatures:
        q += 5
    # polyphony (0-5)
    if avg_polyphony > 2.0:
        q += 5
    elif avg_polyphony > 1.3:
        q += 3

    quality_score_v2 = min(q, 100)

    # --- training suitability (피아노 엔진 학습 적합도) ---
    ts = quality_score_v2
    if instrument_category == "piano_solo":
        ts *= 1.0
    elif instrument_category == "piano_dominant":
        ts *= 0.8
    elif instrument_category == "piano_mixed":
        ts *= 0.4
    else:
        ts *= 0.1
    training_suitability = min(ts, 100)

    return {
        "instrument_category": instrument_category,
        "piano_ratio": round(piano_ratio, 4),
        "num_instruments": num_instruments,
        "has_drums": has_drums,
        "velocity_mean": round(vel_mean, 2),
        "velocity_std": round(vel_std, 2),
        "velocity_quality": velocity_quality,
        "timing_deviation_mean": round(timing_dev_mean, 6),
        "timing_quality": timing_quality,
        "has_pedal": has_pedal,
        "pedal_type": pedal_type,
        "pedal_event_count": pedal_events,
        "pitch_range": pitch_range,
        "avg_notes_per_second": round(avg_nps, 2),
        "avg_polyphony": round(avg_polyphony, 2),
        "pitch_entropy": round(pitch_entropy, 4),
        "avg_tempo": round(avg_tempo_bpm, 2),
        "tempo_changes": tempo_changes,
        "difficulty_level": difficulty_level,
        "difficulty_label": difficulty_label,
        "content_fingerprint": content_fingerprint,
        "quality_score_v2": round(quality_score_v2, 2),
        "training_suitability": round(training_suitability, 2),
        "analyzed_at": datetime.now().isoformat(),
    }


def _worker_analyze(path):
    """워커 프로세스에서 실행 — segfault 격리"""
    return analyze_file(path)


def _make_error_tuple(file_id):
    return ("no_piano", 0, 0, False,
            None, None, None, None, None,
            False, "none", 0, 0, 0, 0, 0,
            0, 0, 1, "beginner", None,
            0, 0, datetime.now().isoformat(), file_id)


def _make_result_tuple(result, file_id):
    return (
        result["instrument_category"],
        result["piano_ratio"],
        result["num_instruments"],
        result["has_drums"],
        result["velocity_mean"],
        result["velocity_std"],
        result["velocity_quality"],
        result["timing_deviation_mean"],
        result["timing_quality"],
        result["has_pedal"],
        result["pedal_type"],
        result["pedal_event_count"],
        result["pitch_range"],
        result["avg_notes_per_second"],
        result["avg_polyphony"],
        result["pitch_entropy"],
        result["avg_tempo"],
        result["tempo_changes"],
        result["difficulty_level"],
        result["difficulty_label"],
        result["content_fingerprint"],
        result["quality_score_v2"],
        result["training_suitability"],
        result["analyzed_at"],
        file_id,
    )


def main():
    log("=" * 60)
    log("Phase 1: 피아노 분류 + 품질 분석 시작 (subprocess 격리 모드)")
    log("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)

    # 미분석 파일 조회 (analyzed_at IS NULL)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM files WHERE analyzed_at IS NULL AND file_type IN ('mid', 'midi')")
    total = c.fetchone()[0]
    log(f"분석 대상: {total:,} 파일 (MIDI only, 미분석)")

    if total == 0:
        log("모든 파일 분석 완료 상태.")
        conn.close()
        return

    processed = 0
    errors = 0
    crashes = 0
    categories = defaultdict(int)

    # Pool: maxtasksperchild=50으로 메모리 누수 방지, 워커 crash 시 자동 재시작
    pool = mp.Pool(processes=2, maxtasksperchild=50)

    while True:
        c.execute("""
            SELECT id, path FROM files
            WHERE analyzed_at IS NULL AND file_type IN ('mid', 'midi')
            LIMIT ?
        """, (BATCH_SIZE,))
        batch = c.fetchall()
        if not batch:
            break

        # 비동기 분석 (타임아웃 10초/파일)
        paths = [path for _, path in batch]
        async_results = []
        for path in paths:
            ar = pool.apply_async(_worker_analyze, (path,))
            async_results.append(ar)

        updates = []
        for (file_id, path), ar in zip(batch, async_results):
            try:
                result = ar.get(timeout=30)  # 30초 타임아웃
            except mp.TimeoutError:
                result = None
                crashes += 1
            except Exception:
                result = None
                crashes += 1

            if result is None:
                errors += 1
                updates.append(_make_error_tuple(file_id))
            else:
                categories[result["instrument_category"]] += 1
                updates.append(_make_result_tuple(result, file_id))

            processed += 1

        c.executemany("""
            UPDATE files SET
                instrument_category=?, piano_ratio=?, num_instruments=?, has_drums=?,
                velocity_mean=?, velocity_std=?, velocity_quality=?,
                timing_deviation_mean=?, timing_quality=?,
                has_pedal=?, pedal_type=?, pedal_event_count=?,
                pitch_range=?, avg_notes_per_second=?, avg_polyphony=?, pitch_entropy=?,
                avg_tempo=?, tempo_changes=?,
                difficulty_level=?, difficulty_label=?,
                content_fingerprint=?,
                quality_score_v2=?, training_suitability=?,
                analyzed_at=?
            WHERE id=?
        """, updates)
        conn.commit()
        del updates
        gc.collect()

        log(f"  진행: {processed:,}/{total:,} ({processed*100//total}%) | 에러: {errors:,} | "
            f"크래시: {crashes:,} | "
            f"piano_solo: {categories.get('piano_solo',0):,} | "
            f"piano_dom: {categories.get('piano_dominant',0):,} | "
            f"no_piano: {categories.get('no_piano',0):,}")

    pool.close()
    pool.join()
    conn.close()

    # 최종 리포트
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_processed": processed,
        "errors": errors,
        "crashes": crashes,
        "categories": dict(categories),
    }
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log(f"\n{'='*60}")
    log(f"완료! 총 {processed:,} 파일 분석")
    log(f"카테고리 분포: {json.dumps(dict(categories), indent=2)}")
    log(f"에러: {errors:,} | 크래시: {crashes:,}")
    log(f"리포트: {REPORT_FILE}")
    log(f"{'='*60}")


if __name__ == "__main__":
    main()
