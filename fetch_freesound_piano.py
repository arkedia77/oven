"""
Freesound.org 피아노 오디오 수집 스크립트
ACE-Step LoRA 학습용 — 프로덕션 스타일 피아노/키보드

사용법:
  python fetch_freesound_piano.py --api-key YOUR_API_KEY [--output-dir ./freesound_piano]
"""

import argparse
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

API_BASE = "https://freesound.org/apiv2"

SEARCH_QUERIES = [
    "piano loop",
    "piano chord progression",
    "piano melody",
    "rhodes loop",
    "electric piano loop",
    "keys loop",
    "piano riff",
    "lofi piano",
    "jazz piano",
    "soul piano",
    "piano chords",
    "wurlitzer loop",
    "piano ballad",
    "piano ambient",
    "piano rnb",
]

# CC0 or CC-BY (학습에 사용 가능) — URL 형식으로 매칭
ALLOWED_LICENSES = [
    "publicdomain/zero",    # CC0
    "licenses/by/",         # CC-BY (but not by-nc)
]

# CC-BY-NC는 제외
BLOCKED_LICENSES = [
    "licenses/by-nc",
]

MIN_DURATION = 10.0   # 초
MAX_DURATION = 240.0  # 초
MIN_SAMPLERATE = 22050
PAGE_SIZE = 150
MAX_PAGES_PER_QUERY = 10


def api_get(endpoint, params, api_key):
    params["token"] = api_key
    url = f"{API_BASE}{endpoint}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ACE-Step-Piano-Collector/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 60 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"  HTTP {e.code}: {e.reason}", flush=True)
                return None
        except Exception as e:
            print(f"  Error: {e}", flush=True)
            time.sleep(5)
    return None


def download_file(url, dest_path, api_key):
    download_url = f"{url}?token={api_key}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": "ACE-Step-Piano-Collector/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(dest_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            return True
        except Exception as e:
            print(f"  Download retry {attempt+1}: {e}", flush=True)
            time.sleep(5)
    return False


def search_and_collect(api_key, output_dir):
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = output_dir / "metadata.jsonl"
    dataset_entries = []

    # 이미 수집된 ID 추적
    collected_ids = set()
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                collected_ids.add(entry["freesound_id"])
        print(f"기존 수집 데이터 {len(collected_ids)}개 발견, 이어서 수집합니다.", flush=True)

    total_downloaded = len(collected_ids)

    for query in SEARCH_QUERIES:
        print(f"\n=== 검색: '{query}' ===", flush=True)
        page = 1

        while page <= MAX_PAGES_PER_QUERY:
            params = {
                "query": query,
                "fields": "id,name,tags,description,duration,samplerate,channels,type,license,previews,download,avg_rating,num_ratings",
                "filter": f"duration:[{MIN_DURATION} TO {MAX_DURATION}] samplerate:[{MIN_SAMPLERATE} TO *]",
                "sort": "rating_desc",
                "page_size": PAGE_SIZE,
                "page": page,
            }

            data = api_get("/search/text/", params, api_key)
            if not data or "results" not in data:
                break

            results = data["results"]
            if not results:
                break

            print(f"  페이지 {page}: {len(results)}개 결과 (전체 {data.get('count', '?')}개)", flush=True)

            for sound in results:
                sid = sound["id"]
                if sid in collected_ids:
                    continue

                # 라이선스 필터
                license_name = sound.get("license", "")
                if any(bl in license_name for bl in BLOCKED_LICENSES):
                    continue
                if not any(lic in license_name for lic in ALLOWED_LICENSES):
                    continue

                # 오디오 다운로드 (preview HQ — 128kbps MP3, API key 불필요)
                previews = sound.get("previews", {})
                preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")

                if not preview_url:
                    continue

                # 파일명 생성
                safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in sound["name"][:60])
                filename = f"{sid}_{safe_name}.mp3"
                dest = audio_dir / filename

                if dest.exists():
                    collected_ids.add(sid)
                    total_downloaded += 1
                    continue

                # 다운로드 (preview는 토큰 불필요)
                try:
                    req = urllib.request.Request(preview_url, headers={"User-Agent": "ACE-Step-Piano-Collector/1.0"})
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        with open(dest, "wb") as f:
                            f.write(resp.read())
                except Exception as e:
                    print(f"  다운로드 실패 [{sid}]: {e}")
                    continue

                # 메타데이터 저장
                entry = {
                    "freesound_id": sid,
                    "filename": filename,
                    "name": sound["name"],
                    "tags": sound.get("tags", []),
                    "description": sound.get("description", "")[:500],
                    "duration": sound["duration"],
                    "samplerate": sound.get("samplerate", 0),
                    "license": license_name,
                    "avg_rating": sound.get("avg_rating", 0),
                    "num_ratings": sound.get("num_ratings", 0),
                }

                with open(metadata_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

                collected_ids.add(sid)
                total_downloaded += 1

                if total_downloaded % 50 == 0:
                    print(f"  >>> 총 {total_downloaded}개 수집 완료")

            # 다음 페이지
            if not data.get("next"):
                break
            page += 1
            time.sleep(0.5)  # rate limit 존중

    print(f"\n=== 수집 완료: 총 {total_downloaded}개 ===")
    print(f"오디오: {audio_dir}")
    print(f"메타데이터: {metadata_path}")
    return total_downloaded


def generate_dataset_json(output_dir):
    """메타데이터에서 ACE-Step용 dataset.json 생성"""
    metadata_path = output_dir / "metadata.jsonl"
    dataset_path = output_dir / "dataset.json"

    if not metadata_path.exists():
        print("metadata.jsonl이 없습니다.")
        return

    entries = []
    with open(metadata_path, encoding="utf-8") as f:
        for line in f:
            meta = json.loads(line)

            # 태그에서 캡션 생성
            tags = meta.get("tags", [])
            tag_str = ", ".join(tags[:15]) if tags else "piano, instrumental"

            # BPM 추출 시도 (태그나 이름에서)
            bpm = ""
            for t in tags:
                if t.replace("bpm", "").strip().isdigit():
                    bpm = t
                    break

            caption_parts = []
            # 장르/스타일 태그
            style_tags = [t for t in tags if t.lower() in (
                "jazz", "lofi", "lo-fi", "soul", "rnb", "r&b", "pop", "house",
                "ambient", "cinematic", "classical", "blues", "funk", "gospel",
                "hip-hop", "trap", "chill", "electronic", "disco",
            )]
            if style_tags:
                caption_parts.extend(style_tags[:3])

            # 악기 태그
            inst_tags = [t for t in tags if t.lower() in (
                "piano", "keys", "keyboard", "rhodes", "wurlitzer",
                "electric-piano", "synth", "organ",
            )]
            if inst_tags:
                caption_parts.extend(inst_tags[:2])
            else:
                caption_parts.append("piano")

            caption_parts.append("instrumental")

            if bpm:
                caption_parts.append(bpm)

            # 설명에서 키 정보 추출
            desc = meta.get("description", "").lower()
            for key_name in ["c major", "c minor", "d major", "d minor", "e major", "e minor",
                             "f major", "f minor", "g major", "g minor", "a major", "a minor",
                             "b major", "b minor", "c# minor", "eb minor", "f# minor", "ab minor", "bb minor"]:
                if key_name in desc:
                    caption_parts.append(key_name)
                    break

            entries.append({
                "audio_path": f"audio/{meta['filename']}",
                "caption": ", ".join(caption_parts),
                "lyrics": "[Instrumental]",
                "is_instrumental": True,
                "freesound_id": meta["freesound_id"],
            })

    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"dataset.json 생성: {len(entries)}개 엔트리 → {dataset_path}")


def main():
    parser = argparse.ArgumentParser(description="Freesound 피아노 오디오 수집")
    parser.add_argument("--api-key", required=True, help="Freesound API key")
    parser.add_argument("--output-dir", default="./freesound_piano", help="출력 디렉토리")
    parser.add_argument("--generate-tags-only", action="store_true", help="이미 수집된 데이터로 dataset.json만 생성")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.generate_tags_only:
        generate_dataset_json(output_dir)
        return

    # 1. 수집
    total = search_and_collect(args.api_key, output_dir)

    # 2. dataset.json 생성
    if total > 0:
        generate_dataset_json(output_dir)

    print(f"\n다음 단계: 5090으로 전송")
    print(f"  scp -r {output_dir} leo@100.107.229.5:D:/data/ace-step-piano/")


if __name__ == "__main__":
    main()
