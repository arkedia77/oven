"""Generate samples for Lee Hi LoKR — baseline + best epoch."""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import torch

print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}", flush=True)

ARTIST_DIR = r"C:\Users\leo\ace-step-v15\lokr_artists\leehi"
SAVE_DIR = r"C:\Users\leo\ace-step-v15\lokr_samples\leehi"

CAPTION = "Korean R&B soul, powerful emotional female vocals, piano, string arrangement, intimate atmosphere, 80 BPM"
LYRICS = """[verse]
창밖으로 비가 내려
흐릿한 유리창 너머
네 목소리가 들려와
잊혀지지 않는 밤

[chorus]
숨이 벅차올라도
괜찮다고 말해줘
이 긴 밤이 지나면
다시 웃을 수 있을까

[verse]
혼자 걷는 거리 위에
너의 온기가 스며들어
아직도 네가 그리워
눈물이 고여만 와

[chorus]
한숨처럼 깊은 맘
누가 알아줄 수 있을까
그대 없는 하루가
이렇게 길 줄 몰랐어"""


def get_best_checkpoint(artist_dir):
    ckpt_dir = os.path.join(artist_dir, "output", "checkpoints")
    best_loss = 999
    best_path = None
    for d in os.listdir(ckpt_dir):
        m = re.match(r"epoch_(\d+)_loss_([\d.]+)", d)
        if m:
            loss = float(m.group(2))
            if loss < best_loss:
                best_loss = loss
                best_path = os.path.join(ckpt_dir, d)
    return best_path, best_loss


def generate_sample(handler, save_path):
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
        print(f"    -> {audio.get('path', 'saved')}", flush=True)


best_path, best_loss = get_best_checkpoint(ARTIST_DIR)
print(f"Best checkpoint: {os.path.basename(best_path)}, loss={best_loss:.4f}", flush=True)

handler = AceStepHandler()
handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None,
    device="cuda",
    offload_to_cpu=False,
)

print("[baseline]", flush=True)
generate_sample(handler, os.path.join(SAVE_DIR, "baseline"))

print(f"[lokr best] Loading {os.path.basename(best_path)}...", flush=True)
handler.load_lora(best_path)
generate_sample(handler, os.path.join(SAVE_DIR, "lokr_best"))

print("DONE!", flush=True)
