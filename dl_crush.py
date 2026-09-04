#!/usr/bin/env python3
"""크러쉬(Crush) 곡 수집 — ACE-Step 1.5 LoKR 학습용"""

import subprocess
import json
import os
import re

OUTPUT_DIR = os.path.expanduser("~/oven/crush_dataset")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEARCHES = [
    "ytsearch50:Crush 크러쉬 official audio",
    "ytsearch50:크러쉬 Crush MV",
    "ytsearch30:Crush 크러쉬 album track",
    "ytsearch30:크러쉬 솔로 음원",
    "ytsearch20:크러쉬 with HER 앨범",
    "ytsearch20:크러쉬 wonderlost 앨범",
    "ytsearch20:크러쉬 FANG 앨범",
    "ytsearch20:크러쉬 From Midnight To Sunrise",
    "ytsearch20:Crush 크러쉬 feat",
]

DELIM = "|||"

# 크러쉬 가수 관련 키워드 (제목에 포함되어야 함)
CRUSH_PATTERNS = [
    r"크러쉬",
    r"(?i)crush\s*\(",      # Crush (
    r"(?i)crush\s*-",       # Crush -
    r"(?i)crush\s*feat",    # Crush feat
    r"(?i)crush\s*'",       # Crush '
    r"(?i)^crush\s",        # Crush at start
    r"(?i)CRUSH\s",         # CRUSH (all caps)
]

# 확실히 아닌 것 제외
EXCLUDE_PATTERNS = [
    r"(?i)candy crush",
    r"(?i)crush on you.*tour",  # 팬캠 제외
    r"(?i)signs.*crush",
    r"(?i)crush.*stages",
    r"(?i)turn.*crush",
    r"(?i)reaction",
    r"(?i)cover\b",
    r"(?i)live\b.*concert",
    r"(?i)fancam",
    r"(?i)fan cam",
    r"(?i)직캠",
    r"(?i)ARTMS",
]


def is_crush_music(title):
    if any(re.search(p, title) for p in EXCLUDE_PATTERNS):
        return False
    return any(re.search(p, title) for p in CRUSH_PATTERNS)


def search_videos(query):
    cmd = [
        "yt-dlp", "--flat-playlist",
        "--print", f"%(id)s{DELIM}%(duration)s{DELIM}%(title)s",
        "--no-warnings", query,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.strip().split(DELIM)
        if len(parts) < 3:
            continue
        try:
            dur = float(parts[1])
        except (ValueError, TypeError):
            continue
        title = parts[2]
        if 60 <= dur <= 600 and is_crush_music(title):
            videos.append({"id": parts[0], "title": title, "duration": int(dur)})
    return videos


def download_audio(video_id, output_dir):
    output_template = os.path.join(output_dir, f"%(id)s.%(ext)s")
    cmd = [
        "yt-dlp", "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--no-playlist", "--no-warnings",
        "-o", output_template,
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return os.path.exists(os.path.join(output_dir, f"{video_id}.wav"))
    except subprocess.TimeoutExpired:
        return False


def main():
    print("=== 크러쉬(Crush) 곡 수집 ===")
    print(f"출력: {OUTPUT_DIR}\n")

    existing = {f.replace(".wav", "") for f in os.listdir(OUTPUT_DIR) if f.endswith(".wav")}
    print(f"기존 파일: {len(existing)}개\n")

    # 검색
    all_videos = {}
    for q in SEARCHES:
        print(f"검색: {q}... ", end="", flush=True)
        vids = search_videos(q)
        new = 0
        for v in vids:
            if v["id"] not in all_videos:
                all_videos[v["id"]] = v
                new += 1
        print(f"{len(vids)}개 발견, {new}개 신규 (누적 {len(all_videos)})")

    print(f"\n총 고유 트랙: {len(all_videos)}개")
    print("\n트랙 목록:")
    for v in sorted(all_videos.values(), key=lambda x: x["title"]):
        print(f"  {v['duration']:>3}s  {v['title'][:80]}")

    # 메타데이터 저장
    meta_path = os.path.join(OUTPUT_DIR, "tracklist.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(list(all_videos.values()), f, ensure_ascii=False, indent=2)
    print(f"\n트랙 리스트 저장: {meta_path}")

    # 다운로드
    to_dl = [v for v in all_videos.values() if v["id"] not in existing]
    print(f"\n다운로드 대상: {len(to_dl)}개\n")

    if not to_dl:
        print("다운로드할 곡이 없습니다.")
        return

    success, fail = 0, 0
    for i, v in enumerate(to_dl, 1):
        print(f"  [{i}/{len(to_dl)}] {v['title'][:60]}... ", end="", flush=True)
        if download_audio(v["id"], OUTPUT_DIR):
            print(f"OK ({v['duration']}s)")
            success += 1
        else:
            print("FAIL")
            fail += 1

    total_wav = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".wav")])
    print(f"\n=== 완료: 성공 {success}, 실패 {fail}, 총 WAV {total_wav}개 ===")


if __name__ == "__main__":
    main()
