"""Preprocess piano-v2 segments (240 files) to ACE-Step tensors for v3."""
import sys
sys.path.insert(0, r"C:\Users\leo\ace-step-v15")
from acestep.training_v2.preprocess import preprocess_audio_files

preprocess_audio_files(
    audio_dir=r"D:\data\piano-v2\segments",
    output_dir=r"D:\data\piano-v2\tensors",
    checkpoint_dir=r"C:\Users\leo\ace-step-v15\checkpoints",
    variant="turbo",
    max_duration=30.0,
)
print("[DONE]", flush=True)
