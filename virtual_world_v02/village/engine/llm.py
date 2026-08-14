import hashlib
import json
import os
import time
import requests
from village import config  # 모듈 참조 — seed_everything의 런타임 변경 즉시 반영


def _mock_response(messages: list) -> str:
    """결정적 mock 응답 — 입력 해시 기반. REPRO_MOCK_LLM=1에서만 사용.
    LLM 배치 비결정성을 배제하고 순수 엔진(random) 결정성을 검증하기 위함."""
    h = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"[mock:{h[:12]}] 결정적 응답입니다."


def _record_call_length(messages: list, max_tokens: int, ok: bool, err: str = ""):
    """호출별 프롬프트 길이 계측(A-093, kee 승인 2026-08-15) — ★계측 전용·거동 무변경.

    왜 넣는가: sim.log의 `prompt=N자`는 appraisal 호출에만 찍혀서, 08-04·08-11·08-12
    abort 때 «실제로 죽인 요청의 길이»가 미상으로 남았다(=긴 프롬프트 가설이 미검정인 이유).
    ★특히 오류 경로에서는 usage가 안 와서 길이를 사후에 복원할 방법이 아예 없다.

    ⚠계측이 시뮬을 죽이면 안 되므로 전체를 except로 감싼다(로깅 실패는 조용히 버림).
    ⚠hot path에 append I/O 1회가 늘어난다 — 무시할 만하나 abort 재발 시 제일 먼저
      의심해야 할 변경분이다(kee 조건 ⒞).
    """
    try:
        from village import config
        chars = sum(len(str(m.get("content", ""))) for m in messages)
        rec = {
            "t": round(time.time(), 3),
            "chars": chars,
            "msgs": len(messages),
            "mt": max_tokens,
            "ok": 1 if ok else 0,
        }
        if err:
            rec["err"] = err[:120]
        path = config.DATA_DIR.parent / "llm_call_lengths.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _derive_seed(messages: list, base: int) -> int:
    """메시지 내용으로 결정적 seed 도출 — 같은 입력→같은 seed→같은 출력(재현),
    입력이 다르면 다른 seed(캐릭터별 응답 다양성 유지). 호출 순서에 비의존."""
    payload = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    h = int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16)
    return (base + h) % (2 ** 31)


def chat(messages: list, max_tokens: int = 1024, temperature: float = None,
         seed: int = None) -> str:
    # 재현성 진단용 결정적 mock (환경변수 가드 — 라이브 무영향)
    if os.environ.get("REPRO_MOCK_LLM") == "1":
        return _mock_response(messages)
    # replay 모드: 기록된 출력 재생(서버 미사용) → 배치 비결정성(⑤) 우회
    from village import replay
    if replay.is_replaying():
        return replay.replay_call(messages)
    if temperature is None:
        temperature = config.TEMPERATURE
    # --- 재현성(옵트인): REPRODUCIBLE=True일 때만 seed 주입 + temp 고정. 라이브(False)는 무영향 ---
    if config.REPRODUCIBLE:
        if seed is None:
            seed = _derive_seed(messages, config.LLM_SEED or 0)
        if config.REPRODUCIBLE_TEMPERATURE is not None:
            temperature = config.REPRODUCIBLE_TEMPERATURE
    try:
        req = {
            "model": config.MODEL_NAME,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "chat_template_kwargs": {"thinking": False},
        }
        if seed is not None:
            req["seed"] = seed
        # 동시성 실측용 timings 요청(llama.cpp가 prompt/gen ms 반환). 미지원 서버는 무시.
        req["timings_per_token"] = True
        _t0 = time.time()
        resp = requests.post(
            config.API_URL,
            json=req,
            timeout=120,
        )
        resp.raise_for_status()
        _latency = time.time() - _t0
        data = resp.json()
        # 프로파일 기록(카운터는 항상 누적, 파일기록은 가드) — 동시성 실측
        from village import profiling
        _usage = data.get("usage") or {}
        profiling.record_llm(
            _latency,
            prompt_tokens=_usage.get("prompt_tokens"),
            gen_tokens=_usage.get("completion_tokens"),
            timings=data.get("timings"),
        )
        msg = data["choices"][0]["message"]
        content = msg.get("content", "").strip()
        if not content:
            content = "(무응답)"
        # record 모드: 실제 출력을 기록 → 이후 replay로 완전 재현
        if replay.is_recording():
            replay.record_call(messages, content, seed)
        from village import safety_rail
        safety_rail.record_llm_result(is_error=False)
        _record_call_length(messages, max_tokens, ok=True)
        return content
    except Exception as e:
        from village import safety_rail
        safety_rail.record_llm_result(is_error=True)
        _record_call_length(messages, max_tokens, ok=False, err=f"{type(e).__name__}: {e}")
        return f"[오류: {e}]"
