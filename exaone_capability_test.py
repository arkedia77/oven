"""
EXAONE 4.0 32B 종합 능력 테스트 — 6카테고리 20테스트
ThemeBank/leomusic 파이프라인 투입 적합성 판단용
"""
import json, requests, time, re, sys

EXAONE_URL = "http://100.107.229.5:8080/v1/chat/completions"

# 테스트용 참조 가사 (leomusic 스타일 한국어 가사)
REF_LYRICS = """[Verse 1]
새벽 두 시에 방송을 켰거든
화면 속 애가 웃고 있잖아
그 말 한마디에 눈물이 났었어
진짜로 쏟아졌거든

[soft piano arpeggio]

[Pre-Chorus]
픽셀 너머로 손을 뻗으면
닿을 것 같은 그 온기가
가짜인 걸 알면서도
왜 이렇게 따뜻한 건지

[Chorus]
화면이 꺼지면 사라질 너인걸
알면서도 또 켜잖아
이 밤이 끝나면 혼자인 걸
알면서도 웃고 있잖아

[warm string swell]

[Verse 2]
댓글창에 적은 고마워가
허공에 뜨는 풍선 같거든
잡으려 하면 터지는 그 말이
내 하루를 버티게 했잖아

[Bridge]
진짜 위로가 뭔지 몰라
가짜 웃음이 날 살렸거든
모순투성이 이 새벽이
그래도 내 편이었잖아

[Chorus]
화면이 꺼지면 사라질 너인걸
알면서도 또 켜잖아
이 밤이 끝나면 혼자인 걸
알면서도 웃고 있잖아

[piano fade out]"""

REF_LYRICS_HIPHOP = """[Verse 1]
매일 아침 알람 세 개를 깨도
눈 뜨면 이미 지각이야
커피 한 잔에 담긴 각성제
그게 내 하루의 시작이지

월급날까지 남은 날 세다가
통장 잔고에 한숨이 나와
점심값 아끼려 편의점 삼각김밥
이게 서울 생존법이야

[Pre-Chorus]
그래도 버텨 매일매일
포기하면 끝이니까
작은 방 한 칸이 내 왕국이야
여기서부터 다시 시작해

[Chorus]
출근길 지하철 사람들 사이
다들 같은 표정이야
그래도 걸어 멈추지 마
오늘도 살아남는 거야

[hard snare hit]

[Verse 2]
야근 끝나고 편의점 맥주 하나
벤치에 앉아 하늘을 봐
별은 안 보여도 달은 떠 있어
그것만으로 충분해

상사한테 깨진 자존심
화장실에서 삼킨 눈물
그래도 내일 아침이면
다시 넥타이를 매지"""


def call_exaone(system, user, max_tokens=2500, temperature=0.7, prefill=""):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})
    try:
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
    except Exception as e:
        return f"[ERROR] {e}", 0


def count_syllables_ko(text):
    return sum(1 for c in text if '가' <= c <= '힣')


def count_chars_ko(text):
    clean = re.sub(r'\[.*?\]', '', text)
    clean = re.sub(r'\s+', '', clean)
    return len(clean)


def check_endings(text, pool):
    lines = [l.strip() for l in text.split('\n') if l.strip() and not l.strip().startswith('[')]
    if not lines:
        return 0, 0
    matches = 0
    for line in lines:
        for ending in pool:
            e = ending.replace('~', '')
            if line.endswith(e):
                matches += 1
                break
    return matches, len(lines)


def has_english(text):
    clean = re.sub(r'\[.*?\]', '', text)
    eng = re.findall(r'[a-zA-Z]{3,}', clean)
    return len(eng)


def extract_section_tags(text):
    return re.findall(r'\[([A-Z][a-zA-Z\s\d]+)\]', text)


def extract_instrument_tags(text):
    return re.findall(r'\[([a-z][a-z\s]+)\]', text)


# =====================================================================
# Category 1: 제약 출력 형식 준수
# =====================================================================

def test_1_1_single_line_theme():
    """한 줄 테마 생성 (20~50자 이내)"""
    system = """당신은 음악 테마 발굴 전문가입니다.
테마를 딱 한 줄(20~50자)만 출력하세요.
설명, 가사, 컨셉, 제목, 해설 등 절대 쓰지 마세요.
구체적인 장면/소재가 있어야 합니다.

좋은 출력 예시:
할머니가 쓰던 나무 도마의 칼자국 수를 세던 오후

테마 한 줄만 출력:"""

    results = []
    for agent, desc in [("세인", "트렌드, 기술과 인간의 접점"), ("해학", "자조/풍자/블랙코미디"), ("나그네", "여행/이동의 감정학")]:
        out, tok = call_exaone(system, f"에이전트: {agent}\n세계관: {desc}\n장르: Ballad", max_tokens=80, temperature=0.9)
        lines = [l.strip() for l in out.strip().split('\n') if l.strip()]
        first_line = lines[0] if lines else out.strip()
        char_count = len(first_line)
        results.append({
            "agent": agent,
            "output": out.strip()[:200],
            "first_line": first_line[:100],
            "line_count": len(lines),
            "char_count": char_count,
            "pass_single_line": len(lines) == 1,
            "pass_length": 15 <= char_count <= 60,
            "pass_no_explanation": not any(k in out for k in ["컨셉", "제목:", "설명:", "**", "###"]),
        })
    return results


def test_1_2_json_output():
    """JSON 형식 출력 (에피소드 생성)"""
    system = """당신은 음악 에피소드 설계 전문가입니다.
아래 JSON 형식만 출력하세요. 설명/해설 금지.
{"episode":"...","emotion_trajectory":"...","energy_pattern":"...","imagery":["..."],"voice_mood":"..."}
JSON만 출력:"""

    results = []
    for theme in ["새벽 편의점에서 전 여자친구를 마주친 순간", "할머니의 된장찌개 냄새가 나는 골목"]:
        out, tok = call_exaone(system, f"테마: {theme}\n장르: R&B", max_tokens=400, temperature=0.7, prefill='{"episode":"')
        valid_json = False
        try:
            json.loads(out)
            valid_json = True
        except:
            start = out.find('{')
            end = out.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    json.loads(out[start:end])
                    valid_json = True
                except:
                    pass
        has_all_keys = all(k in out for k in ["episode", "emotion_trajectory", "energy_pattern", "imagery", "voice_mood"])
        results.append({
            "theme": theme,
            "output": out[:300],
            "pass_valid_json": valid_json,
            "pass_has_keys": has_all_keys,
            "pass_no_extra": not any(k in out for k in ["###", "설명:", "참고:"]),
        })
    return results


def test_1_3_numbered_list():
    """번호 매기기 리스트 형식"""
    system = "당신은 음악 테마 전문가입니다. 요청받은 개수만큼 번호를 매겨 테마를 나열하세요. 각 테마는 한 줄, 20~40자. 번호와 테마만 출력. 해설 금지."
    out, tok = call_exaone(system, "5개의 '이별' 관련 테마를 번호를 매겨 나열하세요.", max_tokens=300, temperature=0.8)
    lines = [l.strip() for l in out.strip().split('\n') if l.strip()]
    numbered = [l for l in lines if re.match(r'^\d+[\.\)]\s', l)]
    return [{
        "output": out[:500],
        "total_lines": len(lines),
        "numbered_lines": len(numbered),
        "pass_count_5": len(numbered) == 5,
        "pass_all_numbered": len(numbered) == len(lines),
        "pass_no_explanation": not any(k in out for k in ["참고", "추가", "이 테마", "위의"]),
    }]


def test_1_4_char_count_control():
    """글자수 제어 (정확히 N자 이내 요약)"""
    system = "다음 텍스트를 정확히 50자 이내로 요약하세요. 요약문만 출력. 원문 반복, 해설 금지."
    long_text = "서울 강남역 근처의 작은 카페에서 매일 아침 같은 자리에 앉아 아메리카노를 마시는 남자가 있다. 그는 항상 창가 자리를 고집하며, 노트북 대신 낡은 수첩에 무언가를 적는다. 주인장은 그가 소설가라고 했지만, 아무도 그의 이름으로 된 책을 본 적이 없다."
    out, tok = call_exaone(system, long_text, max_tokens=100, temperature=0.3)
    clean = out.strip().split('\n')[0].strip()
    return [{
        "output": clean[:200],
        "char_count": len(clean),
        "pass_under_50": len(clean) <= 55,
        "pass_single_line": '\n' not in out.strip(),
        "pass_no_meta": not any(k in out for k in ["요약:", "원문:", "결과:"]),
    }]


# =====================================================================
# Category 2: 한국어 가사 생성
# =====================================================================

def test_2_1_lyrics_zero_shot():
    """가사 생성 — 제로샷 (프리필 없음)"""
    system = """당신은 한국 음악 작사가 'Seoul Kim'입니다.
스타일: 시적 서정
종결어미: ~거든/~잖아/~인걸/~했어
가사 길이: 350~500자
섹션 태그: [Verse 1], [Pre-Chorus], [Chorus] 등 대괄호+Title Case
악기 태그 3~8개: [soft piano arpeggio] 등 소문자
한국어 가사만 출력하세요. 해설/분석 절대 금지.
[Verse 1]로 시작하세요."""

    out, tok = call_exaone(system, "테마: 빗소리에 묻힌 전화벨\n장르: Piano Ballad", max_tokens=1000, temperature=0.7)
    sections = extract_section_tags(out)
    instruments = extract_instrument_tags(out)
    eng_count = has_english(out)
    char_count = count_chars_ko(out)
    endings_match, total_lines = check_endings(out, ["거든", "잖아", "인걸", "했어"])

    return [{
        "method": "zero-shot",
        "output": out[:600],
        "char_count": char_count,
        "sections": sections,
        "instruments": instruments,
        "english_words": eng_count,
        "endings_match": f"{endings_match}/{total_lines}",
        "pass_korean_only": eng_count <= 2,
        "pass_has_sections": len(sections) >= 3,
        "pass_has_instruments": len(instruments) >= 2,
        "pass_char_range": 250 <= char_count <= 600,
        "pass_starts_verse": out.strip().startswith("[Verse"),
        "pass_no_analysis": not any(k in out for k in ["감정 궤적", "에너지 패턴", "프로덕션", "해설"]),
    }]


def test_2_2_lyrics_with_prefill():
    """가사 생성 — 프리필 트릭"""
    system = """당신은 한국 음악 작사가 'Arkedia'입니다.
스타일: 인디·시티팝
종결어미: ~야/~지/~까/~걸/~네
가사 길이: 350~500자
한국어 가사만. [Verse 1]로 시작. 해설 금지."""

    out, tok = call_exaone(system, "테마: 자판기 커피를 두 잔 뽑는 습관\n장르: City Pop",
                           max_tokens=1000, temperature=0.7, prefill="[Verse 1]\n")
    sections = extract_section_tags(out)
    instruments = extract_instrument_tags(out)
    eng_count = has_english(out)
    char_count = count_chars_ko(out)
    endings_match, total_lines = check_endings(out, ["야", "지", "까", "걸", "네"])

    return [{
        "method": "prefill",
        "output": out[:600],
        "char_count": char_count,
        "sections": sections,
        "english_words": eng_count,
        "endings_ratio": f"{endings_match}/{total_lines}",
        "pass_korean_only": eng_count <= 2,
        "pass_has_sections": len(sections) >= 3,
        "pass_char_range": 250 <= char_count <= 600,
        "pass_starts_verse": out.strip().startswith("[Verse"),
        "pass_endings_50pct": endings_match / max(total_lines, 1) >= 0.4,
    }]


def test_2_3_lyrics_few_shot():
    """가사 생성 — 퓨샷 (예시 제공 후 생성)"""
    system = """당신은 한국 음악 작사가입니다.
아래 예시와 같은 형식으로 가사를 쓰세요. 해설 금지.

[예시]
[Verse 1]
새벽 두 시에 방송을 켰거든
화면 속 애가 웃고 있잖아
그 말 한마디에 눈물이 났었어
진짜로 쏟아졌거든

[soft piano arpeggio]

[Pre-Chorus]
픽셀 너머로 손을 뻗으면
닿을 것 같은 그 온기가

[Chorus]
화면이 꺼지면 사라질 너인걸
알면서도 또 켜잖아

위와 동일한 형식으로 새로운 가사를 써주세요."""

    out, tok = call_exaone(system, "테마: 우산 없이 걸어본 퇴근길\n장르: Acoustic\n작사가: Haru\n종결어미: ~어/~야/~지/~네/~걸",
                           max_tokens=1000, temperature=0.7, prefill="[Verse 1]\n")
    sections = extract_section_tags(out)
    eng_count = has_english(out)
    char_count = count_chars_ko(out)
    endings_match, total_lines = check_endings(out, ["어", "야", "지", "네", "걸"])

    return [{
        "method": "few-shot + prefill",
        "output": out[:600],
        "char_count": char_count,
        "sections": sections,
        "english_words": eng_count,
        "endings_ratio": f"{endings_match}/{total_lines}",
        "pass_korean_only": eng_count <= 2,
        "pass_has_sections": len(sections) >= 3,
        "pass_char_range": 250 <= char_count <= 600,
        "pass_endings_50pct": endings_match / max(total_lines, 1) >= 0.4,
    }]


def test_2_4_lyrics_chain_of_thought():
    """가사 생성 — 체인오브소트 (사고→생성 2단계)"""
    # Step A: 구조 설계
    system_a = """주어진 테마로 가사 구조를 설계하세요.
출력 형식 (JSON만):
{"sections":["Verse 1","Pre-Chorus","Chorus","Verse 2","Bridge","Chorus"],"per_section_lines":4,"key_images":["이미지1","이미지2","이미지3"],"hook_phrase":"후렴 핵심 구절"}
JSON만 출력:"""

    plan_raw, tok_a = call_exaone(system_a, "테마: 새벽 배달 오토바이의 빨간 불빛\n장르: R&B",
                                   max_tokens=300, temperature=0.5, prefill='{"sections":["')
    # Step B: 구조 기반 가사 생성
    system_b = """당신은 한국 음악 작사가 'Sona'입니다.
스타일: 재즈팝. 종결어미: ~어/~지/~나/~걸/~야
아래 구조를 따라 한국어 가사를 쓰세요. 해설 금지."""

    out, tok_b = call_exaone(system_b, f"구조 설계:\n{plan_raw[:300]}\n\n위 구조대로 가사를 써주세요.",
                              max_tokens=1000, temperature=0.7, prefill="[Verse 1]\n")
    sections = extract_section_tags(out)
    eng_count = has_english(out)
    char_count = count_chars_ko(out)

    return [{
        "method": "chain-of-thought (2-step)",
        "plan": plan_raw[:300],
        "output": out[:600],
        "char_count": char_count,
        "sections": sections,
        "english_words": eng_count,
        "tokens_total": tok_a + tok_b,
        "pass_korean_only": eng_count <= 2,
        "pass_has_sections": len(sections) >= 3,
        "pass_char_range": 250 <= char_count <= 600,
    }]


# =====================================================================
# Category 3: 한국어 언어 품질
# =====================================================================

def test_3_1_ending_compliance():
    """종결어미 풀 준수도 — 작사가 3명 비교"""
    results = []
    lyricists = [
        ("Seoul Kim", "시적 서정", ["거든", "잖아", "인걸", "했어"]),
        ("Mushin", "힙합", ["야", "지", "다", "해", "어"]),
        ("나비", "자조팝", ["잖아", "어", "야", "지뭐", "다고"]),
    ]
    for name, style, pool in lyricists:
        system = f"""당신은 한국 작사가 '{name}'입니다. 스타일: {style}.
종결어미의 50% 이상을 다음에서 사용: {'/'.join('~'+e for e in pool)}
한국어 가사만. 해설 금지."""
        out, tok = call_exaone(system, f"테마: 늦은 밤 한강 산책\n장르: {'Hip-Hop' if name=='Mushin' else 'Ballad'}",
                               max_tokens=800, temperature=0.7, prefill="[Verse 1]\n")
        match, total = check_endings(out, pool)
        ratio = match / max(total, 1)
        results.append({
            "lyricist": name,
            "output": out[:400],
            "endings_match": f"{match}/{total} ({ratio:.0%})",
            "pass_50pct": ratio >= 0.5,
            "pass_korean": has_english(out) <= 2,
        })
    return results


def test_3_2_register_consistency():
    """어체 일관성 — 반말/존댓말 혼용 검사"""
    system = """당신은 한국 작사가입니다. 반말체로만 가사를 쓰세요.
~요/~습니다/~입니다 등 존댓말 어미를 절대 사용하지 마세요.
한국어 가사만. 해설 금지."""
    out, tok = call_exaone(system, "테마: 카페에서 마주친 옛 친구\n장르: Indie Pop",
                           max_tokens=800, temperature=0.7, prefill="[Verse 1]\n")
    polite = re.findall(r'(?:요|습니다|입니다|세요|겠습니다|합니다)(?:\s|$|\.)', out)
    lines = [l.strip() for l in out.split('\n') if l.strip() and not l.strip().startswith('[')]
    return [{
        "output": out[:500],
        "polite_endings_found": polite[:10],
        "polite_count": len(polite),
        "total_lines": len(lines),
        "pass_no_polite": len(polite) <= 1,
        "pass_korean": has_english(out) <= 2,
    }]


def test_3_3_imagery_freshness():
    """이미지 참신성 — 클리셰 vs 참신 비율"""
    system = """당신은 한국 작사가입니다. 참신한 비유와 이미지를 사용하세요.
'별처럼 빛나', '바다처럼 넓은', '꽃처럼 아름다운' 같은 흔한 비유를 피하세요.
구체적인 사물/장면/감각을 사용하세요.
한국어 가사만. 해설 금지."""
    out, tok = call_exaone(system, "테마: 졸업식 날 빈 교실\n장르: Acoustic",
                           max_tokens=800, temperature=0.8, prefill="[Verse 1]\n")
    cliches = ["별처럼", "바다처럼", "꽃처럼", "하늘처럼", "눈처럼", "바람처럼",
               "영원히", "언제까지나", "빛나는", "아름다운"]
    found_cliches = [c for c in cliches if c in out]
    return [{
        "output": out[:500],
        "cliches_found": found_cliches,
        "cliche_count": len(found_cliches),
        "pass_low_cliche": len(found_cliches) <= 2,
        "pass_korean": has_english(out) <= 2,
    }]


def test_3_4_wordplay():
    """언어유희/라임 — 힙합 가사에서 라임 검출"""
    system = """당신은 힙합 작사가 'Mushin'입니다.
각 연의 마지막 음절이 라임을 맞추도록 쓰세요.
한국어 가사만. 해설 금지."""
    out, tok = call_exaone(system, "테마: 새벽 3시 라면 끓이기\n장르: Hip-Hop",
                           max_tokens=800, temperature=0.8, prefill="[Verse 1]\n")
    lines = [l.strip() for l in out.split('\n') if l.strip() and not l.strip().startswith('[')]
    # 마지막 글자 추출
    last_chars = []
    for l in lines:
        if l:
            last_chars.append(l[-1])
    # 연속 라인 마지막 글자 유사성 (같은 모음)
    def get_vowel(char):
        if '가' <= char <= '힣':
            code = ord(char) - 0xAC00
            return (code // 28) % 21
        return -1

    rhyme_pairs = 0
    for i in range(len(last_chars) - 1):
        if get_vowel(last_chars[i]) == get_vowel(last_chars[i+1]) and get_vowel(last_chars[i]) >= 0:
            rhyme_pairs += 1

    return [{
        "output": out[:500],
        "total_lines": len(lines),
        "last_chars": ''.join(last_chars[:20]),
        "rhyme_pairs": rhyme_pairs,
        "pass_has_rhymes": rhyme_pairs >= 3,
        "pass_korean": has_english(out) <= 2,
    }]


# =====================================================================
# Category 4: 분석·비평 능력
# =====================================================================

def test_4_1_structured_scoring():
    """구조화된 점수 매기기 (가사 6기준 평가)"""
    system = """당신은 한국 음악 가사 평가 전문가입니다.
아래 6개 기준으로 가사를 평가하세요.

출력 형식 (JSON만):
{"singability":{"score":8,"comment":"..."},"originality":{"score":7,"comment":"..."},"imagery":{"score":8,"comment":"..."},"structure":{"score":7,"comment":"..."},"emotion":{"score":8,"comment":"..."},"title_fit":{"score":7,"comment":"..."},"total":45,"summary":"..."}

JSON만 출력. 해설/서론 금지."""

    out, tok = call_exaone(system, f"제목: 화면이 꺼지면\n장르: Piano Ballad\n작사가: Seoul Kim\n\n{REF_LYRICS}",
                           max_tokens=600, temperature=0.3, prefill='{"singability":{"score":')
    valid_json = False
    has_scores = False
    try:
        data = json.loads(out)
        valid_json = True
        has_scores = all(k in data for k in ["singability", "originality", "imagery"])
    except:
        start = out.find('{')
        end = out.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(out[start:end])
                valid_json = True
                has_scores = all(k in data for k in ["singability", "originality", "imagery"])
            except:
                pass

    return [{
        "output": out[:500],
        "pass_valid_json": valid_json,
        "pass_has_scores": has_scores,
        "pass_no_preamble": not out.strip().startswith("이 가사") and not out.strip().startswith("평가"),
    }]


def test_4_2_line_critique():
    """줄별 비평 — 가사 생성 없이 분석만"""
    system = """당신은 가사 비평가입니다.
아래 가사의 약한 줄 3개를 지적하고, 왜 약한지 설명하세요.
새로운 가사를 쓰지 마세요. 기존 가사에서 약한 부분만 인용+분석하세요.

출력 형식:
1. "[원문 줄]" — 약한 이유
2. "[원문 줄]" — 약한 이유
3. "[원문 줄]" — 약한 이유

위 형식만 출력."""

    out, tok = call_exaone(system, f"가사:\n{REF_LYRICS}", max_tokens=500, temperature=0.3)
    lines = [l.strip() for l in out.strip().split('\n') if l.strip()]
    has_quotes = sum(1 for l in lines if '"' in l or '"' in l or '「' in l)
    has_numbering = sum(1 for l in lines if re.match(r'^\d+[\.\)]', l))
    # 새 가사를 생성했는지 체크
    has_new_lyrics = any(tag in out for tag in ["[Verse", "[Chorus", "[Pre-Chorus"])

    return [{
        "output": out[:600],
        "line_count": len(lines),
        "has_quotes": has_quotes,
        "has_numbering": has_numbering,
        "pass_no_new_lyrics": not has_new_lyrics,
        "pass_has_critique": has_quotes >= 2 or has_numbering >= 2,
        "pass_format": has_numbering >= 3,
    }]


def test_4_3_translation_quality():
    """한영 번역 — 가사 뉘앙스 보존"""
    system = """한국어 가사를 영어로 번역하세요.
- 직역이 아닌 의역으로, 노래 가사로서의 리듬감 유지
- 각 줄을 대응시켜 번역
- 번역문만 출력. 원문 반복, 해설 금지."""

    source = """새벽 두 시에 방송을 켰거든
화면 속 애가 웃고 있잖아
그 말 한마디에 눈물이 났었어
진짜로 쏟아졌거든"""

    out, tok = call_exaone(system, f"번역할 가사:\n{source}", max_tokens=300, temperature=0.5)
    lines_out = [l.strip() for l in out.strip().split('\n') if l.strip()]
    has_english_out = sum(1 for l in lines_out if re.search(r'[a-zA-Z]{3,}', l))
    return [{
        "output": out[:400],
        "output_lines": len(lines_out),
        "english_lines": has_english_out,
        "pass_is_english": has_english_out >= 3,
        "pass_line_match": abs(len(lines_out) - 4) <= 2,
        "pass_no_korean_repeat": source[:20] not in out,
    }]


# =====================================================================
# Category 5: 수정·편집 능력
# =====================================================================

def test_5_1_targeted_replacement():
    """타겟 줄 교체 — 지정 줄만 수정"""
    system = """당신은 가사 편집자입니다.
지정된 줄만 수정하고, 나머지는 그대로 유지하세요.
전체 가사를 다시 써서 출력하되, 수정된 줄만 바꾸세요.
해설/분석 금지. 수정된 가사 전문만 출력."""

    out, tok = call_exaone(system, f"""다음 가사에서 아래 2줄만 더 참신한 표현으로 수정하세요:
- "화면 속 애가 웃고 있잖아" → 더 구체적인 이미지로
- "이 밤이 끝나면 혼자인 걸" → 더 감각적인 표현으로

원본 가사:
{REF_LYRICS}""", max_tokens=1200, temperature=0.5)

    # 수정되지 않아야 할 줄이 그대로 있는지
    preserved = [
        "새벽 두 시에 방송을 켰거든",
        "픽셀 너머로 손을 뻗으면",
        "알면서도 또 켜잖아",
    ]
    preserved_count = sum(1 for p in preserved if p in out)
    # 수정 대상 줄이 바뀌었는지
    changed_1 = "화면 속 애가 웃고 있잖아" not in out
    changed_2 = "이 밤이 끝나면 혼자인 걸" not in out

    return [{
        "output": out[:600],
        "preserved_lines": f"{preserved_count}/{len(preserved)}",
        "pass_preserved": preserved_count >= 2,
        "pass_changed_1": changed_1,
        "pass_changed_2": changed_2,
        "pass_has_sections": "[Verse" in out or "[Chorus" in out,
    }]


def test_5_2_register_conversion():
    """어체 변환 — 반말→존댓말 또는 역변환"""
    system = """다음 반말 가사를 존댓말(~요 체)로 변환하세요.
의미와 구조를 유지하고 어미만 변환하세요.
변환된 가사만 출력. 해설 금지."""

    source = """잠이 안 와 뒤척이다가
네 사진을 또 꺼냈어
웃고 있는 너를 보면서
나도 모르게 따라 웃었어"""

    out, tok = call_exaone(system, f"변환할 가사:\n{source}", max_tokens=300, temperature=0.3)
    polite = re.findall(r'(?:요|어요|았어요|았죠|네요|거든요|잖아요)(?:\s|$)', out)
    # 원문이 그대로 남아있지 않은지
    unchanged = source.strip() == out.strip()

    return [{
        "output": out[:400],
        "polite_endings_found": len(polite),
        "pass_has_polite": len(polite) >= 3,
        "pass_changed": not unchanged,
        "pass_structure_kept": "사진" in out and ("웃" in out or "웃었" in out),
    }]


def test_5_3_condensation():
    """압축 — 긴 가사를 짧게"""
    system = """다음 가사를 절반 길이로 압축하세요.
- 핵심 이미지와 감정을 유지
- 섹션 구조 유지 (Verse/Chorus 최소)
- 압축된 가사만 출력. 해설 금지."""

    out, tok = call_exaone(system, f"압축할 가사:\n{REF_LYRICS_HIPHOP}", max_tokens=600, temperature=0.5,
                           prefill="[Verse 1]\n")
    original_chars = count_chars_ko(REF_LYRICS_HIPHOP)
    new_chars = count_chars_ko(out)
    ratio = new_chars / max(original_chars, 1)

    return [{
        "output": out[:500],
        "original_chars": original_chars,
        "new_chars": new_chars,
        "ratio": f"{ratio:.0%}",
        "pass_shorter": ratio < 0.7,
        "pass_not_empty": new_chars > 50,
        "pass_has_sections": "[Verse" in out or "[Chorus" in out,
        "pass_key_images": "지하철" in out or "출근" in out or "알람" in out,
    }]


# =====================================================================
# Category 6: 일반 한국어 글쓰기
# =====================================================================

def test_6_1_ad_copy():
    """광고 카피 — 짧은 임팩트 있는 문구"""
    system = """당신은 한국 광고 카피라이터입니다.
다음 형식으로 출력하세요:
헤드라인: (10~20자, 임팩트 있는 한 줄)
서브카피: (30~50자, 감정을 건드리는 한 줄)
CTA: (10~15자, 행동 유도)

위 3줄만 출력. 해설/분석 금지."""

    out, tok = call_exaone(system, "제품: 늦은 밤 배달 가능한 수제 도시락\n타겟: 야근하는 20-30대 직장인", max_tokens=200, temperature=0.7)
    has_headline = "헤드라인" in out or "headline" in out.lower()
    has_sub = "서브" in out or "서브카피" in out
    has_cta = "CTA" in out or "cta" in out.lower()
    lines = [l.strip() for l in out.strip().split('\n') if l.strip()]

    return [{
        "output": out[:400],
        "line_count": len(lines),
        "pass_has_headline": has_headline,
        "pass_has_sub": has_sub,
        "pass_has_cta": has_cta,
        "pass_concise": len(lines) <= 6,
        "pass_korean": has_english(out) <= 1,
    }]


def test_6_2_essay_paragraph():
    """에세이 단락 — 서정적 산문"""
    system = """다음 테마로 에세이 한 단락(150~250자)을 쓰세요.
- 구체적인 감각 묘사 포함
- 1인칭 시점
- 산문만 출력. 제목, 해설, 분석 금지."""

    out, tok = call_exaone(system, "테마: 비 오는 날 창밖을 바라보며 마시는 차 한 잔", max_tokens=400, temperature=0.7)
    clean = re.sub(r'\s+', '', out.strip())
    char_count = len(clean)
    has_title = out.strip().startswith('#') or out.strip().startswith('제목') or out.strip().startswith('**')

    return [{
        "output": out[:500],
        "char_count": char_count,
        "pass_length": 100 <= char_count <= 350,
        "pass_no_title": not has_title,
        "pass_first_person": "나" in out or "내" in out,
        "pass_sensory": any(w in out for w in ["냄새", "소리", "향", "따뜻", "차가운", "빗소리", "김", "촉감"]),
        "pass_korean": has_english(out) <= 1,
    }]


# =====================================================================
# 메인 실행
# =====================================================================

ALL_TESTS = {
    "1. 제약 출력 형식": {
        "1.1 한 줄 테마": test_1_1_single_line_theme,
        "1.2 JSON 출력": test_1_2_json_output,
        "1.3 번호 리스트": test_1_3_numbered_list,
        "1.4 글자수 제어": test_1_4_char_count_control,
    },
    "2. 한국어 가사 생성": {
        "2.1 제로샷": test_2_1_lyrics_zero_shot,
        "2.2 프리필": test_2_2_lyrics_with_prefill,
        "2.3 퓨샷": test_2_3_lyrics_few_shot,
        "2.4 체인오브소트": test_2_4_lyrics_chain_of_thought,
    },
    "3. 한국어 언어 품질": {
        "3.1 종결어미 준수": test_3_1_ending_compliance,
        "3.2 어체 일관성": test_3_2_register_consistency,
        "3.3 이미지 참신성": test_3_3_imagery_freshness,
        "3.4 라임/언어유희": test_3_4_wordplay,
    },
    "4. 분석·비평": {
        "4.1 구조화 점수": test_4_1_structured_scoring,
        "4.2 줄별 비평": test_4_2_line_critique,
        "4.3 번역 품질": test_4_3_translation_quality,
    },
    "5. 수정·편집": {
        "5.1 타겟 교체": test_5_1_targeted_replacement,
        "5.2 어체 변환": test_5_2_register_conversion,
        "5.3 압축": test_5_3_condensation,
    },
    "6. 일반 한국어": {
        "6.1 광고 카피": test_6_1_ad_copy,
        "6.2 에세이": test_6_2_essay_paragraph,
    },
}


def run_all():
    all_results = {}
    summary = {}
    total_pass = 0
    total_criteria = 0
    test_num = 0
    total_tests = sum(len(tests) for tests in ALL_TESTS.values())

    for cat_name, tests in ALL_TESTS.items():
        cat_results = {}
        cat_pass = 0
        cat_total = 0
        print(f"\n{'='*70}")
        print(f"  {cat_name}")
        print(f"{'='*70}")

        for test_name, test_fn in tests.items():
            test_num += 1
            print(f"\n  [{test_num}/{total_tests}] {test_name}...")
            start = time.time()
            try:
                results = test_fn()
            except Exception as e:
                results = [{"error": str(e)}]
            elapsed = time.time() - start

            # pass 카운트
            for r in results:
                pass_keys = [k for k in r if k.startswith("pass_")]
                for pk in pass_keys:
                    cat_total += 1
                    total_criteria += 1
                    if r.get(pk):
                        cat_pass += 1
                        total_pass += 1

                # 출력 미리보기
                preview = r.get("output", r.get("first_line", ""))[:100]
                pass_status = [f"{'✓' if r.get(k) else '✗'} {k[5:]}" for k in r if k.startswith("pass_")]
                print(f"    {' | '.join(pass_status)}")
                if preview:
                    print(f"    미리보기: {preview[:80]}...")

            cat_results[test_name] = {"results": results, "elapsed": f"{elapsed:.1f}s"}
            print(f"    ({elapsed:.1f}초)")

        all_results[cat_name] = cat_results
        summary[cat_name] = f"{cat_pass}/{cat_total}"
        print(f"\n  ▸ {cat_name} 합계: {cat_pass}/{cat_total}")

    # 최종 요약
    print(f"\n{'='*70}")
    print(f"  EXAONE 4.0 32B 종합 능력 테스트 결과")
    print(f"{'='*70}")
    for cat, score in summary.items():
        p, t = map(int, score.split('/'))
        pct = p/t*100 if t else 0
        bar = '█' * int(pct/5) + '░' * (20 - int(pct/5))
        print(f"  {cat:20s}  {bar} {score} ({pct:.0f}%)")
    print(f"\n  총합: {total_pass}/{total_criteria} ({total_pass/max(total_criteria,1)*100:.0f}%)")
    print(f"{'='*70}")

    all_results["_summary"] = summary
    all_results["_total"] = f"{total_pass}/{total_criteria}"
    return all_results


if __name__ == "__main__":
    print("EXAONE 4.0 32B 종합 능력 테스트 — 6카테고리 20테스트")
    print(f"엔드포인트: {EXAONE_URL}\n")

    # 연결 테스트
    print("연결 테스트...")
    try:
        test_out, test_tok = call_exaone("테스트", "안녕하세요", max_tokens=10)
        print(f"  연결 성공 ({test_tok} tokens)\n")
    except Exception as e:
        print(f"  연결 실패: {e}")
        sys.exit(1)

    start = time.time()
    results = run_all()
    elapsed = time.time() - start

    output_path = "/Users/leo/oven/exaone_capability_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n소요 시간: {elapsed:.0f}초")
    print(f"결과 저장: {output_path}")
