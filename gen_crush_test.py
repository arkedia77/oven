"""Generate Crush LoKR test sample."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import torch

print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}", flush=True)

LOKR_PATH = r"C:\Users\leo\ace-step-v15\crush_output\final"
SAVE_DIR = r"C:\Users\leo\ace-step-v15\crush_samples"
os.makedirs(SAVE_DIR, exist_ok=True)

handler = AceStepHandler()
print("Initializing DiT service...", flush=True)
result = handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None,
    device="cuda",
    offload_to_cpu=False,
)
print(f"DiT init: {result[0][:80]}", flush=True)

print(f"Loading LoKR from {LOKR_PATH}...", flush=True)
msg = handler.load_lora(LOKR_PATH)
print(f"LoKR: {msg}", flush=True)
print(f"lora_loaded={handler.lora_loaded}, use_lora={handler.use_lora}, scale={handler.lora_scale}", flush=True)

caption = "Smooth Korean R&B, soulful male vocals, dreamy synth pads, soft drums, romantic mood, 85 BPM"
lyrics = """[verse]
사랑이란 말로는 부족해
너의 곁에 있고 싶어
이 밤이 지나도
변하지 않을 마음

[chorus]
너만 있으면 돼
세상 다 가진 것 같아
내 곁에 있어줘
영원히 이대로"""

print(f"\n=== Generating Crush-style R&B ===", flush=True)
params = GenerationParams(
    caption=caption,
    lyrics=lyrics,
    instrumental=False,
    vocal_language="ko",
    duration=60,
    task_type="text2music",
    thinking=False,
)
config = GenerationConfig(
    batch_size=1,
    seeds=[42],
    audio_format="wav",
)

try:
    res = generate_music(
        dit_handler=handler,
        llm_handler=None,
        params=params,
        config=config,
        save_dir=SAVE_DIR,
    )
    for audio in res.audios:
        print(f"  -> {audio.get('path', 'N/A')}", flush=True)
except Exception as e:
    print(f"  FAILED: {e}", flush=True)

print("\nDONE", flush=True)
