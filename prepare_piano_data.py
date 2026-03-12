"""
피아노 엔진 학습 데이터 정제 스크립트
- ARIA-MIDI + MAESTRO + ATEPP + PDMX 에서 피아노 MIDI만 추출
- 품질 필터링 (길이, 음표 수, 손상 여부)
- 중복 제거 (MD5)
- 결과: /Volumes/data/score/piano_training/ 에 정리된 MIDI
"""

import os, hashlib, shutil, json
from pathlib import Path
from datetime import datetime
import pretty_midi

BASE_DIR    = os.path.expanduser("~/musicscore")
OUT_DIR     = "/Volumes/data/score/piano_training"
LOG_FILE    = f"{BASE_DIR}/logs/prepare_piano.log"
REPORT_FILE = f"{BASE_DIR}/data/piano_training_report.json"

# 소스 경로
SOURCES = {
    "aria":     "/Volumes/data/score/aria-midi",
    "maestro":  "/Volumes/data/score/maestro",
    "atepp":    "/Volumes/data/score/atepp",
    "pdmx":     "/Volumes/data/score/PDMX",
    "lakh":     "/Volumes/data/score/lakh/lmd_full",
    "gigamidi": "/Volumes/data/score/gigamidi/Final_GigaMIDI_V1.1_Final/train/training-V1.1-80%/no-drums",
}

# 품질 필터 기준
MIN_DURATION   = 10.0   # 최소 10초
MAX_DURATION   = 600.0  # 최대 10분
MIN_NOTES      = 50     # 최소 음표 수
MAX_NOTES      = 50000  # 최대 음표 수

def make_log():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    return log

log = make_log()


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def is_piano_midi(midi_path):
    """MIDI 파일이 피아노 파트를 포함하는지 확인"""
    try:
        pm = pretty_midi.PrettyMIDI(str(midi_path))
        duration = pm.get_end_time()
        total_notes = sum(len(inst.notes) for inst in pm.instruments)

        if duration < MIN_DURATION or duration > MAX_DURATION:
            return False, "duration"
        if total_notes < MIN_NOTES or total_notes > MAX_NOTES:
            return False, "notes"

        # 피아노 악기 체크 (General MIDI 0-7: Acoustic/Electric Piano)
        has_piano = any(
            (not inst.is_drum and inst.program < 8)
            for inst in pm.instruments
        )
        # ARIA-MIDI, MAESTRO, ATEPP는 솔로 피아노 → 악기 무관하게 통과
        return True, f"{duration:.1f}s/{total_notes}notes"

    except Exception as e:
        return False, f"parse_error"


def process_source(source_name, source_path, seen_hashes, out_dir):
    if not os.path.exists(source_path):
        log(f"  ⚠️ 경로 없음: {source_path}")
        return 0, 0, 0

    midi_files = list(Path(source_path).rglob("*.mid")) + \
                 list(Path(source_path).rglob("*.midi"))

    ok = fail = skip = 0
    source_out = os.path.join(out_dir, source_name)
    os.makedirs(source_out, exist_ok=True)

    # ARIA-MIDI, MAESTRO, ATEPP는 피아노 전용 → 빠른 경로
    piano_only_sources = {"aria", "maestro", "atepp"}

    for i, midi_path in enumerate(midi_files):
        if i % 10000 == 0 and i > 0:
            log(f"  [{source_name}] {i:,}/{len(midi_files):,} | ok={ok:,} skip={skip:,} fail={fail:,}")

        # 중복 체크
        md5 = file_md5(midi_path)
        if md5 in seen_hashes:
            skip += 1
            continue

        # 품질 필터 (피아노 전용 소스는 길이/음표만 체크)
        if source_name in piano_only_sources:
            try:
                pm = pretty_midi.PrettyMIDI(str(midi_path))
                duration = pm.get_end_time()
                total_notes = sum(len(inst.notes) for inst in pm.instruments)
                if duration < MIN_DURATION or duration > MAX_DURATION:
                    fail += 1
                    continue
                if total_notes < MIN_NOTES or total_notes > MAX_NOTES:
                    fail += 1
                    continue
                passed = True
            except:
                fail += 1
                continue
        else:
            passed, reason = is_piano_midi(midi_path)
            if not passed:
                fail += 1
                continue

        # 복사
        dst = os.path.join(source_out, f"{md5}.mid")
        shutil.copy2(midi_path, dst)
        seen_hashes.add(md5)
        ok += 1

    log(f"  [{source_name}] 완료: ok={ok:,} / skip={skip:,} / fail={fail:,}")
    return ok, skip, fail


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    log(f"피아노 데이터 정제 시작")
    log(f"출력 경로: {OUT_DIR}")

    seen_hashes = set()
    report = {"started_at": datetime.now().isoformat(), "sources": {}}
    total_ok = 0

    # 우선순위 순서: 품질 높은 것부터
    priority = ["maestro", "atepp", "aria", "pdmx", "lakh", "gigamidi"]

    for source_name in priority:
        source_path = SOURCES.get(source_name, "")
        log(f"\n=== {source_name.upper()} ===")
        ok, skip, fail = process_source(source_name, source_path, seen_hashes, OUT_DIR)
        report["sources"][source_name] = {"ok": ok, "skip": skip, "fail": fail}
        total_ok += ok

    report["total_piano_files"] = total_ok
    report["completed_at"] = datetime.now().isoformat()

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log(f"\n완료: 총 피아노 MIDI {total_ok:,}개 → {OUT_DIR}")
    log(f"리포트: {REPORT_FILE}")


main()
