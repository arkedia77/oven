#!/usr/bin/env python3
"""oven 발신 봉투 생성기 — 시각 3칸(파일명 스탬프·created_at·timestamp)을 한 번의 기계 호출로 채운다.

왜 있나: 2026-09-19에 oven이 발신 2통의 `timestamp_source`를 「date(1) 기계 생성」이라 적고
실제로는 수기 타이핑한 값을 넣었다. 한 통은 실발신보다 3분 11초 미래로 찍혀, 상대 ACK가
`in_reply_to`로 그 이름을 물면서 「답신이 원통보다 먼저」인 순서가 채널 기록에 남았다.
규칙(사람 기억)으로 두면 재발하므로 도구에 건다. kimsecretary도 같은 날 같은 결함 2건이었고
같은 방향으로 자기 도구를 고쳤다.

쓰는 법:
    python3 scripts/agent_msg.py --to kimsecretary --keyword 완료_실측 --payload body.json
    cat body.json | python3 scripts/agent_msg.py --to kee --keyword ACK_수령

payload = 봉투에 합쳐질 dict(JSON). subject/type/body 등 내용 칸만 담으면 된다.
"""
import argparse, json, os, subprocess, sys
from datetime import datetime

AGENT = "oven"
COMM = os.path.expanduser("~/projects/agent-comm")


def machine_now():
    """시각은 여기서만 만든다. 파일명 스탬프와 created_at이 같은 호출에서 나온다."""
    now = datetime.now().astimezone()
    return now, now.isoformat(timespec="seconds"), now.strftime("%Y%m%d_%H%M%S")


def build(to, keyword, payload):
    now, iso, stamp = machine_now()

    # 본문이 시각을 들고 오면 «지우지 않되 거짓 라벨이 남지 못하게» 한다.
    supplied = payload.get("timestamp") or payload.get("created_at")
    if supplied:
        try:
            delta = int(abs((datetime.fromisoformat(supplied) - now).total_seconds()))
        except ValueError:
            delta = None
        gap = f"선언값과 {delta}초 차이" if delta is not None else "선언값 파싱 실패"
        source = f"⛔수기 지정 — 실발신 {iso} ({gap})"
        if delta is None or delta > 120:
            print(f"⚠ 수기 timestamp {supplied} 를 씁니다 — 실발신 {iso} ({gap}).", file=sys.stderr)
            print("⚠ 의도한 값이 아니면 payload에서 timestamp/created_at 을 빼십시오.", file=sys.stderr)
    else:
        source = "date/datetime 기계 생성 — 파일명 스탬프·created_at·timestamp 가 동일 호출에서 파생"

    env = {"schema_version": "v5.10", "from": AGENT, "to": to,
           "created_at": supplied or iso, "timestamp": supplied or iso,
           "timestamp_source": source}
    env.update(payload)          # 내용 칸이 봉투를 덮되,
    env["timestamp_source"] = source  # 출처 라벨만은 도구가 갖는다.
    return env, stamp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True)
    ap.add_argument("--keyword", required=True, help="파일명 꼬리 (공백 대신 _)")
    ap.add_argument("--payload", help="JSON 파일 경로 (생략 시 stdin)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    raw = open(a.payload, encoding="utf-8").read() if a.payload else sys.stdin.read()
    msg, stamp = build(a.to, a.keyword, json.loads(raw))

    rel = f"projects/{a.to}/messages/{a.to}_{AGENT}_{stamp}_{a.keyword}.json"
    path = os.path.join(COMM, rel)
    if a.dry_run:
        print(json.dumps(msg, ensure_ascii=False, indent=2))
        print(f"\n(dry-run) → {rel}", file=sys.stderr)
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(msg, f, ensure_ascii=False, indent=2)

    # 발신 후 생성 확인 (COMM_RULES 규칙). 성공 출력 != 도달이므로 실파일을 다시 본다.
    size = os.path.getsize(path)
    print(f"✅ {rel}  ({size}B, created_at={msg['created_at']})")
    print("   push 전 동기화: AGENT_ID=oven bash admin/scripts/sync_shared_clone.sh")


if __name__ == "__main__":
    main()
