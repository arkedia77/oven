import hashlib
import json
import requests
from village import config  # 모듈 참조 — seed_everything의 런타임 변경 즉시 반영


def _derive_seed(messages: list, base: int) -> int:
    """메시지 내용으로 결정적 seed 도출 — 같은 입력→같은 seed→같은 출력(재현),
    입력이 다르면 다른 seed(캐릭터별 응답 다양성 유지). 호출 순서에 비의존."""
    payload = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    h = int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16)
    return (base + h) % (2 ** 31)


def chat(messages: list, max_tokens: int = 1024, temperature: float = None,
         seed: int = None) -> str:
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
        resp = requests.post(
            config.API_URL,
            json=req,
            timeout=120,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        content = msg.get("content", "").strip()
        if not content:
            content = "(무응답)"
        return content
    except Exception as e:
        return f"[오류: {e}]"
