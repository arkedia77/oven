"""Generate 6 piano LoRA comparison samples with seed 42."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import torch

print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}", flush=True)

PROMPTS = [
    ("01_lyrical",  "lyrical solo piano, emotional, slow tempo, reverb, cinematic, instrumental"),
    ("02_jazz",     "jazz piano trio, swing, walking bass, brushed drums, warm tone, instrumental"),
    ("03_classical","classical piano sonata, romantic era, expressive dynamics, instrumental"),
    ("04_darkcine", "dark cinematic piano, suspenseful, minor key, sparse notes, film score, instrumental"),
    ("05_ragtime",  "ragtime piano, upbeat, syncopated, early 1900s style, instrumental"),
    ("06_lofi",     "lo-fi piano, mellow, rainy mood, soft felt piano, ambient pads, instrumental"),
]

LORA_PATH = r"D:\output\piano-lora\final"
SAVE_DIR = r"D:\output\piano-lora\samples_final"
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

print(f"Loading LoRA from {LORA_PATH}...", flush=True)
msg = handler.load_lora(LORA_PATH)
print(f"LoRA: {msg}", flush=True)
print(f"lora_loaded={handler.lora_loaded}, use_lora={handler.use_lora}, scale={handler.lora_scale}", flush=True)

for tag, caption in PROMPTS:
    print(f"\n=== {tag} ===", flush=True)
    params = GenerationParams(
        caption=caption,
        lyrics="[Instrumental]",
        instrumental=True,
        duration=30,
        task_type="text2music",
        thinking=False,
    )
    config = GenerationConfig(
        batch_size=1,
        seeds=[42],
        audio_format="wav",
    )
    out_dir = os.path.join(SAVE_DIR, tag)
    os.makedirs(out_dir, exist_ok=True)
    try:
        res = generate_music(
            dit_handler=handler,
            llm_handler=None,
            params=params,
            config=config,
            save_dir=out_dir,
        )
        for audio in res.audios:
            print(f"  -> {audio.get('path', 'N/A')}", flush=True)
    except Exception as e:
        print(f"  FAILED: {e}", flush=True)

print("\nDONE", flush=True)
