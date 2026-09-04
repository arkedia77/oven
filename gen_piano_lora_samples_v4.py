"""Generate v4 comparison samples: 4 checkpoints × 6 prompts."""
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

BASE_OUT = r"D:\output\piano-lora-v4\samples"
CKPT_ROOT = r"D:\output\piano-lora-v4\checkpoints"

VARIANTS = [
    ("ep30",  os.path.join(CKPT_ROOT, "epoch_30_loss_0.5547")),
    ("ep60",  os.path.join(CKPT_ROOT, "epoch_60_loss_0.5380")),
    ("ep90",  os.path.join(CKPT_ROOT, "epoch_90_loss_0.5276")),
    ("ep120", r"D:\output\piano-lora-v4\final"),
]

handler = AceStepHandler()
print("Initializing DiT...", flush=True)
result = handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None,
    device="cuda",
    offload_to_cpu=False,
)
print(f"DiT init: {result[0][:80]}", flush=True)

for tag, lora_path in VARIANTS:
    print(f"\n=== {tag} ===", flush=True)
    msg = handler.load_lora(lora_path)
    print(f"[{tag}] LoRA: {msg}", flush=True)
    for ptag, caption in PROMPTS:
        out_dir = os.path.join(BASE_OUT, tag, ptag)
        os.makedirs(out_dir, exist_ok=True)
        params = GenerationParams(
            caption=caption, lyrics="[Instrumental]", instrumental=True,
            duration=30, task_type="text2music", thinking=False,
        )
        config = GenerationConfig(batch_size=1, seeds=[42], audio_format="wav")
        try:
            res = generate_music(dit_handler=handler, llm_handler=None,
                                 params=params, config=config, save_dir=out_dir)
            for audio in res.audios:
                print(f"  {tag}/{ptag} -> {audio.get('path', 'N/A')}", flush=True)
        except Exception as e:
            print(f"  {tag}/{ptag} FAILED: {e}", flush=True)

print("\nDONE", flush=True)
