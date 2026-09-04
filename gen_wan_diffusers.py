"""
레오뮤직 스토리 뮤직비디오 생성 (Wan2.1 T2V-1.3B via diffusers)
3 episodes: 눈인사, 물오리, 열두 살의 노을
1.3B model — safe for 5090 (68GB RAM, 32GB VRAM)
"""
import torch
import gc
import time
import os

OUTPUT_DIR = r"D:\liszt\output\leomusic_mv"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)


def main():
    from diffusers import WanPipeline
    from diffusers.utils import export_to_video

    log("Loading WanPipeline T2V-1.3B (Wan2.1) in bf16...")
    t0 = time.time()

    pipe = WanPipeline.from_pretrained(
        "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        torch_dtype=torch.bfloat16,
    )
    pipe.enable_model_cpu_offload()
    pipe.enable_vae_tiling()

    log(f"Pipeline loaded in {time.time()-t0:.0f}s")

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

        # Clear memory between generations
        del output
        gc.collect()
        torch.cuda.empty_cache()

    log("All 3 videos complete!")


if __name__ == "__main__":
    main()
