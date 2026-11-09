"""ComfyUI 교체 전후 /object_info 대조 (oven 2026-11-09 · A-177 자기 발제 ⑥).

왜: 11-09 leowin 0.42→0.44.2 교체에서 «노드 21종 있음»은 통과했지만
TextEncodeMOSSImageEdit 에 required 칸 image_strength 가 새로 생겨 옛 API 그래프가 400 으로 거부됨.
ComfyUI 는 API 그래프에서 빠진 required 칸을 기본값으로 채우지 않는다(execution.py validate_inputs
→ "required_input_missing", 0.44.2 실측). 노드 «존재»만 보면 이 구멍을 놓친다.

받기:  curl -s http://<host>:<port>/object_info > before.json   (교체 전 · 교체 후 각각)
쓰기:  python3 -I comfy_upgrade_diff.py before.json after.json [--nodes nodes.txt] [--json]
       nodes.txt = 꼭 있어야 할 노드 이름(공백·줄바꿈 구분). 없으면 before 의 모든 노드를 대상으로 봄.
종료 코드: 0 = 위험 0 · 1 = 위험 있음(지정 노드 없음 / 새 required 칸 / required 칸 사라짐·타입 변화) · 2 = 입력 오류
"""
import argparse
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict) or not d:
        sys.exit(f"{path}: object_info 가 아님(빈 값이거나 dict 아님)")
    return d


def inputs(node):
    """{칸이름: (구분 required/optional, 타입 문자열 또는 선택지 목록)}. hidden 은 그래프가 안 보내므로 뺌."""
    out = {}
    for cat in ("required", "optional"):
        for name, spec in (node.get("input", {}).get(cat) or {}).items():
            t = spec[0] if isinstance(spec, list) and spec else spec
            out[name] = (cat, t)
    return out


def type_label(t):
    if isinstance(t, list):  # 콤보(선택지) — 선택지 변화는 타입 변화로 안 봄
        return "COMBO"
    return str(t)


def default_of(node, name):
    for cat in ("required", "optional"):
        spec = (node.get("input", {}).get(cat) or {}).get(name)
        if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict):
            return spec[1].get("default")
    return None


def diff_node(name, b, a):
    """한 노드의 입력 칸 변화 → (위험 목록, 참고 목록)."""
    risk, note = [], []
    bi, ai = inputs(b), inputs(a)
    for k in sorted(set(bi) | set(ai)):
        if k not in bi:
            cat = ai[k][0]
            d = default_of(a, k)
            if cat == "required":
                risk.append(f"새 required 칸 {k} ({type_label(ai[k][1])}, 기본 {d!r}) — 이 칸 없는 옛 API 그래프는 400")
            else:
                note.append(f"새 optional 칸 {k} ({type_label(ai[k][1])})")
        elif k not in ai:
            if bi[k][0] == "required":
                risk.append(f"required 칸 {k} 사라짐 — 이 칸을 보내는 그래프는 확인 필요")
            else:
                note.append(f"optional 칸 {k} 사라짐")
        else:
            (bc, bt), (ac, at) = bi[k], ai[k]
            if type_label(bt) != type_label(at):
                risk.append(f"칸 {k} 타입 {type_label(bt)} → {type_label(at)}")
            if bc != ac:
                if ac == "required":
                    risk.append(f"칸 {k} optional → required")
                else:
                    note.append(f"칸 {k} required → optional (옛 그래프 그대로 통과)")
            if isinstance(bt, list) and isinstance(at, list):
                gone = [x for x in bt if x not in at]
                if gone:
                    risk.append(f"칸 {k} 선택지 사라짐 {gone[:5]}{' …' if len(gone) > 5 else ''}")
    if [o for o in b.get("output", [])] != [o for o in a.get("output", [])]:
        risk.append(f"출력 {b.get('output')} → {a.get('output')} — 연결 번호 확인 필요")
    return risk, note


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 교체 전후 /object_info 대조")
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--nodes", help="꼭 있어야 할 노드 이름 파일")
    ap.add_argument("--json", action="store_true", help="결과를 JSON 으로")
    o = ap.parse_args()
    b, a = load(o.before), load(o.after)
    if o.nodes:
        with open(o.nodes, encoding="utf-8") as f:
            want = f.read().split()
    else:
        want = sorted(b)
    res = {
        "before_count": len(b), "after_count": len(a),
        "watched": len(want),
        "missing_after": [n for n in want if n not in a],
        "missing_before": [n for n in want if n not in b],
        "removed": sorted(set(b) - set(a)),
        "added_count": len(set(a) - set(b)),
        "changed": {},
    }
    for n in want:
        if n in a and n in b:
            risk, note = diff_node(n, b[n], a[n])
            if risk or note:
                res["changed"][n] = {"risk": risk, "note": note}
    n_risk = len(res["missing_after"]) + sum(len(v["risk"]) for v in res["changed"].values())
    res["risk_total"] = n_risk
    if o.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"노드 수 {res['before_count']} → {res['after_count']} · 새 노드 {res['added_count']} · 사라진 노드 {len(res['removed'])}")
        if res["removed"]:
            print("  사라진 노드:", ", ".join(res["removed"][:30]) + (" …" if len(res["removed"]) > 30 else ""))
        print(f"대상 {res['watched']}종 중 교체 후 없음 {len(res['missing_after'])}: {res['missing_after']}")
        if res["missing_before"]:
            print(f"  (교체 전에도 없던 대상 {res['missing_before']} — 목록 확인)")
        for n, v in res["changed"].items():
            print(f"[{'위험' if v['risk'] else '참고'}] {n}")
            for x in v["risk"]:
                print("   ⚠", x)
            for x in v["note"]:
                print("   ·", x)
        print(f"위험 합계 {n_risk}" + (" — 그래프 고친 뒤 실생성으로 확인" if n_risk else " — 입력 칸 기준 문제 없음(실생성 1건은 따로)"))
    sys.exit(1 if n_risk else 0)


if __name__ == "__main__":
    main()
