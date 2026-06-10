"""
가상 월드 시뮬레이션 — Gemma 4 기반 4인 에이전트
매 10분마다 페어가 대화하고, 각자 기억 파일에 반영/학습
"""

import json
import time
import os
import random
import itertools
from datetime import datetime
from pathlib import Path
import requests

BASE_DIR = Path(__file__).parent
MEMORIES_DIR = BASE_DIR / "memories"
CONV_DIR = BASE_DIR / "conversations"
API_URL = "http://100.107.229.5:8080/v1/chat/completions"

AGENTS = {
    "민수": {
        "persona": "30대 소프트웨어 개발자. 논리적이고 호기심이 많다. 새로운 기술을 좋아하고, 비유를 들어 설명하는 걸 즐긴다. 가끔 개발자 유머를 던진다.",
        "interests": ["프로그래밍", "AI", "게임", "커피"],
    },
    "지영": {
        "persona": "20대 후반 싱어송라이터. 감성적이고 관찰력이 좋다. 일상에서 영감을 받아 노래를 만든다. 따뜻하고 공감을 잘 해준다.",
        "interests": ["음악", "시", "카페", "산책", "감정"],
    },
    "현우": {
        "persona": "40대 철학 강사. 깊이 생각하길 좋아하고, 질문으로 대화를 이끈다. 유머가 건조하고, 삶의 의미에 대해 자주 이야기한다.",
        "interests": ["철학", "독서", "와인", "영화", "존재론"],
    },
    "소라": {
        "persona": "30대 중반 셰프. 밝고 에너지가 넘친다. 요리를 통해 사람을 이해하려 한다. 음식 비유를 자주 쓰고, 새로운 도전을 즐긴다.",
        "interests": ["요리", "여행", "시장", "사람", "맛"],
    },
}

INTERVAL_SECONDS = 600  # 10분
TOTAL_DURATION = 4 * 3600  # 4시간
EXCHANGES_PER_CONV = 5  # 한 대화당 주고받는 횟수


def get_memory(name: str) -> str:
    path = MEMORIES_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def save_memory(name: str, content: str):
    path = MEMORIES_DIR / f"{name}.md"
    path.write_text(content, encoding="utf-8")


def append_memory(name: str, new_entry: str):
    current = get_memory(name)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    updated = current + f"\n\n## [{timestamp}]\n{new_entry}"
    save_memory(name, updated)


def chat(messages: list, max_tokens: int = 1024) -> str:
    try:
        resp = requests.post(
            API_URL,
            json={
                "model": "google_gemma-4-26B-A4B-it-Q8_0.gguf",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.8,
                "chat_template_kwargs": {"thinking": False},
            },
            timeout=120,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        content = msg.get("content", "").strip()
        if not content:
            content = "(응답 없음)"
        return content
    except Exception as e:
        return f"[오류: {e}]"


def build_system_prompt(name: str) -> str:
    agent = AGENTS[name]
    memory = get_memory(name)
    memory_section = f"\n\n## 내 기억:\n{memory}" if memory else "\n\n(아직 기억이 없음)"

    return (
        f"너는 '{name}'이라는 사람이야. 가상 마을에서 친구들과 함께 살고 있어.\n"
        f"성격: {agent['persona']}\n"
        f"관심사: {', '.join(agent['interests'])}\n"
        f"\n규칙:\n"
        f"- thinking 없이 바로 한국어로 답해. 2-4문장.\n"
        f"- 상대방의 이전 말을 참고해서 대화를 이어가.\n"
        f"- 기억에 있는 내용을 자연스럽게 활용해.\n"
        f"- 새로운 것을 배우거나 느끼면 표현해.\n"
        f"{memory_section}"
    )


def run_conversation(name_a: str, name_b: str, round_num: int) -> dict:
    """두 에이전트 간 대화 수행"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n{'='*60}")
    print(f"[라운드 {round_num}] {name_a} ↔ {name_b} ({datetime.now().strftime('%H:%M')})")
    print(f"{'='*60}")

    history_a = [{"role": "system", "content": build_system_prompt(name_a)}]
    history_b = [{"role": "system", "content": build_system_prompt(name_b)}]

    # 첫 인사 생성
    opener_prompt = (
        f"{name_b}을(를) 우연히 마주쳤어. "
        f"반갑게 인사하며 대화를 시작해. 최근 관심사나 기억을 자연스럽게 꺼내봐."
    )
    history_a.append({"role": "user", "content": opener_prompt})
    greeting = chat(history_a)
    history_a.append({"role": "assistant", "content": greeting})
    print(f"\n{name_a}: {greeting}")

    exchanges = [{"speaker": name_a, "text": greeting}]

    # 대화 주고받기
    for i in range(EXCHANGES_PER_CONV - 1):
        # B 응답
        history_b.append({"role": "user", "content": f"[{name_a}이(가) 말함]: {greeting}"})
        response_b = chat(history_b)
        history_b.append({"role": "assistant", "content": response_b})
        print(f"\n{name_b}: {response_b}")
        exchanges.append({"speaker": name_b, "text": response_b})

        if i < EXCHANGES_PER_CONV - 2:
            # A 응답
            history_a.append({"role": "user", "content": f"[{name_b}이(가) 답함]: {response_b}"})
            greeting = chat(history_a)
            history_a.append({"role": "assistant", "content": greeting})
            print(f"\n{name_a}: {greeting}")
            exchanges.append({"speaker": name_a, "text": greeting})

    conv_record = {
        "round": round_num,
        "timestamp": timestamp,
        "participants": [name_a, name_b],
        "exchanges": exchanges,
    }

    # 대화 로그 저장
    conv_path = CONV_DIR / f"round{round_num:03d}_{name_a}_{name_b}_{timestamp}.json"
    conv_path.write_text(json.dumps(conv_record, ensure_ascii=False, indent=2), encoding="utf-8")

    return conv_record


def reflect(name: str, conv_record: dict):
    """대화 후 각 에이전트가 자기 기억에 반영"""
    other = [p for p in conv_record["participants"] if p != name][0]
    conv_text = "\n".join(
        f"{ex['speaker']}: {ex['text']}" for ex in conv_record["exchanges"]
    )

    prompt = (
        f"방금 {other}와(과) 나눈 대화야:\n\n{conv_text}\n\n"
        f"thinking 없이 바로 한국어로 답해. "
        f"이 대화에서 기억할 것을 1-3줄로 정리해: "
        f"상대방에 대해 새로 알게 된 것, 느낀 감정, 다음에 이야기하고 싶은 주제."
    )

    messages = [
        {"role": "system", "content": build_system_prompt(name)},
        {"role": "user", "content": prompt},
    ]

    reflection = chat(messages, max_tokens=2048)
    append_memory(name, f"**{other}와의 대화 후 메모:**\n{reflection}")
    print(f"\n  💭 {name} 기억 업데이트: {reflection[:80]}...")


def generate_pairs():
    """6개 고유 페어를 순환 생성"""
    names = list(AGENTS.keys())
    all_pairs = list(itertools.combinations(names, 2))
    random.shuffle(all_pairs)
    while True:
        for pair in all_pairs:
            yield pair
        random.shuffle(all_pairs)


def init_memories():
    """초기 기억 파일 생성"""
    for name in AGENTS:
        path = MEMORIES_DIR / f"{name}.md"
        if not path.exists():
            agent = AGENTS[name]
            init_content = (
                f"# {name}의 기억\n\n"
                f"나는 {name}. {agent['persona']}\n"
                f"좋아하는 것: {', '.join(agent['interests'])}\n"
                f"오늘부터 이 마을에서 친구들과 함께 지내게 됐다.\n"
            )
            save_memory(name, init_content)
            print(f"✓ {name} 기억 파일 초기화")


def main():
    print("=" * 60)
    print("🏘️  가상 월드 시뮬레이션 시작")
    print(f"   에이전트: {', '.join(AGENTS.keys())}")
    print(f"   간격: {INTERVAL_SECONDS}초 (10분)")
    print(f"   총 시간: {TOTAL_DURATION // 3600}시간")
    print(f"   시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    init_memories()

    pairs = generate_pairs()
    start_time = time.time()
    round_num = 0

    while (time.time() - start_time) < TOTAL_DURATION:
        round_num += 1
        pair = next(pairs)
        name_a, name_b = pair

        # 대화 수행
        conv = run_conversation(name_a, name_b, round_num)

        # 양쪽 모두 반영
        reflect(name_a, conv)
        reflect(name_b, conv)

        elapsed = time.time() - start_time
        remaining = TOTAL_DURATION - elapsed
        print(f"\n⏱️  경과: {elapsed/60:.0f}분 / 남은: {remaining/60:.0f}분")
        print(f"   다음 대화까지 {INTERVAL_SECONDS}초 대기...")

        if remaining > INTERVAL_SECONDS:
            time.sleep(INTERVAL_SECONDS)
        else:
            break

    print("\n" + "=" * 60)
    print("🏁 시뮬레이션 종료!")
    print(f"   총 라운드: {round_num}")
    print(f"   총 시간: {(time.time() - start_time)/60:.0f}분")
    print("=" * 60)

    # 최종 요약
    for name in AGENTS:
        mem = get_memory(name)
        lines = len(mem.split("\n"))
        print(f"   {name}: 기억 {lines}줄")


if __name__ == "__main__":
    main()
