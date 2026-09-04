import audiosr
import torch
import os

input_dir = "/Users/leo/oven/v6_preview/samples"
output_dir = "/Users/leo/oven/v6_preview/audiosr_test"

# Load model
print("Loading AudioSR model...")
audiosr_model = audiosr.build_model(model_name="basic", device="mps")

# Test on a couple of samples
test_files = ["01_hisaishi.wav", "04_yiruma.wav"]

for fname in test_files:
    input_path = os.path.join(input_dir, fname)
    if not os.path.exists(input_path):
        print(f"Skip: {input_path} not found")
        continue
    
    print(f"\nProcessing {fname}...")
    waveform = audiosr.super_resolution(
        audiosr_model,
        input_path,
        seed=42,
        guidance_scale=3.5,
        ddim_steps=50,
    )
    
    output_path = os.path.join(output_dir, f"sr_{fname}")
    import soundfile as sf
    sf.write(output_path, waveform[0].T, samplerate=48000)
    print(f"Saved: {output_path}")

print("\nDone!")
