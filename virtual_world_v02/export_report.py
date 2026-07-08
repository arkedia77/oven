#!/usr/bin/env python3
"""재현성 ④ 논문포맷 export — 다회통계 리포트를 학술 표/CSV + 재현패키지로.

입력: repro_runs/multiseed_report.json (orchestrate_multiseed 산출)
출력: repro_runs/export/
  - summary.md   : 메트릭별 mean±std/95%CI 표 + 시드별 raw 표 (논문/리포트용)
  - summary.csv  : 메트릭 요약 (기계판독)
  - per_seed.csv : 시드별 raw (기계판독)
  - REPRODUCE.md : 재현 패키지 매니페스트 (seed/LLM로그/재현명령)

재현성 트랙의 마지막 단계. seed+LLM로그 재생으로 서버 비결정성(⑤) 무관하게 재현 가능.
"""
import csv
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
REPRO_ROOT = BASE / "repro_runs"


def export_ab(report_path):
    """A/B 개입 실험 리포트(run_ab.py 산출) → md/csv + REPRODUCE (A-7).
    effect 표에 각 메트릭 95%CI가 0을 제외하는지(sig ★) 표기 — 검정 아닌 CI 기반."""
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    out = report_path.parent / "export"
    out.mkdir(parents=True, exist_ok=True)

    name = report["name"]
    seeds = report["seeds"]
    ticks = report["ticks"]
    mode = report.get("mode", "?")
    summary = report["summary"]
    per_seed = report["per_seed"]
    keys = list(summary["effect"].keys())
    spec = report.get("spec", {})

    def ps(seed):
        return per_seed.get(str(seed)) or per_seed.get(seed)

    def sig(e):
        return "★" if e["n"] > 1 and abs(e["mean"]) > e["ci95"] else ""

    # 1) markdown
    md = [
        f"# 하모니시티 A/B 개입 실험 리포트 — {name}",
        "",
        f"- 시드: {seeds} (N={len(seeds)})",
        f"- 틱/런: {ticks}",
        f"- LLM 모드: {mode}",
        f"- spec: `{spec.get('path','?')}` (sha256 `{spec.get('sha256','?')[:16]}`)",
        "",
        "## 개입 효과 (treat − ctrl, paired)",
        "",
        "| 메트릭 | ctrl mean | treat mean | effect | 95% CI | sig |",
        "|---|---|---|---|---|---|",
    ]
    for k in keys:
        c, t, e = summary["ctrl"][k], summary["treat"][k], summary["effect"][k]
        md.append(f"| {k} | {c['mean']} | {t['mean']} | {e['mean']:+} | ±{e['ci95']} | {sig(e)} |")
    md += ["", "> sig ★ = 95%CI가 0을 제외(효과의 CI 하한 > 0). 통계 검정이 아닌 CI 기반 표기 — 과대해석 주의.",
           "", "## 시드별 diff (treat − ctrl)", "",
           "| seed | " + " | ".join(keys) + " |",
           "|---|" + "|".join("---" for _ in keys) + "|"]
    for s in seeds:
        row = ps(s)["diff"]
        md.append(f"| {s} | " + " | ".join(f"{row[k]:+}" for k in keys) + " |")
    (out / "ab_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # 2) ab_summary.csv (효과 요약)
    with open(out / "ab_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "ctrl_mean", "treat_mean", "effect_mean", "effect_std", "effect_ci95", "sig"])
        for k in keys:
            c, t, e = summary["ctrl"][k], summary["treat"][k], summary["effect"][k]
            w.writerow([k, c["mean"], t["mean"], e["mean"], e["std"], e["ci95"], sig(e)])

    # 3) per_seed diff csv
    with open(out / "ab_per_seed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seed"] + [f"{k}_diff" for k in keys])
        for s in seeds:
            row = ps(s)["diff"]
            w.writerow([s] + [row[k] for k in keys])

    # 4) 재현 패키지
    repro = [
        f"# 재현 패키지 (A/B: {name})",
        "",
        "paired 개입 실험. 같은 seed의 ctrl/treat은 첫 개입 틱까지 동일 궤적이며,",
        "개입 spec은 순수 상태변경이라 mock 모드에서 완전 결정적으로 재현된다.",
        f"real LLM 모드는 record 로그(`s{{seed}}_{{cond}}_llm.jsonl`, record={report.get('record')})로 재생 재현.",
        "",
        "## 개입 spec (전문)",
        "```json",
        json.dumps(spec.get("content", {}), ensure_ascii=False, indent=2),
        "```",
        f"- sha256: `{spec.get('sha256','?')}`",
        "",
        "## 재현 명령",
        "```bash",
        f"python run_ab.py --spec {spec.get('path','<spec>')} --seeds {len(seeds)} --ticks {ticks}"
        + (" --mock" if mode == "mock" else ""),
        "```",
    ]
    (out / "REPRODUCE.md").write_text("\n".join(repro) + "\n", encoding="utf-8")

    print(f"A-7 A/B export 완료: {out}")
    for f in sorted(out.glob("*")):
        print(f"  - {f.name}")
    return out


def export(report_path=None):
    report_path = Path(report_path) if report_path else REPRO_ROOT / "multiseed_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    out = REPRO_ROOT / "export"
    out.mkdir(parents=True, exist_ok=True)

    seeds = report["seeds"]
    ticks = report["ticks"]
    mode = report.get("mode", "?")
    summary = report["summary"]
    per_seed = report["per_seed"]  # json이라 키가 str
    keys = list(summary.keys())

    def ps(seed):
        return per_seed.get(str(seed)) or per_seed.get(seed)

    # 1) markdown 리포트
    md = [
        "# 하모니시티 재현성 다회통계 리포트",
        "",
        f"- 시드: {seeds} (N={len(seeds)})",
        f"- 틱/런: {ticks}",
        f"- LLM 모드: {mode}",
        "",
        "## 메트릭 요약 (mean ± std, 95% CI)",
        "",
        "| 메트릭 | mean | std | 95% CI | N |",
        "|---|---|---|---|---|",
    ]
    for k in keys:
        s = summary[k]
        md.append(f"| {k} | {s['mean']} | {s['std']} | ±{s['ci95']} | {s['n']} |")
    md += ["", "## 시드별 raw", "", "| seed | " + " | ".join(keys) + " |",
           "|---|" + "|".join("---" for _ in keys) + "|"]
    for seed in seeds:
        row = ps(seed)
        md.append(f"| {seed} | " + " | ".join(str(row[k]) for k in keys) + " |")
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # 2) summary.csv
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "mean", "std", "ci95", "n"])
        for k in keys:
            s = summary[k]
            w.writerow([k, s["mean"], s["std"], s["ci95"], s["n"]])

    # 3) per_seed.csv
    with open(out / "per_seed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seed"] + keys)
        for seed in seeds:
            row = ps(seed)
            w.writerow([seed] + [row[k] for k in keys])

    # 4) 재현 패키지 매니페스트
    repro = [
        "# 재현 패키지 (REPRODUCE)",
        "",
        "결과를 비트단위로 재현하기 위한 일체. random=seed 고정 + LLM=기록 재생으로",
        "llama.cpp 배치 비결정성(⑤)과 무관하게 동일 산출물을 보장한다.",
        "",
        "## 구성",
        "- seed별 LLM 호출 로그: `multiseed_s{seed}_llm.jsonl` (record 출력)",
        "- seed별 산출물: `multiseed_s{seed}/` (relationships/world_state/characters)",
        "",
        "## 재현 명령 (각 시드)",
        "```bash",
    ]
    for seed in seeds:
        repro.append(
            f"HARMONICITY_DATA_DIR=<out_dir> REPRO_REPLAY=repro_runs/multiseed_s{seed}_llm.jsonl "
            f"python run_reproducible.py --run {seed} {ticks}"
        )
    repro += ["```", "",
              "재생 산출물의 해시가 원본 `multiseed_s{seed}/`와 일치하면 재현 성공."]
    (out / "REPRODUCE.md").write_text("\n".join(repro) + "\n", encoding="utf-8")

    print(f"④ export 완료: {out}")
    for f in sorted(out.glob("*")):
        print(f"  - {f.name}")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--ab" in args:
        export_ab(args[args.index("--ab") + 1])
    else:
        export(args[0] if args else None)
