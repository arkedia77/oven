"""v5: segment Salamander-rendered piano wavs into 30s clips."""
import os, random, glob
from pathlib import Path
import numpy as np
import soundfile as sf

RAW_DIR = "/Users/leo/oven/v5_data/render"
OUT_DIR = "/Users/leo/oven/v5_data/segments"
SEG_SEC = 30.0
SR_TARGET = 48000
RMS_MIN = 0.01
PEAK_MAX = 0.99
MAX_PER_SONG = 20
STRIDE_SEC = 45.0
RANDOM_SEED = 42

os.makedirs(OUT_DIR, exist_ok=True)
random.seed(RANDOM_SEED)
kept_total = 0
skipped_silence = 0
skipped_clip = 0

for wav_path in sorted(glob.glob(os.path.join(RAW_DIR, "*.wav"))):
    name = Path(wav_path).stem
    try:
        data, sr = sf.read(wav_path, dtype="float32")
    except Exception as e:
        print(f"[SKIP] {name}: read error {e}", flush=True)
        continue
    if data.ndim == 2:
        data = data.mean(axis=1)
    if sr != SR_TARGET:
        print(f"[SKIP] {name}: sr={sr} != {SR_TARGET}", flush=True)
        continue

    seg_len = int(SEG_SEC * sr)
    stride = int(STRIDE_SEC * sr)
    total = len(data)
    if total < seg_len * 2:
        print(f"[SKIP] {name}: too short ({total/sr:.0f}s)", flush=True)
        continue

    candidates = list(range(0, total - seg_len, stride))
    random.shuffle(candidates)

    kept_this = 0
    for start in candidates:
        if kept_this >= MAX_PER_SONG:
            break
        seg = data[start:start + seg_len]
        rms = float(np.sqrt(np.mean(seg ** 2)))
        peak = float(np.max(np.abs(seg)))
        if rms < RMS_MIN:
            skipped_silence += 1; continue
        if peak > PEAK_MAX:
            skipped_clip += 1; continue
        out_name = f"{name}_seg{start//sr:05d}.wav"
        out_path = os.path.join(OUT_DIR, out_name)
        sf.write(out_path, seg, sr, subtype="PCM_16")
        kept_this += 1; kept_total += 1
    print(f"[OK] {name}: kept {kept_this} / {len(candidates)}", flush=True)

print(f"\nTotal kept: {kept_total}, silence skipped: {skipped_silence}, clip skipped: {skipped_clip}", flush=True)
