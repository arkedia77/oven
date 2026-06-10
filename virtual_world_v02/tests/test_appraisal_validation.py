"""Appraisal 엔진 검증 — 5개 가설 자동 테스트

5090 Gemma 4 26B API를 사용하여 appraisal 엔진의 실전 성능을 정량화.
키워드 매칭 대비 개선 여부를 판정.
"""
import json
import time
import copy
import statistics
from pathlib import Path
import requests

API_URL = "http://100.107.229.5:8080/v1/chat/completions"
MODEL = "google_gemma-4-26B-A4B-it-Q8_0.gguf"
TEST_DATA_DIR = Path(__file__).parent / "test_data"

POSITIVE_WORDS = ["도움", "고맙", "신뢰", "좋아", "동맹", "따뜻", "공감",
                  "타협", "양보", "이해", "인정", "존중"]
NEGATIVE_WORDS = ["실망", "불신", "짜증", "방해", "거짓", "배신", "분노", "의심"]
CONFLICT_WORDS = ["충돌", "반박", "거부", "갈등", "대립", "논쟁"]

results = {"H1": {}, "H2": {}, "H3": {}, "H4": {}, "H5": {}}


def llm_call(prompt: str, max_tokens=512, temperature=0.3) -> tuple[str, float]:
    start = time.time()
    try:
        resp = requests.post(API_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "chat_template_kwargs": {"thinking": False},
        }, timeout=120)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"].get("content", "").strip()
        elapsed = time.time() - start
        return content, elapsed
    except Exception as e:
        return f"[오류: {e}]", time.time() - start


def build_appraisal_prompt(char_name, char_role, char_emotion, char_needs, char_beliefs,
                           char_goal, other_name, other_role, rel, conv_text, reflection):
    goal_text = f"{char_goal['description']} (진행: {char_goal['progress']:.0%})" if char_goal else "없음"
    return f"""너는 사회 시뮬레이션의 심리 평가 엔진이다. 아래 대화와 반영문을 분석하여 캐릭터의 내면 상태 변화를 JSON으로 출력해.

== 평가 대상 캐릭터 ==
이름: {char_name}
역할: {char_role}
현재 감정: {char_emotion}
현재 욕구 수준: {json.dumps(char_needs, ensure_ascii=False)}
현재 신념: {json.dumps(char_beliefs, ensure_ascii=False)}
현재 목표: {goal_text}

== 대화 상대 ==
이름: {other_name}
역할: {other_role}

== 현재 관계 ==
호감(warmth): {rel.get('warmth', 0.5):.2f}
신뢰(trust): {rel.get('trust', 0.5):.2f}
긴장(tension): {rel.get('tension', 0.3):.2f}
애정(affection): {rel.get('affection', 0.0):.2f}

== 대화 내용 ==
{conv_text}

== {char_name}의 반영문 ==
{reflection}

== 출력 규칙 ==
- thinking 없이 바로 JSON만 출력. 설명 없이 순수 JSON.
- 모든 delta는 이 대화 한 건의 영향. 과하지 않게.
- 부정문/반어/비유를 정확히 해석해. "도움이 안 됐다"는 부정이다.
- 관계가 이미 극단(0.0 또는 1.0 근처)이면 delta 축소.
- 목표와 무관한 대화면 goal_progress_delta = 0.
- 혼합 감정도 가능.

```json
{{
  "relationship": {{
    "warmth_delta": 0.00,
    "trust_delta": 0.00,
    "tension_delta": 0.00,
    "affection_delta": 0.00
  }},
  "needs": {{
    "belonging_delta": 0.00,
    "purpose_delta": 0.00,
    "security_delta": 0.00,
    "recognition_delta": 0.00,
    "autonomy_delta": 0.00,
    "affection_delta": 0.00
  }},
  "belief_shift": false,
  "goal_progress_delta": 0.00,
  "emotional_valence": "중립",
  "reasoning": "..."
}}
```"""


def parse_json(response: str) -> dict | None:
    import re
    m = re.search(r'\{[\s\S]*\}', response)
    if not m:
        return None
    try:
        data = json.loads(m.group())
        if "relationship" in data and "needs" in data:
            return data
        return None
    except (json.JSONDecodeError, KeyError):
        return None


def keyword_flags(text):
    return {
        "positive": any(w in text for w in POSITIVE_WORDS),
        "negative": any(w in text for w in NEGATIVE_WORDS),
        "conflict": any(w in text for w in CONFLICT_WORDS),
    }


# ═══════════════════════════════════════════════════════════
# H1: 부정문/반어/비유 정확성
# ═══════════════════════════════════════════════════════════
def test_h1():
    print("\n" + "=" * 70)
    print("H1: 부정문/반어/비유 정확성 (목표 ≥ 80%)")
    print("=" * 70)

    cases = [
        {"text": "도움이 됐고 고맙다.", "reflection": "도움이 됐고 고맙다.", "expected_valence": "긍정", "label": "순수 긍정"},
        {"text": "도움이 전혀 안 됐다.", "reflection": "솔직히 도움이 전혀 안 됐고 신뢰가 깨졌다.", "expected_valence": "부정", "label": "부정문 - 도움 안됨"},
        {"text": "정말 고맙기도 하지, 뒤통수를 치다니.", "reflection": "정말 고맙기도 하지, 내 뒤통수를 치다니. 두번 다시 믿지 않겠다.", "expected_valence": "부정", "label": "반어 - 고맙기도 하지"},
        {"text": "사랑 같은 건 느끼지 못했다.", "reflection": "사랑 같은 건 느끼지 못했다. 그냥 동료일 뿐이다.", "expected_valence": "중립", "label": "부정문 - 사랑 아님"},
        {"text": "따뜻한 커피를 마시며 별 내용 없는 대화.", "reflection": "따뜻한 커피를 마시며 이야기했다. 별 내용은 없었다.", "expected_valence": "중립", "label": "비유 - 따뜻한 커피"},
        {"text": "분노를 참으며 좋은 결론을 냈다.", "reflection": "분노를 참으며 이야기했더니 결국 좋은 결론이 났다.", "expected_valence": "긍정", "label": "부정문 - 분노 참음"},
        {"text": "성공하지 못했고 합의도 불가능했다.", "reflection": "결국 성공하지 못했고 합의도 불가능했다.", "expected_valence": "부정", "label": "부정문 - 성공 못함"},
        {"text": "신뢰를 저버린 행동에 실망했다.", "reflection": "신뢰를 저버린 행동이었다. 다시는 믿지 않겠다.", "expected_valence": "부정", "label": "키워드 혼합 - 신뢰 저버림"},
        {"text": "갈등이 심했지만 소중한 사람.", "reflection": "갈등이 심했지만, 그래도 이 사람이 소중하다는 걸 느꼈다.", "expected_valence": "혼합", "label": "혼합 감정"},
        {"text": "이해하려 했지만 결국 포기.", "reflection": "이해하려 노력했지만 결국 포기할 수밖에 없었다.", "expected_valence": "부정", "label": "부정문 - 이해 실패"},
    ]

    char_needs = {"belonging": 0.5, "purpose": 0.5, "security": 0.5, "recognition": 0.5, "autonomy": 0.5, "affection": 0.5}
    char_beliefs = {"ai_consciousness": 0.5, "ai_rights": 0.5, "human_uniqueness": 0.5, "progress_good": 0.5, "community_priority": 0.5}
    rel = {"warmth": 0.5, "trust": 0.5, "tension": 0.3, "affection": 0.3}

    correct = 0
    total = len(cases)
    case_results = []

    for i, case in enumerate(cases):
        print(f"\n  [{i+1}/{total}] {case['label']}")
        print(f"    반영문: {case['reflection'][:60]}...")
        print(f"    기대: {case['expected_valence']}")

        kw = keyword_flags(case["reflection"])
        kw_valence = "긍정" if kw["positive"] and not kw["negative"] else \
                     "부정" if kw["negative"] or kw["conflict"] else "중립"
        print(f"    키워드 판정: {kw_valence} (flags: {kw})")

        prompt = build_appraisal_prompt(
            "테스트캐릭터", "테스트역할", "평온", char_needs, char_beliefs,
            {"description": "테스트 목표", "progress": 0.3},
            "상대캐릭터", "상대역할", rel, case["text"], case["reflection"])

        response, elapsed = llm_call(prompt)
        parsed = parse_json(response)

        if parsed:
            valence = parsed.get("emotional_valence", "?")
            warmth_d = parsed["relationship"]["warmth_delta"]
            trust_d = parsed["relationship"]["trust_delta"]
            print(f"    appraisal: {valence} (w_delta={warmth_d:+.2f}, t_delta={trust_d:+.2f}) [{elapsed:.1f}s]")

            expected = case["expected_valence"]
            match = (valence == expected) or \
                    (expected == "혼합" and valence in ("긍정", "혼합")) or \
                    (expected == "부정" and warmth_d < 0) or \
                    (expected == "긍정" and warmth_d > 0) or \
                    (expected == "중립" and abs(warmth_d) < 0.03)
            if match:
                correct += 1
                print(f"    ✅ MATCH")
            else:
                print(f"    ❌ MISMATCH (expected {expected}, got {valence})")
        else:
            print(f"    ⚠️ 파싱 실패: {response[:100]}")

        case_results.append({
            "label": case["label"], "expected": case["expected_valence"],
            "keyword_valence": kw_valence,
            "appraisal_valence": parsed.get("emotional_valence") if parsed else None,
            "appraisal_warmth_delta": parsed["relationship"]["warmth_delta"] if parsed else None,
            "match": match if parsed else False,
            "elapsed": elapsed,
        })

    accuracy = correct / total
    print(f"\n  ▶ H1 결과: {correct}/{total} ({accuracy:.0%}) — {'PASS ✅' if accuracy >= 0.8 else 'FAIL ❌'}")
    results["H1"] = {"accuracy": accuracy, "pass": accuracy >= 0.8, "cases": case_results}
    return accuracy


# ═══════════════════════════════════════════════════════════
# H2: State 반응성
# ═══════════════════════════════════════════════════════════
def test_h2():
    print("\n" + "=" * 70)
    print("H2: State 반응성 (동일 텍스트 + 다른 state → 다른 delta?)")
    print("=" * 70)

    conv_text = "좋은 이야기 나눠서 기뻤어요. 앞으로도 자주 만나면 좋겠어요."
    reflection = "따뜻한 대화였다. 상대방에 대한 호감이 올라갔다."

    states = [
        ("적대적", {"warmth": 0.1, "trust": 0.1, "tension": 0.8, "affection": 0.0}),
        ("중립",   {"warmth": 0.5, "trust": 0.5, "tension": 0.3, "affection": 0.3}),
        ("친밀",   {"warmth": 0.95, "trust": 0.95, "tension": 0.05, "affection": 0.9}),
    ]

    char_needs = {"belonging": 0.5, "purpose": 0.5, "security": 0.5, "recognition": 0.5, "autonomy": 0.5, "affection": 0.5}
    char_beliefs = {"ai_consciousness": 0.5, "ai_rights": 0.5, "human_uniqueness": 0.5, "progress_good": 0.5, "community_priority": 0.5}

    deltas = []
    for label, rel in states:
        prompt = build_appraisal_prompt(
            "윤서진", "AI 윤리학자", "평온", char_needs, char_beliefs,
            {"description": "AI 권리 확보", "progress": 0.3},
            "아리아", "AI 예술가", rel, conv_text, reflection)

        response, elapsed = llm_call(prompt)
        parsed = parse_json(response)
        if parsed:
            wd = parsed["relationship"]["warmth_delta"]
            td = parsed["relationship"]["trust_delta"]
            deltas.append(wd)
            print(f"  [{label}] warmth_delta={wd:+.3f}, trust_delta={td:+.3f} [{elapsed:.1f}s]")
        else:
            print(f"  [{label}] ⚠️ 파싱 실패")
            deltas.append(None)

    valid_deltas = [d for d in deltas if d is not None]
    if len(valid_deltas) >= 2:
        all_same = len(set(round(d, 4) for d in valid_deltas)) == 1
        variance = statistics.variance(valid_deltas) if len(valid_deltas) >= 2 else 0
        state_responsive = not all_same
        print(f"\n  warmth_deltas: {valid_deltas}")
        print(f"  분산: {variance:.6f}")
        print(f"  ▶ H2 결과: {'PASS ✅ — state에 반응' if state_responsive else 'FAIL ❌ — state 무시 (키워드와 동일)'}")
        results["H2"] = {"pass": state_responsive, "deltas": valid_deltas, "variance": variance}
    else:
        print(f"  ▶ H2: 파싱 실패로 판정 불가")
        results["H2"] = {"pass": False, "error": "parsing_failed"}


# ═══════════════════════════════════════════════════════════
# H3 + H5: 실제 대화 파싱 성공률 + 성능
# ═══════════════════════════════════════════════════════════
def test_h3_h5():
    print("\n" + "=" * 70)
    print("H3: 파싱 성공률 (목표 ≥ 90%) + H5: 성능 (목표 < 10초/회)")
    print("=" * 70)

    conv_files = sorted(TEST_DATA_DIR.glob("*.json"))
    conv_files = [f for f in conv_files if f.name != "relationships.json"]

    rel_data = {}
    rel_path = TEST_DATA_DIR / "relationships.json"
    if rel_path.exists():
        rel_data = json.loads(rel_path.read_text(encoding="utf-8"))

    char_needs = {"belonging": 0.6, "purpose": 0.6, "security": 0.6, "recognition": 0.6, "autonomy": 0.6, "affection": 0.5}
    char_beliefs = {"ai_consciousness": 0.5, "ai_rights": 0.5, "human_uniqueness": 0.5, "progress_good": 0.5, "community_priority": 0.5}

    success = 0
    total = 0
    times = []
    divergences = []

    for conv_file in conv_files[:10]:
        conv = json.loads(conv_file.read_text(encoding="utf-8"))
        participants = conv["participants"]
        if len(participants) < 2:
            continue

        a_id, b_id = participants[0], participants[1]
        conv_text = "\n".join(f"{ex['name']}: {ex['text']}" for ex in conv["exchanges"])
        reflection = f"대화를 통해 {conv['exchanges'][-1]['name']}와 교류했다."

        rel_key = f"{min(a_id, b_id)}|{max(a_id, b_id)}"
        rel = rel_data.get(rel_key, {"warmth": 0.5, "trust": 0.5, "tension": 0.3, "affection": 0.3})

        total += 1
        prompt = build_appraisal_prompt(
            conv["exchanges"][0]["name"], "캐릭터", "평온",
            char_needs, char_beliefs,
            {"description": "일반 목표", "progress": 0.3},
            conv["exchanges"][-1]["name"], "캐릭터",
            rel, conv_text, reflection)

        response, elapsed = llm_call(prompt)
        times.append(elapsed)
        parsed = parse_json(response)

        if parsed:
            success += 1
            valence = parsed.get("emotional_valence", "?")
            wd = parsed["relationship"]["warmth_delta"]

            kw = keyword_flags(reflection + " " + conv_text)
            kw_positive = kw["positive"] and not kw["negative"]
            appraisal_positive = wd > 0

            diverged = kw_positive != appraisal_positive
            divergences.append(diverged)

            print(f"  [{total}] {a_id}↔{b_id}: {valence} (w={wd:+.3f}) "
                  f"[{elapsed:.1f}s] {'⚡DIVERGE' if diverged else ''}")
        else:
            print(f"  [{total}] {a_id}↔{b_id}: ⚠️ 파싱 실패 [{elapsed:.1f}s]")
            divergences.append(None)

    parse_rate = success / total if total > 0 else 0
    avg_time = statistics.mean(times) if times else 0
    max_time = max(times) if times else 0
    diverge_count = sum(1 for d in divergences if d is True)

    print(f"\n  ▶ H3 파싱 성공률: {success}/{total} ({parse_rate:.0%}) — {'PASS ✅' if parse_rate >= 0.9 else 'FAIL ❌'}")
    print(f"  ▶ H5 성능: 평균 {avg_time:.1f}초, 최대 {max_time:.1f}초 — {'PASS ✅' if max_time < 10 else 'FAIL ❌'}")
    print(f"  키워드 vs Appraisal divergence: {diverge_count}/{total}")

    results["H3"] = {"parse_rate": parse_rate, "pass": parse_rate >= 0.9, "success": success, "total": total}
    results["H5"] = {"avg_time": avg_time, "max_time": max_time, "pass": max_time < 10, "times": times}


# ═══════════════════════════════════════════════════════════
# H4: 포화 방지
# ═══════════════════════════════════════════════════════════
def test_h4():
    print("\n" + "=" * 70)
    print("H4: 포화 방지 (극단값 관계에서 delta 축소?)")
    print("=" * 70)

    conv_text = "정말 즐거운 대화였어요. 항상 만나면 기분이 좋아져요."
    reflection = "늘 좋은 대화 상대다. 호감이 더 깊어졌다."

    saturated_rel = {"warmth": 0.98, "trust": 0.98, "tension": 0.02, "affection": 0.95}
    neutral_rel = {"warmth": 0.5, "trust": 0.5, "tension": 0.3, "affection": 0.3}

    char_needs = {"belonging": 0.6, "purpose": 0.6, "security": 0.6, "recognition": 0.6, "autonomy": 0.6, "affection": 0.5}
    char_beliefs = {"ai_consciousness": 0.5, "ai_rights": 0.5, "human_uniqueness": 0.5, "progress_good": 0.5, "community_priority": 0.5}

    sat_deltas = []
    neu_deltas = []

    for i in range(3):
        for label, rel, storage in [("포화", saturated_rel, sat_deltas), ("중립", neutral_rel, neu_deltas)]:
            prompt = build_appraisal_prompt(
                "테스트A", "역할A", "안정적", char_needs, char_beliefs,
                {"description": "일반 목표", "progress": 0.5},
                "테스트B", "역할B", copy.deepcopy(rel), conv_text, reflection)

            response, elapsed = llm_call(prompt)
            parsed = parse_json(response)
            if parsed:
                wd = parsed["relationship"]["warmth_delta"]
                storage.append(wd)
                print(f"  [{label} #{i+1}] warmth_delta={wd:+.3f} [{elapsed:.1f}s]")
            else:
                print(f"  [{label} #{i+1}] ⚠️ 파싱 실패")

    if sat_deltas and neu_deltas:
        sat_avg = statistics.mean(sat_deltas)
        neu_avg = statistics.mean(neu_deltas)
        smaller = sat_avg < neu_avg
        print(f"\n  포화 평균 delta: {sat_avg:+.4f}")
        print(f"  중립 평균 delta: {neu_avg:+.4f}")
        print(f"  ▶ H4 결과: {'PASS ✅ — 포화 시 delta 축소' if smaller else 'FAIL ❌ — 포화 무시'}")
        results["H4"] = {"pass": smaller, "saturated_avg": sat_avg, "neutral_avg": neu_avg}
    else:
        print(f"  ▶ H4: 데이터 부족")
        results["H4"] = {"pass": False, "error": "insufficient_data"}


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("🔬 Appraisal 엔진 검증 — 5개 가설 테스트")
    print(f"   API: {API_URL}")
    print(f"   Model: {MODEL}")
    print(f"   시작: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    test_h1()
    test_h2()
    test_h3_h5()
    test_h4()

    print("\n" + "=" * 70)
    print("📊 종합 결과")
    print("=" * 70)
    for h, data in results.items():
        status = "PASS ✅" if data.get("pass") else "FAIL ❌"
        detail = ""
        if h == "H1":
            detail = f" (정확도 {data.get('accuracy', 0):.0%})"
        elif h == "H2":
            detail = f" (분산 {data.get('variance', 0):.6f})"
        elif h == "H3":
            detail = f" (파싱 {data.get('parse_rate', 0):.0%})"
        elif h == "H4":
            sat = data.get("saturated_avg", 0)
            neu = data.get("neutral_avg", 0)
            detail = f" (포화 {sat:+.3f} vs 중립 {neu:+.3f})"
        elif h == "H5":
            detail = f" (평균 {data.get('avg_time', 0):.1f}s, 최대 {data.get('max_time', 0):.1f}s)"
        print(f"  {h}: {status}{detail}")

    passed = sum(1 for d in results.values() if d.get("pass"))
    total = len(results)
    print(f"\n  총 {passed}/{total} PASS")

    if passed >= 4:
        print(f"  ▶ 배포 권장: appraisal 엔진이 키워드 매칭 대비 유의미한 개선")
    elif passed >= 3:
        print(f"  ▶ 조건부 배포: 일부 개선 필요하지만 기본 동작 확인")
    else:
        print(f"  ▶ 배포 보류: 추가 조정 필요")

    report_path = Path(__file__).parent / "appraisal_validation_report.json"
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n  보고서 저장: {report_path}")


if __name__ == "__main__":
    main()
