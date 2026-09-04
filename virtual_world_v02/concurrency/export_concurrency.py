#!/usr/bin/env python3
"""동시성 실측 리포트 export — concurrency_report.json(+gpu.csv) → md/csv.

A06 승격 근거 + venture 영업 자산. N별 throughput·세계별 wall-clock·GPU util·"SLA 허용
한계 N"·클라우드 환산 단가를 표로. BENCHMARK_REPORT.md 표 구조 답습.

사용: python concurrency/export_concurrency.py concurrency_runs/run [--tick-budget 200]
"""
import argparse
import csv
import json
import sys
from pathlib import Path


def _load_gpu(gpu_csv: Path):
    rows = []
    if not gpu_csv or not gpu_csv.exists():
        return rows
    with open(gpu_csv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "ts": float(r["ts"]),
                    "gpu_util": float(r["gpu_util"]) if r.get("gpu_util") else None,
                    "mem_used": float(r["mem_used_mb"]) if r.get("mem_used_mb") else None,
                    "mem_total": float(r["mem_total_mb"]) if r.get("mem_total_mb") else None,
                    "power": float(r["power_w"]) if r.get("power_w") else None,
                    "slots": float(r["slots_active"]) if r.get("slots_active") not in (None, "", "None") else None,
                })
            except Exception:
                continue
    return rows


def _gpu_slice(rows, phase):
    if not rows or not phase:
        return {}
    t0, t1 = phase
    sub = [r for r in rows if t0 <= r["ts"] <= t1]
    def agg(key, fn):
        vals = [r[key] for r in sub if r.get(key) is not None]
        return round(fn(vals), 1) if vals else None
    return {
        "gpu_util_mean": agg("gpu_util", lambda v: sum(v) / len(v)),
        "gpu_util_max": agg("gpu_util", max),
        "mem_used_max_mb": agg("mem_used", max),
        "mem_total_mb": agg("mem_total", max),
        "power_max_w": agg("power", max),
        "slots_max": agg("slots", max),
        "samples": len(sub),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--tick-budget", type=float, default=200.0,
                    help="라이브 TICK_SECONDS — 세계별 tick wall이 이 안이면 실시간 유지(SLA)")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    report = json.loads((run_dir / "concurrency_report.json").read_text(encoding="utf-8"))
    meta = report["meta"]
    gpu_rows = _load_gpu(Path(meta["gpu_csv"])) if meta.get("gpu_csv") else []

    # 레벨별 GPU 슬라이스 결합 + SLA 판정
    sla_limit = 0
    for L in report["levels"]:
        L["gpu"] = _gpu_slice(gpu_rows, L.get("phase"))
        tick_mean = L["tick_wall_s"]["mean"]
        L["realtime_ok"] = bool(tick_mean and tick_mean < args.tick_budget)
        if L["realtime_ok"] and L["failures"] == 0 and L["N"] > sla_limit:
            sla_limit = L["N"]

    # --- summary.md ---
    md = []
    md.append("# 하모니시티 동시성 실측 리포트 (A06 승격 근거)\n")
    md.append(f"- 모드: **{meta['mode']}** / API: `{meta.get('api_url')}` / "
              f"틱/세계: {meta['ticks']} / 측정시간: {meta['elapsed_s']}s")
    md.append(f"- **SLA 허용 동시 세계 한계 = N≤{sla_limit}** "
              f"(세계별 tick wall-clock < {args.tick_budget:.0f}s=라이브 실시간 예산, 실패 0 기준)\n")
    md.append("## N별 동시 가동 실측\n")
    md.append("| N | ok/실패 | makespan(s) | 세계 wall mean±std(s) | tick wall mean(s) | "
              "LLM lat mean(s) | throughput(calls/s) | GPU util mean/max(%) | VRAM max(MB) | slots max | 실시간 |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for L in report["levels"]:
        g = L.get("gpu", {})
        ww, tw, ll = L["world_wall_s"], L["tick_wall_s"], L["llm_latency_s"]
        md.append(
            f"| {L['N']} | {L['ok']}/{L['failures']} | {L['makespan_s']} | "
            f"{ww['mean']}±{ww['std']} | {tw['mean']} | {ll['mean']} | "
            f"{L['throughput_llm_per_s']} | "
            f"{g.get('gpu_util_mean','-')}/{g.get('gpu_util_max','-')} | "
            f"{g.get('mem_used_max_mb','-')} | {g.get('slots_max','-')} | "
            f"{'✅' if L['realtime_ok'] else '❌'} |")

    md.append("\n## 해석\n")
    md.append("- **throughput 포화점**: calls/s가 N 증가에도 더 안 오르는 지점 = llama.cpp "
              "배치 처리 상한(서버 슬롯/KV-cache). 그 위로는 세계별 wall-clock만 선형 저하.")
    md.append("- **VRAM cap**: mem_used_max가 mem_total에 근접하는 N = 5090 32GB의 물리적 동시 세계 상한.")
    md.append(f"- **A06 승격 문구(제안)**: \"단일 5090 + llama.cpp에서 동시 N={sla_limit} 세계가 "
              "실시간(tick<예산) 유지됨을 실측. throughput·VRAM 포화점은 위 표 참조 — "
              "'추정·미실측'을 실측치로 대체.\"")

    # 클라우드 환산(개략): 세계당 GPU 점유율 = util_mean / N
    md.append("\n## 클라우드 환산(개략)\n")
    md.append("| N | GPU util/세계(%) | 비고 |")
    md.append("|---|---|---|")
    for L in report["levels"]:
        g = L.get("gpu", {})
        um = g.get("gpu_util_mean")
        per = round(um / L["N"], 2) if um and L["N"] else "-"
        md.append(f"| {L['N']} | {per} | {'실시간' if L['realtime_ok'] else '저하'} |")

    (run_dir / "concurrency_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # --- summary.csv (기계판독) ---
    with open(run_dir / "concurrency_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["N", "ok", "failures", "makespan_s", "world_wall_mean", "world_wall_std",
                    "tick_wall_mean", "llm_lat_mean", "throughput_calls_s",
                    "gpu_util_mean", "gpu_util_max", "vram_used_max_mb", "slots_max", "realtime_ok"])
        for L in report["levels"]:
            g = L.get("gpu", {})
            w.writerow([L["N"], L["ok"], L["failures"], L["makespan_s"],
                        L["world_wall_s"]["mean"], L["world_wall_s"]["std"],
                        L["tick_wall_s"]["mean"], L["llm_latency_s"]["mean"],
                        L["throughput_llm_per_s"], g.get("gpu_util_mean"), g.get("gpu_util_max"),
                        g.get("mem_used_max_mb"), g.get("slots_max"), L["realtime_ok"]])

    print(f"SLA 허용 동시 세계 한계 N≤{sla_limit}")
    print(f"리포트: {run_dir/'concurrency_report.md'} , {run_dir/'concurrency_summary.csv'}")


if __name__ == "__main__":
    main()
