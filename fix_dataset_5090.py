#!/usr/bin/env python3
"""Fix dataset.json: remove duplicates, correct durations, improve captions"""
import json
import os
import re
import sys
import wave
from pathlib import Path

BASE = Path(r"C:\Users\leo\ace-step-v15\lokr_artists")

ARTIST_CAPTIONS = {
    "악뮤": "Korean acoustic folk pop duo, warm male-female harmonized vocals, guitar, youthful emotional mood",
    "DAY6__데이식스": "Korean pop rock band, energetic male vocals, electric guitar, drums, emotional band sound",
    "IVE__아이브": "K-pop girl group, powerful female vocals, bright synth, dance pop, confident modern production",
    "황치열": "Korean ballad, powerful emotional male vocals, piano, string orchestra, dramatic mood",
    "아일릿": "K-pop girl group, fresh youthful female vocals, catchy synth pop, bright dance production",
    "방탄소년단": "K-pop boy group, dynamic male vocals and rap, modern hybrid pop, powerful production",
    "투어스": "K-pop boy group, smooth male vocals, bright pop, youthful energy, catchy melody",
}


def process_artist(artist_folder):
    artist_dir = BASE / artist_folder
    wav_dir = artist_dir / "wav"
    mp3_dir = artist_dir / "mp3"

    if not wav_dir.exists():
        print(f"  WAV dir not found: {wav_dir}")
        return

    # Remove timestamp duplicates
    for d in [wav_dir, mp3_dir]:
        if not d.exists():
            continue
        for f in list(d.iterdir()):
            if re.search(r"_\d{8}_\d{6}\.\w+$", f.name):
                base = re.sub(r"_\d{8}_\d{6}(\.\w+)$", r"\1", f.name)
                if (d / base).exists():
                    f.unlink()
                    print(f"  Removed dup: {f.name}")

    caption = ARTIST_CAPTIONS.get(artist_folder, "Korean pop, modern production, radio hit")

    dataset = []
    seen_ranks = set()
    for f in sorted(wav_dir.glob("*.wav")):
        m = re.match(r"(\d+)\.", f.name)
        rank = int(m.group(1)) if m else 0
        if rank in seen_ranks:
            continue
        seen_ranks.add(rank)

        try:
            w = wave.open(str(f), "rb")
            dur = w.getnframes() / w.getframerate()
            w.close()
        except Exception:
            dur = 180

        tm = re.match(r"\d+\.\s*(.+?)\s*-\s*.+?\.\w+$", f.name)
        title = tm.group(1) if tm else f.stem

        dataset.append({
            "id": f.stem,
            "audio_path": f.name,
            "caption": caption,
            "lyrics": "",
            "duration": int(dur),
            "title": title,
            "rank": rank,
        })
        print(f"  [{rank:3d}] {title} - {dur:.0f}s")

    ds_path = artist_dir / "dataset.json"
    with open(ds_path, "w", encoding="utf-8") as fout:
        json.dump(dataset, fout, ensure_ascii=False, indent=2)
    print(f"  => {len(dataset)} entries saved to {ds_path}")
    return len(dataset)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        folders = [target]
    else:
        folders = [d.name for d in sorted(BASE.iterdir()) if d.is_dir()]

    for folder in folders:
        print(f"\n{'='*50}")
        print(f"Processing: {folder}")
        print(f"{'='*50}")
        process_artist(folder)


if __name__ == "__main__":
    main()
