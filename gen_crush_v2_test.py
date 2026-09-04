"""Generate Crush v2 LoKR test samples — multi-checkpoint evaluation."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import torch

print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}", flush=True)

LOKR_DIR = r"C:\Users\leo\ace-step-v15\crush_v2_output"
SAVE_DIR = r"C:\Users\leo\ace-step-v15\crush_v2_samples"
os.makedirs(SAVE_DIR, exist_ok=True)

PROMPTS = [
    {
        "name": "ballad",
        "caption": "Korean R&B ballad, emotional male vocals, piano, string arrangement, romantic mood, 70 BPM",
        "lyrics": """[verse]
밤하늘에 별이 쏟아져
너의 이름을 부르면
이 세상 모든 게 멈춘 듯해
숨이 막힐 것 같아

[chorus]
사랑해 너를 사랑해
이 말밖에 할 수 없어
영원히 너의 곁에서
이대로 머물고 싶어""",
    },
    {
        "name": "uptempo",
        "caption": "Korean R&B pop, smooth male vocals, funky bass, bright synth, upbeat confident mood, 105 BPM",
        "lyrics": """[verse]
월요일 아침 눈을 떠
거울 속에 비친 나
오늘은 뭔가 다를 거야
느낌이 좋아 yeah

[chorus]
Let's go 멈추지 마
이 리듬에 몸을 맡겨
하루를 통째로 삼켜
우리만의 frequency""",
    },
    {
        "name": "midtempo",
        "caption": "Korean R&B, dreamy male vocals, synth pads, soft drums, late night driving mood, 88 BPM",
        "lyrics": """[verse]
새벽 세시 도시의 불빛
창문 너머로 흘러가
너의 목소리가 귓가에
아직도 맴돌아

[chorus]
잠이 오지 않아
네 생각에 또 밤을 새워
이 밤이 끝나지 않길
기도하는 마음으로""",
    },
]


def run_test(checkpoint_path, suffix):
    """Generate samples from a given checkpoint."""
    handler = AceStepHandler()
    print(f"\nInitializing DiT service...", flush=True)
    result = handler.initialize_service(
        project_root=r"C:\Users\leo\ace-step-v15",
        config_path=None,
        device="cuda",
        offload_to_cpu=False,
    )
    print(f"DiT init: {result[0][:80]}", flush=True)

    if checkpoint_path:
        print(f"Loading LoKR from {checkpoint_path}...", flush=True)
        msg = handler.load_lora(checkpoint_path)
        print(f"LoKR: {msg}", flush=True)

    for p in PROMPTS:
        print(f"\n=== Generating: {p['name']} ({suffix}) ===", flush=True)
        params = GenerationParams(
            caption=p["caption"],
            lyrics=p["lyrics"],
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
        save_path = os.path.join(SAVE_DIR, f"{p['name']}_{suffix}")
        os.makedirs(save_path, exist_ok=True)

        try:
            res = generate_music(
                dit_handler=handler,
                llm_handler=None,
                params=params,
                config=config,
                save_dir=save_path,
            )
            for audio in res.audios:
                print(f"  -> {audio.get('path', 'N/A')}", flush=True)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)


if __name__ == "__main__":
    # Baseline (no LoKR)
    print("=" * 60, flush=True)
    print("BASELINE (no LoKR)", flush=True)
    print("=" * 60, flush=True)
    run_test(None, "baseline")

    # Test each checkpoint
    for epoch in [200, 300, 400, 500]:
        ckpt_dir = os.path.join(LOKR_DIR, "checkpoints", f"epoch_{epoch}*")
        import glob
        matches = glob.glob(ckpt_dir)
        if matches:
            ckpt = matches[0]
        else:
            ckpt = os.path.join(LOKR_DIR, "final") if epoch == 500 else None

        if ckpt and os.path.isdir(ckpt):
            print("=" * 60, flush=True)
            print(f"EPOCH {epoch}: {ckpt}", flush=True)
            print("=" * 60, flush=True)
            run_test(ckpt, f"epoch{epoch}")

    print("\n\nALL DONE!", flush=True)
