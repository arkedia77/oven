"""Wan2.1-T2V-1.3B 모델 다운로드 + 영상 생성 통합 스크립트
SSH 끊김에도 독립 실행되도록 설계
"""
import time, os, sys, gc, torch

LOG = r"C:\Users\leo\wan22_repo\wan_full_log.txt"
OUTPUT_DIR = r"D:\liszt\output\leomusic_mv"
MODEL_DIR = r"D:\models\Wan2.1-T2V-1.3B-Diffusers"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    print(line, end="", flush=True)
    with open(LOG, "a") as f:
        f.write(line)

EPISODES = [
    {
        "name": "eye_greeting",
        "title": "눈인사",
        "prompt": (
            "A warm cinematic scene in a modern coworking space in Seoul. "
            "Morning sunlight streams through floor-to-ceiling windows. "
            "A young woman sits at a shared desk, opens her laptop, places a water bottle to the left. "
            "She glances sideways. Across the desk partition, a young man looks up from his screen. "
            "Their eyes meet for a brief moment. They exchange a subtle nod and a faint smile. "
            "Soft bokeh background with other workers typing. Coffee machine steam rises in the distance. "
            "Gentle, intimate mood. Shot on 35mm film, shallow depth of field, warm color grading."
        ),
    },
    {
        "name": "duck_on_water",
        "title": "물오리",
        "prompt": (
            "A contemplative cinematic scene at golden hour. An elderly Korean man sits alone "
            "on a concrete riverbank embankment, a folded newspaper beneath him. "
            "He gazes at the calm river where three ducks float serenely on the water surface. "
            "The sunset paints the river in deep orange and amber reflections. "
            "A gentle breeze ripples the water. The ducks appear peaceful above, "
            "but their feet paddle steadily beneath the surface. "
            "Distant bicycle bell sound. Warm nostalgic atmosphere. "
            "Wide shot transitioning to close-up of the old man's weathered, peaceful face. "
            "Shot on 35mm film, cinematic color grading, golden hour lighting."
        ),
    },
    {
        "name": "sunset_at_twelve",
        "title": "열두 살의 노을",
        "prompt": (
            "A poetic cinematic scene of a twelve-year-old Korean boy sitting alone "
            "on concrete stairs of an apartment rooftop. He wears a sweaty soccer jersey, "
            "his shoelaces untied. Sweat glistens on his forehead as it cools. "
            "Between the tall apartment buildings, a brilliant red and orange sunset descends. "
            "The sky transitions from warm gold to deep purple. "
            "The boy stares at the sunset with a quiet, contemplative expression, "
            "discovering beauty for the first time. Streetlights begin to flicker on below. "
            "Far away, the sound of friends calling fades. "
            "Intimate coming-of-age atmosphere. Shot on 35mm film, "
            "anamorphic lens flare, warm to cool color transition."
        ),
    },
]

# Step 1: Load pipeline from local model (downloaded by dl_and_gen.bat)
log("=== Loading pipeline from local model ===")
from diffusers import WanPipeline
from diffusers.utils import export_to_video

pipe = WanPipeline.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()
pipe.enable_vae_tiling()
log("Pipeline loaded")

for i, ep in enumerate(EPISODES, 1):
    log(f"[{i}/3] Generating: {ep['title']} ({ep['name']})")
    t1 = time.time()

    output = pipe(
        prompt=ep["prompt"],
        num_frames=81,
        guidance_scale=5.0,
        num_inference_steps=50,
        height=480,
        width=832,
    )

    save_path = os.path.join(OUTPUT_DIR, f"leomusic_{ep['name']}.mp4")
    export_to_video(output.frames[0], save_path, fps=16)
    elapsed = time.time() - t1
    log(f"  DONE: {save_path} ({elapsed:.0f}s / {elapsed/60:.1f}min)")

    del output
    gc.collect()
    torch.cuda.empty_cache()

log("=== All 3 videos complete! ===")
