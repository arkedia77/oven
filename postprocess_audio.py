"""Batch post-processing for ACE-Step generated piano samples."""
import argparse, glob, json, os, sys
import numpy as np
import soundfile as sf
import pedalboard as pb
import pyloudnorm

IR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "impulse_responses", "voxengo")
IR_MUSIKVEREIN = os.path.join(IR_DIR, "Musikvereinsaal.wav")
IR_SCALA = os.path.join(IR_DIR, "Scala Milan Opera Hall.wav")
IR_SALON = os.path.join(IR_DIR, "French 18th Century Salon.wav")

def _make_conv_preset(ir_path, mix, comp_threshold=-20, comp_ratio=2.5):
    plugins = [pb.HighpassFilter(cutoff_frequency_hz=30),
               pb.Compressor(threshold_db=comp_threshold, ratio=comp_ratio, attack_ms=10, release_ms=100)]
    if os.path.exists(ir_path):
        plugins.append(pb.Convolution(ir_path, mix=mix))
    else:
        plugins.append(pb.Reverb(room_size=0.5, damping=0.7, wet_level=mix, dry_level=1-mix, width=1.0))
    plugins += [pb.Gain(gain_db=-1.0), pb.Limiter(threshold_db=-1.0, release_ms=100)]
    return pb.Pedalboard(plugins)

def _tape_saturation(audio, drive=0.12):
    driven = audio * (1.0 + drive * 3.0)
    saturated = np.tanh(driven)
    return audio * (1.0 - drive) + saturated * drive


def _make_studio_preset(ir_path, wet=0.22):
    """Full chain: saturation → convolution reverb → EQ → compression → limiter."""
    plugins = [
        pb.HighpassFilter(cutoff_frequency_hz=35),
        pb.PeakFilter(cutoff_frequency_hz=300, gain_db=-2.0, q=1.0),
        pb.LowShelfFilter(cutoff_frequency_hz=150, gain_db=1.5, q=0.7),
        pb.PeakFilter(cutoff_frequency_hz=3000, gain_db=1.5, q=0.8),
        pb.HighShelfFilter(cutoff_frequency_hz=10000, gain_db=2.0, q=0.7),
    ]
    if os.path.exists(ir_path):
        plugins.append(pb.Convolution(ir_path, mix=wet))
    else:
        plugins.append(pb.Reverb(room_size=0.6, damping=0.6, wet_level=wet, dry_level=1-wet, width=1.0))
    plugins += [
        pb.Compressor(threshold_db=-20, ratio=2.0, attack_ms=30, release_ms=200),
        pb.Gain(gain_db=-1.0),
        pb.Limiter(threshold_db=-1.0, release_ms=100),
    ]
    return pb.Pedalboard(plugins)


PRESETS = {
    "concert": _make_conv_preset(IR_MUSIKVEREIN, mix=0.20),
    "intimate": _make_conv_preset(IR_SALON, mix=0.12, comp_threshold=-18, comp_ratio=2.0),
    "cinematic": _make_conv_preset(IR_SCALA, mix=0.30, comp_threshold=-22, comp_ratio=2.0),
    "bright": pb.Pedalboard([
        pb.HighpassFilter(cutoff_frequency_hz=60),
        pb.Compressor(threshold_db=-18, ratio=2.5, attack_ms=8, release_ms=80),
        pb.HighShelfFilter(cutoff_frequency_hz=4000, gain_db=2.0),
        pb.Reverb(room_size=0.25, damping=0.8, wet_level=0.12, dry_level=0.88, width=0.7),
        pb.Gain(gain_db=-1.0),
        pb.Limiter(threshold_db=-1.0, release_ms=100),
    ]),
    "studio": _make_studio_preset(IR_SALON, wet=0.22),
    "studio_large": _make_studio_preset(IR_MUSIKVEREIN, wet=0.18),
}

PRESETS_WITH_SATURATION = {"studio", "studio_large"}

PROMPT_PRESET_MAP = {
    "01_lyrical": "concert",
    "02_jazz": "intimate",
    "03_classical": "concert",
    "04_darkcine": "cinematic",
    "05_ragtime": "bright",
    "06_lofi": "intimate",
}

TARGET_LUFS = -14.0


def process_file(src, dst, board, sr=48000, preset_name=""):
    audio, file_sr = sf.read(src)
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]
    if file_sr != sr:
        sr = file_sr

    if preset_name in PRESETS_WITH_SATURATION:
        audio = _tape_saturation(audio, drive=0.12)

    processed = board(audio.T, sr).T

    meter = pyloudnorm.Meter(sr)
    loudness = meter.integrated_loudness(processed)
    if not np.isinf(loudness):
        processed = pyloudnorm.normalize.loudness(processed, loudness, TARGET_LUFS)

    peak = np.max(np.abs(processed))
    if peak > 0.99:
        processed = processed * (0.99 / peak)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    sf.write(dst, processed, sr, subtype="PCM_16")
    return sr, len(audio) / sr


def process_directory(src_dir, dst_dir, preset=None, auto_map=True):
    wavs = sorted(glob.glob(os.path.join(src_dir, "**", "*.wav"), recursive=True))
    if not wavs:
        print(f"No WAV files found in {src_dir}")
        return

    results = []
    for w in wavs:
        rel = os.path.relpath(w, src_dir)
        dst = os.path.join(dst_dir, rel)

        if auto_map and preset is None:
            parts = rel.replace(os.sep, "/").split("/")
            prompt_tag = next((p for p in parts if p in PROMPT_PRESET_MAP), None)
            chosen = PROMPT_PRESET_MAP.get(prompt_tag, "concert")
        else:
            chosen = preset or "concert"

        board = PRESETS[chosen]
        sr, dur = process_file(w, dst, board, preset_name=chosen)
        results.append({"src": rel, "preset": chosen, "sr": sr, "duration": dur})
        print(f"  [{chosen:>10}] {rel}", flush=True)

    manifest = os.path.join(dst_dir, "manifest.json")
    with open(manifest, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nProcessed {len(results)} files → {dst_dir}")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Batch audio post-processing")
    p.add_argument("src", help="Source directory of WAV files")
    p.add_argument("dst", help="Destination directory for processed files")
    p.add_argument("--preset", choices=list(PRESETS.keys()),
                   help="Force a single preset (default: auto-map by prompt tag)")
    p.add_argument("--list-presets", action="store_true", help="Show available presets")
    args = p.parse_args()

    if args.list_presets:
        for name, board in PRESETS.items():
            print(f"  {name}: {[type(p).__name__ for p in board]}")
        sys.exit(0)

    print(f"Source: {args.src}")
    print(f"Dest:   {args.dst}")
    print(f"Preset: {args.preset or 'auto-map'}\n")
    process_directory(args.src, args.dst, preset=args.preset)
