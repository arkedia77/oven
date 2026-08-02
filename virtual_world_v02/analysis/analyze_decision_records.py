"""D-L1 판단기록 1차 분석 — parsed(LLM appraisal) vs fallback(키워드) 판정 차이 정량화.

질문: appraisal 회귀(키워드 fallback 전량)가 실제로 세계에 다른 영향을 줬는가?
방법: decision_records.jsonl의 interpretation_status별 relationships_delta 분포 비교.
"""
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from village import data_caveats  # noqa: E402  기계 캐비엇(kee 지시 2026-08-02)
from collections import Counter, defaultdict

import sys
PATH = sys.argv[1] if len(sys.argv) > 1 else "data/decision_records.jsonl"
KEYS = ("warmth", "trust", "tension", "affection")

recs = []
with open(PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            recs.append(json.loads(line))

print(f"총 레코드: {len(recs)}")
print(f"judgment_type: {Counter(r.get('judgment_type') for r in recs)}")
print(f"interpretation_status: {Counter(r.get('interpretation_status') for r in recs)}")
_days = [r['tick'] for r in recs]
print(f"day 범위: {min(_days)} ~ {max(_days)} (tick 필드=day 근사)")
data_caveats.warn(days=_days, stream=sys.stdout)
print()

# choice 분포 (parsed면 emotional_valence, fallback이면 'keyword_fallback')
print("=== choice 분포 ===")
for status in ("parsed", "fallback"):
    sub = [r for r in recs if r.get("interpretation_status") == status]
    print(f"  {status:9s} n={len(sub):4d}  {dict(Counter(r.get('choice') for r in sub).most_common(6))}")
print()

# relationships_delta 비교
print("=== relationships_delta 비교 (parsed vs fallback) ===")
groups = defaultdict(list)
for r in recs:
    d = (r.get("outcome") or {}).get("relationships_delta") or {}
    groups[r.get("interpretation_status")].append(d)

hdr = f"{'status':10s} {'n':>5s}"
for k in KEYS:
    hdr += f" | {k}: mean/±0아닌비율"
print(hdr)
for status in ("parsed", "fallback"):
    ds = groups.get(status, [])
    if not ds:
        continue
    row = f"{status:10s} {len(ds):5d}"
    for k in KEYS:
        vals = [d.get(k, 0.0) for d in ds]
        nz = sum(1 for v in vals if abs(v) > 1e-9)
        mean = st.mean(vals) if vals else 0.0
        row += f" | {mean:+.4f} / {100*nz/len(vals):4.1f}%"
    print(row)
print()

# 절대 변화폭(부호 무시) — "얼마나 세게 움직이는가"
print("=== |delta| 평균 (변화 강도) ===")
for status in ("parsed", "fallback"):
    ds = groups.get(status, [])
    if not ds:
        continue
    parts = []
    for k in KEYS:
        vals = [abs(d.get(k, 0.0)) for d in ds]
        parts.append(f"{k}={st.mean(vals):.4f}")
    print(f"  {status:9s} n={len(ds):4d}  " + "  ".join(parts))
print()

# 부호 편향 — 키워드 긍정편향 가설 검증 (warmth/trust 양수 비율)
print("=== 부호 편향 (양수 비율, 0 제외) ===")
for status in ("parsed", "fallback"):
    ds = groups.get(status, [])
    if not ds:
        continue
    parts = []
    for k in KEYS:
        vals = [d.get(k, 0.0) for d in ds if abs(d.get(k, 0.0)) > 1e-9]
        if vals:
            pos = sum(1 for v in vals if v > 0)
            parts.append(f"{k}={100*pos/len(vals):5.1f}%(n={len(vals)})")
        else:
            parts.append(f"{k}=  n/a")
    print(f"  {status:9s}  " + "  ".join(parts))
