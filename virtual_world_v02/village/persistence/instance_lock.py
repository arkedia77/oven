"""data dir 단위 인스턴스 락 — 좀비 race 2차 방어 + 멀티테넌트 격리 토대.

좀비 사고(2026-06-06): 두 run_village 프로세스가 같은 data/를 번갈아 덮어쓰는 race.
1차 방어 = run_village.py의 OS 전역 mutex(전역 단일 인스턴스).
2차 방어(본 모듈) = data dir별 락 — 같은 data dir을 다른 살아있는 프로세스가 점유 중이면 거부.

전역 mutex와 달리 '디렉토리 단위'라 멀티테넌트(여러 data dir = 여러 인스턴스 동시)와 정합.
락 파일: <data_dir>/.instance.lock  = {pid, host, started, data_dir}

stale 판정: 같은 호스트의 죽은 PID → 탈취. 살아있는 PID 또는 다른 호스트 → 거부(보수적).
"""
import json
import os
import socket
from datetime import datetime
from pathlib import Path

LOCK_NAME = ".instance.lock"


def _pid_alive(pid: int) -> bool:
    """PID 생존 여부. 불확실하면 True(살아있다고 간주 → stale 오탈취 방지)."""
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h:
                return False  # 핸들 못 열면 미존재
            try:
                code = ctypes.c_ulong()
                if ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code)):
                    return code.value == STILL_ACTIVE
                return True
            finally:
                ctypes.windll.kernel32.CloseHandle(h)
        else:
            os.kill(pid, 0)
            return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # 권한 없음 = 프로세스 존재
    except Exception:
        return True  # 불확실 → 보수적으로 살아있다고 간주


def _read_lock(lock_path: Path):
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception:
        return None


class InstanceLockError(RuntimeError):
    pass


def acquire(data_dir, force: bool = False) -> Path:
    """data_dir 인스턴스 락 획득. 충돌 시 InstanceLockError.
    force=True면 stale 무시하고 강제 탈취(복구용)."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = data_dir / LOCK_NAME
    host = socket.gethostname()

    existing = _read_lock(lock_path)
    if existing and not force:
        opid = int(existing.get("pid", -1))
        ohost = existing.get("host", "")
        if opid == os.getpid() and ohost == host:
            return lock_path  # 자기 락 — 재진입 허용
        if ohost != host:
            raise InstanceLockError(
                f"다른 호스트({ohost})가 {data_dir} 점유 중(pid={opid}). 거부.")
        if _pid_alive(opid):
            raise InstanceLockError(
                f"살아있는 프로세스(pid={opid}, {ohost})가 {data_dir} 점유 중. 거부.")
        # 같은 호스트의 죽은 PID = stale → 탈취 (좀비 사고 후 watchdog 재기동 시나리오)

    payload = {
        "pid": os.getpid(),
        "host": host,
        "started": datetime.now().isoformat(timespec="seconds"),
        "data_dir": str(data_dir),
    }
    lock_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return lock_path


def release(data_dir) -> None:
    """자기 소유 락만 제거. 타인 락은 건드리지 않음."""
    lock_path = Path(data_dir) / LOCK_NAME
    existing = _read_lock(lock_path)
    if existing and int(existing.get("pid", -1)) == os.getpid():
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
