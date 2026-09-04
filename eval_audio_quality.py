"""Audio quality evaluation for ACE-Step generated piano samples."""
import argparse, glob, json, os, sys
import numpy as np
import soundfile as sf

def analyze_file(path, sr_target=48000):
    import librosa
    y, sr = sf.read(path)
    if y.ndim > 1:
        y = np.mean(y, axis=1)
    if sr != sr_target:
        y = librosa.resample(y, orig_sr=sr, target_sr=sr_target)
        sr = sr_target

    dur = len(y) / sr
    metrics = {"file": os.path.basename(path), "duration": round(dur, 2), "sr": sr}

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    metrics["rms_mean"] = round(float(np.mean(rms)), 5)
    metrics["rms_std"] = round(float(np.std(rms)), 5)
    metrics["rms_min"] = round(float(np.min(rms)), 5)

    silence_frames = np.sum(rms < 0.005)
    metrics["silence_ratio"] = round(float(silence_frames / len(rms)), 3)

    cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)[0]
    metrics["centroid_mean"] = round(float(np.mean(cent)), 1)
    metrics["centroid_std"] = round(float(np.std(cent)), 1)

    flatness = librosa.feature.spectral_flatness(y=y, hop_length=512)[0]
    metrics["flatness_mean"] = round(float(np.mean(flatness)), 4)
    metrics["flatness_max"] = round(float(np.max(flatness)), 4)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=512, onset_envelope=onset_env)
    metrics["onset_count"] = int(len(onsets))
    metrics["onset_rate"] = round(len(onsets) / dur, 2) if dur > 0 else 0
    if len(onset_env) > 0:
        metrics["onset_strength_mean"] = round(float(np.mean(onset_env)), 4)
        metrics["onset_strength_max"] = round(float(np.max(onset_env)), 4)

    peak = float(np.max(np.abs(y)))
    metrics["peak"] = round(peak, 4)

    loud_mask = rms > np.percentile(rms, 75)
    quiet_mask = (rms > 0.001) & (rms < np.percentile(rms, 25))
    if np.any(quiet_mask) and np.any(loud_mask):
        snr = 20 * np.log10(np.mean(rms[loud_mask]) / np.mean(rms[quiet_mask]))
        metrics["snr_estimate_db"] = round(float(snr), 1)
    else:
        metrics["snr_estimate_db"] = None

    flags = []
    if metrics["silence_ratio"] > 0.3:
        flags.append("HIGH_SILENCE")
    if metrics["flatness_mean"] > 0.3:
        flags.append("NOISY")
    if metrics["centroid_mean"] < 500:
        flags.append("MUDDY")
    if metrics["centroid_mean"] > 6000:
        flags.append("HARSH")
    if metrics["onset_count"] < 3:
        flags.append("FEW_ONSETS")
    if metrics["rms_mean"] < 0.01:
        flags.append("VERY_QUIET")
    if peak > 0.999:
        flags.append("CLIPPED")

    if flags:
        metrics["grade"] = "RED" if any(f in ["NOISY", "CLIPPED", "VERY_QUIET"] for f in flags) else "YELLOW"
    else:
        metrics["grade"] = "GREEN"
    metrics["flags"] = flags

    return metrics


def analyze_directory(src_dir, output_json=None):
    wavs = sorted(glob.glob(os.path.join(src_dir, "**", "*.wav"), recursive=True))
    if not wavs:
        print(f"No WAV files in {src_dir}")
        return []

    results = []
    summary = {"GREEN": 0, "YELLOW": 0, "RED": 0}
    for w in wavs:
        rel = os.path.relpath(w, src_dir)
        m = analyze_file(w)
        m["path"] = rel
        results.append(m)
        grade = m["grade"]
        icon = {"GREEN": "\u2705", "YELLOW": "\u26a0\ufe0f", "RED": "\u274c"}[grade]
        flags_str = f" [{', '.join(m['flags'])}]" if m["flags"] else ""
        print(f"  {icon} {rel:50s} centroid={m['centroid_mean']:6.0f}  flatness={m['flatness_mean']:.4f}  "
              f"onsets={m['onset_count']:3d}  silence={m['silence_ratio']:.2f}{flags_str}", flush=True)
        summary[grade] += 1

    print(f"\n--- Summary: {summary['GREEN']} GREEN / {summary['YELLOW']} YELLOW / {summary['RED']} RED ---")

    if output_json:
        with open(output_json, "w") as f:
            json.dump({"summary": summary, "samples": results}, f, indent=2, ensure_ascii=False)
        print(f"Report: {output_json}")

    return results


def compare_sets(report_a, report_b, label_a="A", label_b="B"):
    """Compare aggregate metrics between two eval reports."""
    def avg(samples, key):
        vals = [s[key] for s in samples if s.get(key) is not None]
        return np.mean(vals) if vals else 0

    print(f"\n{'Metric':<25} {label_a:>12} {label_b:>12} {'Delta':>12}")
    print("-" * 65)
    for key in ["centroid_mean", "flatness_mean", "rms_mean", "onset_count", "silence_ratio", "snr_estimate_db"]:
        va = avg(report_a, key)
        vb = avg(report_b, key)
        delta = vb - va
        sign = "+" if delta > 0 else ""
        print(f"  {key:<23} {va:12.4f} {vb:12.4f} {sign}{delta:11.4f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Audio quality evaluation")
    p.add_argument("src", help="Directory of WAV files to evaluate")
    p.add_argument("-o", "--output", help="Output JSON report path")
    p.add_argument("--compare", help="Second directory to compare against")
    args = p.parse_args()

    print(f"Evaluating: {args.src}\n")
    results_a = analyze_directory(args.src, args.output)

    if args.compare:
        print(f"\nEvaluating comparison: {args.compare}\n")
        out_b = args.output.replace(".json", "_b.json") if args.output else None
        results_b = analyze_directory(args.compare, out_b)
        compare_sets(results_a, results_b, label_a=os.path.basename(args.src), label_b=os.path.basename(args.compare))
