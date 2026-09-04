"""Compare original ACE-Step output vs AudioSR enhanced output spectrum."""
import numpy as np
import wave
import os
import sys

def analyze(filepath):
    w = wave.open(filepath, 'r')
    sr = w.getframerate()
    nch = w.getnchannels()
    nbytes = w.getsampwidth()
    nframes = w.getnframes()
    mid = nframes // 2
    start = max(0, mid - sr * 2)
    w.setpos(start)
    raw = w.readframes(sr * 5)
    w.close()

    if nbytes == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    elif nbytes == 3:
        samples = []
        for i in range(0, len(raw), 3):
            val = int.from_bytes(raw[i:i+3], 'little', signed=True)
            samples.append(val)
        data = np.array(samples, dtype=np.float64)
    elif nbytes == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float64)
    else:
        raise ValueError(f"Unsupported sample width: {nbytes}")

    if nch >= 2:
        data = data.reshape(-1, nch)[:, 0]

    N = len(data)
    fft = np.abs(np.fft.rfft(data))
    freqs = np.fft.rfftfreq(N, 1.0 / sr)
    power = fft ** 2
    total = power.sum()
    ref_power = power[freqs < 500].mean()

    return sr, nbytes, freqs, power, total, ref_power

pairs = [
    ("Original", "/Users/leo/oven/v6_preview/samples/01_hisaishi.wav",
     "AudioSR", "/Users/leo/oven/v6_preview/audiosr_test/sr_01_hisaishi.wav"),
    ("Original", "/Users/leo/oven/v6_preview/samples/04_yiruma.wav",
     "AudioSR", "/Users/leo/oven/v6_preview/audiosr_test/sr_04_yiruma.wav"),
]

for orig_label, orig_path, sr_label, sr_path in pairs:
    if not os.path.exists(sr_path):
        print(f"Skipping {sr_path} (not yet generated)")
        continue

    print(f"\n{'='*70}")
    print(f"  {os.path.basename(orig_path)}")
    print(f"{'='*70}")

    for label, path in [(orig_label, orig_path), (sr_label, sr_path)]:
        sr, nbytes, freqs, power, total, ref_power = analyze(path)
        print(f"\n  [{label}] sr={sr}, {nbytes*8}bit")
        print(f"  {'Band':>16} | {'Power (dB)':>10} | {'Energy %':>8}")
        print(f"  {'-'*16}-+-{'-'*10}-+-{'-'*8}")

        bands = [(0,500),(500,1000),(1000,2000),(2000,4000),(4000,8000),(8000,12000),(12000,16000),(16000,20000),(20000,24000)]
        for lo, hi in bands:
            mask = (freqs >= lo) & (freqs < hi)
            if mask.sum() == 0:
                continue
            band_pow = power[mask].mean()
            pct = power[mask].sum() / total * 100
            db = 10 * np.log10(band_pow / ref_power) if (band_pow > 0 and ref_power > 0) else -999
            print(f"  {lo:>6}-{hi:>5} Hz | {db:>8.1f}dB | {pct:>6.2f}%")

        cum = np.cumsum(power) / total * 100
        for thresh in [90, 95, 99]:
            idx = np.searchsorted(cum, thresh)
            if idx < len(freqs):
                print(f"  {thresh}% energy below: {freqs[idx]:.0f} Hz")
