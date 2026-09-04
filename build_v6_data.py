"""v6 dataset build: aria-midi → multi-sf2 render → 30s segments.

Usage:
  python3 build_v6_data.py                    # render + segment
  python3 build_v6_data.py --render-only      # render MIDIs only
  python3 build_v6_data.py --segment-only     # segment existing renders only

Composer picks are configured in PICKS below — update with Leo before running.
"""
import json, os, random, subprocess, sys, time, hashlib
import numpy as np
import soundfile as sf_mod

ARIA = "/Volumes/project backup/score/aria-midi/aria-midi-v1-ext"
OUT_ROOT = "/Users/leo/oven/v6_data"
OUT_RENDER = os.path.join(OUT_ROOT, "render")
OUT_SEG = os.path.join(OUT_ROOT, "segments")
INDEX_CACHE = os.path.join(OUT_ROOT, "midi_index.json")
MANIFEST_PATH = os.path.join(OUT_ROOT, "manifest.json")

# === SOUNDFONTS — add paths here ===
SF2_LIST = [
    ("/Users/leo/oven/soundfonts/SalamanderGrandPiano.sf2", "salamander"),
    ("/Users/leo/oven/soundfonts/IdO_Grand_Piano.sf2", "ido"),
    # ("/Users/leo/oven/soundfonts/YDP_GrandPiano.sf2", "ydp"),  # Leo 청취 후 결정
]

# === COMPOSER PICKS — Leo와 상의 후 확정 ===
PICKS = {
    # "composer_name": count,
    # 아래는 플레이스홀더 — Leo가 선정 후 업데이트
    # "chopin": 10, "debussy": 8, "satie": 8, "einaudi": 8,
    # "hisaishi": 8, "yiruma": 6, "ravel": 5, "beethoven": 5,
    # "bach": 4, "schubert": 4, "glass": 4, "tiersen": 4,
    # "sakamoto": 3, "rachmaninoff": 3, "grieg": 3, "liszt": 2,
}

SCORE_MIN = 0.95
SEED = 42

# Segmentation params
SEG_LEN = 30.0
STRIDE = 45.0
MAX_PER_SONG = 20
SR_TARGET = 48000
RMS_MIN = 0.01
PEAK_MAX = 0.99
FADE_MS = 50

random.seed(SEED)


def build_file_index():
    if os.path.exists(INDEX_CACHE):
        idx = json.load(open(INDEX_CACHE))
        print(f"  loaded cached index: {len(idx)} entries", flush=True)
        return idx
    idx = {}
    t0 = time.time()
    for root, _, files in os.walk(f"{ARIA}/data"):
        for fn in files:
            if fn.endswith(".mid"):
                stem = fn[:-4]
                mid_id, take = stem.split("_")
                idx[f"{int(mid_id)}_{take}"] = os.path.join(root, fn)
    os.makedirs(OUT_ROOT, exist_ok=True)
    json.dump(idx, open(INDEX_CACHE, "w"))
    print(f"  built index: {len(idx)} files in {time.time()-t0:.1f}s", flush=True)
    return idx


def select_midis(meta):
    if not PICKS:
        print("  PICKS is empty — configure composer list before running!", flush=True)
        sys.exit(1)

    buckets = {c: [] for c in PICKS}
    for k, v in meta.items():
        md = v.get("metadata", {})
        comp = md.get("composer", "")
        if comp not in buckets:
            continue
        scores = v.get("audio_scores", {})
        best_take, best_s = None, 0
        for take, s in scores.items():
            if s > best_s:
                best_s = s
                best_take = take
        if best_s < SCORE_MIN:
            continue
        buckets[comp].append((k, best_take, best_s))

    picks = []
    for comp, n in PICKS.items():
        pool = buckets[comp]
        random.shuffle(pool)
        sel = pool[:n]
        picks.extend([(comp, mid, take) for mid, take, _ in sel])
        print(f"  {comp}: {len(sel)}/{len(pool)} picked", flush=True)
    return picks


def render_midis(picks, idx):
    os.makedirs(OUT_RENDER, exist_ok=True)
    manifest = []
    total = len(picks) * len(SF2_LIST)
    i = 0
    for comp, mid, take in picks:
        key = f"{mid}_{take}"
        if key not in idx:
            print(f"  MISSING {comp}/{key}", flush=True)
            continue
        src = idx[key]
        for sf2_path, sf2_tag in SF2_LIST:
            i += 1
            out = os.path.join(OUT_RENDER, f"{comp}_{key}_{sf2_tag}.wav")
            if os.path.exists(out) and os.path.getsize(out) > 100_000:
                print(f"  [{i}/{total}] {comp}/{key}/{sf2_tag} (cached)", flush=True)
                manifest.append({"midi": key, "composer": comp, "sf2": sf2_tag, "wav": out})
                continue
            t0 = time.time()
            r = subprocess.run(
                ["fluidsynth", "-ni", "-F", out, "-r", str(SR_TARGET), "-g", "0.6", sf2_path, src],
                capture_output=True, text=True
            )
            if r.returncode != 0:
                print(f"  [{i}/{total}] FAIL {comp}/{key}/{sf2_tag}: {r.stderr[:200]}", flush=True)
                continue
            sz_mb = os.path.getsize(out) / 1e6
            print(f"  [{i}/{total}] {comp}/{key}/{sf2_tag} → {sz_mb:.1f}MB ({time.time()-t0:.1f}s)", flush=True)
            manifest.append({"midi": key, "composer": comp, "sf2": sf2_tag, "wav": out})
    return manifest


def make_fade(n_samples, sr):
    n = int(FADE_MS / 1000 * sr)
    n = min(n, n_samples // 2)
    fade_in = np.linspace(0, 1, n) ** 2
    fade_out = np.linspace(1, 0, n) ** 2
    return n, fade_in, fade_out


def segment_renders(render_manifest):
    os.makedirs(OUT_SEG, exist_ok=True)
    seg_manifest = []
    total_seg = 0
    seg_samples = int(SEG_LEN * SR_TARGET)
    stride_samples = int(STRIDE * SR_TARGET)
    fade_n, fade_in, fade_out = make_fade(seg_samples, SR_TARGET)

    for entry in render_manifest:
        wav_path = entry["wav"]
        data, sr = sf_mod.read(wav_path)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        if sr != SR_TARGET:
            continue

        tag = os.path.splitext(os.path.basename(wav_path))[0]
        count = 0
        pos = 0
        while pos + seg_samples <= len(data) and count < MAX_PER_SONG:
            seg = data[pos:pos + seg_samples].copy()
            rms = np.sqrt(np.mean(seg ** 2))
            peak = np.max(np.abs(seg))
            if rms < RMS_MIN or peak > PEAK_MAX:
                pos += stride_samples
                continue

            seg[:fade_n] *= fade_in
            seg[-fade_n:] *= fade_out

            out_name = f"{tag}_seg{count:02d}.wav"
            out_path = os.path.join(OUT_SEG, out_name)
            sf_mod.write(out_path, seg, SR_TARGET, subtype="PCM_16")
            seg_manifest.append({
                "file": out_name, "source": tag,
                "composer": entry["composer"], "sf2": entry["sf2"],
                "rms": round(float(rms), 5), "peak": round(float(peak), 4),
            })
            count += 1
            total_seg += 1
            pos += stride_samples

    seg_manifest_path = os.path.join(OUT_SEG, "manifest.json")
    with open(seg_manifest_path, "w") as f:
        json.dump(seg_manifest, f, indent=2, ensure_ascii=False)
    print(f"\n  Total segments: {total_seg}", flush=True)
    print(f"  Manifest: {seg_manifest_path}", flush=True)
    return seg_manifest


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--render-only", action="store_true")
    p.add_argument("--segment-only", action="store_true")
    args = p.parse_args()

    print("[1] Loading metadata...", flush=True)
    meta = json.load(open(f"{ARIA}/metadata.json"))

    print("[2] Building file index...", flush=True)
    idx = build_file_index()

    if not args.segment_only:
        print("[3] Selecting MIDIs...", flush=True)
        picks = select_midis(meta)
        print(f"\n[4] Rendering {len(picks)} MIDIs × {len(SF2_LIST)} sf2s...", flush=True)
        render_manifest = render_midis(picks, idx)
        with open(MANIFEST_PATH, "w") as f:
            json.dump(render_manifest, f, indent=2)
    else:
        render_manifest = json.load(open(MANIFEST_PATH))

    if not args.render_only:
        print(f"\n[5] Segmenting {len(render_manifest)} renders...", flush=True)
        segment_renders(render_manifest)

    print("\nDONE", flush=True)
