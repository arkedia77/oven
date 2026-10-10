# oven Strata PoC measurements (leowin, localhost only)
import json, time, urllib.request, sys, os
B = "http://127.0.0.1:8080"
OUT = r"C:\strata\oven_poc"; os.makedirs(OUT, exist_ok=True)

def post(path, body, headers=None, stream=False, timeout=1800):
    h = {"Content-Type": "application/json", "Authorization": "Bearer x"}
    h.update(headers or {})
    req = urllib.request.Request(B + path, data=json.dumps(body).encode("utf-8"), headers=h)
    return urllib.request.urlopen(req, timeout=timeout)

def chat_stream(messages, max_tokens, temperature=0.2):
    """OpenAI streaming: returns text, reasoning, t_first, t_total, usage"""
    t0 = time.time(); t_first = None; text = []; think = []; usage = None
    r = post("/v1/chat/completions", {"model": "x", "messages": messages, "max_tokens": max_tokens,
             "temperature": temperature, "stream": True, "stream_options": {"include_usage": True}})
    for raw in r:
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data:"): continue
        d = line[5:].strip()
        if d == "[DONE]": break
        try: j = json.loads(d)
        except ValueError: continue
        if j.get("usage"): usage = j["usage"]
        for c in j.get("choices", []):
            dl = c.get("delta", {})
            piece = dl.get("content") or ""; rp = dl.get("reasoning_content") or dl.get("reasoning") or ""
            if (piece or rp) and t_first is None: t_first = time.time() - t0
            if piece: text.append(piece)
            if rp: think.append(rp)
    return {"text": "".join(text), "reasoning": "".join(think), "t_first": t_first, "t_total": time.time() - t0, "usage": usage}

res = {"started": time.strftime("%Y-%m-%d %H:%M:%S")}
def save(): json.dump(res, open(os.path.join(OUT, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

try: res["status"] = json.loads(urllib.request.urlopen(B + "/v1/status", timeout=30).read().decode("utf-8", "replace"))
except Exception as e: res["status_error"] = repr(e)

# 1) speed: short chat x3 (code prompt)
res["speed_short"] = []
for i in range(3):
    r = chat_stream([{"role": "user", "content": "Write a Python function that merges overlapping intervals, with a short docstring and 3 test cases. Code only."}], 500)
    u = r["usage"] or {}
    ct = u.get("completion_tokens"); gen_t = r["t_total"] - (r["t_first"] or 0)
    res["speed_short"].append({"t_first": r["t_first"], "t_total": r["t_total"], "usage": u,
        "decode_tok_s": (ct / gen_t) if ct and gen_t > 0 else None, "chars": len(r["text"]), "reasoning_chars": len(r["reasoning"]), "head": r["text"][:300]})
    save()

# 2) prompt reading: long prompt (~4K and ~12K tokens of code-like text), 16 output tokens
filler = "\n".join(f"def f{i}(x):\n    # helper number {i}\n    return x * {i} + {i % 7}\n" for i in range(4000))
res["prefill"] = []
for n_chars in (16000, 48000):
    r = chat_stream([{"role": "user", "content": filler[:n_chars] + "\n\nHow many functions are defined above? Answer with one number."}], 16)
    u = r["usage"] or {}; pt = u.get("prompt_tokens")
    res["prefill"].append({"chars": n_chars, "t_first": r["t_first"], "t_total": r["t_total"], "usage": u,
        "prompt_tok_s": (pt / r["t_first"]) if pt and r["t_first"] else None, "text": r["text"][:100], "reasoning_chars": len(r["reasoning"])})
    save()

# 3) Korean x5
KQ = ["조선 시대 세종대왕의 주요 업적 세 가지를 각각 한 문장으로 설명해 주세요.",
      "회사 동료에게 보내는 정중한 회의 일정 변경 요청 이메일을 5문장 이내로 써 주세요. 회의는 원래 목요일 오후 2시였고 금요일 오전 10시로 옮기고 싶습니다.",
      "다음 문장을 자연스러운 한국어로 고쳐 주세요: '나는 어제 친구를 만나서 영화를 봤는데 그 영화가 매우 재미있어서 다시 볼 것을 원한다.'",
      "파이썬에서 리스트와 튜플의 차이를 초보자에게 설명하고, 각각의 예시 코드를 한 줄씩 보여 주세요.",
      "철수는 사과 12개를 가지고 있었습니다. 영희에게 5개를 주고, 가게에서 8개를 더 샀습니다. 그 뒤 절반을 동생에게 주었습니다. 철수에게 남은 사과는 몇 개인지 풀이와 함께 답하세요."]
res["korean"] = []
for q in KQ:
    r = chat_stream([{"role": "user", "content": q}], 1500)
    u = r["usage"] or {}; ct = u.get("completion_tokens"); gen_t = r["t_total"] - (r["t_first"] or 0)
    res["korean"].append({"q": q, "a": r["text"], "reasoning_chars": len(r["reasoning"]), "t_first": r["t_first"], "t_total": r["t_total"], "usage": u,
                          "decode_tok_s": (ct / gen_t) if ct and gen_t > 0 else None})
    save()

# 4) Anthropic format: plain + tool use
AH = {"x-api-key": "x", "anthropic-version": "2023-06-01"}
try:
    r = post("/v1/messages", {"model": "claude-x", "max_tokens": 300, "messages": [{"role": "user", "content": "Reply with exactly: PONG"}]}, AH)
    res["anthropic_plain"] = json.loads(r.read().decode("utf-8", "replace"))
except Exception as e: res["anthropic_plain_error"] = repr(e)
save()
try:
    r = post("/v1/messages", {"model": "claude-x", "max_tokens": 600,
        "tools": [{"name": "read_file", "description": "Read a file from disk", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}],
        "messages": [{"role": "user", "content": "Use the read_file tool to read C:/tmp/notes.txt."}]}, AH)
    res["anthropic_tool"] = json.loads(r.read().decode("utf-8", "replace"))
except Exception as e: res["anthropic_tool_error"] = repr(e)
res["finished"] = time.strftime("%Y-%m-%d %H:%M:%S"); save()
print("done", res["finished"])
