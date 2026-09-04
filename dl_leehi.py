"""Download Lee Hi curated 20 tracks as WAV for ACE-Step training."""
import json, subprocess, os

TRACKLIST = "/Users/leo/oven/leehi_curated/tracklist.json"
OUTPUT_DIR = "/Users/leo/oven/leehi_curated"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(TRACKLIST) as f:
    tracks = json.load(f)

print(f"Downloading {len(tracks)} tracks to {OUTPUT_DIR}")

for i, t in enumerate(tracks, 1):
    vid = t["id"]
    out_path = os.path.join(OUTPUT_DIR, f"{vid}.wav")
    if os.path.exists(out_path):
        print(f"[{i}/{len(tracks)}] SKIP (exists): {t['title']}")
        continue

    print(f"[{i}/{len(tracks)}] Downloading: {t['title']} ({vid})")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-x", "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", out_path,
        f"https://www.youtube.com/watch?v={vid}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:200]}")
    else:
        if os.path.exists(out_path):
            size_mb = os.path.getsize(out_path) / 1024 / 1024
            print(f"  OK: {size_mb:.1f} MB")
        else:
            print(f"  WARNING: file not found after download")

print("\nDone!")
print(f"Files: {len([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.wav')])}/{len(tracks)}")
