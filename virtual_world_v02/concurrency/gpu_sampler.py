#!/usr/bin/env python3
"""GPU/VRAM + llama.cpp 슬롯 샘플러 — 동시성 실측용.

ogo(5090, Windows)에서 동시성 벤치와 병행 실행해 GPU util·VRAM·전력·llama.cpp 활성
슬롯 수를 시계열 CSV로 적재. nvidia-smi와 llama.cpp /slots(있으면)를 폴링.

사용:
  python concurrency/gpu_sampler.py --out gpu.csv --interval-ms 1000 --duration 1800
  # 또는 stop 파일로 종료: --stop-file concurrency_runs/STOP
크로스플랫폼(nvidia-smi는 Windows/Linux 동일). /slots 미지원 서버면 슬롯열은 공란.
"""
import argparse
import csv
import os
import subprocess
import sys
import time

try:
    import requests
except Exception:
    requests = None

NVIDIA_QUERY = "utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu"


def _slots_base(api_url: str) -> str:
    # config.API_URL = http://host:8080/v1/chat/completions → http://host:8080/slots
    if not api_url:
        return None
    base = api_url.split("/v1/")[0].rstrip("/")
    return base + "/slots"


def sample_nvidia():
    """반환: (gpu_util, mem_used_mb, mem_total_mb, power_w, temp_c) 또는 None."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", f"--query-gpu={NVIDIA_QUERY}",
             "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=10,
        ).decode("utf-8", "ignore").strip()
        # 멀티 GPU면 첫 줄(5090 단일 가정)
        first = out.splitlines()[0]
        parts = [p.strip() for p in first.split(",")]
        return tuple(parts[:5])
    except Exception:
        return None


def sample_slots(slots_url):
    """llama.cpp /slots 폴링 → 활성(processing) 슬롯 수, 전체 슬롯 수."""
    if not (slots_url and requests):
        return (None, None)
    try:
        r = requests.get(slots_url, timeout=5)
        r.raise_for_status()
        slots = r.json()
        if isinstance(slots, list):
            total = len(slots)
            # llama.cpp 슬롯 상태 키는 버전마다 다름(state/is_processing)
            active = sum(
                1 for s in slots
                if s.get("state") in (1, "processing") or s.get("is_processing")
            )
            return (active, total)
    except Exception:
        pass
    return (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval-ms", type=int, default=1000)
    ap.add_argument("--duration", type=float, default=0, help="0=무한(stop 파일/Ctrl-C까지)")
    ap.add_argument("--stop-file", default=None)
    ap.add_argument("--api-url", default=os.environ.get(
        "HARMONICITY_API_URL", "http://localhost:8080/v1/chat/completions"))
    args = ap.parse_args()

    slots_url = _slots_base(args.api_url)
    interval = args.interval_ms / 1000.0
    t_end = time.time() + args.duration if args.duration > 0 else None

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts", "gpu_util", "mem_used_mb", "mem_total_mb",
                    "power_w", "temp_c", "slots_active", "slots_total"])
        print(f"[gpu_sampler] start out={args.out} interval={interval}s "
              f"slots_url={slots_url}", flush=True)
        try:
            while True:
                if t_end and time.time() >= t_end:
                    break
                if args.stop_file and os.path.exists(args.stop_file):
                    break
                nv = sample_nvidia() or ("", "", "", "", "")
                sa, st = sample_slots(slots_url)
                w.writerow([round(time.time(), 3), *nv, sa, st])
                f.flush()
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
    print("[gpu_sampler] done", flush=True)


if __name__ == "__main__":
    main()
