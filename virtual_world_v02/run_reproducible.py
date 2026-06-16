#!/usr/bin/env python3
"""재현성 검증 진입점 — 같은 seed로 짧은 시뮬런 2회 실행 후 산출물 동일성 검증.

라이브 시뮬(run_village.py)과 완전 분리:
  - 별도 data dir(HARMONICITY_DATA_DIR 환경변수) — 라이브 data/ 무침범
  - max_ticks 제한 + fast 모드(틱 대기 생략)
  - 서브프로세스 격리 — 모듈 전역상태(need_history/reputation_matrix 등) 오염 없이 깨끗한 2회 실행

비교 대상: LLM 생성 텍스트 자체가 아니라 '엔진 상태 산출물'의 수렴(relationships/reputation/
world_state 등)을 정규화 해시로 비교. 같은 seed → 동일 상태면 재현성 PASS.

※ 주의: 같은 llama.cpp 서버를 라이브 시뮬이 동시에 사용 중이면 배치 동시처리 비결정성(⑤)이
   섞일 수 있음. 그 경우 FAIL은 ②/⑤ 트랙에서 다룰 배치불변 이슈의 실증 신호다.

사용:
  python run_reproducible.py [--seed N] [--ticks K]   # 오케스트레이터(기본): 2회 실행+비교
  python run_reproducible.py --run SEED TICKS         # 단일 런 (내부 서브프로세스용)
"""
import sys
import os
import json
import math
import shutil
import hashlib
import statistics
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
REPRO_ROOT = BASE / "repro_runs"

# 비교 대상 산출물 (엔진 상태 수렴 검증). characters/*.json은 별도로 모두 포함.
COMPARE_FILES = [
    "world_state.json", "relationships.json", "reputation.json",
    "need_history.json", "knowledge_base.json", "atmosphere.json",
    "relationship_history.json", "belief_history.json",
]


def _run_single(seed: int, ticks: int):
    """단일 검증 런 — seed 고정 후 N틱 실행. data dir은 부모가 환경변수로 지정.
    REPRO_RECORD/REPRO_REPLAY 환경변수로 LLM record/replay 모드 활성화."""
    sys.path.insert(0, str(BASE))
    from village import config, replay
    from village.persistence import instance_lock
    from village.repro import seed_everything
    from village.main import main
    rec_path = os.environ.get("REPRO_RECORD")
    rep_path = os.environ.get("REPRO_REPLAY")
    if rec_path:
        replay.init_record(rec_path)
    elif rep_path:
        replay.init_replay(rep_path)
    instance_lock.acquire(config.DATA_DIR)  # 검증런도 자기 dir 격리(라이브 dir 오침범 방지)
    try:
        seed_everything(seed)
        main(max_ticks=ticks, fast=True)
    finally:
        replay.close()
        if rep_path:
            print(f"[replay stats] {replay.stats()}")
        instance_lock.release(config.DATA_DIR)


def _hash_dir(data_dir: Path):
    """data dir 산출물의 정규화 해시. (전체해시, {파일명: 해시}) 반환."""
    files = [data_dir / f for f in COMPARE_FILES if (data_dir / f).exists()]
    char_dir = data_dir / "characters"
    if char_dir.exists():
        files += sorted(char_dir.glob("*.json"))

    digest = {}
    overall = hashlib.sha256()
    for p in sorted(files, key=lambda x: str(x.relative_to(data_dir))):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            norm = json.dumps(obj, ensure_ascii=False, sort_keys=True)
        except Exception:
            norm = p.read_text(encoding="utf-8")
        rel = str(p.relative_to(data_dir))
        d = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        digest[rel] = d
        overall.update(rel.encode("utf-8"))
        overall.update(d.encode("utf-8"))
    return overall.hexdigest(), digest


def _spawn(seed: int, ticks: int, data_dir: Path, extra_env: dict = None) -> int:
    env = dict(os.environ)
    env["HARMONICITY_DATA_DIR"] = str(data_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, str(BASE / "run_reproducible.py"), "--run", str(seed), str(ticks)],
        env=env, cwd=str(BASE),
    )
    return proc.returncode


def orchestrate(seed: int, ticks: int) -> bool:
    print(f"=== 재현성 검증: seed={seed}, ticks={ticks}, 동일 seed 2회 실행 ===")
    dirs = []
    for tag in ("run_a", "run_b"):
        d = REPRO_ROOT / f"seed{seed}_{tag}"
        if d.exists():
            shutil.rmtree(d)
        (d / "characters").mkdir(parents=True, exist_ok=True)
        dirs.append(d)

    for i, d in enumerate(dirs):
        print(f"\n--- 런 {i + 1}/2 → {d.name} ---", flush=True)
        rc = _spawn(seed, ticks, d)
        if rc != 0:
            print(f"❌ 런 {i + 1} 비정상 종료(rc={rc})")
            return False

    ha, da = _hash_dir(dirs[0])
    hb, db = _hash_dir(dirs[1])
    print(f"\n런A 해시: {ha[:16]}  ({len(da)}개 파일)")
    print(f"런B 해시: {hb[:16]}  ({len(db)}개 파일)")

    if ha == hb:
        print("재현성 검증: PASS ✅ (같은 seed → 동일 엔진 산출물)")
        return True

    print("재현성 검증: FAIL ❌ — 불일치 파일:")
    for k in sorted(set(da) | set(db)):
        if da.get(k) != db.get(k):
            print(f"  - {k}: A={(da.get(k) or '-')[:10]} B={(db.get(k) or '-')[:10]}")
    print("  ↳ 같은 서버를 라이브 시뮬이 동시 사용 중이면 배치 비결정성(⑤) 가능성. ②/⑤ 트랙에서 정밀 분석.")
    return False


def orchestrate_replay(seed: int, ticks: int) -> bool:
    """②replay 검증: record 런(실제 LLM, 로그 기록) → replay 런(로그 재생) → 산출물 동일성.
    배치 비결정성(⑤)이 있어도 replay는 기록을 그대로 재생하므로 PASS여야 함."""
    print(f"=== ②replay 검증: seed={seed}, ticks={ticks} (record→replay 완전 재현) ===")
    rec_dir = REPRO_ROOT / f"replay_seed{seed}_record"
    rep_dir = REPRO_ROOT / f"replay_seed{seed}_replay"
    log_path = REPRO_ROOT / f"replay_seed{seed}_llm.jsonl"
    for d in (rec_dir, rep_dir):
        if d.exists():
            shutil.rmtree(d)
        (d / "characters").mkdir(parents=True, exist_ok=True)

    print("\n--- record 런 (실제 LLM 호출 + 출력 기록) ---", flush=True)
    rc = _spawn(seed, ticks, rec_dir, {"REPRO_RECORD": str(log_path)})
    if rc != 0:
        print(f"❌ record 런 실패(rc={rc})")
        return False

    print("\n--- replay 런 (기록 재생, LLM 서버 미사용) ---", flush=True)
    rc = _spawn(seed, ticks, rep_dir, {"REPRO_REPLAY": str(log_path)})
    if rc != 0:
        print(f"❌ replay 런 실패(rc={rc})")
        return False

    n_calls = sum(1 for line in open(log_path, encoding="utf-8") if line.strip())
    ha, da = _hash_dir(rec_dir)
    hb, db = _hash_dir(rep_dir)
    print(f"\n기록된 LLM 호출: {n_calls}건")
    print(f"record 해시: {ha[:16]}  ({len(da)}개 파일)")
    print(f"replay 해시: {hb[:16]}  ({len(db)}개 파일)")

    if ha == hb:
        print("②replay 검증: PASS ✅ (record→replay 완전 재현, ⑤ 배치비결정성 우회 성공)")
        return True
    print("②replay 검증: FAIL ❌ — 불일치 파일:")
    for k in sorted(set(da) | set(db)):
        if da.get(k) != db.get(k):
            print(f"  - {k}: A={(da.get(k) or '-')[:10]} B={(db.get(k) or '-')[:10]}")
    return False


def _extract_metrics(data_dir: Path) -> dict:
    """산출물 relationships.json에서 다회통계용 메트릭 추출."""
    rel = json.loads((data_dir / "relationships.json").read_text(encoding="utf-8"))
    pairs = list(rel.values()) if isinstance(rel, dict) else rel
    n = len(pairs) or 1

    def g(p, k):
        return p.get(k, 0) if isinstance(p, dict) else 0

    warmths = [g(p, "warmth") for p in pairs]
    trusts = [g(p, "trust") for p in pairs]
    tensions = [g(p, "tension") for p in pairs]
    return {
        "avg_warmth": round(sum(warmths) / n, 4),
        "avg_trust": round(sum(trusts) / n, 4),
        "avg_tension": round(sum(tensions) / n, 4),
        "ceiling": sum(1 for p in pairs if g(p, "warmth") >= 1.0 and g(p, "trust") >= 1.0),
        "affection_sat": sum(1 for p in pairs if g(p, "affection") >= 0.95),
        "active_rels": sum(1 for p in pairs if g(p, "interaction_count") > 0),
        "n_pairs": len(pairs),
    }


def _stats(values: list) -> dict:
    """mean±std + 95% CI (정규근사). N<2면 CI=0(표기상 단일관측)."""
    n = len(values)
    m = statistics.mean(values) if n else 0.0
    sd = statistics.stdev(values) if n > 1 else 0.0
    ci = 1.96 * sd / math.sqrt(n) if n > 1 else 0.0
    return {"mean": round(m, 4), "std": round(sd, 4), "ci95": round(ci, 4), "n": n}


def orchestrate_multiseed(seeds: list, ticks: int, mock: bool = False, record: bool = True) -> dict:
    """③다회통계: N시드 반복 실행 → 메트릭별 mean±std/95%CI + 시드별 raw.
    venture 합의 포맷. record=True면 시드별 LLM 로그도 보관(재현가능 다회통계)."""
    mode = "mock" if mock else "real LLM"
    print(f"=== ③다회통계: seeds={seeds} ({len(seeds)}회), ticks={ticks}, {mode} ===")
    per_seed = {}
    for s in seeds:
        d = REPRO_ROOT / f"multiseed_s{s}"
        if d.exists():
            shutil.rmtree(d)
        (d / "characters").mkdir(parents=True, exist_ok=True)
        extra = {}
        if mock:
            extra["REPRO_MOCK_LLM"] = "1"
        elif record:
            extra["REPRO_RECORD"] = str(REPRO_ROOT / f"multiseed_s{s}_llm.jsonl")
        print(f"\n--- seed {s} 실행 ---", flush=True)
        rc = _spawn(s, ticks, d, extra)
        if rc != 0:
            print(f"❌ seed {s} 실패(rc={rc}) — 제외")
            continue
        per_seed[s] = _extract_metrics(d)

    keys = ["avg_warmth", "avg_trust", "avg_tension", "ceiling", "affection_sat", "active_rels"]
    summary = {k: _stats([per_seed[s][k] for s in per_seed]) for k in keys}
    report = {
        "seeds": list(per_seed.keys()), "ticks": ticks, "mode": mode,
        "per_seed": per_seed, "summary": summary,
    }
    out = REPRO_ROOT / "multiseed_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== 다회통계 리포트 (N={len(per_seed)}) ===")
    print(f"{'metric':<16}{'mean':>10}{'std':>10}{'95%CI':>10}")
    for k in keys:
        st = summary[k]
        print(f"{k:<16}{st['mean']:>10}{st['std']:>10}{st['ci95']:>10}")
    print("\n시드별 raw:")
    print(f"{'seed':<8}" + "".join(f"{k[:9]:>11}" for k in keys))
    for s in per_seed:
        print(f"{s:<8}" + "".join(f"{per_seed[s][k]:>11}" for k in keys))
    print(f"\n리포트 저장: {out}")
    return report


def main_cli():
    args = sys.argv[1:]
    if args and args[0] == "--run":
        _run_single(int(args[1]), int(args[2]))
        return

    seed, ticks = 42, 4
    if "--seed" in args:
        seed = int(args[args.index("--seed") + 1])
    if "--ticks" in args:
        ticks = int(args[args.index("--ticks") + 1])
    if "--replay-test" in args:
        ok = orchestrate_replay(seed, ticks)
        sys.exit(0 if ok else 1)
    if "--multiseed" in args:
        nseed = int(args[args.index("--multiseed") + 1])
        seeds = list(range(1, nseed + 1))
        orchestrate_multiseed(seeds, ticks, mock="--mock" in args)
        sys.exit(0)
    if "--mock" in args:
        os.environ["REPRO_MOCK_LLM"] = "1"  # _spawn이 env 복사 → 서브프로세스 전파
        print("[mock LLM 모드] 순수 엔진(random) 결정성만 검증")
    ok = orchestrate(seed, ticks)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main_cli()
