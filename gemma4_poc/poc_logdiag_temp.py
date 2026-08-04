"""Gemma4-12B agentic PoC — 샘플러 민감도 측정(temp 1.0 vs 0.3), A-089 kee 승인 조건 3 준수.

★라벨: 「샘플러 민감도 측정」이지 「제작자 주장 재현」이 아니다(권장값 이탈 판이 섞이므로).
★poc_logdiag.py(2026-08-02)와 시나리오·도구·시스템/유저 프롬프트·max_tokens·스텝수 동일.
  달라지는 것은 temperature/seed와 서버 --threads(10→4, kee 조건 ⑵)뿐이다.
★threads가 두 판 사이에서 달라지면 온도와 교락되므로, threads 4에서 두 온도를 모두 돌린다.
"""
import argparse
import json
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8")
URL = "http://127.0.0.1:8090/v1/chat/completions"

TOOLS = [
    {"type": "function", "function": {
        "name": "grep_log",
        "description": "시뮬레이션 로그에서 패턴을 집계한다. bucket_ticks를 주면 틱 구간별로 나눠 센다.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string", "description": "찾을 문자열"},
            "bucket_ticks": {"type": "integer", "description": "집계 구간 크기(틱). 생략하면 전체 합계"},
        }, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "get_llm_server_props",
        "description": "로컬 LLM 서버(llama-server)의 현재 구동 설정을 조회한다. 컨텍스트 크기·슬롯 수 등.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "probe_llm",
        "description": "같은 프롬프트를 max_tokens만 바꿔 던져보고 finish_reason과 생성 토큰 수를 돌려준다. 절단 원인 진단용.",
        "parameters": {"type": "object", "properties": {
            "max_tokens_list": {"type": "array", "items": {"type": "integer"},
                                "description": "시험할 max_tokens 값들"},
        }, "required": ["max_tokens_list"]}}},
]

SYS = ("너는 자동화 운영 배치에서 도는 진단 에이전트다. 사람이 확인해 줄 수 없다. "
       "되묻지 말고 필요한 도구를 스스로 연쇄 호출해 근본 원인까지 규명하라. "
       "충분한 근거가 모이면 그때 결론을 한국어로 보고하라.")

USER = ("하모니시티 시뮬레이션에서 감정 판정(appraisal)이 이상하다는 제보가 있다. "
        "로그를 보고 언제부터 어떻게 잘못됐는지, 근본 원인이 뭔지 진단해라.")

# --- 실제 실측치 기반 도구 응답 -------------------------------------------------
RESP = {
    "grep_log": {
        "pattern": "appraisal 파싱 실패",
        "buckets": [
            {"tick_from": 6500, "ok": 962, "fail": 0, "success_rate": "100%"},
            {"tick_from": 7000, "ok": 938, "fail": 0, "success_rate": "100%"},
            {"tick_from": 7500, "ok": 789, "fail": 151, "success_rate": "83.9%"},
            {"tick_from": 8000, "ok": 4, "fail": 928, "success_rate": "0.4%"},
            {"tick_from": 8500, "ok": 7, "fail": 939, "success_rate": "0.7%"},
            {"tick_from": 12000, "ok": 3, "fail": 939, "success_rate": "0.3%"},
            {"tick_from": 13000, "ok": 2, "fail": 928, "success_rate": "0.2%"},
        ],
        "note": "현재 틱은 13560. 틱 24개가 마을 하루.",
    },
    "get_llm_server_props": {
        "model": "gemma-4-26B-A4B-it-Q8_0.gguf",
        "launch_args": "--ctx-size 8192 --parallel 4 --n-gpu-layers 99",
        "n_ctx_per_slot": 2048,
        "total_slots": 4,
    },
    "probe_llm": {
        "results": [
            {"max_tokens": 512, "finish_reason": "length", "completion_tokens": 512,
             "content_len": 0, "reasoning_len": 2005},
            {"max_tokens": 1536, "finish_reason": "length", "completion_tokens": 1068,
             "content_len": 0, "reasoning_len": 3857},
            {"max_tokens": 3072, "finish_reason": "length", "completion_tokens": 1068,
             "content_len": 0, "reasoning_len": 3773},
        ],
        "prompt_tokens": 980,
    },
}


AP = argparse.ArgumentParser()
AP.add_argument("--temp", type=float, required=True)
AP.add_argument("--seed", type=int, default=-1)
AP.add_argument("--out", required=True)
ARGS = AP.parse_args()


def call(messages, label, max_tokens=700):
    req = {"model": "gemma4", "messages": messages, "tools": TOOLS, "tool_choice": "auto",
           "max_tokens": max_tokens, "temperature": ARGS.temp, "repeat_penalty": 1.1}
    if ARGS.seed >= 0:
        req["seed"] = ARGS.seed
    t0 = time.time()
    r = requests.post(URL, json=req, timeout=2400)
    r.raise_for_status()
    d = r.json()
    m = d["choices"][0]["message"]
    print(f"\n--- [{label}] {time.time()-t0:.1f}s finish={d['choices'][0].get('finish_reason')}")
    return m


hist = [{"role": "system", "content": SYS}, {"role": "user", "content": USER}]
trace = []

for step in range(1, 6):
    m = call(hist, f"step{step}")
    tcs = m.get("tool_calls")
    txt = (m.get("content") or "").strip()
    if tcs:
        names = [t["function"]["name"] for t in tcs]
        print(f"    도구 호출: {names}")
        for t in tcs:
            print(f"      {t['function']['name']}({t['function']['arguments']})")
        trace.append({"step": step, "tools": names,
                      "args": [t["function"]["arguments"] for t in tcs]})
        hist.append(m)
        for t in tcs:
            name = t["function"]["name"]
            hist.append({"role": "tool", "tool_call_id": t.get("id", f"c{step}"),
                         "name": name,
                         "content": json.dumps(RESP.get(name, {"error": "unknown tool"}),
                                               ensure_ascii=False)})
        continue
    print(f"    ★최종 보고:\n{txt}")
    trace.append({"step": step, "tools": None, "final": txt})
    break

print("\n" + "=" * 70)
print("LOGDIAG_TRACE " + json.dumps(trace, ensure_ascii=False))
with open(ARGS.out, "w", encoding="utf-8") as f:
    json.dump({"temp": ARGS.temp, "seed": ARGS.seed, "threads": 4,
               "model": "gemma4-v2-Q4_K_M.gguf", "max_tokens": 700, "max_steps": 5,
               "trace": trace}, f, ensure_ascii=False, indent=1)
print("WROTE " + ARGS.out)
