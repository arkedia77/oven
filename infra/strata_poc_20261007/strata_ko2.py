import json, time, urllib.request, os
B="http://127.0.0.1:8080"; OUT=r"C:\strata\oven_poc"
KQ=["조선 시대 세종대왕의 주요 업적 세 가지를 각각 한 문장으로 설명해 주세요.",
    "회사 동료에게 보내는 정중한 회의 일정 변경 요청 이메일을 5문장 이내로 써 주세요. 회의는 원래 목요일 오후 2시였고 금요일 오전 10시로 옮기고 싶습니다.",
    "다음 문장을 자연스러운 한국어로 고쳐 주세요: '나는 어제 친구를 만나서 영화를 봤는데 그 영화가 매우 재미있어서 다시 볼 것을 원한다.'",
    "파이썬에서 리스트와 튜플의 차이를 초보자에게 설명하고, 각각의 예시 코드를 한 줄씩 보여 주세요. 반드시 한국어로 답하세요."]
res=[]
for q in KQ:
    t0=time.time()
    req=urllib.request.Request(B+"/v1/chat/completions",data=json.dumps({"model":"x","messages":[{"role":"user","content":q}],"max_tokens":6000,"temperature":0.2}).encode("utf-8"),headers={"Content-Type":"application/json","Authorization":"Bearer x"})
    j=json.loads(urllib.request.urlopen(req,timeout=1800).read().decode("utf-8","replace"))
    m=j["choices"][0]["message"]
    res.append({"q":q,"a":m.get("content"),"reasoning_chars":len(m.get("reasoning_content") or m.get("reasoning") or ""),"finish":j["choices"][0].get("finish_reason"),"usage":j.get("usage"),"t":time.time()-t0})
    json.dump(res,open(os.path.join(OUT,"korean_rerun_max6000.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("done")
