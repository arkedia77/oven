"""Generate v6 samples: final checkpoint x 6 prompts."""
import sys, os
sys.path.insert(0, r"C:\Users\leo\ace-step-v15")
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import torch

print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}", flush=True)

PROMPTS = [
    ("01_hisaishi",  "joe hisaishi style solo piano, gentle, cinematic, studio ghibli, emotional, instrumental"),
    ("02_einaudi",   "ludovico einaudi style minimalist piano, repetitive patterns, emotional crescendo, instrumental"),
    ("03_sakamoto",  "ryuichi sakamoto style piano, ambient, contemplative, sparse, modern classical, instrumental"),
    ("04_yiruma",    "yiruma style romantic piano, flowing melody, gentle, sentimental, instrumental"),
    ("05_darkcine",  "dark cinematic piano, suspenseful, minor key, sparse notes, film score, instrumental"),
    ("06_lofi",      "lo-fi piano, mellow, rainy mood, soft felt piano, ambient pads, instrumental"),
]

BASE_OUT = r"D:\output\piano-lora-v6\samples"
LORA_PATH = r"D:\output\piano-lora-v6\final"

handler = AceStepHandler()
print("Initializing DiT...", flush=True)
result = handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None,
    device="cuda",
    offload_to_cpu=False,
)
print(f"DiT init: {result[0][:80]}", flush=True)

msg = handler.load_lora(LORA_PATH)
print(f"LoRA loaded: {msg}", flush=True)

for ptag, caption in PROMPTS:
    out_dir = os.path.join(BASE_OUT, ptag)
    os.makedirs(out_dir, exist_ok=True)
    params = GenerationParams(
        caption=caption, lyrics="[Instrumental]", instrumental=True,
        duration=30, task_type="text2music", thinking=False,
    )
    config = GenerationConfig(batch_size=1, seeds=[42], audio_format="wav")
    try:
        res = generate_music(dit_handler=handler, llm_handler=None,
                             params=params, config=config)
        if res.success and res.audios:
            import soundfile as sf
            audio_info = res.audios[0]
            tensor = audio_info.get("tensor")
            sr = audio_info.get("sample_rate", 48000)
            if tensor is not None:
                audio_np = tensor.cpu().numpy()
                dst = os.path.join(out_dir, "seed42.wav")
                sf.write(dst, audio_np.T, sr, subtype="PCM_16")
                print(f"  [{ptag}] OK → {dst}", flush=True)
            else:
                print(f"  [{ptag}] No tensor. Keys: {list(audio_info.keys())}", flush=True)
        else:
            print(f"  [{ptag}] FAIL: {res.error}", flush=True)
    except Exception as e:
        print(f"  [{ptag}] FAIL: {e}", flush=True)

print("\nDONE", flush=True)
