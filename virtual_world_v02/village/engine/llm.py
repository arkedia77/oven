import requests
from village.config import API_URL, MODEL_NAME, TEMPERATURE


def chat(messages: list, max_tokens: int = 1024, temperature: float = None) -> str:
    if temperature is None:
        temperature = TEMPERATURE
    try:
        resp = requests.post(
            API_URL,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "chat_template_kwargs": {"thinking": False},
            },
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
