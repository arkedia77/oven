"""Generate Hisaishi-style EP (Electric Piano) using base ACE-Step model (no LoRA)."""
import sys, os
sys.path.insert(0, r"C:\Users\leo\ace-step-v15")
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import torch
import soundfile as sf

print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}", flush=True)

PROMPTS = [
    ("ep_hisaishi_rhodes", "joe hisaishi style rhodes electric piano, warm, cinematic, gentle, emotional, studio ghibli, instrumental"),
    ("ep_hisaishi_wurlitzer", "joe hisaishi style wurlitzer electric piano, vintage, warm tone, cinematic, emotional, instrumental"),
    ("ep_hisaishi_epiano", "joe hisaishi style electric piano, smooth, jazzy, warm pads, cinematic, emotional, instrumental"),
]

OUT_DIR = r"D:\output\ep_hisaishi"

handler = AceStepHandler()
print("Initializing DiT (base model, no LoRA)...", flush=True)
result = handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None,
    device="cuda",
    offload_to_cpu=False,
)
print(f"DiT init: {result[0][:80]}", flush=True)

for ptag, caption in PROMPTS:
    os.makedirs(OUT_DIR, exist_ok=True)
    params = GenerationParams(
        caption=caption, lyrics="[Instrumental]", instrumental=True,
        duration=30, task_type="text2music", thinking=False,
    )
    config = GenerationConfig(batch_size=1, seeds=[42], audio_format="wav")
    try:
        res = generate_music(dit_handler=handler, llm_handler=None,
                             params=params, config=config)
        if res.success and res.audios:
            audio_info = res.audios[0]
            tensor = audio_info.get("tensor")
            sr = audio_info.get("sample_rate", 48000)
            if tensor is not None:
                audio_np = tensor.cpu().numpy()
                dst = os.path.join(OUT_DIR, f"{ptag}.wav")
                sf.write(dst, audio_np.T, sr, subtype="PCM_16")
                print(f"  [{ptag}] OK -> {dst}", flush=True)
            else:
                print(f"  [{ptag}] No tensor. Keys: {list(audio_info.keys())}", flush=True)
        else:
            print(f"  [{ptag}] FAIL: {res.error}", flush=True)
    except Exception as e:
        print(f"  [{ptag}] FAIL: {e}", flush=True)

print("\nDONE", flush=True)
