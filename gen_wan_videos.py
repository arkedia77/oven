"""
레오뮤직 스토리 뮤직비디오 생성 (Wan2.2 T2V-A14B)
3개 에피소드: 눈인사, 물오리, 열두 살의 노을
"""
import subprocess
import sys
import os
import time

PYTHON = r"C:\Users\leo\liszt\venv\Scripts\python.exe"
GENERATE = r"C:\Users\leo\wan22_repo\generate.py"
CKPT = r"D:\models\Wan2.2-T2V-A14B"
OUTPUT_DIR = r"D:\liszt\output\leomusic_mv"

# 에피소드별 영상 프롬프트 (cinematic, detailed)
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
        "size": "1280*720",
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
        "size": "1280*720",
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
            "The boy stares at the sunset with a quiet, contemplative expression — "
            "discovering beauty for the first time. Streetlights begin to flicker on below. "
            "Far away, the sound of friends calling fades. "
            "Intimate coming-of-age atmosphere. Shot on 35mm film, "
            "anamorphic lens flare, warm to cool color transition."
        ),
        "size": "1280*720",
    },
]


def main():
    ts = time.strftime("%Y%m%d_%H%M%S")
    print(f"[{ts}] Starting leomusic MV generation — 3 episodes")
    print(f"Model: {CKPT}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    # Create output dir
    os.makedirs(OUTPUT_DIR, exist_ok=True) if not os.name == "nt" else None

    for i, ep in enumerate(EPISODES, 1):
        t0 = time.time()
        save_file = f"{OUTPUT_DIR}\\leomusic_{ep['name']}_{ts}.mp4"
        print(f"[{i}/3] Generating: {ep['title']} ({ep['name']})")
        print(f"  Prompt: {ep['prompt'][:80]}...")
        print(f"  Output: {save_file}")

        cmd = [
            PYTHON, GENERATE,
            "--task", "t2v-A14B",
            "--ckpt_dir", CKPT,
            "--size", ep["size"],
            "--prompt", ep["prompt"],
            "--save_file", save_file,
            "--offload_model", "true",
            "--sample_steps", "30",
            "--frame_num", "81",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        elapsed = time.time() - t0

        if result.returncode == 0:
            print(f"  DONE in {elapsed:.0f}s ({elapsed/60:.1f}min)")
        else:
            print(f"  FAILED (rc={result.returncode}) in {elapsed:.0f}s")
            print(f"  stderr: {result.stderr[-500:]}")

        if result.stdout:
            # Print last few lines of stdout for progress info
            lines = result.stdout.strip().split("\n")
            for line in lines[-5:]:
                print(f"  > {line}")
        print()

    print(f"All done! Check {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
