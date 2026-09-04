#!/usr/bin/env python3
"""
벅스 TOP 100 MP3 → 아티스트별 LoKR dataset.json 자동 생성
사용법: python build_lokr_datasets.py <mp3_dir> <output_dir> [--min-songs 4]
"""
import argparse
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path


def parse_bugs_filename(fname: str):
    m = re.match(r"(\d+)\.\s*(.+?)\s*-\s*(.+?)(?:_\d{8}_\d{6})?\.mp3$", fname)
    if not m:
        return None
    return {
        "rank": int(m.group(1)),
        "title": m.group(2).strip(),
        "artist": m.group(3).strip(),
    }


def get_duration(fpath: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", fpath],
            capture_output=True, text=True, timeout=10
        )
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def guess_caption(title: str, artist: str) -> str:
    return f"Korean pop, {artist} style vocals, modern production, radio hit"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mp3_dir", help="Directory with MP3 files")
    parser.add_argument("output_dir", help="Output base directory")
    parser.add_argument("--min-songs", type=int, default=4, help="Minimum songs per artist for LoKR")
    args = parser.parse_args()

    mp3_dir = Path(args.mp3_dir)
    output_dir = Path(args.output_dir)

    artist_songs = defaultdict(list)
    for f in sorted(mp3_dir.glob("*.mp3")):
        info = parse_bugs_filename(f.name)
        if info:
            info["path"] = str(f)
            info["filename"] = f.name
            artist_songs[info["artist"]].append(info)

    print(f"Total artists: {len(artist_songs)}")
    print(f"Artists with >= {args.min_songs} songs:")

    eligible = {}
    for artist, songs in sorted(artist_songs.items(), key=lambda x: -len(x[1])):
        if len(songs) >= args.min_songs:
            eligible[artist] = songs
            print(f"  {artist}: {len(songs)} songs")

    for artist, songs in eligible.items():
        safe_name = re.sub(r'[^\w가-힣]', '_', artist).strip('_')
        artist_dir = output_dir / safe_name
        artist_dir.mkdir(parents=True, exist_ok=True)

        dataset = []
        for s in songs:
            mp3_name = s["filename"]
            wav_name = Path(mp3_name).stem + ".wav"
            dur = get_duration(s["path"])
            dataset.append({
                "id": Path(mp3_name).stem,
                "audio_path": wav_name,
                "mp3_source": mp3_name,
                "caption": guess_caption(s["title"], artist),
                "lyrics": "",
                "duration": int(dur),
                "title": s["title"],
                "artist": artist,
                "rank": s["rank"],
            })

        ds_path = artist_dir / "dataset.json"
        with open(ds_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        print(f"  -> {ds_path} ({len(dataset)} entries)")

    summary = {a: len(s) for a, s in eligible.items()}
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSummary saved to {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
