"""ComfyUI 교체 전후 /object_info 대조 (oven 2026-11-09 · A-177 자기 발제 ⑥).

왜: 11-09 leowin 0.42→0.44.2 교체에서 «노드 21종 있음»은 통과했지만
TextEncodeMOSSImageEdit 에 required 칸 image_strength 가 새로 생겨 옛 API 그래프가 400 으로 거부됨.
ComfyUI 는 API 그래프에서 빠진 required 칸을 기본값으로 채우지 않는다(execution.py validate_inputs
→ "required_input_missing", 0.44.2 실측). 노드 «존재»만 보면 이 구멍을 놓친다.

받기:  curl -s http://<host>:<port>/object_info > before.json   (교체 전 · 교체 후 각각)
쓰기:  python3 -I comfy_upgrade_diff.py before.json after.json [--nodes nodes.txt] [--json]
       nodes.txt = 꼭 있어야 할 노드 이름(공백·줄바꿈 구분). 없으면 before 의 모든 노드를 대상으로 봄.
종료 코드: 0 = 위험 0 · 1 = 위험 있음(지정 노드 없음 / 새 required 칸 / 타입 변화 / 선택지 사라짐 / min·max 좁아짐) · 2 = 입력 오류

판정 기준(11-13 스터디 · leowin 0.44.2 execution.py validate_inputs 대조, reklcli:~/oven/notes/study_comfy_input_validation.md):
  빠진 required 칸 → 400 required_input_missing (기본값 안 채움 · `advanced` 표시 칸도 똑같이 required)
  빠진 optional 칸 → 통과(노드 함수의 파이썬 기본값 · object_info 의 default 아님)
  모르는 칸(사라진 칸) → 검사 없이 조용히 버려짐(400 아님) → 위험 아님·참고로 표시, 동작 바뀜은 실생성으로 확인
  콤보 값이 선택지 밖 → 400 value_not_in_list (콤보 표기 2가지: [[선택지…], {..}] 와 V3 ["COMBO", {"options": [...]}])
  min 미만 / max 초과 → 400 value_smaller_than_min / value_bigger_than_max
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
    if isinstance(t, list):  # 옛 표기 콤보 = V3 "COMBO" 와 같은 타입으로 봄(선택지는 따로 비교)
        return "COMBO"
    return str(t)


def extra_of(node, name):
    for cat in ("required", "optional"):
        spec = (node.get("input", {}).get(cat) or {}).get(name)
        if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict):
            return spec[1]
    return {}


def options_of(t, extra):
    """콤보 선택지. 옛 표기 = 타입 자리에 목록, V3 표기 = "COMBO" + extra["options"]. 콤보 아니면 None."""
    if isinstance(t, list):
        return t
    if t == "COMBO":
        return list(extra.get("options") or [])
    return None


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
                note.append(f"required 칸 {k} 사라짐 — 보내도 조용히 버려짐(400 아님) · 동작 바뀜은 실생성으로 확인")
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
            be, ae = extra_of(b, k), extra_of(a, k)
            bo, ao = options_of(bt, be), options_of(at, ae)
            if bo is not None and ao is not None:
                gone = [x for x in bo if x not in ao]
                if gone:
                    risk.append(f"칸 {k} 선택지 사라짐 {gone[:5]}{' …' if len(gone) > 5 else ''} — 그 값 보내면 400")
            for lim, narrower in (("min", lambda o, n: n > o), ("max", lambda o, n: n < o)):
                if lim in ae and (lim not in be or narrower(be[lim], ae[lim])):
                    risk.append(f"칸 {k} {lim} {be.get(lim)!r} → {ae[lim]!r} — 범위 밖 옛 값은 400")
            if be.get("default") != ae.get("default"):
                note.append(f"칸 {k} 기본값 {be.get('default')!r} → {ae.get('default')!r} (값 보내는 API 그래프엔 영향 없음)")
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
