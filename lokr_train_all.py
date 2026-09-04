#!/usr/bin/env python3
"""
Sequential LoKR training for all eligible artists.
Run on 5090: python lokr_train_all.py [--skip-akmu]
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

VENV_PYTHON = r"C:\Users\leo\ace-step-v15\venv\Scripts\python.exe"
ACE_DIR = Path(r"C:\Users\leo\ace-step-v15")
BASE_DIR = Path(r"C:\Users\leo\ace-step-v15\lokr_artists")
CHECKPOINT = r"D:\models\ACE-Step-v1.5"
LOG_FILE = BASE_DIR / "train_all.log"

ARTISTS = [
    "DAY6__데이식스",
    "IVE__아이브",
    "황치열",
    "투어스",
    "방탄소년단",
    "아일릿",
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_cmd(args, desc=""):
    log(f"  CMD: {' '.join(args[:6])}...")
    t0 = time.time()
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ACE_DIR),
    )
    elapsed = time.time() - t0
    if result.returncode != 0:
        log(f"  FAILED ({elapsed:.0f}s): {result.stderr[-500:]}")
        return False
    log(f"  OK ({elapsed:.0f}s)")
    return True


def preprocess(artist):
    artist_dir = BASE_DIR / artist
    return run_cmd([
        VENV_PYTHON, "-u", "train.py", "--yes", "fixed",
        "--checkpoint-dir", CHECKPOINT,
        "--base-model", "turbo",
        "--preprocess",
        "--audio-dir", str(artist_dir / "wav"),
        "--tensor-output", str(artist_dir / "tensors"),
        "--dataset-dir", str(artist_dir / "tensors"),
        "--dataset-json", str(artist_dir / "dataset.json"),
        "--output-dir", str(artist_dir / "output"),
        "--adapter-type", "lokr",
        "--lokr-linear-dim", "128",
        "--lokr-linear-alpha", "256",
        "--lokr-weight-decompose",
        "--lr", "1e-4",
        "--epochs", "500",
    ], f"preprocess {artist}")


def train(artist):
    artist_dir = BASE_DIR / artist
    return run_cmd([
        VENV_PYTHON, "-u", "train.py", "--yes", "fixed",
        "--checkpoint-dir", CHECKPOINT,
        "--base-model", "turbo",
        "--dataset-dir", str(artist_dir / "tensors"),
        "--output-dir", str(artist_dir / "output"),
        "--adapter-type", "lokr",
        "--lokr-linear-dim", "128",
        "--lokr-linear-alpha", "256",
        "--lokr-weight-decompose",
        "--lr", "1e-4",
        "--epochs", "500",
        "--batch-size", "2",
        "--gradient-accumulation", "2",
        "--scheduler-type", "cosine",
        "--warmup-steps", "100",
        "--cfg-ratio", "0.15",
        "--shift", "3.0",
        "--dropout", "0.05",
    ], f"train {artist}")


def main():
    log("=" * 60)
    log("LoKR Train All - Sequential Pipeline")
    log(f"Artists: {len(ARTISTS)}")
    log("=" * 60)

    results = {}
    for i, artist in enumerate(ARTISTS, 1):
        artist_dir = BASE_DIR / artist
        tensor_dir = artist_dir / "tensors"

        log(f"\n[{i}/{len(ARTISTS)}] === {artist} ===")

        # Check if tensors already exist
        existing = list(tensor_dir.glob("*.pt")) if tensor_dir.exists() else []
        if existing:
            log(f"  Tensors exist ({len(existing)} files), skipping preprocess")
        else:
            tensor_dir.mkdir(parents=True, exist_ok=True)
            if not preprocess(artist):
                log(f"  SKIP {artist}: preprocess failed")
                results[artist] = "PREPROCESS_FAILED"
                continue

        # Check if already trained
        output_dir = artist_dir / "output" / "checkpoints"
        if output_dir.exists() and any(output_dir.iterdir()):
            log(f"  Output exists, checking completion...")
            epochs_done = [d.name for d in output_dir.iterdir() if d.is_dir()]
            if any("epoch_500" in e for e in epochs_done):
                log(f"  Already trained to 500 epochs, skipping")
                results[artist] = "ALREADY_DONE"
                continue

        (artist_dir / "output").mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        if train(artist):
            elapsed = time.time() - t0
            results[artist] = f"OK ({elapsed/60:.0f}min)"
        else:
            results[artist] = "TRAIN_FAILED"

    log("\n" + "=" * 60)
    log("FINAL RESULTS")
    log("=" * 60)
    for artist, status in results.items():
        log(f"  {artist}: {status}")

    with open(BASE_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"Results saved to {BASE_DIR / 'results.json'}")
    log("All done!")


if __name__ == "__main__":
    main()
