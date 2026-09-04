#!/usr/bin/env python3
"""
5090에서 실행: bugs_top100/ MP3를 아티스트별 폴더로 분류 + WAV 변환 + dataset.json 생성
사용법: python organize_bugs_5090.py [--min-songs 4] [--artist ARTIST_NAME]
"""
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

MP3_DIR = Path(r"C:\Users\leo\ace-step-v15\bugs_top100")
BASE_DIR = Path(r"C:\Users\leo\ace-step-v15\lokr_artists")
FFMPEG = r"C:\Users\leo\ffmpeg\bin\ffmpeg.exe"


def parse_filename(fname):
    m = re.match(r"(\d+)\.\s*(.+?)\s*-\s*(.+?)(?:_\d{8}_\d{6})?\.mp3$", fname)
    if not m:
        return None
    return {"rank": int(m.group(1)), "title": m.group(2).strip(), "artist": m.group(3).strip()}


def safe_name(artist):
    return re.sub(r'[^\w가-힣]', '_', artist).strip('_')


def get_duration_ffprobe(fpath):
    try:
        r = subprocess.run(
            [FFMPEG.replace("ffmpeg", "ffprobe"), "-v", "quiet",
             "-show_entries", "format=duration", "-of", "csv=p=0", str(fpath)],
            capture_output=True, text=True, timeout=10
        )
        return float(r.stdout.strip())
    except Exception:
        return 180.0


def convert_to_wav(mp3_path, wav_path):
    if wav_path.exists() and wav_path.stat().st_size > 0:
        return True
    try:
        subprocess.run(
            [FFMPEG, "-y", "-i", str(mp3_path), "-ar", "48000", "-ac", "1",
             "-sample_fmt", "s16", str(wav_path)],
            capture_output=True, timeout=60
        )
        return wav_path.exists()
    except Exception as e:
        print(f"  ERROR converting {mp3_path.name}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-songs", type=int, default=4)
    parser.add_argument("--artist", type=str, default=None, help="Process only this artist")
    args = parser.parse_args()

    artist_songs = defaultdict(list)
    for f in sorted(MP3_DIR.glob("*.mp3")):
        info = parse_filename(f.name)
        if info:
            info["path"] = f
            artist_songs[info["artist"]].append(info)

    if args.artist:
        target = {k: v for k, v in artist_songs.items() if safe_name(k) == args.artist or k == args.artist}
        if not target:
            print(f"Artist '{args.artist}' not found. Available:")
            for a, s in sorted(artist_songs.items(), key=lambda x: -len(x[1])):
                if len(s) >= args.min_songs:
                    print(f"  {safe_name(a)} ({a}): {len(s)} songs")
            return
        eligible = target
    else:
        eligible = {a: s for a, s in artist_songs.items() if len(s) >= args.min_songs}

    print(f"Processing {len(eligible)} artists...")
    for artist, songs in sorted(eligible.items(), key=lambda x: -len(x[1])):
        sn = safe_name(artist)
        artist_dir = BASE_DIR / sn
        mp3_sub = artist_dir / "mp3"
        wav_sub = artist_dir / "wav"
        mp3_sub.mkdir(parents=True, exist_ok=True)
        wav_sub.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"Artist: {artist} ({sn}) - {len(songs)} songs")
        print(f"{'='*60}")

        dataset = []
        for s in songs:
            src = s["path"]
            dst_mp3 = mp3_sub / src.name
            if not dst_mp3.exists():
                import shutil
                shutil.copy2(src, dst_mp3)

            wav_name = src.stem + ".wav"
            wav_path = wav_sub / wav_name
            print(f"  [{s['rank']:3d}] {s['title']}", end="")

            if convert_to_wav(src, wav_path):
                dur = get_duration_ffprobe(wav_path)
                print(f" -> WAV OK ({dur:.0f}s)")
            else:
                dur = 180
                print(" -> WAV FAILED")

            dataset.append({
                "id": src.stem,
                "audio_path": wav_name,
                "caption": f"Korean pop, {artist} style, modern production, radio hit",
                "lyrics": "",
                "duration": int(dur),
                "title": s["title"],
                "artist": artist,
                "rank": s["rank"],
            })

        ds_path = artist_dir / "dataset.json"
        with open(ds_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print(f"  dataset.json saved: {len(dataset)} entries")

    print("\nDone!")


if __name__ == "__main__":
    main()
