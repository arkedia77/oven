"""3일 관찰 리포트용 구간별 관계지표 집계.

Day = Tick/24 + 1 (로그 실측 확인)
구간 경계(tick → day):
  ① 고장   : ~13566  → ~Day 565
  ② 슬롯4096·mt1536 : 13567~13568 → Day 566 (2틱, 표본 무의미)
  ③ mt2560 : 13569~14003 → Day 566~583
  ④ A단계  : 14004~     → Day 584~
히스토리는 60일치이므로 창 = Day (maxday-59) ~ maxday.
경계일(Day 566)은 혼재라 제외한다.
"""
import json
import statistics as st

MAXDAY = 615  # 로그 실측 maxDay
H = json.load(open("rh3.json", encoding="utf-8"))
R = json.load(open("rel3.json", encoding="utf-8"))
AX = ("warmth", "trust", "tension", "affection")

n = len(next(iter(H.values()))["warmth"])
days = list(range(MAXDAY - n + 1, MAXDAY + 1))
print(f"history 창: Day {days[0]} ~ {days[-1]} ({n}일), 쌍 {len(H)}")

SEGS = [
    ("① 고장(fallback)", [d for d in days if d <= 565]),
    ("③ mt2560",        [d for d in days if 567 <= d <= 583]),
    ("④ A단계",          [d for d in days if d >= 584]),
]

idx = {d: i for i, d in enumerate(days)}

print("\n=== 구간별 관계지표 평균(전 쌍·전일 평균) ===")
hdr = f"{'구간':16s} {'일수':>4s}"
for a in AX:
    hdr += f" {a:>10s}"
print(hdr)
for name, ds in SEGS:
    if not ds:
        continue
    row = f"{name:16s} {len(ds):4d}"
    for a in AX:
        vals = []
        for pair, h in H.items():
            arr = h[a]
            for d in ds:
                i = idx[d]
                if i < len(arr):
                    vals.append(arr[i])
        row += f" {st.mean(vals):10.4f}"
    print(row)

print("\n=== 구간별 tension 활성도 (0이 아닌 쌍-일 비율) ===")
for name, ds in SEGS:
    if not ds:
        continue
    tot = nz = 0
    for pair, h in H.items():
        arr = h["tension"]
        for d in ds:
            i = idx[d]
            if i < len(arr):
                tot += 1
                if abs(arr[i]) > 1e-9:
                    nz += 1
    print(f"  {name:16s} 비영 {nz}/{tot} = {100*nz/max(1,tot):5.1f}%")

print("\n=== 구간 말일 기준 zero_relations / floor 고정 / Ceiling ===")
for name, ds in SEGS:
    if not ds:
        continue
    last = idx[ds[-1]]
    out = []
    for a in ("warmth", "trust"):
        z = sum(1 for h in H.values() if last < len(h[a]) and h[a][last] == 0.0)
        f15 = sum(1 for h in H.values() if last < len(h[a]) and abs(h[a][last] - 0.15) < 1e-9)
        out.append(f"{a}: zero={z} floor0.15={f15}")
    ceil = sum(1 for h in H.values() for a in AX if last < len(h[a]) and h[a][last] >= 0.90)
    print(f"  {name:16s} (Day {ds[-1]})  " + " | ".join(out) + f" | >=0.90 {ceil}쌍-축")

print("\n=== 현재 시점(relationships.json) ===")
for a in AX:
    v = [p.get(a, 0.0) for p in R.values()]
    z = sum(1 for x in v if x == 0.0)
    f15 = sum(1 for x in v if abs(x - 0.15) < 1e-9)
    print(f"  {a:10s} mean={st.mean(v):.4f} max={max(v):.4f} zero={z} floor0.15={f15} >=0.90={sum(1 for x in v if x>=0.90)}")
