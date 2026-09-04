import json, glob, requests

EXAONE_URL = "http://100.107.229.5:8080/v1/chat/completions"

SYSTEM_PROMPT = """당신은 가사 비교 전문가입니다.
원본 가사와 수정본 가사를 받으면, 변경된 부분만 추출해서 다음 형식으로 정리해주세요:

### 변경 요약
(전체적으로 뭘 바꿨는지 1-2줄)

### 변경 내역
각 변경마다:

**[섹션명]**
- 원본: "원본 가사"
- 수정: "수정된 가사"
- 이유: (왜 바꿨는지 한 줄)

변경되지 않은 부분은 생략하세요. 변경이 없으면 "수정 없음 — 원곡 유지"라고만 써주세요."""

# Load originals
songs = []
for f in sorted(glob.glob("/Users/leo/leomusic2/generations/K*_STEP5_lyrics.json")):
    with open(f) as fp:
        data = json.load(fp)
        for s in data["songs"]:
            if "lyrics" in s:
                songs.append({
                    "batch": data["batch"],
                    "id": s["id"],
                    "lyricist": s.get("lyricist", "?"),
                    "genre": s.get("genre_group", "?"),
                    "lyrics": s["lyrics"],
                })

# Load revisions
with open("/Users/leo/oven/lyrics_revision_exaone.json") as f:
    revisions = json.load(f)

rev_map = {(r["batch"], r["id"]): r["revision"] for r in revisions}

selected = songs[:10]
results = []

for i, song in enumerate(selected):
    key = (song["batch"], song["id"])
    revision = rev_map.get(key, "")

    print(f"[{i+1}/10] Comparing {song['batch']}-{song['id']} ({song['lyricist']}, {song['genre']})...")

    user_msg = f"""장르: {song['genre']} | 작사가: {song['lyricist']}

=== 원본 ===
{song['lyrics']}

=== 수정본 ===
{revision}"""

    resp = requests.post(EXAONE_URL, json={
        "model": "exaone",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 1500,
        "temperature": 0.2,
    }, timeout=180)

    data = resp.json()
    comparison = data["choices"][0]["message"]["content"]
    tokens = data["usage"]["total_tokens"]

    results.append({
        "batch": song["batch"],
        "id": song["id"],
        "lyricist": song["lyricist"],
        "genre": song["genre"],
        "original": song["lyrics"],
        "comparison": comparison,
        "tokens_used": tokens,
    })
    print(f"  Done ({tokens} tokens)")

output_path = "/Users/leo/oven/lyrics_comparison_exaone.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nAll comparisons saved to {output_path}")
