#!/usr/bin/env python3
"""appraisal 파싱 회귀 조기경보 (kee 승인 2026-08-02, 제안 ⓐ).

배경: appraisal 파싱이 tick ~7,700 ~ 13,568 동안 사실상 죽어 있었으나(성공률 ~0.5%)
      244 마을일 동안 아무도 몰랐다. 그 재발을 막는 것이 이 감시자의 목적이다.

판정 기준(실측으로 확정 — 상세는 아래 THRESHOLD/PERSIST 주석):
  롤링 WINDOW개 appraisal 창의 성공률이 THRESHOLD 미만인 상태가
  새 이벤트 PERSIST개 동안 지속되면 경보 마커를 남긴다.

라이브 무침범: sim.log를 읽기만 하며 시뮬레이션 프로세스를 건드리지 않는다.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent
LOG = Path(os.environ.get("HARMONICITY_SIM_LOG", BASE / "sim.log"))
MARKER = BASE / "PARSE_DEGRADATION_ALERT.json"

# --- 임계 근거(2026-08-02 실측, 구간④ n=1,428) ---------------------------------
# 정상 운영 중에도 롤링 최저 성공률은: 창100 = 94.0% / 창200 = 94.5% / 창400 = 96.5%
# → kee 권고 임계 95%는 창100·200에서는 **오탐**이다. 창400에서만 성립(여유 1.5%p).
# → 창을 400으로 키워 임계 95%를 유지한다(오탐을 결정한 변수는 임계값이 아니라 창 크기였다).
#    붕괴(0.4%)나 부분회복 정체(87.6%)는 첫 창에서 즉시 걸린다.
WINDOW = int(os.environ.get("PARSE_WATCH_WINDOW", 400))
THRESHOLD = float(os.environ.get("PARSE_WATCH_THRESHOLD", 95.0))
# --- 지속성 조건(PERSIST) ---------------------------------------------------
# ★2026-08-02 정정: 롤링 창은 stride=1이라 인접한 두 창이 400개 중 399개를 공유한다.
#   따라서 처음 설계했던 「연속 2창 위반」은 새 이벤트 1개 차이일 뿐이라
#   노이즈 필터로 사실상 기능하지 않았다(kee 질의로 드러남).
#   → 지속성을 '연속 위반 창 수'가 아니라 **위반이 지속된 새 이벤트 수**로 정의한다.
#   기본 200 = 창의 절반이 갈릴 때까지 위반이 유지되어야 통지 → 실질 지속성 확인.
PERSIST = int(os.environ.get("PARSE_WATCH_PERSIST", 200))
# 관찰 시작 tick(그 이전 = 회귀·수복 구간이라 경보 대상 아님). A단계 마커.
SINCE_TICK = int(os.environ.get("PARSE_WATCH_SINCE_TICK", 14004))

RE_TICK = re.compile(r"Tick (\d+)")
RE_OK = re.compile(r"appraisal \[")
RE_NG = re.compile("appraisal 파싱 실패")
RE_PROMPT = re.compile(r"prompt=(\d+)자")


def scan(path: Path):
    """(events, prompts, last_tick) — events: 1=성공 0=실패 시퀀스."""
    events, prompts = [], []
    cur, last = 0, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = RE_TICK.search(line)
            if m:
                cur = int(m.group(1))
                last = cur
                continue
            if cur < SINCE_TICK:
                continue
            ok = bool(RE_OK.search(line))
            ng = bool(RE_NG.search(line))
            if not (ok or ng):
                continue
            events.append(1 if ok else 0)
            p = RE_PROMPT.search(line)
            if p:
                prompts.append(int(p.group(1)))
    return events, prompts, last


def evaluate(events):
    """(지속 이벤트 수, 최근 창 성공률, 최저 창 성공률).

    run = 끝에서부터 임계 미만이 이어진 롤링 창 위치 수.
    stride=1이므로 이 값은 곧 **위반이 지속된 새 appraisal 이벤트 수**와 같다.
    """
    if len(events) < WINDOW:
        return 0, None, 0
    rates = []
    run = 0
    worst = 100.0
    for i in range(0, len(events) - WINDOW + 1):
        r = 100.0 * sum(events[i:i + WINDOW]) / WINDOW
        rates.append(r)
        worst = min(worst, r)
    # 끝에서부터 위반이 이어진 창 위치 수 = 위반 지속 이벤트 수(stride=1)
    for r in reversed(rates):
        if r < THRESHOLD:
            run += 1
        else:
            break
    return run, rates[-1], worst


def main():
    if not LOG.exists():
        print(f"[watch] 로그 없음: {LOG}")
        return 0
    events, prompts, last_tick = scan(LOG)
    run, latest, worst = evaluate(events)
    med = sorted(prompts)[len(prompts) // 2] if prompts else None
    summary = {
        "last_tick": last_tick,
        "events": len(events),
        "window": WINDOW,
        "threshold": THRESHOLD,
        "latest_window_rate": round(latest, 2) if latest is not None else None,
        "worst_window_rate": round(worst, 2) if events else None,
        "persist_events": run,
        "persist_required": PERSIST,
        "prompt_chars_median": med,
        "prompt_chars_max": max(prompts) if prompts else None,
        "prompt_samples": len(prompts),
    }
    print("[watch] " + json.dumps(summary, ensure_ascii=False))

    if run >= PERSIST:
        summary["alert"] = (
            f"appraisal 파싱 성공률이 롤링 {WINDOW}창 기준 {THRESHOLD}% 미만인 상태로 "
            f"새 이벤트 {run}개(요구 {PERSIST}개) 동안 지속됨 — 회귀 의심. "
            f"라이브 설정을 임의로 바꾸지 말고 kee에 회부할 것."
        )
        summary["hint"] = (
            "prompt_chars_median 이 과거 대비 커졌으면 «프롬프트 자연 증가로 슬롯 컨텍스트 초과» "
            "가설을 우선 확인. 규칙: 프롬프트 토큰 + max_tokens < 슬롯 n_ctx(= ctx-size / parallel)."
        )
        MARKER.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[watch] ★ALERT 기록: {MARKER}")
        return 2
    if MARKER.exists():
        MARKER.unlink()
        print("[watch] 회복 확인 — 기존 경보 마커 제거")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
