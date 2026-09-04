import json, requests, random, time

EXAONE_URL = "http://100.107.229.5:8080/v1/chat/completions"

AGENTS = {
    "세인": "트렌드, 기술과 인간의 접점, 세대 감성, 사회적 순간",
    "관조": "일상의 시학, 기억, 관계, 자연, 사물의 의인화",
    "아리스토": "철학, 심리학, 실존, 내면 갈등, 보편적 진리",
    "해윰": "영화적 장면, 색온도, 사운드스케이프, 편집 문법",
    "연서": "사랑/이별/썸, 관계의 미세 신호, 디지털 사랑 증거",
    "해학": "자조/풍자/블랙코미디, 모순과 아이러니, 펀치라인",
    "동화": "아이의 시선, 사물 1인칭 서사, 판타지→현실 착지",
    "나그네": "여행/이동의 감정학, 사진 한 장의 기록, 떠남과 귀환",
    "화폭": "색채/구도/빛, 정적 시각예술, 프레임 안/밖의 긴장",
    "고2병": "10대 당사자의 날것, 교실 우주, 첫사랑/우정/입시",
}

LYRICISTS = {
    "Seoul Kim": {"style": "시적 서정", "endings": "~거든/~잖아/~인걸/~했어", "chars": "350~500"},
    "Arkedia": {"style": "인디·시티팝", "endings": "~야/~지/~까/~걸/~네", "chars": "350~500"},
    "Mushin": {"style": "힙합", "endings": "~야/~지/~다/~해/~어", "chars": "500~900"},
    "Prism": {"style": "댄스/팝", "endings": "~야/~어/~해/~지", "chars": "350~500"},
    "Haru": {"style": "인디 어쿠스틱", "endings": "~어/~야/~지/~네/~걸", "chars": "350~500"},
    "Sona": {"style": "재즈팝", "endings": "~어/~지/~나/~걸/~야", "chars": "300~500"},
    "달하": {"style": "어덜트 컨템포러리", "endings": "~지/~네/~겠지/~더라", "chars": "350~500"},
    "석돌": {"style": "인디록", "endings": "~다/~지/~잖아/~는데/~까", "chars": "350~500"},
    "나비": {"style": "자조팝", "endings": "~잖아/~어/~야/~지뭐/~다고", "chars": "350~500"},
}

GENRES = ["Piano Ballad", "R&B", "Indie Pop", "Acoustic", "Hip-Hop", "City Pop", "Jazz Pop", "Indie Rock", "Dance Pop", "Adult Contemporary"]

SECTION_TAGS = "Intro, Verse 1, Verse 2, Pre-Chorus, Chorus, Chorus 2, Bridge, Outro, Hook, Drop"


def call_exaone(system, user, max_tokens=2500, temperature=0.7, prefill=""):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})
    resp = requests.post(EXAONE_URL, json={
        "model": "exaone",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }, timeout=300)
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    if prefill:
        content = prefill + content
    return content, data["usage"]["total_tokens"]


# === STEP 1: 테마 뽑기 ===
STEP1_SYSTEM = """당신은 음악 테마 발굴 전문가입니다.

[규칙]
- 테마를 딱 한 줄(20~50자)만 출력하세요.
- 설명, 가사, 컨셉, 제목, 해설 등 절대 쓰지 마세요.
- 구체적인 장면/소재가 있어야 합니다.
- 추상적이거나 뻔한 것은 피하세요.

[좋은 출력 예시]
입력: 에이전트=식탁, 장르=Ballad
출력: 할머니가 쓰던 나무 도마의 칼자국 수를 세던 오후

입력: 에이전트=해학, 장르=Pop
출력: 다이어트 앱에 치킨 먹은 걸 솔직하게 기록하는 사람

입력: 에이전트=나그네, 장르=Acoustic
출력: 공항 환승 게이트에서 충전기 없이 보낸 다섯 시간

[나쁜 출력 예시 — 절대 이렇게 하지 마세요]
- 제목을 붙이거나 **볼드**를 쓰는 것
- 가사를 쓰는 것
- 컨셉 설명을 쓰는 것
- 여러 줄을 쓰는 것

테마 한 줄만 출력:"""


# === STEP 2: 에피소드 확장 ===
STEP2_SYSTEM = """당신은 음악 에피소드 설계 전문가입니다.

[임무] 테마를 3막 에피소드로 확장하고 음악 씨드를 추출하세요.
[출력 형식] 아래 JSON만 출력. 설명/해설/가사 금지.

[출력 예시]
{"episode":"퇴근길 지하철에서 갑자기 할머니 생각이 난다. 손에 쥔 도시락 냄새가 어릴 적 부엌과 겹치며, 눈시울이 붉어진 채로 집에 도착해 냉장고를 연다.","emotion_trajectory":"무심함→그리움→따뜻한 슬픔","energy_pattern":"low→mid→low","imagery":["지하철 손잡이에 매달린 손","도시락 김 서리는 뚜껑","냉장고 불빛에 비친 얼굴"],"voice_mood":"잔잔하지만 목이 메인 듯한 중저음"}

JSON만 출력:"""


# === STEP 5: 가사 쓰기 ===
STEP5_SYSTEM_TEMPLATE = """당신은 한국 음악 작사가 '{lyricist}'입니다.
스타일: {style}
선호 종결어미: {endings}

[절대 규칙]
1. 가사 길이: {chars}자
2. 섹션 태그는 [Verse 1], [Pre-Chorus], [Chorus] 등 대괄호+Title Case
3. 종결어미의 50% 이상은 선호 종결어미에서 사용
4. ~다/~요 비율 15% 이하
5. 악기 태그 3~8개: [soft piano arpeggio], [warm string swell] 등
6. 한국어 가사만 (영어 금지, 고유명사/감탄사 제외)

[출력 형식]
가사만 출력하세요. 해설/분석/프로덕션 노트/감정 궤적 설명/작곡 방향 등 절대 쓰지 마세요.
[Verse 1]로 시작해서 가사 텍스트만 출력하세요.

[출력 예시]
[Verse 1]
새벽 네 시의 커서
깜빡이는 물음표
증명할 수 없는 것들이
머리 위로 쌓여가

[soft piano arpeggio]

[Pre-Chorus]
어머니의 세 글자
기도했어
읽지 않은 채로 둔 그 말이
화면 위에 떠 있어

[Chorus]
무릎이 먼저 알았어
머리보다 먼저
차가운 나무 바닥 위에
닿는 순간

[warm string swell]

위와 같은 형식으로 가사를 써주세요. 해설 금지."""


# === STEP 8: 제목 짓기 ===
STEP8_SYSTEM = """당신은 한국 음악 제목 전문가입니다.

[규칙]
1. 2~7음절 (1음절 금지, 8음절 이상 금지)
2. 제목이 가사 본문에 등장하는 구절이어야 함
3. ~다/~이다 선언적 어미 금지
4. 후렴(Chorus) 훅에서 추출 우선

[출력 형식] JSON 한 줄만. 해설/분석 금지.

[출력 예시]
{"titles":["무릎이 먼저","깜빡이는 물음표","새벽빛"],"pick":"무릎이 먼저","reason":"후렴 첫 줄, 4음절, 강렬한 이미지"}

JSON만 출력:"""


def run_pipeline():
    agents_selected = random.sample(list(AGENTS.keys()), 10)
    lyricist_names = list(LYRICISTS.keys())
    results = []

    for i, agent_name in enumerate(agents_selected):
        agent_desc = AGENTS[agent_name]
        lyricist_name = lyricist_names[i % len(lyricist_names)]
        lyricist = LYRICISTS[lyricist_name]
        genre = GENRES[i % len(GENRES)]

        print(f"\n{'='*60}")
        print(f"[{i+1}/10] 에이전트: {agent_name} | 작사가: {lyricist_name} | 장르: {genre}")
        print(f"{'='*60}")

        # Step 1: 테마
        print(f"  Step 1: 테마 뽑기...")
        theme_raw, tok1 = call_exaone(
            STEP1_SYSTEM,
            f"에이전트: {agent_name}\n세계관: {agent_desc}\n장르 힌트: {genre}",
            max_tokens=60, temperature=0.9,
            prefill=""
        )
        theme = theme_raw.strip().split('\n')[0].strip().strip('"').strip("'").strip('*').strip()
        if len(theme) > 80:
            theme = theme[:80]
        print(f"    테마: {theme} ({tok1} tokens)")

        # Step 2: 에피소드
        print(f"  Step 2: 에피소드 확장...")
        episode_raw, tok2 = call_exaone(
            STEP2_SYSTEM,
            f"테마: {theme}\n장르: {genre}",
            max_tokens=400, temperature=0.7,
            prefill='{"episode":"'
        )
        print(f"    에피소드 생성 완료 ({tok2} tokens)")
        try:
            episode = json.loads(episode_raw)
        except json.JSONDecodeError:
            start = episode_raw.find('{')
            end = episode_raw.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    episode = json.loads(episode_raw[start:end])
                except:
                    episode = {"episode": episode_raw[:300], "emotion_trajectory": "", "energy_pattern": "", "imagery": [], "voice_mood": ""}
            else:
                episode = {"episode": episode_raw[:300], "emotion_trajectory": "", "energy_pattern": "", "imagery": [], "voice_mood": ""}

        # Step 5: 가사
        print(f"  Step 5: 가사 쓰기...")
        step5_system = STEP5_SYSTEM_TEMPLATE.format(
            lyricist=lyricist_name,
            style=lyricist["style"],
            endings=lyricist["endings"],
            chars=lyricist["chars"],
            section_tags=SECTION_TAGS,
        )
        step5_user = f"""테마: {theme}
장르: {genre}
에피소드: {episode.get('episode', '')}
감정 궤적: {episode.get('emotion_trajectory', '')}
에너지 패턴: {episode.get('energy_pattern', '')}
이미지: {', '.join(episode.get('imagery', []) if isinstance(episode.get('imagery'), list) else [])}
보컬 분위기: {episode.get('voice_mood', '')}

위 내용을 바탕으로 가사를 써주세요."""

        lyrics_raw, tok5 = call_exaone(step5_system, step5_user, max_tokens=1000, temperature=0.7,
                                        prefill="[Verse 1]\n")
        # 해설 부분 제거 (가사 뒤에 붙는 분석글)
        lyrics = lyrics_raw
        for marker in ["\n\n---", "\n\n###", "\n\n가사는 ", "\n\n**해설", "\n\n> ", "\n\n작곡", "\n\n이 곡"]:
            idx = lyrics.find(marker)
            if idx > 100:
                lyrics = lyrics[:idx].strip()
        print(f"    가사 완료 ({len(lyrics)}자, {tok5} tokens)")

        # Step 8: 제목
        print(f"  Step 8: 제목 짓기...")
        title_raw, tok8 = call_exaone(
            STEP8_SYSTEM,
            f"장르: {genre}\n작사가: {lyricist_name}\n\n{lyrics}",
            max_tokens=200, temperature=0.5,
            prefill='{"titles":["'
        )
        try:
            title_data = json.loads(title_raw)
        except json.JSONDecodeError:
            start = title_raw.find('{')
            end = title_raw.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    title_data = json.loads(title_raw[start:end])
                except:
                    title_data = {"titles": [], "pick": "", "reason": title_raw[:200]}
            else:
                title_data = {"titles": [], "pick": "", "reason": title_raw[:200]}
        print(f"    제목: {title_data.get('pick', '?')} ({tok8} tokens)")

        total_tokens = tok1 + tok2 + tok5 + tok8

        results.append({
            "index": i + 1,
            "agent": agent_name,
            "agent_desc": agent_desc,
            "lyricist": lyricist_name,
            "genre": genre,
            "theme": theme,
            "episode": episode,
            "lyrics": lyrics,
            "title": title_data,
            "tokens": {"step1": tok1, "step2": tok2, "step5": tok5, "step8": tok8, "total": total_tokens},
        })

        print(f"  === 완료: {title_data.get('pick', '?')} ({total_tokens} tokens total) ===")

    return results


if __name__ == "__main__":
    print("ThemeBank EXAONE Pipeline Test — 10세트")
    print(f"모델: EXAONE 4.0 32B Q5_K_M @ 100.107.229.5:8080\n")

    start = time.time()
    results = run_pipeline()
    elapsed = time.time() - start

    output_path = "/Users/leo/oven/themebank_exaone_results_v3.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"전체 완료: {elapsed:.0f}초")
    print(f"결과 저장: {output_path}")
    print(f"\n=== 10곡 요약 ===")
    for r in results:
        print(f"  [{r['index']}] {r['title'].get('pick', '?')} — {r['agent']}×{r['lyricist']} ({r['genre']})")
        print(f"      테마: {r['theme']}")
