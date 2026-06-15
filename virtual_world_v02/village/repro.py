"""재현성(Reproducibility) 유틸 — 시드 고정. 옵트인.

라이브 시뮬(run_village.py)은 이 모듈을 호출하지 않으므로 영향 없음.
재현성 검증런(run_reproducible.py)에서만 seed_everything()을 호출한다.

엔진은 표준 `random` 모듈만 사용(numpy/torch 미사용)하므로 random.seed 고정으로 충분.
LLM 비결정성은 llama.cpp `seed` 파라미터(llm.chat 내 _derive_seed)로 별도 처리.
※ 배치 동시처리 부동소수점 비결정성(배치불변 결정론)은 별도 R&D 트랙(⑤).
"""
import random

from village import config


def seed_everything(seed: int) -> None:
    """random 시드 고정 + config 재현성 모드 활성화.

    config를 모듈 속성으로 변경하므로, config를 `from village import config`로
    참조하는 모듈(llm.py 등)에 런타임 즉시 반영된다.
    """
    random.seed(seed)
    config.REPRODUCIBLE = True
    config.RANDOM_SEED = seed
    config.LLM_SEED = seed


def is_reproducible() -> bool:
    return bool(config.REPRODUCIBLE)
