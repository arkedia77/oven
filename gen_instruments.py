"""Generate samples with different instruments."""
import sys, os
sys.path.insert(0, r"C:\Users\leo\ace-step-v15")
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import soundfile as sf
import torch

print(f"CUDA: {torch.cuda.is_available()}", flush=True)

PROMPTS = [
    ("rhodes", "solo rhodes electric piano, warm, soulful, neo-soul, jazzy chords, mellow, instrumental, studio recording, high fidelity"),
    ("wurlitzer", "solo wurlitzer electric piano, vintage, funky, groovy, warm overdrive, instrumental, studio quality, hi-fi"),
    ("eguitar_clean", "solo clean electric guitar, jazz, warm tone, fingerpicking, mellow, instrumental, studio recording, high fidelity"),
    ("eguitar_crunch", "electric guitar, blues rock, crunchy overdrive, expressive bends, soulful, instrumental, studio quality, hi-fi"),
]

BASE_OUT = r"D:\output\instrument_samples"

handler = AceStepHandler()
result = handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None, device="cuda", offload_to_cpu=False,
)
print(f"DiT init: {result[0][:80]}", flush=True)

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
            tensor = res.audios[0].get("tensor")
            sr = res.audios[0].get("sample_rate", 48000)
            if tensor is not None:
                dst = os.path.join(out_dir, "seed42.wav")
                sf.write(dst, tensor.cpu().numpy().T, sr, subtype="PCM_16")
                print(f"  [{ptag}] OK -> {dst}", flush=True)
    except Exception as e:
        print(f"  [{ptag}] FAIL: {e}", flush=True)

print("DONE", flush=True)
