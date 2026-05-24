"""Generate 차오름 LoKR samples — baseline + best epoch."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import torch

print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}", flush=True)

CAPTION = "Korean trot, emotional male vocals, vibrato, traditional trot ballad arrangement, accordion, guitar, heartfelt, 95 BPM"
LYRICS = """[verse]
고향의 그 언덕길을
홀로 걸어가는 밤에
어머니 손잡고 걸던
그 시절이 그리워라

[chorus]
돌아갈 수 없는 그날
눈물이 앞을 가려도
가슴에 품은 그 사랑
영원히 잊지 못해요

[verse]
세월은 강물처럼
흘러가고 또 흘러가
주름진 이 두 손으로
당신을 그려봅니다

[chorus]
돌아갈 수 없는 그날
눈물이 앞을 가려도
가슴에 품은 그 사랑
영원히 잊지 못해요
"""

SAVE_DIR = r"C:\Users\leo\chaoreum_samples"
BEST_CKPT = r"C:\Users\leo\chaoreum_output\checkpoints\epoch_400_loss_0.9721"

def generate(handler, save_path):
    os.makedirs(save_path, exist_ok=True)
    params = GenerationParams(
        caption=CAPTION,
        lyrics=LYRICS,
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
    res = generate_music(
        dit_handler=handler,
        llm_handler=None,
        params=params,
        config=config,
        save_dir=save_path,
    )
    for audio in res.audios:
        print(f"  -> {audio.get('path', 'saved')}", flush=True)

handler = AceStepHandler()
handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None,
    device="cuda",
    offload_to_cpu=False,
)

print("[baseline]", flush=True)
generate(handler, os.path.join(SAVE_DIR, "baseline"))

print(f"[lokr best] Loading {BEST_CKPT}...", flush=True)
handler.load_lora(BEST_CKPT)
generate(handler, os.path.join(SAVE_DIR, "lokr_best"))

print("DONE!", flush=True)
