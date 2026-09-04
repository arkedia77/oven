#!/usr/bin/env python3
"""하모니시티 추가 실험 진입점 — T1(항상성 감도)/T5(섭동 탄성) 자동화.

라이브 시뮬 무침범. 별도 data dir + fast 모드.

사용:
  python run_experiments.py --homeostasis-sweep --ticks 24 --mock
  python run_experiments.py --perturbation --ticks 48 --mock
  python run_experiments.py --homeostasis-sweep --ticks 24   # real LLM
"""
import sys
import os
import json
import copy
import shutil
import statistics
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
EXPERIMENT_ROOT = BASE / "experiment_runs"

COMPARE_KEYS = ["warmth", "trust", "tension", "affection"]


def _extract_metrics(data_dir: Path) -> dict:
    rel_path = data_dir / "relationships.json"
    if not rel_path.exists():
        return {}
    rel = json.loads(rel_path.read_text(encoding="utf-8"))
    pairs = list(rel.values()) if isinstance(rel, dict) else rel
    if not pairs:
        return {}
    n = len(pairs)
    metrics = {}
    for key in COMPARE_KEYS:
        vals = [p.get(key, 0.0) for p in pairs]
        metrics[f"avg_{key}"] = sum(vals) / n
        metrics[f"max_{key}"] = max(vals)
        metrics[f"min_{key}"] = min(vals)
        if key in ("warmth", "trust"):
            metrics[f"above_07_{key}"] = sum(1 for v in vals if v > 0.7)
            metrics[f"zero_{key}"] = sum(1 for v in vals if v < 0.01)
    active = sum(1 for p in pairs if p.get("interaction_count", 0) > 0)
    metrics["active_rels"] = active
    metrics["n_pairs"] = n
    return metrics


def _spawn_with_config(seed, ticks, data_dir, config_overrides=None, mock=False,
                       timeout_minutes=60):
    env = dict(os.environ)
    env["HARMONICITY_DATA_DIR"] = str(data_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    if mock:
        env["REPRO_MOCK_LLM"] = "1"
    if config_overrides:
        env["HARMONICITY_CONFIG_OVERRIDES"] = json.dumps(config_overrides)
    try:
        proc = subprocess.run(
            [sys.executable, str(BASE / "run_reproducible.py"), "--run", str(seed), str(ticks)],
            env=env, cwd=str(BASE),
            timeout=timeout_minutes * 60,
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {timeout_minutes}min exceeded")
        return -1


# ── T1: Homeostasis Sensitivity Sweep ──

HOMEOSTASIS_GRID = [
    {"label": "baseline",    "warmth_decay": 0.008, "trust_decay": 0.006, "soft_ceil": 0.85},
    {"label": "half_decay",  "warmth_decay": 0.004, "trust_decay": 0.003, "soft_ceil": 0.85},
    {"label": "quarter_decay", "warmth_decay": 0.002, "trust_decay": 0.0015, "soft_ceil": 0.85},
    {"label": "high_ceil",   "warmth_decay": 0.008, "trust_decay": 0.006, "soft_ceil": 0.92},
    {"label": "half_high",   "warmth_decay": 0.004, "trust_decay": 0.003, "soft_ceil": 0.92},
    {"label": "minimal",     "warmth_decay": 0.002, "trust_decay": 0.0015, "soft_ceil": 0.92},
]


def run_homeostasis_sweep(ticks: int, seed: int = 42, mock: bool = False):
    print(f"=== T1: 항상성 감도 스윕 (ticks={ticks}, seed={seed}, {'mock' if mock else 'real'}) ===\n")
    results = []
    for cfg in HOMEOSTASIS_GRID:
        label = cfg["label"]
        data_dir = EXPERIMENT_ROOT / f"T1_{label}_s{seed}"
        if data_dir.exists():
            shutil.rmtree(data_dir)
        (data_dir / "characters").mkdir(parents=True, exist_ok=True)

        overrides = {
            "WARMTH_DECAY_RATE": cfg["warmth_decay"],
            "TRUST_DECAY_RATE": cfg["trust_decay"],
            "WARMTH_SOFT_CEILING": cfg["soft_ceil"],
            "TRUST_SOFT_CEILING": cfg["soft_ceil"],
        }
        print(f"--- {label}: decay w={cfg['warmth_decay']} t={cfg['trust_decay']} ceil={cfg['soft_ceil']} ---")
        rc = _spawn_with_config(seed, ticks, data_dir, overrides, mock)
        if rc != 0:
            print(f"  [FAIL] 실패 (rc={rc})")
            results.append({"label": label, "status": "FAIL", **cfg})
            continue
        m = _extract_metrics(data_dir)
        m.update(cfg)
        m["status"] = "OK"
        results.append(m)
        print(f"  avg_w={m.get('avg_warmth',0):.4f} max_w={m.get('max_warmth',0):.4f} "
              f"above_07={m.get('above_07_warmth',0)} zero={m.get('zero_warmth',0)} "
              f"avg_ten={m.get('avg_tension',0):.4f}")

    report_path = EXPERIMENT_ROOT / "T1_homeostasis_report.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n리포트: {report_path}")
    _print_t1_table(results)
    return results


def _print_t1_table(results):
    print("\n| label | w_decay | t_decay | ceil | avg_w | max_w | >0.7 | =0 | avg_ten |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        if r.get("status") != "OK":
            print(f"| {r['label']} | FAIL |")
            continue
        print(f"| {r['label']} | {r['warmth_decay']} | {r['trust_decay']} | "
              f"{r['soft_ceil']} | {r.get('avg_warmth',0):.4f} | {r.get('max_warmth',0):.4f} | "
              f"{r.get('above_07_warmth',0)} | {r.get('zero_warmth',0)} | "
              f"{r.get('avg_tension',0):.4f} |")


# ── T6: Reputation Erosion Sensitivity Sweep ──

REP_EROSION_GRID = [
    {"label": "rep_baseline", "rep_mult": 1.0, "rep_floor": 0.0},
    {"label": "rep_half", "rep_mult": 0.5, "rep_floor": 0.0},
    {"label": "rep_quarter", "rep_mult": 0.25, "rep_floor": 0.0},
    {"label": "rep_floor_02", "rep_mult": 1.0, "rep_floor": 0.2},
    {"label": "rep_half_floor", "rep_mult": 0.5, "rep_floor": 0.15},
    {"label": "rep_off", "rep_mult": 0.0, "rep_floor": 0.0},
]


def run_rep_erosion_sweep(ticks: int, seed: int = 42, mock: bool = False):
    print(f"=== T6: 평판 침식 감도 스윕 (ticks={ticks}, seed={seed}, {'mock' if mock else 'real'}) ===\n")
    results = []
    for cfg in REP_EROSION_GRID:
        label = cfg["label"]
        data_dir = EXPERIMENT_ROOT / f"T6_{label}_s{seed}"
        if data_dir.exists():
            shutil.rmtree(data_dir)
        (data_dir / "characters").mkdir(parents=True, exist_ok=True)

        overrides = {
            "REP_EROSION_MULT": cfg["rep_mult"],
            "REP_WARMTH_FLOOR": cfg["rep_floor"],
        }
        print(f"--- {label}: mult={cfg['rep_mult']} floor={cfg['rep_floor']} ---")
        rc = _spawn_with_config(seed, ticks, data_dir, overrides, mock)
        if rc != 0:
            print(f"  [FAIL] 실패 (rc={rc})")
            results.append({"label": label, "status": "FAIL", **cfg})
            continue
        m = _extract_metrics(data_dir)
        m.update(cfg)
        m["status"] = "OK"
        results.append(m)
        print(f"  avg_w={m.get('avg_warmth',0):.4f} zero_w={m.get('zero_warmth',0)} "
              f"avg_ten={m.get('avg_tension',0):.4f}")

    report_path = EXPERIMENT_ROOT / "T6_rep_erosion_report.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n리포트: {report_path}")
    _print_t6_table(results)
    return results


def _print_t6_table(results):
    print("\n| label | mult | floor | avg_w | max_w | >0.7 | =0 | avg_ten |")
    print("|---|---|---|---|---|---|---|---|")
    for r in results:
        if r.get("status") != "OK":
            print(f"| {r['label']} | FAIL |")
            continue
        print(f"| {r['label']} | {r['rep_mult']} | {r['rep_floor']} | "
              f"{r.get('avg_warmth',0):.4f} | {r.get('max_warmth',0):.4f} | "
              f"{r.get('above_07_warmth',0)} | {r.get('zero_warmth',0)} | "
              f"{r.get('avg_tension',0):.4f} |")


# ── T5: Perturbation Resilience Test ──

def _apply_perturbation(data_dir: Path, perturbation: str):
    rel_path = data_dir / "relationships.json"
    rels = json.loads(rel_path.read_text(encoding="utf-8"))

    if perturbation == "tension_all_05":
        for r in rels.values():
            r["tension"] = 0.5
    elif perturbation == "warmth_top10_zero":
        ranked = sorted(rels.items(), key=lambda x: x[1].get("warmth", 0), reverse=True)
        for k, _ in ranked[:10]:
            rels[k]["warmth"] = 0.0
            rels[k]["trust"] = 0.0
    elif perturbation == "tension_05_warmth_zero":
        for r in rels.values():
            r["tension"] = 0.5
            r["warmth"] = 0.0
            r["trust"] = 0.0

    rel_path.write_text(json.dumps(rels, indent=2, ensure_ascii=False), encoding="utf-8")
    return _extract_metrics(data_dir)


def _copy_live_data(src_dir: Path, dst_dir: Path):
    import glob
    for f in ["world_state.json", "relationships.json", "reputation.json",
              "need_history.json", "knowledge_base.json", "atmosphere.json",
              "relationship_history.json", "belief_history.json"]:
        src = src_dir / f
        if src.exists():
            shutil.copy2(src, dst_dir / f)
    src_chars = src_dir / "characters"
    dst_chars = dst_dir / "characters"
    dst_chars.mkdir(exist_ok=True)
    if src_chars.exists():
        for cf in src_chars.glob("*.json"):
            shutil.copy2(cf, dst_chars / cf.name)


def run_perturbation(ticks: int, seed: int = 42, mock: bool = False,
                     source_data: str = None):
    src = Path(source_data) if source_data else BASE / "data"
    print(f"=== T5: 섭동 탄성 테스트 (ticks={ticks}, seed={seed}, "
          f"{'mock' if mock else 'real'}, source={src}) ===\n")

    scenarios = [
        {"label": "control", "perturbation": None},
        {"label": "tension_spike", "perturbation": "tension_all_05"},
        {"label": "warmth_reset_top10", "perturbation": "warmth_top10_zero"},
        {"label": "full_crisis", "perturbation": "tension_05_warmth_zero"},
    ]
    results = []
    for sc in scenarios:
        label = sc["label"]
        data_dir = EXPERIMENT_ROOT / f"T5_{label}_s{seed}"
        if data_dir.exists():
            shutil.rmtree(data_dir)
        (data_dir / "characters").mkdir(parents=True, exist_ok=True)

        _copy_live_data(src, data_dir)

        before = _extract_metrics(data_dir)
        if sc["perturbation"]:
            perturbed = _apply_perturbation(data_dir, sc["perturbation"])
            print(f"--- {label}: 섭동 적용 ---")
            print(f"  before: avg_w={before.get('avg_warmth',0):.4f} avg_ten={before.get('avg_tension',0):.4f}")
            print(f"  after:  avg_w={perturbed.get('avg_warmth',0):.4f} avg_ten={perturbed.get('avg_tension',0):.4f}")
        else:
            print(f"--- {label}: 무섭동 대조군 ---")
            print(f"  initial: avg_w={before.get('avg_warmth',0):.4f} avg_ten={before.get('avg_tension',0):.4f}")

        env = dict(os.environ)
        env["HARMONICITY_DATA_DIR"] = str(data_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        if mock:
            env["REPRO_MOCK_LLM"] = "1"

        rc = subprocess.run(
            [sys.executable, str(BASE / "run_reproducible.py"), "--run", str(seed), str(ticks)],
            env=env, cwd=str(BASE),
        ).returncode

        if rc != 0:
            print(f"  [FAIL] 실패 (rc={rc})")
            results.append({"label": label, "status": "FAIL"})
            continue

        after = _extract_metrics(data_dir)
        after["label"] = label
        after["perturbation"] = sc["perturbation"]
        after["status"] = "OK"
        after["before_avg_warmth"] = before.get("avg_warmth", 0)
        after["before_avg_tension"] = before.get("avg_tension", 0)
        results.append(after)
        print(f"  result: avg_w={after.get('avg_warmth',0):.4f} avg_t={after.get('avg_trust',0):.4f} "
              f"avg_ten={after.get('avg_tension',0):.4f}")

    report_path = EXPERIMENT_ROOT / "T5_perturbation_report.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n리포트: {report_path}")
    _print_t5_table(results)
    return results


def _print_t5_table(results):
    print("\n| scenario | avg_w | avg_t | avg_ten | max_w | zero_w |")
    print("|---|---|---|---|---|---|")
    for r in results:
        if r.get("status") != "OK":
            print(f"| {r['label']} | FAIL |")
            continue
        print(f"| {r['label']} | {r.get('avg_warmth',0):.4f} | {r.get('avg_trust',0):.4f} | "
              f"{r.get('avg_tension',0):.4f} | {r.get('max_warmth',0):.4f} | "
              f"{r.get('zero_warmth',0)} |")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--homeostasis-sweep", action="store_true")
    parser.add_argument("--perturbation", action="store_true")
    parser.add_argument("--rep-erosion", action="store_true")
    parser.add_argument("--ticks", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--source-data", type=str, default=None,
                        help="T5: 초기 데이터 디렉토리 (기본: data/)")
    args = parser.parse_args()

    if args.homeostasis_sweep:
        run_homeostasis_sweep(args.ticks, args.seed, args.mock)
    elif args.perturbation:
        run_perturbation(args.ticks, args.seed, args.mock, args.source_data)
    elif args.rep_erosion:
        run_rep_erosion_sweep(args.ticks, args.seed, args.mock)
    else:
        parser.print_help()
