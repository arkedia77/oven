#!/usr/bin/env python3
"""동시성 실측 오케스트레이터 — 사업계획서 A06("동시 세계 15~20개") 실측 검증.

단일 5090 + 단일 llama.cpp 서버에서 N개 세계를 *동시* 가동(각자 별도 HARMONICITY_DATA_DIR)
하고, N을 스윕하며 세계별 wall-clock·aggregate throughput·실패율을 측정한다. GPU util/VRAM은
concurrency/gpu_sampler.py를 병행 실행해 별도 CSV로 수집(리포트가 phase 윈도우로 슬라이스).

재현성 트랙(run_reproducible.py)의 _run_single(--run) 진입점 + _extract_metrics/_stats를 재사용.
차이는 subprocess.run(순차) → Popen(동시). 라이브 시뮬(data/)은 절대 건드리지 않음(별도 dir).

사용(로컬 메커니즘 검증, 서버 불필요):
  python concurrency/run_concurrency.py --mock --levels 1,2 --ticks 4
실측(ogo, 합의 윈도우):
  python concurrency/run_concurrency.py --levels 1,2,4,8,12,16,20 --ticks 24 --gpu \
      --api-url http://localhost:8080/v1/chat/completions
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent.parent          # virtual_world_v02
sys.path.insert(0, str(BASE))
from run_reproducible import _extract_metrics, _stats  # noqa: E402

CONC_ROOT = BASE / "concurrency_runs"


def _launch_world(seed: int, ticks: int, data_dir: Path, api_url: str, mock: bool):
    (data_dir / "characters").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HARMONICITY_DATA_DIR"] = str(data_dir)
    env["HARMONICITY_PROFILE"] = "1"          # 세계별 profile_{pid}.jsonl 적재
    env["PYTHONIOENCODING"] = "utf-8"
    if api_url:
        env["HARMONICITY_API_URL"] = api_url
    if mock:
        env["REPRO_MOCK_LLM"] = "1"           # 서버 없이 엔진만(메커니즘 검증)
    log = open(data_dir.parent / "world.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(BASE / "run_reproducible.py"), "--run", str(seed), str(ticks)],
        env=env, cwd=str(BASE), stdout=log, stderr=subprocess.STDOUT,
    )
    return {"proc": proc, "log": log, "dir": data_dir, "start": time.time(), "seed": seed}


def _read_profile(data_dir: Path) -> dict:
    """세계의 profile_*.jsonl 집계 → llm latency 리스트, tick wall 리스트, 호출수."""
    files = glob.glob(str(data_dir / "profile_*.jsonl"))
    llm_lat, tick_wall, llm_wait = [], [], []
    n_llm = n_tick = 0
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("t") == "llm":
                    n_llm += 1
                    llm_lat.append(r.get("latency_s", 0.0))
                elif r.get("t") == "tick":
                    n_tick += 1
                    tick_wall.append(r.get("wall_s", 0.0))
                    llm_wait.append(r.get("llm_wait_s", 0.0))
    return {"n_llm": n_llm, "n_tick": n_tick, "llm_lat": llm_lat,
            "tick_wall": tick_wall, "llm_wait": llm_wait}


def run_level(N: int, ticks: int, seed_base: int, api_url: str, mock: bool, root: Path) -> dict:
    print(f"\n=== N={N} 세계 동시 가동 (ticks={ticks}, {'mock' if mock else 'real'}) ===", flush=True)
    level_dir = root / f"N{N:02d}"
    workers = []
    for i in range(N):
        d = level_dir / f"world_{i}" / "data"
        workers.append(_launch_world(seed_base + i, ticks, d, api_url, mock))

    pending = set(range(N))
    while pending:
        for i in list(pending):
            rc = workers[i]["proc"].poll()
            if rc is not None:
                workers[i]["rc"] = rc
                workers[i]["end"] = time.time()
                pending.discard(i)
        time.sleep(0.5)
    for w in workers:
        w["log"].close()

    starts = [w["start"] for w in workers]
    ends = [w["end"] for w in workers]
    makespan = max(ends) - min(starts)

    world_walls, total_llm, total_ticks = [], 0, 0
    all_tick_walls, all_llm_lat = [], []
    failures = 0
    for w in workers:
        if w.get("rc", 1) != 0:
            failures += 1
            continue
        world_walls.append(w["end"] - w["start"])
        prof = _read_profile(w["dir"])
        total_llm += prof["n_llm"]
        total_ticks += prof["n_tick"]
        all_tick_walls += prof["tick_wall"]
        all_llm_lat += prof["llm_lat"]

    summary = {
        "N": N, "ticks": ticks, "ok": N - failures, "failures": failures,
        "makespan_s": round(makespan, 2),
        "world_wall_s": _stats(world_walls),
        "tick_wall_s": _stats(all_tick_walls),
        "llm_latency_s": _stats(all_llm_lat),
        "throughput_llm_per_s": round(total_llm / makespan, 3) if makespan else 0,
        "throughput_ticks_per_s": round(total_ticks / makespan, 3) if makespan else 0,
        "total_llm_calls": total_llm,
        "phase": [round(min(starts), 3), round(max(ends), 3)],  # GPU CSV 슬라이스용
    }
    print(f"  ok={summary['ok']}/{N} makespan={summary['makespan_s']}s "
          f"world_wall mean={summary['world_wall_s']['mean']}s "
          f"llm_lat mean={summary['llm_latency_s']['mean']}s "
          f"throughput={summary['throughput_llm_per_s']} calls/s", flush=True)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default="1,2,4,8,12,16,20")
    ap.add_argument("--ticks", type=int, default=24)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--api-url", default=os.environ.get("HARMONICITY_API_URL"))
    ap.add_argument("--mock", action="store_true", help="서버 없이 엔진만(메커니즘 검증)")
    ap.add_argument("--gpu", action="store_true", help="gpu_sampler 병행 실행")
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    levels = [int(x) for x in args.levels.split(",") if x.strip()]
    root = CONC_ROOT / args.tag
    if root.exists():
        import shutil
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    gpu_proc = None
    gpu_csv = root / "gpu.csv"
    if args.gpu:
        gpu_proc = subprocess.Popen(
            [sys.executable, str(BASE / "concurrency" / "gpu_sampler.py"),
             "--out", str(gpu_csv), "--interval-ms", "1000",
             "--api-url", args.api_url or "http://localhost:8080/v1/chat/completions"],
            cwd=str(BASE),
        )
        time.sleep(2)  # 베이스라인 몇 샘플 확보

    levels_out = []
    t_start = time.time()
    for N in levels:
        levels_out.append(run_level(N, args.ticks, args.seed_base, args.api_url, args.mock, root))

    if gpu_proc:
        gpu_proc.terminate()
        try:
            gpu_proc.wait(timeout=10)
        except Exception:
            gpu_proc.kill()

    report = {
        "meta": {
            "mode": "mock" if args.mock else "real",
            "api_url": args.api_url, "ticks": args.ticks,
            "seed_base": args.seed_base, "levels": levels,
            "elapsed_s": round(time.time() - t_start, 1),
            "gpu_csv": str(gpu_csv) if args.gpu else None,
        },
        "levels": levels_out,
    }
    out = root / "concurrency_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== 동시성 실측 완료 (levels={levels}) → {out} ===")
    print(f"{'N':>4}{'ok':>5}{'makespan':>10}{'world_wall':>12}{'llm_lat':>9}{'calls/s':>9}")
    for L in levels_out:
        print(f"{L['N']:>4}{L['ok']:>5}{L['makespan_s']:>10}"
              f"{L['world_wall_s']['mean']:>12}{L['llm_latency_s']['mean']:>9}"
              f"{L['throughput_llm_per_s']:>9}")


if __name__ == "__main__":
    main()
