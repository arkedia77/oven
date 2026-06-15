#!/usr/bin/env python3
"""Harmonicity village simulation launcher — self-redirecting for detached mode."""
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

os.environ["PYTHONIOENCODING"] = "utf-8"

base_dir = Path(__file__).parent
log_path = base_dir / "sim.log"
crash_path = base_dir / "sim_crash.log"

# --- 단일 인스턴스 가드 (Windows named mutex) ---
# 좀비/중복 프로세스가 같은 data/를 동시에 덮어쓰는 race 방지 (2026-06-06 사고 대응).
# 로그 오픈보다 먼저 검사 → 중복 기동이 sim.log 잠금 충돌(PermissionError)로 크래시하지 않고
# 깔끔히 종료. 프로세스 종료 시 OS가 mutex를 자동 해제하므로 stale lock 문제 없음.
_mutex_handle = None
try:
    if os.name == "nt":
        import ctypes
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\HarmonicityVillageSim")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            sys.exit(0)  # 이미 실행 중 — 중복 기동 조용히 거부
except Exception:
    pass  # mutex 설정 실패 시 가드 없이 진행 (기존 동작 유지)

try:
    log_fh = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = log_fh
    sys.stderr = log_fh
except Exception as e:
    with open(crash_path, "a", encoding="utf-8") as ef:
        ef.write(f"[{datetime.now()}] Failed to open log: {e}\n")
    sys.exit(1)

if _mutex_handle:
    print(f"[{datetime.now()}] [guard] 단일 인스턴스 mutex 획득. 시뮬레이션 시작.")

try:
    sys.path.insert(0, str(base_dir))
    # --- data dir 인스턴스 락 (좀비 race 2차 방어 + 멀티테넌트 격리) ---
    # mutex(전역 1차) 우회/실패 시에도 같은 data dir 동시점유를 차단.
    import atexit
    from village import config
    from village.persistence import instance_lock
    try:
        instance_lock.acquire(config.DATA_DIR)
        atexit.register(instance_lock.release, config.DATA_DIR)
        print(f"[{datetime.now()}] [guard] data dir 인스턴스 락 획득: {config.DATA_DIR}")
    except instance_lock.InstanceLockError as e:
        print(f"[{datetime.now()}] [guard] data dir 락 거부 — 중복 점유 차단, 종료: {e}")
        sys.exit(0)
    from village.main import main
    main()
except SystemExit:
    raise
except Exception:
    with open(crash_path, "a", encoding="utf-8") as ef:
        ef.write(f"\n[{datetime.now()}] {'='*40}\n")
        traceback.print_exc(file=ef)
    sys.exit(1)
