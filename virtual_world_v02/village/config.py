import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
# DATA_DIR: 재현성 검증런은 HARMONICITY_DATA_DIR 환경변수로 별도 dir 격리(라이브는 미설정→기본 data/)
DATA_DIR = Path(os.environ.get("HARMONICITY_DATA_DIR", str(BASE_DIR / "data")))
VILLAGE_DIR = Path(__file__).parent

# API_URL: 머신별 분기(ogo=localhost / 로컬=100.107.229.5). 동시성 실측·멀티엔드포인트용으로
# HARMONICITY_API_URL 환경변수 override 지원. 미설정 시 기존 기본값 보존(라이브/ogo 무영향).
API_URL = os.environ.get("HARMONICITY_API_URL", "http://100.107.229.5:8080/v1/chat/completions")
MODEL_NAME = os.environ.get("HARMONICITY_MODEL_NAME", "google_gemma-4-26B-A4B-it-Q8_0.gguf")

TICK_SECONDS = 200  # 3.3 real minutes per tick (reduced from 150, ~25% compute saving)
TICKS_PER_DAY = 24  # 24 ticks = 1 village day (matches 24-hour cycle)
VILLAGE_HOURS_PER_TICK = 1

EXCHANGES_PER_CONVERSATION = 3
MAX_TOKENS_CONVERSATION = 2048
MAX_TOKENS_REFLECTION = 2048
MAX_TOKENS_MONOLOGUE = 1024
MAX_TOKENS_RETROSPECTIVE = 1024
TEMPERATURE = 0.85

# --- 재현성 (Reproducibility) — 옵트인. 모두 미설정/False = 기존 비결정 동작 유지(라이브 무영향) ---
# 재현성 검증런에서만 활성화 (run_reproducible.py). 라이브 run_village.py는 건드리지 않음.
REPRODUCIBLE = False              # True면 시드 고정 모드 (random + LLM)
RANDOM_SEED = None               # int 설정 시 random.seed 고정 (seed_everything에서 사용)
LLM_SEED = 0                     # llama.cpp 결정적 seed 도출 base (메시지 해시와 합산)
# 재현성 모드 LLM temperature. None=기존 TEMPERATURE(0.85) 유지가 기본 —
# seed 고정만으로 재현성 확보하면서 시뮬 다양성/창발 보존(하모니시티는 변화관찰이 핵심).
# 0.0(greedy)으로 두면 seed가 무의미해지고 응답이 보수적으로 수렴 → 다양성 손실이라 비권장.
REPRODUCIBLE_TEMPERATURE = None

MAX_EPISODES = 50
CONSOLIDATION_INTERVAL = 1

MAX_CONVERSATIONS_PER_TICK = 2
SOLO_MONOLOGUES_PER_TICK = 1

RETROSPECTIVE_INTERVAL_DAYS = 10
