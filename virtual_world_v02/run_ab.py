#!/usr/bin/env python3
"""A/B 개입 실험 오케스트레이터 (Phase A-6).

시드 짝지은(paired) 2조건 비교로 "개입 효과"를 추정한다:
  각 seed에 대해
    ctrl  = 개입 없음
    treat = HARMONICITY_INTERVENTION=<spec>로 개입 주입
  같은 seed의 ctrl/treat은 첫 개입 틱까지 동일 궤적(intervention.apply_one이 순수 상태변경)
  → paired design. diff = treat - ctrl. 시드 간 분산이 차이에서 상쇄되어 좁은 CI로 효과 검출.

재사용: run_reproducible._spawn / village.metrics.extract_metrics·stats
라이브 무침범: 별도 data dir(ab_runs/{name}/...), fast 검증런, 라이브 data/ 미접근.

사용:
  python run_ab.py --spec specs/tension_shock.json --seeds 5 --ticks 24 [--mock] [--no-record]
"""
import os
import sys
import json
import shutil
import hashlib
from pathlib import Path

BASE = Path(__file__).parent
AB_ROOT = BASE / "ab_runs"

sys.path.insert(0, str(BASE))
from run_reproducible import _spawn  # noqa: E402
from village.metrics import extract_metrics, stats, METRIC_KEYS  # noqa: E402
from village import intervention  # noqa: E402


def _load_and_validate_spec(spec_path: Path) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    errs = intervention.validate_spec(spec)
    if errs:
        print(f"❌ spec 검증 실패({spec_path}):")
        for e in errs:
            print("   -", e)
        sys.exit(1)
    return spec


def orchestrate_ab(spec_path, seeds: list, ticks: int,
                   mock: bool = False, record: bool = True) -> dict:
    spec_path = Path(spec_path)
    spec = _load_and_validate_spec(spec_path)
    name = spec.get("name") or spec_path.stem
    spec_text = spec_path.read_text(encoding="utf-8")
    spec_sha = hashlib.sha256(spec_text.encode("utf-8")).hexdigest()
    mode = "mock" if mock else "real LLM"

    run_dir = AB_ROOT / name
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== A/B 개입 실험: {name} ===")
    print(f"  spec={spec_path.name} ({spec_sha[:12]}), seeds={seeds}, ticks={ticks}, {mode}")

    per_seed = {}
    for s in seeds:
        print(f"\n--- seed {s} ---", flush=True)
        cond_metrics = {}
        for cond in ("ctrl", "treat"):
            d = run_dir / f"s{s}_{cond}"
            (d / "characters").mkdir(parents=True, exist_ok=True)
            extra = {}
            if mock:
                extra["REPRO_MOCK_LLM"] = "1"
            elif record:
                extra["REPRO_RECORD"] = str(run_dir / f"s{s}_{cond}_llm.jsonl")
            if cond == "treat":
                extra["HARMONICITY_INTERVENTION"] = str(spec_path)
            print(f"  [{cond}] 실행...", flush=True)
            rc = _spawn(s, ticks, d, extra)
            if rc != 0:
                print(f"  ❌ seed {s} {cond} 실패(rc={rc}) — 시드 제외")
                cond_metrics = None
                break
            cond_metrics[cond] = extract_metrics(d)
        if cond_metrics is None:
            continue
        diff = {k: round(cond_metrics["treat"][k] - cond_metrics["ctrl"][k], 4)
                for k in METRIC_KEYS}
        per_seed[s] = {"ctrl": cond_metrics["ctrl"], "treat": cond_metrics["treat"], "diff": diff}

    # 집계
    summary = {
        "ctrl": {k: stats([per_seed[s]["ctrl"][k] for s in per_seed]) for k in METRIC_KEYS},
        "treat": {k: stats([per_seed[s]["treat"][k] for s in per_seed]) for k in METRIC_KEYS},
        "effect": {k: stats([per_seed[s]["diff"][k] for s in per_seed]) for k in METRIC_KEYS},
    }
    report = {
        "name": name,
        "spec": {"path": str(spec_path), "sha256": spec_sha, "content": spec},
        "seeds": list(per_seed.keys()), "ticks": ticks, "mode": mode,
        "record": (record and not mock),
        "per_seed": per_seed, "summary": summary,
    }
    out = run_dir / "ab_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 콘솔 요약
    print(f"\n=== 효과 요약 (treat - ctrl, N={len(per_seed)}) ===")
    print(f"{'metric':<16}{'ctrl':>10}{'treat':>10}{'effect':>10}{'95%CI':>10}{'  sig':>6}")
    for k in METRIC_KEYS:
        c, t, e = summary["ctrl"][k], summary["treat"][k], summary["effect"][k]
        # ★ = |effect| CI 하한이 0 초과(= 95%CI가 0을 제외). ci95=0(mock 무분산)도 mean≠0이면 확정.
        sig = "★" if e["n"] > 1 and abs(e["mean"]) > e["ci95"] else ""
        print(f"{k:<16}{c['mean']:>10}{t['mean']:>10}{e['mean']:>+10}{e['ci95']:>10}{sig:>6}")
    print(f"\n리포트: {out}")
    print("  (sig ★ = 95%CI가 0을 제외 — 검정 아닌 CI 기반 표기, 과대해석 주의)")
    return report


def main_cli():
    args = sys.argv[1:]
    if "--spec" not in args:
        print("사용: python run_ab.py --spec <spec.json> [--seeds N] [--ticks K] [--mock] [--no-record]")
        sys.exit(2)
    spec_path = args[args.index("--spec") + 1]
    nseed = int(args[args.index("--seeds") + 1]) if "--seeds" in args else 5
    ticks = int(args[args.index("--ticks") + 1]) if "--ticks" in args else 24
    seeds = list(range(1, nseed + 1))
    orchestrate_ab(spec_path, seeds, ticks,
                   mock="--mock" in args, record="--no-record" not in args)


if __name__ == "__main__":
    main_cli()
