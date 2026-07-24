#!/usr/bin/env python3
"""D-M1 계측기 슬롯 — 창발·폴백·판단분산·기억영속 리포트 진입점.

읽기전용. 시뮬 프로세스에 로드되지 않으며 어떤 옵트인 가드도 필요 없다(설계상 무영향).

사용:
  python run_instrumentation.py [DATA_DIR] [--json|--md]
  DATA_DIR 생략 시 ./data (로컬 canonical 기본 경로).
"""
import json
import sys
from pathlib import Path

from village import instrumentation

BASE = Path(__file__).parent


def _md(report: dict) -> str:
    lines = [f"# 하모니시티 D-M1 계측 리포트 — `{report['data_dir']}`", ""]

    fb = report["fallback"]
    lines += ["## 폴백율", "", f"- 전체 N={fb['n']}"]
    ov = fb.get("overall", {})
    if ov:
        lines.append(f"- 전체 fallback_rate={ov.get('fallback_rate')} ({ov.get('fallback')}/{ov.get('n')})")
    lines.append("")
    lines.append("| decider_id | n | fallback_rate |")
    lines.append("|---|---|---|")
    for k, v in fb.get("by_decider", {}).items():
        lines.append(f"| {k} | {v['n']} | {v['fallback_rate']} |")
    lines.append("")

    jd = report["judgment_dispersion"]
    lines += ["## 판단분산 (entropy, bits)", "", f"- 전체 N(parsed)={jd['n']}", ""]
    lines.append("| group | n | n_distinct_choices | entropy_bits |")
    lines.append("|---|---|---|---|")
    for k, v in jd.get("groups", {}).items():
        lines.append(f"| {k} | {v['n']} | {v['n_distinct_choices']} | {v['entropy_bits']} |")
    lines.append("")

    em = report["emergence"]
    role = em["role_emergence"]
    lines += ["## 창발", "", f"- 역할 배정 캐릭터 수: {role['n_characters']}",
              f"- 역할 분포: {role['distribution']}",
              f"- 역할 entropy(bits): {role['role_entropy_bits']}"]
    conc = em["interaction_concentration"]
    lines += [f"- 관계 집중도 Gini: {conc['gini']} (캐릭터 {conc['n_characters']}명)", ""]

    mp = report["memory_persistence"]
    lines += ["## 기억영속", "", f"- 캐릭터 수: {mp['n_characters']}", "",
              "| char | 관계요약 커버리지 | key_events | belief_shifts | episodes | cap도달 |",
              "|---|---|---|---|---|---|"]
    for cid, v in mp.get("characters", {}).items():
        lines.append(
            f"| {cid} | {v['relationship_summary_coverage']} | {v['n_key_events']} | "
            f"{v['n_belief_shifts']} | {v['n_episodes']} | {v['episodes_at_cap']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    data_dir = Path(args[0]) if args else BASE / "data"

    report = instrumentation.full_report(data_dir)

    if "--json" in flags:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_md(report))


if __name__ == "__main__":
    main()
