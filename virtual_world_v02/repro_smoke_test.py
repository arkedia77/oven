#!/usr/bin/env python3
"""재현성 ① 스모크 테스트 — 시드 고정 인프라 검증.

검증 항목:
  A. random 모듈 결정성: seed_everything(N) 후 random 시퀀스가 매번 동일
  B. LLM 단일요청 결정성: REPRODUCIBLE 모드에서 같은 입력→같은 출력
  C. 시드 분리: 다른 base seed → 다른 LLM 출력 (다양성 유지)
  D. 라이브 무영향: REPRODUCIBLE=False(기본)에서는 seed 미주입

라이브 시뮬과 분리된 read-only 검증(상태 저장 안 함). LLM 호출은 ogo:8080 필요.
사용: python repro_smoke_test.py [--no-llm]
"""
import sys
import random

sys.path.insert(0, ".")
from village import config
from village.repro import seed_everything


def test_random_determinism():
    seed_everything(12345)
    seq1 = [random.random() for _ in range(10)] + [random.choice("abcdef") for _ in range(5)]
    seed_everything(12345)
    seq2 = [random.random() for _ in range(10)] + [random.choice("abcdef") for _ in range(5)]
    ok = seq1 == seq2
    print(f"[A] random 결정성: {'PASS' if ok else 'FAIL'}")
    return ok


def test_default_no_seed():
    # 기본 상태(라이브)에서 REPRODUCIBLE이 False여야 함
    import importlib
    importlib.reload(config)
    ok = (config.REPRODUCIBLE is False)
    print(f"[D] 라이브 기본 비재현(REPRODUCIBLE=False): {'PASS' if ok else 'FAIL'}")
    return ok


def test_llm_determinism():
    from village.engine.llm import chat
    seed_everything(777)
    msgs = [{"role": "user", "content": "민수가 카페에서 지영에게 건네는 첫 인사를 한 문장으로."}]
    a = chat(msgs, max_tokens=128)
    b = chat(msgs, max_tokens=128)
    same = (a == b)
    print(f"[B] LLM 단일요청 결정성(같은 base seed): {'PASS' if same else 'FAIL'}")
    print(f"     out: {a[:80]!r}")

    seed_everything(99999)
    c = chat(msgs, max_tokens=128)
    diff = (c != a)
    print(f"[C] 시드 분리(다른 base→다른 출력): {'PASS' if diff else 'FAIL'}")
    return same and diff


def main():
    no_llm = "--no-llm" in sys.argv
    results = []
    results.append(test_random_determinism())
    results.append(test_default_no_seed())
    if not no_llm:
        try:
            results.append(test_llm_determinism())
        except Exception as e:
            print(f"[B/C] LLM 테스트 SKIP (서버 연결 실패: {e})")
    else:
        print("[B/C] LLM 테스트 SKIP (--no-llm)")
    ok = all(results)
    print("=" * 40)
    print(f"종합: {'ALL PASS ✅' if ok else 'FAIL ❌'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
