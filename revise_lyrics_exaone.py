import json, glob, requests

EXAONE_URL = "http://100.107.229.5:8080/v1/chat/completions"

SYSTEM_PROMPT = """당신은 한국 음악 산업에서 20년 경력의 작사 전문가입니다.
가사를 받으면 다음을 수행하세요:

1. **진단**: 가장 약한 부분 2-3곳을 짚어주세요 (어색한 표현, 진부한 비유, 리듬 깨짐, 감정 전달 부족 등)
2. **수정본**: 원곡의 구조와 주제를 유지하면서 전체 가사를 수정해주세요. 수정한 부분은 【】로 표시해주세요.
3. **수정 이유**: 각 주요 수정에 대해 왜 바꿨는지 한 줄씩 설명해주세요.

원곡의 감성과 장르 특성을 존중하면서, 더 자연스럽고 강렬한 가사로 다듬어주세요."""

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

selected = songs[:10]
results = []

for i, song in enumerate(selected):
    print(f"[{i+1}/10] Revising {song['batch']}-{song['id']} ({song['lyricist']}, {song['genre']})...")

    user_msg = f"장르: {song['genre']}\n작사가: {song['lyricist']}\n\n{song['lyrics']}"

    resp = requests.post(EXAONE_URL, json={
        "model": "exaone",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 2000,
        "temperature": 0.5,
    }, timeout=180)

    data = resp.json()
    revision = data["choices"][0]["message"]["content"]
    tokens = data["usage"]["total_tokens"]

    results.append({
        "batch": song["batch"],
        "id": song["id"],
        "lyricist": song["lyricist"],
        "genre": song["genre"],
        "revision": revision,
        "tokens_used": tokens,
    })
    print(f"  Done ({tokens} tokens)")

output_path = "/Users/leo/oven/lyrics_revision_exaone.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nAll revisions saved to {output_path}")
