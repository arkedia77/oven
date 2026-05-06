"""
Suno 후처리 파이프라인 — 투 트랙 (풀믹스 / 스템분리)

사용법:
  # Track A: 풀믹스 (스템분리 없이)
  python suno_postprocess.py input/ output/ --track fullmix

  # Track B: 스템분리 후 개별 처리 + 리믹스
  python suno_postprocess.py input/ output/ --track stems

  # 둘 다 실행 (A/B 비교용)
  python suno_postprocess.py input/ output/ --track both

  # 레퍼런스 트랙으로 matchering
  python suno_postprocess.py input/ output/ --track fullmix --reference ref.wav

입력: WAV 파일 (Suno에서 다운로드한 원본)
출력: output/{fullmix,stems}/ 하위에 처리된 WAV
"""

import argparse
import glob
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pedalboard as pb
import pyloudnorm
import soundfile as sf

TARGET_LUFS = -14.0
SAMPLE_RATE = 44100


# ─── EQ / 처리 체인 ───────────────────────────────────────────────

def build_fullmix_board():
    """풀믹스용 체인: HPF → low-mid 정리 → presence boost → 리버브 억제(dry) → 컴프 → 리미터"""
    return pb.Pedalboard([
        pb.HighpassFilter(cutoff_frequency_hz=30),
        pb.PeakFilter(cutoff_frequency_hz=250, gain_db=-2.5, q=1.2),
        pb.PeakFilter(cutoff_frequency_hz=400, gain_db=-1.5, q=0.8),
        pb.PeakFilter(cutoff_frequency_hz=3000, gain_db=1.5, q=0.9),
        pb.HighShelfFilter(cutoff_frequency_hz=10000, gain_db=1.0, q=0.7),
        pb.Compressor(threshold_db=-18, ratio=2.5, attack_ms=15, release_ms=150),
        pb.Gain(gain_db=-0.5),
        pb.Limiter(threshold_db=-1.0, release_ms=100),
    ])


def build_vocal_board():
    """보컬 스템: de-ess 대역 억제 + presence + 가벼운 컴프"""
    return pb.Pedalboard([
        pb.HighpassFilter(cutoff_frequency_hz=80),
        pb.PeakFilter(cutoff_frequency_hz=200, gain_db=-2.0, q=1.0),
        pb.PeakFilter(cutoff_frequency_hz=3500, gain_db=2.0, q=0.8),
        pb.PeakFilter(cutoff_frequency_hz=6500, gain_db=-1.5, q=2.0),  # de-ess zone
        pb.HighShelfFilter(cutoff_frequency_hz=12000, gain_db=1.0, q=0.7),
        pb.Compressor(threshold_db=-16, ratio=3.0, attack_ms=5, release_ms=80),
        pb.Gain(gain_db=-0.5),
        pb.Limiter(threshold_db=-1.0, release_ms=80),
    ])


def build_drums_board():
    """드럼 스템: 펀치 + 하이햇 정리"""
    return pb.Pedalboard([
        pb.HighpassFilter(cutoff_frequency_hz=30),
        pb.PeakFilter(cutoff_frequency_hz=100, gain_db=1.5, q=1.0),
        pb.PeakFilter(cutoff_frequency_hz=3500, gain_db=1.0, q=0.8),
        pb.PeakFilter(cutoff_frequency_hz=8000, gain_db=-1.0, q=1.5),
        pb.Compressor(threshold_db=-14, ratio=4.0, attack_ms=2, release_ms=50),
        pb.Gain(gain_db=-0.5),
        pb.Limiter(threshold_db=-1.0, release_ms=60),
    ])


def build_bass_board():
    """베이스 스템: 서브 정리 + 펀치"""
    return pb.Pedalboard([
        pb.HighpassFilter(cutoff_frequency_hz=30),
        pb.LowShelfFilter(cutoff_frequency_hz=80, gain_db=1.5, q=0.7),
        pb.PeakFilter(cutoff_frequency_hz=250, gain_db=-1.5, q=1.0),
        pb.PeakFilter(cutoff_frequency_hz=700, gain_db=1.0, q=0.8),
        pb.Compressor(threshold_db=-16, ratio=3.5, attack_ms=5, release_ms=100),
        pb.Gain(gain_db=-0.5),
        pb.Limiter(threshold_db=-1.5, release_ms=80),
    ])


def build_other_board():
    """기타 악기 스템: 밸런스 정리"""
    return pb.Pedalboard([
        pb.HighpassFilter(cutoff_frequency_hz=50),
        pb.PeakFilter(cutoff_frequency_hz=300, gain_db=-1.5, q=0.8),
        pb.PeakFilter(cutoff_frequency_hz=2500, gain_db=1.0, q=0.8),
        pb.Compressor(threshold_db=-18, ratio=2.0, attack_ms=15, release_ms=150),
        pb.Gain(gain_db=-0.5),
        pb.Limiter(threshold_db=-1.0, release_ms=100),
    ])


STEM_BOARDS = {
    "vocals": build_vocal_board(),
    "drums": build_drums_board(),
    "bass": build_bass_board(),
    "other": build_other_board(),
}

STEM_LEVELS = {
    "vocals": 0.0,
    "drums": -1.0,
    "bass": -0.5,
    "other": -1.5,
}


# ─── 유틸 ─────────────────────────────────────────────────────────

def read_audio(path):
    audio, sr = sf.read(path, always_2d=True)
    return audio, sr


def normalize_lufs(audio, sr, target=TARGET_LUFS):
    meter = pyloudnorm.Meter(sr)
    loudness = meter.integrated_loudness(audio)
    if np.isinf(loudness):
        return audio
    normalized = pyloudnorm.normalize.loudness(audio, loudness, target)
    peak = np.max(np.abs(normalized))
    if peak > 0.99:
        normalized = normalized * (0.99 / peak)
    return normalized


def apply_board(audio, sr, board):
    processed = board(audio.T, sr).T
    return processed


def db_to_linear(db):
    return 10 ** (db / 20.0)


def run_matchering(target_path, reference_path, output_path):
    """matchering으로 레퍼런스 매칭 (스펙트럼 + 라우드니스)"""
    import matchering as mg
    mg.process(
        target=target_path,
        reference=reference_path,
        results=[mg.pcm16(output_path)],
    )


# ─── Track A: 풀믹스 파이프라인 ───────────────────────────────────

def process_fullmix(src_path, dst_path, reference_path=None):
    audio, sr = read_audio(src_path)
    board = build_fullmix_board()
    processed = apply_board(audio, sr, board)
    processed = normalize_lufs(processed, sr)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    if reference_path:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        sf.write(tmp_path, processed, sr, subtype="PCM_16")
        try:
            run_matchering(tmp_path, reference_path, dst_path)
        finally:
            os.unlink(tmp_path)
    else:
        sf.write(dst_path, processed, sr, subtype="PCM_16")

    return sr


# ─── Track B: 스템분리 파이프라인 ─────────────────────────────────

def separate_stems(src_path, output_dir):
    """demucs htdemucs_ft 모델로 4-stem 분리"""
    cmd = [
        "demucs",
        "--two-stems=vocals",  # 일단 제거 — 4-stem 전체 분리
        "-n", "htdemucs_ft",
        "--out", output_dir,
        src_path,
    ]
    cmd = [
        "demucs",
        "-n", "htdemucs_ft",
        "--out", output_dir,
        src_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    stem_dir = os.path.join(output_dir, "htdemucs_ft", Path(src_path).stem)
    return stem_dir


def process_stems(src_path, dst_path, reference_path=None):
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"    스템 분리 중...", flush=True)
        stem_dir = separate_stems(src_path, tmp_dir)

        _, sr = read_audio(src_path)
        mixed = None

        for stem_name, board in STEM_BOARDS.items():
            stem_path = os.path.join(stem_dir, f"{stem_name}.wav")
            if not os.path.exists(stem_path):
                continue

            stem_audio, stem_sr = read_audio(stem_path)
            processed = apply_board(stem_audio, stem_sr, board)

            gain = db_to_linear(STEM_LEVELS[stem_name])
            processed = processed * gain

            if mixed is None:
                mixed = np.zeros_like(processed)
            if mixed.shape[0] < processed.shape[0]:
                mixed = np.pad(mixed, ((0, processed.shape[0] - mixed.shape[0]), (0, 0)))
            elif mixed.shape[0] > processed.shape[0]:
                processed = np.pad(processed, ((0, mixed.shape[0] - processed.shape[0]), (0, 0)))
            mixed += processed

        if mixed is None:
            print(f"    ⚠️ 스템 없음, 스킵: {src_path}")
            return None

        mixed = normalize_lufs(mixed, sr)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        if reference_path:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            sf.write(tmp_path, mixed, sr, subtype="PCM_16")
            try:
                run_matchering(tmp_path, reference_path, dst_path)
            finally:
                os.unlink(tmp_path)
        else:
            sf.write(dst_path, mixed, sr, subtype="PCM_16")

    return sr


# ─── 배치 실행 ────────────────────────────────────────────────────

def find_wavs(src_dir):
    patterns = ["*.wav", "*.WAV"]
    wavs = []
    for pat in patterns:
        wavs.extend(glob.glob(os.path.join(src_dir, "**", pat), recursive=True))
    return sorted(set(wavs))


def run_pipeline(src_dir, dst_dir, track="both", reference=None):
    wavs = find_wavs(src_dir)
    if not wavs:
        print(f"WAV 파일 없음: {src_dir}")
        return

    print(f"입력: {src_dir} ({len(wavs)}개 WAV)")
    print(f"출력: {dst_dir}")
    print(f"트랙: {track}")
    if reference:
        print(f"레퍼런스: {reference}")
    print()

    for wav in wavs:
        rel = os.path.relpath(wav, src_dir)
        name = Path(rel).stem
        print(f"  처리: {rel}")

        if track in ("fullmix", "both"):
            dst_fullmix = os.path.join(dst_dir, "fullmix", rel)
            print(f"    [A] 풀믹스...", flush=True)
            process_fullmix(wav, dst_fullmix, reference)
            print(f"    [A] 완료 → {dst_fullmix}")

        if track in ("stems", "both"):
            dst_stems = os.path.join(dst_dir, "stems", rel)
            print(f"    [B] 스템분리...", flush=True)
            result = process_stems(wav, dst_stems, reference)
            if result:
                print(f"    [B] 완료 → {dst_stems}")

    print(f"\n완료. 결과: {dst_dir}/")


# ─── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Suno 후처리 파이프라인 (풀믹스 / 스템분리 투 트랙)"
    )
    parser.add_argument("src", help="입력 WAV 디렉토리")
    parser.add_argument("dst", help="출력 디렉토리")
    parser.add_argument(
        "--track", choices=["fullmix", "stems", "both"], default="both",
        help="처리 트랙 (기본: both)"
    )
    parser.add_argument(
        "--reference", "-r", help="matchering 레퍼런스 WAV (선택)"
    )
    args = parser.parse_args()

    if args.reference and not os.path.exists(args.reference):
        print(f"레퍼런스 파일 없음: {args.reference}")
        return

    run_pipeline(args.src, args.dst, track=args.track, reference=args.reference)


if __name__ == "__main__":
    main()
