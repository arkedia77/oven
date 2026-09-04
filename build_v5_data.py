"""v5 dataset build: aria-midi → Salamander render → 30s segments."""
import json, os, random, subprocess, sys, time

ARIA = "/Volumes/project backup/score/aria-midi/aria-midi-v1-ext"
SF2 = "/Users/leo/oven/soundfonts/IdO_Grand_Piano.sf2"
OUT_RENDER = "/Users/leo/oven/v5_data/render"
OUT_SEG = "/Users/leo/oven/v5_data/segments"
INDEX_CACHE = "/Users/leo/oven/v5_data/midi_index.json"

# composer → count for v5 probe
PICKS = {
    "einaudi": 8, "hisaishi": 8, "satie": 6,
    "yiruma": 4, "debussy": 2, "ravel": 2,
}
SCORE_MIN = 0.95
SEG_PER_SONG = 20
SEG_LEN = 30
STRIDE = 45
SEED = 42

os.makedirs(OUT_RENDER, exist_ok=True)
os.makedirs(OUT_SEG, exist_ok=True)
random.seed(SEED)

print("[1/5] Loading metadata.json...", flush=True)
meta = json.load(open(f"{ARIA}/metadata.json"))

print("[2/5] Filtering candidates...", flush=True)
buckets = {c: [] for c in PICKS}
for k, v in meta.items():
    md = v.get("metadata", {})
    comp = md.get("composer", "")
    if comp not in buckets: continue
    scores = v.get("audio_scores", {})
    best_take = None
    best_s = 0
    for take, s in scores.items():
        if s > best_s:
            best_s = s
            best_take = take
    if best_s < SCORE_MIN: continue
    buckets[comp].append((k, best_take, best_s))

picks = []
for comp, n in PICKS.items():
    pool = buckets[comp]
    random.shuffle(pool)
    sel = pool[:n]
    picks.extend([(comp, mid, take) for mid, take, _ in sel])
    print(f"  {comp}: {len(sel)}/{len(pool)} picked", flush=True)

print(f"\n[3/5] Building/loading file index...", flush=True)
if os.path.exists(INDEX_CACHE):
    idx = json.load(open(INDEX_CACHE))
    print(f"  loaded cached index: {len(idx)} entries", flush=True)
else:
    idx = {}
    t0 = time.time()
    for root, _, files in os.walk(f"{ARIA}/data"):
        for fn in files:
            if fn.endswith(".mid"):
                # 000123_4.mid → id=123, take=4
                stem = fn[:-4]
                mid_id, take = stem.split("_")
                idx[f"{int(mid_id)}_{take}"] = os.path.join(root, fn)
    json.dump(idx, open(INDEX_CACHE, "w"))
    print(f"  built index: {len(idx)} files in {time.time()-t0:.1f}s", flush=True)

print(f"\n[4/5] Rendering {len(picks)} MIDIs with Salamander...", flush=True)
rendered = []
for i, (comp, mid, take) in enumerate(picks, 1):
    key = f"{mid}_{take}"
    if key not in idx:
        print(f"  [{i}/{len(picks)}] MISSING {comp}/{key}", flush=True)
        continue
    src = idx[key]
    out = os.path.join(OUT_RENDER, f"{comp}_{key}.wav")
    if os.path.exists(out) and os.path.getsize(out) > 1_000_000:
        print(f"  [{i}/{len(picks)}] {comp}/{key} (cached)", flush=True)
        rendered.append(out); continue
    t0 = time.time()
    r = subprocess.run(
        ["fluidsynth", "-ni", "-F", out, "-r", "48000", "-g", "0.6", SF2, src],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  [{i}/{len(picks)}] FAIL {comp}/{key}: {r.stderr[:200]}", flush=True)
        continue
    sz_mb = os.path.getsize(out) / 1e6
    print(f"  [{i}/{len(picks)}] {comp}/{key} → {sz_mb:.1f}MB ({time.time()-t0:.1f}s)", flush=True)
    rendered.append(out)

print(f"\n[5/5] Rendered {len(rendered)} files. Done.", flush=True)
print(f"Next: run segmentation script on {OUT_RENDER}/ → {OUT_SEG}/", flush=True)
