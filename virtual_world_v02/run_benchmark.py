#!/usr/bin/env python3
"""
하모니시티 도메인 비교 벤치마크 러너
Usage:
  python run_benchmark.py --domain corporate --ticks 48
  python run_benchmark.py --domain corporate --ticks 48 --mock
  python run_benchmark.py --compare
"""
import sys
import os
import json
import time
import shutil
import random
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).parent
VILLAGE_DIR = ROOT / "village"
DOMAINS_DIR = ROOT / "domains"
BENCHMARK_DIR = ROOT / "benchmark_data"

FILES_TO_SWAP = [
    ("characters/definitions.py", "definitions.py"),
    ("world/locations.py", "locations.py"),
    ("systems/events.py", "events.py"),
    ("systems/social_energy.py", "social_energy.py"),
    ("interaction/prompts.py", "prompts.py"),
]

MOCK_RESPONSES = {
    "conversation": [
        "네, 그 부분에 대해 저도 비슷한 생각을 하고 있었어요. 같이 한번 논의해봐요.",
        "솔직히 말하면 좀 걱정이 됩니다. 이대로 가면 문제가 생길 것 같아요.",
        "그건 좀 다르게 봐야 할 것 같은데요. 제 경험으로는 오히려 반대였거든요.",
        "맞아요, 공감합니다. 저도 최근에 비슷한 고민을 하고 있었어요.",
        "솔직히 실망스러웠어요. 기대했던 것과 너무 달랐거든요.",
        "그 제안 괜찮네요! 한번 시도해볼 만한 가치가 있을 것 같아요.",
        "아직 확신이 안 서요. 좀 더 생각해보고 싶은데, 시간을 좀 주실 수 있나요?",
        "저는 좀 다른 의견인데요. 충돌이 생길 수도 있지만, 이건 중요한 문제라서요.",
    ],
    "reflection": [
        "1. 목표에 약간 도움이 됐다.\n2. 신뢰가 조금 올랐다.\n3. 내일 한번 더 이야기해볼 것.\n4. 조금 안도감.\n5. 상대의 입장을 이해하게 됐다.",
        "1. 방해가 됐다. 갈등이 커졌다.\n2. 불신이 생겼다.\n3. 다른 동맹을 찾아볼 것.\n4. 실망과 분노.\n5. 입장 변화 없음.",
        "1. 진전이 있었다.\n2. 호감이 올랐다.\n3. 구체적 합의안을 정리할 것.\n4. 희망적이다.\n5. 타협의 여지를 인정할 수 있게 됐다.",
        "1. 별다른 변화 없음.\n2. 유지.\n3. 혼자 더 고민해볼 것.\n4. 복잡한 기분.\n5. 약간의 양보를 생각해보게 됐다.",
    ],
    "monologue": [
        "요즘 정말 힘들다. 내가 이 자리에 있는 이유가 뭘까. 내일은 좀 다르게 해봐야지.",
        "아까 그 대화가 계속 머릿속에 맴돈다. 내가 너무 감정적이었나. 다음엔 차분하게.",
        "혼자 있으니까 좀 편하다. 하지만 이대로 괜찮은 건지 모르겠다. 뭔가 변화가 필요해.",
    ],
}


def mock_chat(messages, max_tokens=1024, temperature=0.85):
    content = messages[-1]["content"] if messages else ""
    if "5가지를 각각" in content or "한 줄로" in content:
        return random.choice(MOCK_RESPONSES["reflection"])
    elif "독백" in content or "혼자 있는" in content:
        return random.choice(MOCK_RESPONSES["monologue"])
    else:
        return random.choice(MOCK_RESPONSES["conversation"])


def backup_originals():
    backup_dir = BENCHMARK_DIR / "_backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for village_path, _ in FILES_TO_SWAP:
        src = VILLAGE_DIR / village_path
        if src.exists():
            bak = backup_dir / village_path.replace("/", "_")
            shutil.copy2(src, bak)
    return backup_dir


def restore_originals(backup_dir):
    for village_path, _ in FILES_TO_SWAP:
        bak = backup_dir / village_path.replace("/", "_")
        dst = VILLAGE_DIR / village_path
        if bak.exists():
            shutil.copy2(bak, dst)


def swap_domain_files(domain_name):
    domain_dir = DOMAINS_DIR / domain_name
    for village_path, domain_file in FILES_TO_SWAP:
        src = domain_dir / domain_file
        dst = VILLAGE_DIR / village_path
        if src.exists():
            shutil.copy2(src, dst)
        else:
            print(f"  ⚠️ {domain_file} not found in {domain_name}, keeping original")


def clear_data_dir(data_dir):
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)


def run_domain(domain_name, num_ticks=48, use_mock=False):
    print(f"\n{'='*60}")
    print(f"  🏗️ 도메인: {domain_name.upper()}")
    print(f"  틱 수: {num_ticks} ({num_ticks // 24}일 + {num_ticks % 24}틱)")
    print(f"  LLM: {'Mock' if use_mock else 'Real (Gemma 4)'}")
    print(f"{'='*60}")

    data_dir = BENCHMARK_DIR / domain_name / "data"

    backup_dir = backup_originals()

    try:
        if domain_name != "original":
            swap_domain_files(domain_name)

        clear_data_dir(data_dir)

        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("village"):
                del sys.modules[mod_name]

        import village.config as vc
        vc.DATA_DIR = data_dir
        vc.TICK_SECONDS = 0

        if use_mock:
            import village.engine.llm as vllm
            vllm.chat = mock_chat

        from village.characters.definitions import CHARACTERS
        from village.characters.state import CharacterState
        from village.world.state import WorldState
        from village.main import run_tick, need_history, belief_history, relationship_history

        need_history.clear()
        belief_history.clear()
        relationship_history.clear()

        world = WorldState()
        characters = {}
        for char_id in CHARACTERS:
            characters[char_id] = CharacterState.from_definition(char_id)
        relationships = {}

        metrics = {
            "domain": domain_name,
            "num_ticks": num_ticks,
            "mock_llm": use_mock,
            "started_at": datetime.now().isoformat(),
            "characters": list(CHARACTERS.keys()),
            "character_count": len(CHARACTERS),
            "tick_metrics": [],
            "conversation_count": 0,
            "event_count": 0,
            "final_state": {},
        }

        start_time = time.time()
        conv_count = 0
        event_count = 0

        for tick_num in range(num_ticks):
            tick_start = time.time()
            world.advance_tick()

            conversations_before = _count_conversations(data_dir)
            run_tick(world, characters, relationships)
            conversations_after = _count_conversations(data_dir)

            new_convs = conversations_after - conversations_before
            conv_count += new_convs

            tick_elapsed = time.time() - tick_start

            tick_data = {
                "tick": tick_num + 1,
                "day": world.day,
                "hour": world.hour,
                "new_conversations": new_convs,
                "elapsed_seconds": round(tick_elapsed, 2),
            }
            metrics["tick_metrics"].append(tick_data)

        total_time = time.time() - start_time
        metrics["total_seconds"] = round(total_time, 2)
        metrics["conversation_count"] = conv_count
        metrics["avg_seconds_per_tick"] = round(total_time / num_ticks, 2)

        metrics["final_state"] = _collect_final_metrics(
            characters, relationships, dict(need_history), dict(belief_history)
        )

        result_path = BENCHMARK_DIR / domain_name / "metrics.json"
        result_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  ✅ 완료: {result_path}")
        print(f"  ⏱️ 총 시간: {total_time:.1f}초, 대화 {conv_count}건")

        return metrics

    finally:
        restore_originals(backup_dir)
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("village"):
                del sys.modules[mod_name]


def _count_conversations(data_dir):
    conv_dir = data_dir / "conversations"
    if not conv_dir.exists():
        return 0
    count = 0
    for day_dir in conv_dir.iterdir():
        if day_dir.is_dir():
            count += len(list(day_dir.glob("*.json")))
    return count


def _collect_final_metrics(characters, relationships, need_hist, belief_hist):
    char_metrics = {}
    for cid, char in characters.items():
        char_metrics[cid] = {
            "name": char.name,
            "needs": dict(char.needs),
            "beliefs": dict(char.beliefs),
            "energy": char.energy,
            "emotional_state": char.emotional_state,
            "goals": [
                {"desc": g["description"], "progress": g["progress"]}
                for g in char.goals
            ],
            "interaction_count": len(char.today_interactions),
            "working_memory_size": len(char.working_memory),
        }

    rel_metrics = {}
    for pair_key, rel in relationships.items():
        if isinstance(pair_key, tuple):
            key_str = f"{pair_key[0]}|{pair_key[1]}"
        else:
            key_str = pair_key
        rel_metrics[key_str] = {
            "warmth": round(rel.get("warmth", 0.5), 3),
            "trust": round(rel.get("trust", 0.5), 3),
            "tension": round(rel.get("tension", 0.3), 3),
            "affection": round(rel.get("affection", 0.0), 3),
            "interaction_count": rel.get("interaction_count", 0),
        }

    need_dynamics = {}
    for cid, needs in need_hist.items():
        need_dynamics[cid] = {}
        for need_key, values in needs.items():
            if values:
                need_dynamics[cid][need_key] = {
                    "start": round(values[0], 3),
                    "end": round(values[-1], 3),
                    "min": round(min(values), 3),
                    "max": round(max(values), 3),
                    "mean": round(sum(values) / len(values), 3),
                    "variance": round(_variance(values), 4),
                }

    rel_pairs = list(rel_metrics.values())
    warmths = [r["warmth"] for r in rel_pairs]
    trusts = [r["trust"] for r in rel_pairs]
    tensions = [r["tension"] for r in rel_pairs]

    return {
        "characters": char_metrics,
        "relationships": rel_metrics,
        "need_dynamics": need_dynamics,
        "aggregate": {
            "avg_warmth": round(sum(warmths) / len(warmths), 3) if warmths else 0,
            "avg_trust": round(sum(trusts) / len(trusts), 3) if trusts else 0,
            "avg_tension": round(sum(tensions) / len(tensions), 3) if tensions else 0,
            "warmth_variance": round(_variance(warmths), 4) if warmths else 0,
            "trust_variance": round(_variance(trusts), 4) if trusts else 0,
            "tension_variance": round(_variance(tensions), 4) if tensions else 0,
            "total_interactions": sum(r["interaction_count"] for r in rel_pairs),
            "active_relationships": sum(1 for r in rel_pairs if r["interaction_count"] > 0),
            "total_relationships": len(rel_pairs),
        },
    }


def _variance(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def compare_domains():
    print(f"\n{'='*60}")
    print("  📊 도메인 비교 분석")
    print(f"{'='*60}\n")

    domains = []
    for domain_dir in sorted(BENCHMARK_DIR.iterdir()):
        if domain_dir.is_dir() and domain_dir.name != "_backup":
            metrics_file = domain_dir / "metrics.json"
            if metrics_file.exists():
                data = json.loads(metrics_file.read_text(encoding="utf-8"))
                domains.append(data)

    if not domains:
        print("  ❌ 벤치마크 결과가 없습니다. 먼저 --domain으로 실행하세요.")
        return

    header = f"{'지표':<30}"
    for d in domains:
        header += f"  {d['domain']:>12}"
    print(header)
    print("-" * (30 + 14 * len(domains)))

    rows = [
        ("캐릭터 수", lambda d: d["character_count"]),
        ("총 대화 수", lambda d: d["conversation_count"]),
        ("총 실행 시간(초)", lambda d: d.get("total_seconds", 0)),
        ("틱당 평균 시간(초)", lambda d: d.get("avg_seconds_per_tick", 0)),
    ]

    for label, fn in rows:
        row = f"{label:<30}"
        for d in domains:
            val = fn(d)
            row += f"  {val:>12.1f}" if isinstance(val, float) else f"  {val:>12}"
        print(row)

    print()

    agg_rows = [
        ("평균 호감도 (warmth)", lambda d: d["final_state"]["aggregate"]["avg_warmth"]),
        ("평균 신뢰도 (trust)", lambda d: d["final_state"]["aggregate"]["avg_trust"]),
        ("평균 긴장도 (tension)", lambda d: d["final_state"]["aggregate"]["avg_tension"]),
        ("호감 분산", lambda d: d["final_state"]["aggregate"]["warmth_variance"]),
        ("신뢰 분산", lambda d: d["final_state"]["aggregate"]["trust_variance"]),
        ("긴장 분산", lambda d: d["final_state"]["aggregate"]["tension_variance"]),
        ("총 상호작용 수", lambda d: d["final_state"]["aggregate"]["total_interactions"]),
        ("활성 관계 / 전체", lambda d: f"{d['final_state']['aggregate']['active_relationships']}/{d['final_state']['aggregate']['total_relationships']}"),
    ]

    print(f"{'관계 역학':<30}" + "  " * len(domains))
    print("-" * (30 + 14 * len(domains)))
    for label, fn in agg_rows:
        row = f"{label:<30}"
        for d in domains:
            try:
                val = fn(d)
                if isinstance(val, float):
                    row += f"  {val:>12.4f}"
                else:
                    row += f"  {val:>12}"
            except (KeyError, TypeError):
                row += f"  {'N/A':>12}"
        print(row)

    print()
    print("=" * (30 + 14 * len(domains)))

    report = {
        "generated_at": datetime.now().isoformat(),
        "domains": {d["domain"]: d for d in domains},
    }
    report_path = BENCHMARK_DIR / "comparison_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  📄 상세 보고서: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="하모니시티 도메인 비교 벤치마크")
    parser.add_argument("--domain", choices=["corporate", "education", "consumer", "original"])
    parser.add_argument("--ticks", type=int, default=48, help="실행할 틱 수 (기본: 48 = 2일)")
    parser.add_argument("--mock", action="store_true", help="Mock LLM 사용 (로컬 테스트용)")
    parser.add_argument("--compare", action="store_true", help="기존 결과 비교 분석")
    parser.add_argument("--all", action="store_true", help="모든 도메인 순차 실행")
    args = parser.parse_args()

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    if args.compare:
        compare_domains()
    elif args.all:
        for domain in ["original", "corporate", "education", "consumer"]:
            run_domain(domain, args.ticks, args.mock)
        compare_domains()
    elif args.domain:
        run_domain(args.domain, args.ticks, args.mock)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
