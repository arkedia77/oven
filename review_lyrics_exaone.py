import json, glob, requests

EXAONE_URL = "http://100.107.229.5:8080/v1/chat/completions"

SYSTEM_PROMPT = """당신은 한국 음악 산업에서 20년 경력의 작사 전문가입니다.
가사를 받으면 다음 항목을 평가해주세요:

1. **언어 자연스러움** (1-10): 한국어 표현이 자연스러운가? 어색한 조사/어미가 있는가?
2. **감정 전달력** (1-10): 감정이 구체적이고 진정성 있게 전달되는가?
3. **이미지/비유** (1-10): 시각적 이미지나 비유가 신선하고 효과적인가?
4. **구조 완성도** (1-10): 절 구성, 후렴 반복, 브릿지 전환이 잘 되어있는가?
5. **상업성** (1-10): 대중이 공감하고 따라 부를 수 있는가?
6. **총평**: 2-3문장으로 핵심 강점과 개선점
7. **수정 제안**: 가장 아쉬운 구절 1-2개를 구체적으로 수정 제안

JSON 형식으로 응답해주세요."""

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
    print(f"[{i+1}/10] Reviewing {song['batch']}-{song['id']} ({song['lyricist']}, {song['genre']})...")

    user_msg = f"장르: {song['genre']}\n작사가: {song['lyricist']}\n\n{song['lyrics']}"

    resp = requests.post(EXAONE_URL, json={
        "model": "exaone",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 1000,
        "temperature": 0.3,
    }, timeout=120)

    data = resp.json()
    review = data["choices"][0]["message"]["content"]
    tokens = data["usage"]["total_tokens"]

    results.append({
        "batch": song["batch"],
        "id": song["id"],
        "lyricist": song["lyricist"],
        "genre": song["genre"],
        "review": review,
        "tokens_used": tokens,
    })
    print(f"  Done ({tokens} tokens)")

output_path = "/Users/leo/oven/lyrics_review_exaone.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nAll reviews saved to {output_path}")
