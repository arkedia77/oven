"""
MXL → MIDI 변환 + classify_piano 분석
- pdmx의 미분석 MXL 254K를 MIDI로 변환 후 피아노 분류
- subprocess 격리 (music21 크래시 방지) + timeout
- 실행: nohup ./venv/bin/python3 convert_mxl_to_midi.py > /dev/null 2>&1 &
- 모니터: tail ~/musicscore/logs/convert_mxl.log
"""

import os, sqlite3, traceback, gc
import multiprocessing as mp
from datetime import datetime

BASE_DIR = os.path.expanduser("~/musicscore")
DB_PATH = f"{BASE_DIR}/data/musicscore.db"
LOG_FILE = f"{BASE_DIR}/logs/convert_mxl.log"
MIDI_OUT_DIR = "/Volumes/data/score/PDMX/converted_midi"
BATCH_SIZE = 200
NUM_WORKERS = 1  # 단일 워커 + subprocess 격리
TIMEOUT_PER_FILE = 30  # 초


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


def convert_and_analyze(args):
    """단일 파일 변환 + 분석 (subprocess에서 실행)"""
    file_id, mxl_path = args
    try:
        from music21 import converter
        import symusic
        import numpy as np
        import hashlib

        if not os.path.exists(mxl_path):
            return (file_id, "missing", None)

        # MXL → MIDI 변환
        score = converter.parse(mxl_path)
        basename = os.path.splitext(os.path.basename(mxl_path))[0] + ".mid"
        # 서브폴더 구조 유지
        parts = mxl_path.split("/")
        sub1 = parts[-3] if len(parts) >= 3 else "x"
        sub2 = parts[-2] if len(parts) >= 2 else "x"
        out_dir = os.path.join(MIDI_OUT_DIR, sub1, sub2)
        os.makedirs(out_dir, exist_ok=True)
        midi_path = os.path.join(out_dir, basename)

        score.write("midi", fp=midi_path)

        # symusic으로 분석
        s = symusic.Score(midi_path)
        s_sec = s.to("second")

        PIANO_PROGRAMS = set(range(0, 8))
        tracks = s.tracks
        total_notes = sum(len(t.notes) for t in tracks)

        if total_notes == 0:
            return (file_id, "empty", None)

        # 악기 분류
        piano_notes = 0
        non_piano_notes = 0
        has_drums = False
        instruments = set()

        for t in tracks:
            if t.is_drum:
                has_drums = True
                continue
            instruments.add(t.program)
            if t.program in PIANO_PROGRAMS:
                piano_notes += len(t.notes)
            else:
                non_piano_notes += len(t.notes)

        piano_ratio = piano_notes / max(total_notes, 1)
        if piano_ratio >= 0.95:
            category = "piano_solo"
        elif piano_ratio >= 0.7:
            category = "piano_dominant"
        elif piano_ratio >= 0.3:
            category = "piano_mixed"
        elif piano_notes > 0:
            category = "has_piano"
        else:
            category = "no_piano"

        # velocity 분석
        all_vel = []
        for t in tracks:
            if not t.is_drum:
                all_vel.extend([n.velocity for n in t.notes])

        if not all_vel:
            return (file_id, "no_notes", None)

        vel_arr = np.array(all_vel, dtype=np.float32)
        vel_mean = float(np.mean(vel_arr))
        vel_std = float(np.std(vel_arr))

        if vel_std < 2:
            vel_quality = "flat"
        elif vel_std < 8:
            vel_quality = "step_quantized"
        elif vel_std < 15:
            vel_quality = "low_expression"
        elif vel_std < 25:
            vel_quality = "moderate_expression"
        else:
            vel_quality = "high_expression"

        # timing 분석
        all_onsets = []
        for t in s_sec.tracks:
            if not t.is_drum:
                all_onsets.extend([n.start for n in t.notes])
        all_onsets.sort()

        if len(all_onsets) > 1:
            iois = np.diff(all_onsets)
            iois = iois[iois > 0.01]
            if len(iois) > 0:
                ioi_std = float(np.std(iois % 0.25)) if len(iois) > 10 else 0.1
                if ioi_std < 0.005:
                    timing_quality = "perfectly_quantized"
                elif ioi_std < 0.02:
                    timing_quality = "lightly_humanized"
                elif ioi_std < 0.06:
                    timing_quality = "human_performance"
                else:
                    timing_quality = "loose_timing"
                timing_dev = ioi_std
            else:
                timing_quality = "perfectly_quantized"
                timing_dev = 0.0
        else:
            timing_quality = "perfectly_quantized"
            timing_dev = 0.0

        # pedal 분석
        has_pedal = False
        pedal_type = "none"
        for t in tracks:
            if hasattr(t, "pedals") and len(t.pedals) > 0:
                has_pedal = True
                pedal_type = "binary"
                break
            for ctrl in t.controls:
                if ctrl.number == 64:
                    has_pedal = True
                    if ctrl.value not in (0, 127):
                        pedal_type = "continuous"
                    else:
                        pedal_type = "binary"
                    break

        # duration
        duration = max((n.end for t in s_sec.tracks for n in t.notes), default=0)

        # quality score
        quality_factors = []
        vel_score = min(vel_std / 25.0, 1.0) * 30
        quality_factors.append(vel_score)

        timing_scores = {"perfectly_quantized": 5, "lightly_humanized": 15, "human_performance": 25, "loose_timing": 10}
        quality_factors.append(timing_scores.get(timing_quality, 10))

        pedal_scores = {"none": 0, "binary": 15, "continuous": 20}
        quality_factors.append(pedal_scores.get(pedal_type, 0))

        note_density = total_notes / max(duration, 1)
        density_score = min(note_density / 10.0, 1.0) * 10
        quality_factors.append(density_score)

        if duration >= 30:
            quality_factors.append(10)
        elif duration >= 10:
            quality_factors.append(5)
        else:
            quality_factors.append(0)

        quality_score = min(sum(quality_factors), 100)

        # training suitability
        if category in ("piano_solo", "piano_dominant"):
            suitability = quality_score * (0.8 + 0.2 * piano_ratio)
        else:
            suitability = quality_score * piano_ratio * 0.3

        # difficulty
        if total_notes < 100:
            diff_level, diff_label = 2, "beginner"
        elif total_notes < 500:
            diff_level, diff_label = 4, "elementary"
        elif total_notes < 2000:
            diff_level, diff_label = 5, "intermediate"
        elif total_notes < 5000:
            diff_level, diff_label = 7, "upper_intermediate"
        else:
            diff_level, diff_label = 9, "advanced"

        # fingerprint
        fp_data = f"{total_notes}_{int(duration)}_{int(vel_mean)}_{category}"
        fingerprint = hashlib.md5(fp_data.encode()).hexdigest()

        result = {
            "instrument_category": category,
            "piano_ratio": round(piano_ratio, 4),
            "num_instruments": len(instruments),
            "has_drums": has_drums,
            "velocity_mean": round(vel_mean, 2),
            "velocity_std": round(vel_std, 2),
            "velocity_quality": vel_quality,
            "timing_deviation_mean": round(timing_dev, 6),
            "timing_quality": timing_quality,
            "pedal_type": pedal_type,
            "note_count": total_notes,
            "duration_sec": round(duration, 2),
            "quality_score_v2": round(quality_score, 2),
            "training_suitability": round(suitability, 2),
            "difficulty_level": diff_level,
            "difficulty_label": diff_label,
            "content_fingerprint": fingerprint,
            "midi_path": midi_path,
        }

        return (file_id, "ok", result)

    except Exception as e:
        return (file_id, f"error: {str(e)[:100]}", None)


def main():
    log("=" * 60)
    log("MXL → MIDI 변환 + 분류 시작")
    log("=" * 60)

    os.makedirs(MIDI_OUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT id, path FROM files
        WHERE source='pdmx' AND analyzed_at IS NULL AND file_type='mxl'
    """)
    rows = c.fetchall()
    log(f"대상: {len(rows):,} MXL 파일")

    if not rows:
        log("변환할 파일 없음")
        conn.close()
        return

    ok_count = 0
    err_count = 0
    crash_count = 0
    piano_count = 0

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start:batch_start + BATCH_SIZE]

        # subprocess Pool로 격리 (maxtasksperchild=20으로 메모리 누수 방지)
        pool = mp.Pool(processes=NUM_WORKERS, maxtasksperchild=20)
        try:
            async_results = pool.map_async(convert_and_analyze, batch)
            results = async_results.get(timeout=TIMEOUT_PER_FILE * len(batch))
        except mp.TimeoutError:
            log(f"  ⚠️ 배치 타임아웃 (batch {batch_start}), 스킵")
            pool.terminate()
            pool.join()
            crash_count += len(batch)
            continue
        except Exception as e:
            log(f"  ⚠️ 배치 에러: {str(e)[:80]}")
            pool.terminate()
            pool.join()
            crash_count += len(batch)
            continue
        finally:
            pool.close()
            pool.join()

        updates = []
        for file_id, status, data in results:
            if status == "ok" and data:
                ok_count += 1
                if data["instrument_category"] in ("piano_solo", "piano_dominant"):
                    piano_count += 1
                updates.append((
                    data["instrument_category"], data["piano_ratio"],
                    data["num_instruments"], data["has_drums"],
                    data["velocity_mean"], data["velocity_std"],
                    data["velocity_quality"], data["timing_deviation_mean"],
                    data["timing_quality"], data["pedal_type"],
                    data["note_count"], data["duration_sec"],
                    data["quality_score_v2"], data["training_suitability"],
                    data["difficulty_level"], data["difficulty_label"],
                    data["content_fingerprint"],
                    datetime.now().isoformat(),
                    file_id
                ))
            else:
                err_count += 1

        if updates:
            c.executemany("""
                UPDATE files SET
                    instrument_category=?, piano_ratio=?,
                    num_instruments=?, has_drums=?,
                    velocity_mean=?, velocity_std=?,
                    velocity_quality=?, timing_deviation_mean=?,
                    timing_quality=?, pedal_type=?,
                    note_count=?, duration_sec=?,
                    quality_score_v2=?, training_suitability=?,
                    difficulty_level=?, difficulty_label=?,
                    content_fingerprint=?,
                    analyzed_at=?
                WHERE id=?
            """, updates)
            conn.commit()

        processed = batch_start + len(batch)
        log(f"  진행: {processed:,}/{len(rows):,} ({processed*100//len(rows)}%) | 성공: {ok_count:,} | 에러: {err_count:,} | 크래시: {crash_count:,} | 피아노: {piano_count:,}")

        gc.collect()

    conn.close()

    log(f"\n{'='*60}")
    log(f"MXL 변환 완료: 성공 {ok_count:,} / 에러 {err_count:,} / 피아노 {piano_count:,}")
    log(f"{'='*60}")


if __name__ == "__main__":
    main()
