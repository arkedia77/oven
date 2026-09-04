"""Generate samples for all LoKR-trained artists — baseline + best epoch."""
import sys, os, glob, re, json
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
import torch

print(f"CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}", flush=True)

BASE_DIR = r"C:\Users\leo\ace-step-v15\lokr_artists"
SAVE_DIR = r"C:\Users\leo\ace-step-v15\lokr_samples"

ARTISTS = {
    "악뮤": {
        "caption": "Korean acoustic folk pop, warm male-female duo harmonized vocals, guitar, emotional, 90 BPM",
        "lyrics": "[verse]\n봄바람이 불어오면\n너의 이름을 불러본다\n작은 골목 끝에서\n우리 처음 만났던 그날\n\n[chorus]\n다시 한번 웃어줘\n그 눈부신 미소로\n세상이 환해지는\n너라는 계절이 와",
    },
    "DAY6__데이식스": {
        "caption": "Korean pop rock band, energetic male vocals, electric guitar, drums, emotional anthem, 130 BPM",
        "lyrics": "[verse]\n매일 같은 하루가\n달라지기 시작한 건\n네가 내 이름을 부른\n그 순간부터였어\n\n[chorus]\n소리쳐 불러봐\n이 밤이 끝나기 전에\n우리의 노래로\n세상을 흔들어 놓자",
    },
    "IVE__아이브": {
        "caption": "K-pop girl group, powerful confident female vocals, bright synth, dance pop, 120 BPM",
        "lyrics": "[verse]\nMirror mirror on the wall\n누가 제일 빛나는지\n대답은 이미 정해져\nIt's me 의심할 것 없이\n\n[chorus]\nI'm the one and only\n멈추지 않을 거야\nShine bright like a diamond\n세상을 비출 거야",
    },
    "황치열": {
        "caption": "Korean ballad, powerful emotional male vocals, piano, string orchestra, dramatic, 68 BPM",
        "lyrics": "[verse]\n텅 빈 거리를 걸으며\n너의 흔적을 찾아\n흐릿한 가로등 아래\n추억만이 남아있어\n\n[chorus]\n보고 싶다 너를\n이 밤이 지나면\n다시 만날 수 있을까\n눈물이 멈추질 않아",
    },
    "투어스": {
        "caption": "K-pop boy group, bright smooth male vocals, catchy pop melody, youthful energy, 115 BPM",
        "lyrics": "[verse]\n교실 창가에 앉아\n네 이름을 몰래 써봐\n심장이 두근거려\n이게 바로 첫사랑인가\n\n[chorus]\nLet me follow you\n어디든 따라갈게\n너만 있으면 돼\n세상이 반짝여",
    },
    "방탄소년단": {
        "caption": "K-pop boy group, dynamic male vocals and rap, powerful hybrid pop, modern production, 100 BPM",
        "lyrics": "[verse]\n어둠 속을 걸어왔어\n수많은 밤을 지새우며\n포기란 없었어 우리\n함께라면 두렵지 않아\n\n[chorus]\n달려가 끝까지\n멈추지 마 이 순간\n우리가 만든 길 위에\n영원히 빛날 거야",
    },
    "아일릿": {
        "caption": "K-pop girl group, fresh youthful female vocals, catchy synth pop, bright dance, 118 BPM",
        "lyrics": "[verse]\n오늘따라 유난히\n거울 앞에 오래 서\n설레는 마음 감추며\n교문 앞에서 기다려\n\n[chorus]\nMagnetic 끌려가\n너한테로 자꾸만\n눈이 마주치면\n심장이 boom boom boom",
    },
}


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


def generate_sample(handler, caption, lyrics, save_path):
    os.makedirs(save_path, exist_ok=True)
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
            save_dir=save_path,
        )
        for audio in res.audios:
            print(f"    -> {audio.get('path', 'saved')}", flush=True)
        return True
    except Exception as e:
        print(f"    FAILED: {e}", flush=True)
        return False


def main():
    results = {}

    for artist_name, prompts in ARTISTS.items():
        artist_dir = os.path.join(BASE_DIR, artist_name)
        if not os.path.isdir(artist_dir):
            print(f"SKIP {artist_name}: not found", flush=True)
            continue

        best_path, best_loss = get_best_checkpoint(artist_dir)
        if not best_path:
            print(f"SKIP {artist_name}: no checkpoints", flush=True)
            continue

        print(f"\n{'='*60}", flush=True)
        print(f"{artist_name} (best: {os.path.basename(best_path)}, loss={best_loss:.4f})", flush=True)
        print(f"{'='*60}", flush=True)

        out_dir = os.path.join(SAVE_DIR, artist_name)

        # Init fresh handler for each artist
        handler = AceStepHandler()
        handler.initialize_service(
            project_root=r"C:\Users\leo\ace-step-v15",
            config_path=None,
            device="cuda",
            offload_to_cpu=False,
        )

        # Baseline
        print(f"  [baseline]", flush=True)
        generate_sample(handler, prompts["caption"], prompts["lyrics"],
                        os.path.join(out_dir, "baseline"))

        # Best LoKR
        print(f"  [lokr best] Loading {os.path.basename(best_path)}...", flush=True)
        handler.load_lora(best_path)
        generate_sample(handler, prompts["caption"], prompts["lyrics"],
                        os.path.join(out_dir, "lokr_best"))

        results[artist_name] = {
            "best_checkpoint": os.path.basename(best_path),
            "best_loss": best_loss,
        }
        print(f"  Done!", flush=True)

    with open(os.path.join(SAVE_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nALL DONE! Samples in {SAVE_DIR}", flush=True)


if __name__ == "__main__":
    main()
