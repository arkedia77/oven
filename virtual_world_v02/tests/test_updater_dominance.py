"""Updater Dominance Test — 키워드 매칭이 얼마나 상태 변화를 지배하는지 정량화

3소스 삼각검증 보고서 P0 권고:
  "같은 텍스트에 다른 state 투입 시 delta 동일 = updater 지배 확정"
  "paraphrase/반어/부정문으로 키워드 취약성 정량화"
"""
import copy
import json
from pathlib import Path


# ── 키워드 사전 (conversation.py에서 추출) ──────────────────
POSITIVE_WORDS = ["도움", "고맙", "신뢰", "좋아", "동맹", "따뜻", "공감",
                  "타협", "양보", "이해", "인정", "존중"]
NEGATIVE_WORDS = ["실망", "불신", "짜증", "방해", "거짓", "배신", "분노", "의심"]
CONFLICT_WORDS = ["충돌", "반박", "거부", "갈등", "대립", "논쟁"]
AFFECTION_WORDS = ["사랑", "애정", "설레", "끌리", "그리움", "보고싶", "심장", "두근",
                   "포옹", "가슴", "영혼", "동반자", "유대", "특별", "소중"]
BELIEF_SHIFT_WORDS = ["생각해보니", "일리가", "인정할", "양보",
                      "바꿔야", "다시 생각", "틀렸", "맞는 말"]
GOAL_PROGRESS_WORDS = ["진전", "성공", "달성", "합의", "동의", "승인", "도움"]
GOAL_SETBACK_WORDS = ["실패", "거부", "좌절", "불가", "포기", "방해"]
NEED_CONFLICT_WORDS = ["분노", "짜증", "방해", "거부", "대립", "모독", "위협"]
NEED_AFFECTION_WORDS = ["사랑", "애정", "따뜻", "포옹", "보고싶", "그리", "설레"]


def make_rel(warmth=0.5, trust=0.5, tension=0.3, affection=0.0,
             interaction_count=5, **kw):
    rel = {
        "warmth": warmth, "trust": trust, "tension": tension,
        "affection": affection, "salience": 0.3,
        "interaction_count": interaction_count,
        "last_interaction_day": 0, "consecutive_conflicts": 0,
        "fatigue_cooldown": 0,
    }
    rel.update(kw)
    return rel


def apply_keyword_update(rel: dict, reflection: str, village_avg_tension=0.4):
    """conversation.py _adjust_relationship 로직 복제"""
    positive = any(w in reflection for w in POSITIVE_WORDS)
    negative = any(w in reflection for w in NEGATIVE_WORDS)
    conflict = any(w in reflection for w in CONFLICT_WORDS)
    affectionate = any(w in reflection for w in AFFECTION_WORDS)

    # homeostasis multipliers
    if village_avg_tension > 0.5:
        overshoot = min(1.0, (village_avg_tension - 0.5) / 0.3)
        inc_mult, dec_mult = 1.0 - overshoot * 0.5, 1.0 + overshoot * 0.5
    elif village_avg_tension < 0.3:
        undershoot = min(1.0, (0.3 - village_avg_tension) / 0.2)
        inc_mult, dec_mult = 1.0 + undershoot * 0.5, 1.0 - undershoot * 0.5
    else:
        inc_mult, dec_mult = 1.0, 1.0

    interaction_count = rel.get("interaction_count", 0)
    dampening = 0.5 if interaction_count > 20 else 1.0

    if positive:
        rel["warmth"] = min(1.0, rel["warmth"] + 0.04 * dampening)
        rel["trust"] = min(1.0, rel["trust"] + 0.03 * dampening)
    if negative:
        rel["warmth"] = max(0.0, rel["warmth"] - 0.04 * dampening)
        rel["trust"] = max(0.0, rel["trust"] - 0.04 * dampening)

    if conflict:
        rel["tension"] = min(1.0, rel["tension"] + 0.05 * inc_mult * dampening)
    else:
        rel["tension"] = max(0.0, rel["tension"] - 0.03 * dec_mult)

    tension = rel.get("tension", 0.3)
    tension_dampen = max(0.1, 1.0 - tension)

    if affectionate:
        rel["affection"] = min(1.0, rel["affection"] + 0.08 * tension_dampen * dampening)
    elif positive:
        rel["affection"] = min(1.0, rel["affection"] + 0.02 * tension_dampen * dampening)
    if negative or conflict:
        rel["affection"] = max(0.0, rel["affection"] - 0.02)

    return {"positive": positive, "negative": negative,
            "conflict": conflict, "affectionate": affectionate}


def compute_delta(before: dict, after: dict) -> dict:
    return {k: round(after[k] - before[k], 6)
            for k in ("warmth", "trust", "tension", "affection")}


# ═══════════════════════════════════════════════════════════
# TEST 1: State Independence — 같은 텍스트, 다른 초기 상태
# ═══════════════════════════════════════════════════════════
def test_state_independence():
    print("=" * 70)
    print("TEST 1: State Independence (같은 텍스트 + 다른 초기 상태 → delta 동일?)")
    print("=" * 70)

    test_text = "오늘 대화에서 도움을 많이 받았다. 신뢰가 깊어진 느낌."

    states = [
        ("적대적 관계", make_rel(warmth=0.1, trust=0.1, tension=0.9, affection=0.0)),
        ("중립 관계",   make_rel(warmth=0.5, trust=0.5, tension=0.3, affection=0.3)),
        ("친밀한 관계", make_rel(warmth=0.9, trust=0.9, tension=0.1, affection=0.8)),
    ]

    deltas = []
    for label, rel in states:
        before = copy.deepcopy(rel)
        apply_keyword_update(rel, test_text)
        delta = compute_delta(before, rel)
        deltas.append(delta)
        print(f"\n  [{label}]")
        print(f"    before: w={before['warmth']:.2f} t={before['trust']:.2f} "
              f"ten={before['tension']:.2f} aff={before['affection']:.2f}")
        print(f"    after:  w={rel['warmth']:.2f} t={rel['trust']:.2f} "
              f"ten={rel['tension']:.2f} aff={rel['affection']:.2f}")
        print(f"    delta:  {delta}")

    # affection은 tension_dampen 때문에 다를 수 있음
    warmth_same = len(set(d["warmth"] for d in deltas)) == 1
    trust_same = len(set(d["trust"] for d in deltas)) == 1
    tension_same = len(set(d["tension"] for d in deltas)) == 1
    affection_same = len(set(d["affection"] for d in deltas)) == 1

    print(f"\n  결과:")
    print(f"    warmth  delta 동일? {'✅ YES — state 무시' if warmth_same else '❌ NO — state 참조'}")
    print(f"    trust   delta 동일? {'✅ YES — state 무시' if trust_same else '❌ NO — state 참조'}")
    print(f"    tension delta 동일? {'✅ YES — state 무시' if tension_same else '❌ NO — state 참조'}")
    print(f"    affection delta 동일? {'✅ YES — state 무시' if affection_same else '⚠️ NO — tension_dampen 간접 참조'}")

    dominance_score = sum([warmth_same, trust_same, tension_same]) / 3
    print(f"\n  ▶ Updater Dominance Score (core 3변수): {dominance_score:.0%}")
    print(f"    1.0 = 완전히 키워드 지배, 0.0 = state가 delta를 좌우")

    return {"dominance_score": dominance_score, "deltas": deltas}


# ═══════════════════════════════════════════════════════════
# TEST 2: Keyword Vulnerability — 의미는 같은데 키워드 유무로 결과 다름
# ═══════════════════════════════════════════════════════════
def test_keyword_vulnerability():
    print("\n" + "=" * 70)
    print("TEST 2: Keyword Vulnerability (의미 동일, 키워드 유무로 결과 분기)")
    print("=" * 70)

    pairs = [
        {
            "label": "긍정 표현 — 키워드 有 vs 無",
            "with_kw": "정말 도움이 됐고, 고맙다는 말밖에 할 수 없다.",
            "without_kw": "덕분에 한결 나아졌고, 진심으로 감사하는 마음이 든다.",
            "expected_same": True,
        },
        {
            "label": "부정문 함정 — '도움이 안 됐다'",
            "with_kw": "솔직히 도움이 전혀 안 됐고 신뢰가 깨졌다.",
            "without_kw": "아무런 쓸모가 없었고 믿을 수 없게 됐다.",
            "expected_same": True,
            "note": "키워드 '도움','신뢰' 포함 → 긍정으로 오판 예상",
        },
        {
            "label": "반어 함정 — '고맙기도 하지'",
            "with_kw": "정말 고맙기도 하지, 내 뒤통수를 치다니.",
            "without_kw": "뒤통수를 맞은 기분이다. 두 번 다시 안 만난다.",
            "expected_same": True,
            "note": "키워드 '고맙' 포함 → 긍정으로 오판 예상",
        },
        {
            "label": "혼합 감정 — 갈등 속 애정",
            "with_kw": "갈등이 심했지만, 그래도 이 사람이 소중하다는 걸 느꼈다.",
            "without_kw": "의견 차이가 컸지만, 여전히 이 관계를 지키고 싶다.",
            "expected_same": True,
        },
        {
            "label": "목표 부정문 — '성공하지 못했다'",
            "with_kw": "결국 성공하지 못했고 합의도 불가능했다.",
            "without_kw": "아무것도 이루지 못했고 타결도 어려웠다.",
            "expected_same": True,
            "note": "키워드 '성공','합의' → 진전으로 오판 예상",
        },
    ]

    results = []
    for pair in pairs:
        print(f"\n  [{pair['label']}]")
        if "note" in pair:
            print(f"    ⚠️ {pair['note']}")

        rel_kw = make_rel()
        rel_no = make_rel()
        before = copy.deepcopy(rel_kw)

        flags_kw = apply_keyword_update(rel_kw, pair["with_kw"])
        flags_no = apply_keyword_update(rel_no, pair["without_kw"])

        delta_kw = compute_delta(before, rel_kw)
        delta_no = compute_delta(before, rel_no)

        same = delta_kw == delta_no
        print(f"    키워드有: {pair['with_kw'][:50]}...")
        print(f"      flags: {flags_kw}")
        print(f"      delta: {delta_kw}")
        print(f"    키워드無: {pair['without_kw'][:50]}...")
        print(f"      flags: {flags_no}")
        print(f"      delta: {delta_no}")
        print(f"    의미 동일인데 결과 동일? {'✅ OK' if same else '❌ DIVERGED — 키워드 취약'}")

        results.append({
            "label": pair["label"],
            "same_result": same,
            "delta_with_kw": delta_kw,
            "delta_without_kw": delta_no,
            "flags_with_kw": flags_kw,
            "flags_without_kw": flags_no,
        })

    vulnerable = sum(1 for r in results if not r["same_result"])
    print(f"\n  ▶ 키워드 취약 케이스: {vulnerable}/{len(results)}")
    print(f"    취약률: {vulnerable/len(results):.0%}")

    return results


# ═══════════════════════════════════════════════════════════
# TEST 3: Need Updater 동일 분석
# ═══════════════════════════════════════════════════════════
def test_need_updater():
    print("\n" + "=" * 70)
    print("TEST 3: Need Updater — fulfill_needs_from_conversation 키워드 분석")
    print("=" * 70)

    cases = [
        {
            "label": "긍정 대화 + 분노 키워드 부정문",
            "reflection": "분노를 참으며 이야기했더니 결국 좋은 결론이 났다.",
            "positive": True,
            "note": "'분노' 포함 → security -0.03 (실제로는 분노를 참은 것인데)",
        },
        {
            "label": "애정 표현 부정문",
            "reflection": "사랑 같은 건 느끼지 못했다. 그냥 동료일 뿐이다.",
            "positive": True,
            "note": "'사랑' 포함 → affection +0.06 (실제로는 애정 부정인데)",
        },
        {
            "label": "따뜻함 비유",
            "reflection": "따뜻한 커피를 마시며 이야기했다. 별 내용은 없었다.",
            "positive": True,
            "note": "'따뜻' 포함 → affection +0.06 (커피가 따뜻한 것인데)",
        },
    ]

    for case in cases:
        print(f"\n  [{case['label']}]")
        print(f"    텍스트: {case['reflection']}")
        print(f"    ⚠️ {case['note']}")

        has_conflict = any(w in case["reflection"] for w in NEED_CONFLICT_WORDS)
        has_affection = any(w in case["reflection"] for w in NEED_AFFECTION_WORDS)
        print(f"    갈등 키워드 탐지: {has_conflict}")
        print(f"    애정 키워드 탐지: {has_affection}")
        print(f"    → 오판 여부: {'❌ 오판' if (has_conflict or has_affection) else '✅ 정상'}")


# ═══════════════════════════════════════════════════════════
# TEST 4: 전체 키워드 커버리지
# ═══════════════════════════════════════════════════════════
def test_keyword_coverage():
    print("\n" + "=" * 70)
    print("TEST 4: 키워드 커버리지 — 총 몇 개 단어가 시스템 전체를 결정하는가")
    print("=" * 70)

    all_kw = set()
    categories = {
        "관계 긍정": POSITIVE_WORDS,
        "관계 부정": NEGATIVE_WORDS,
        "갈등": CONFLICT_WORDS,
        "애정": AFFECTION_WORDS,
        "신념 이동": BELIEF_SHIFT_WORDS,
        "목표 진전": GOAL_PROGRESS_WORDS,
        "목표 후퇴": GOAL_SETBACK_WORDS,
        "욕구 갈등": NEED_CONFLICT_WORDS,
        "욕구 애정": NEED_AFFECTION_WORDS,
    }

    for cat, words in categories.items():
        all_kw.update(words)
        print(f"  {cat:12s}: {len(words):2d}개 — {', '.join(words)}")

    # 중복 키워드 (여러 카테고리에 걸침)
    from collections import Counter
    word_counts = Counter()
    for words in categories.values():
        for w in words:
            word_counts[w] += 1
    duplicates = {w: c for w, c in word_counts.items() if c > 1}

    print(f"\n  총 고유 키워드: {len(all_kw)}개")
    print(f"  중복 키워드 (여러 카테고리): {len(duplicates)}개")
    for w, c in sorted(duplicates.items(), key=lambda x: -x[1]):
        cats = [cat for cat, words in categories.items() if w in words]
        print(f"    '{w}' → {c}개 카테고리: {', '.join(cats)}")

    print(f"\n  ▶ {len(all_kw)}개 한국어 단어가 시스템 전체의 상태 변화를 결정")
    print(f"    needs(6변수) + beliefs(5변수) + relationship(4변수) + goals(1변수)")
    print(f"    = 16개 수치 변수의 변화가 {len(all_kw)}개 키워드 존재 여부에 의존")

    return {"total_unique": len(all_kw), "duplicates": duplicates}


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("🔬 Harmonicity Updater Dominance Test")
    print("   목적: 키워드 매칭이 시뮬레이션 상태 변화를 얼마나 지배하는지 정량화\n")

    r1 = test_state_independence()
    r2 = test_keyword_vulnerability()
    test_need_updater()
    r4 = test_keyword_coverage()

    print("\n" + "=" * 70)
    print("📊 종합 결과")
    print("=" * 70)
    print(f"  State Independence (updater 지배도): {r1['dominance_score']:.0%}")
    vulnerable = sum(1 for r in r2 if not r["same_result"])
    print(f"  Keyword Vulnerability (취약률):      {vulnerable}/{len(r2)} ({vulnerable/len(r2):.0%})")
    print(f"  Total Keywords (시스템 전체):         {r4['total_unique']}개 → 16개 수치 변수 결정")
    print(f"  Cross-category Duplicates:            {len(r4['duplicates'])}개 (다중 해석 위험)")

    print(f"\n  ▶ 결론:")
    if r1["dominance_score"] >= 0.66:
        print(f"    키워드 updater가 core 변수를 지배합니다.")
        print(f"    관계 warmth/trust/tension은 초기 state와 무관하게 동일한 delta 적용.")
    print(f"    의미적으로 동일한 텍스트가 키워드 유무만으로 {vulnerable}건 분기.")
    print(f"    → P0 교체(LLM 구조화출력) 정당성 확인.")


if __name__ == "__main__":
    main()
