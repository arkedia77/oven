"""Liszt Comprehensive Test Suite — 4 categories of experiments.

1. Prompt Variations: genre, composer, form prefixes
2. Parameter Tuning: temp, rep_penalty, min_p combos
3. MIDI Prompt: continuation from a starting phrase
4. Generation Length: short / medium / long
"""
import sys, os, json, time, struct
# Fix Windows encoding for étude etc.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\leo\liszt")
sys.path.insert(0, r"C:\Users\leo\liszt\aria")

import torch
from tqdm import tqdm
from ariautils.tokenizer import AbsTokenizer
from ariautils.midi import MidiDict
from aria.run import _load_inference_model_torch
from aria.inference import sample_min_p

DTYPE = torch.bfloat16
SAVE_BASE = r"C:\Users\leo\liszt\eval\test_suite"
NUM_SAMPLES = 2  # per experiment


def apply_repetition_penalty_fast(logits, generated_ids, penalty, window=512):
    if penalty == 1.0 or generated_ids.shape[1] == 0:
        return logits
    recent = generated_ids[:, -window:]
    score = torch.gather(logits, 1, recent)
    score = torch.where(score > 0, score / penalty, score * penalty)
    logits.scatter_(1, recent, score)
    return logits


@torch.autocast("cuda", dtype=DTYPE)
@torch.inference_mode()
def generate(model, tokenizer, prompt, num_variations, max_new_tokens,
             temp=0.95, min_p=0.035, rep_penalty=1.2, rep_window=512):
    prompt_len = len(prompt)
    total_len = prompt_len + max_new_tokens
    model = model.cuda()
    model.eval()
    eos_tok_seen = [False] * num_variations
    seq = torch.stack([
        torch.tensor(tokenizer.encode(
            prompt + [tokenizer.pad_tok] * max_new_tokens
        )) for _ in range(num_variations)
    ]).cuda()
    model.setup_cache(batch_size=num_variations, max_seq_len=total_len, dtype=DTYPE)

    for idx in tqdm(range(prompt_len, total_len), total=max_new_tokens, leave=False):
        with torch.nn.attention.sdpa_kernel(torch.nn.attention.SDPBackend.MATH):
            if idx == prompt_len:
                logits = model.forward(
                    idxs=seq[:, :idx],
                    input_pos=torch.arange(0, idx, device=seq.device),
                )[:, -1]
            else:
                logits = model.forward(
                    idxs=seq[:, idx-1:idx],
                    input_pos=torch.tensor([idx-1], device=seq.device, dtype=torch.int),
                )[:, -1]

        generated_so_far = seq[:, prompt_len:idx]
        if rep_penalty > 1.0 and generated_so_far.shape[1] > 0:
            logits = apply_repetition_penalty_fast(logits, generated_so_far, rep_penalty, rep_window)

        if temp > 0.0:
            probs = torch.softmax(logits / temp, dim=-1)
            next_ids = sample_min_p(probs, min_p).flatten()
        else:
            next_ids = torch.argmax(logits, dim=-1).flatten()

        for _idx in range(num_variations):
            if eos_tok_seen[_idx]:
                next_ids[_idx] = tokenizer.tok_to_id[tokenizer.pad_tok]
            elif next_ids[_idx] == tokenizer.tok_to_id[tokenizer.eos_tok]:
                eos_tok_seen[_idx] = True
        seq[:, idx] = next_ids
        if all(eos_tok_seen):
            break

    results = [tokenizer.decode(s) for s in seq.tolist()]
    results = [r[:r.index(tokenizer.eos_tok)+1] if tokenizer.eos_tok in r else r for r in results]
    return results


def analyze_midi(midi_path):
    """Analyze a MIDI file for quality metrics."""
    try:
        mid = MidiDict.from_midi(midi_path)
    except Exception as e:
        return {"error": str(e)}
    notes = mid.note_msgs
    if len(notes) < 5:
        return {"notes": len(notes), "rep_8gram": 0, "unique_pitches": 0,
                "vel_range": 0, "duration_sec": 0, "pitch_range": 0}
    pitches = [n["data"]["pitch"] for n in notes]
    velocities = [n["data"]["velocity"] for n in notes]
    # Duration from first to last note
    start_ms = min(n["data"]["start"] for n in notes)
    end_ms = max(n["data"]["end"] for n in notes)
    duration_sec = (end_ms - start_ms) / 1000.0

    # 8-gram repetition
    window = 8
    patterns = {}
    for i in range(len(pitches) - window + 1):
        p = tuple(pitches[i:i+window])
        patterns[p] = patterns.get(p, 0) + 1
    repeated = sum(c - 1 for c in patterns.values() if c > 1)
    total = len(pitches) - window + 1
    rep_ratio = repeated / total if total > 0 else 0

    return {
        "notes": len(pitches),
        "unique_pitches": len(set(pitches)),
        "pitch_range": max(pitches) - min(pitches),
        "vel_range": max(velocities) - min(velocities),
        "vel_mean": round(sum(velocities) / len(velocities), 1),
        "rep_8gram": round(rep_ratio * 100, 1),
        "duration_sec": round(duration_sec, 1),
    }


def save_results(results, tokenizer, exp_dir):
    """Save MIDI files and return analysis."""
    os.makedirs(exp_dir, exist_ok=True)
    analyses = []
    for idx, seq in enumerate(results):
        if ("prefix", "instrument", "piano") not in seq:
            seq.insert(1, ("prefix", "instrument", "piano"))
        mid = tokenizer.detokenize(seq)
        midi = mid.to_midi()
        fpath = os.path.join(exp_dir, f"sample_{idx}.mid")
        midi.save(fpath)
        analysis = analyze_midi(fpath)
        analysis["file"] = f"sample_{idx}.mid"
        analysis["file_size"] = os.path.getsize(fpath)
        analyses.append(analysis)
    return analyses


def create_seed_prompt(tokenizer):
    """Create a short C major arpeggio as seed for continuation test."""
    # C4-E4-G4-C5 arpeggio with increasing velocity, each 500ms apart
    seed_notes = [
        ("piano", 60, 80, 0, 500),      # C4
        ("piano", 64, 90, 500, 1000),    # E4
        ("piano", 67, 100, 1000, 1500),  # G4
        ("piano", 72, 110, 1500, 2500),  # C5
    ]
    note_msgs = []
    for inst, pitch, vel, start, end in seed_notes:
        note_msgs.append({
            "type": "note",
            "data": {
                "pitch": pitch,
                "velocity": vel,
                "start": start,
                "end": end,
            },
            "tick": start,
            "channel": 0,
        })
    midi_dict = MidiDict(
        meta_msgs=[],
        tempo_msgs=[{"type": "tempo", "data": 500000, "tick": 0}],
        pedal_msgs=[],
        instrument_msgs=[{"type": "instrument", "data": 0, "tick": 0, "channel": 0}],
        note_msgs=note_msgs,
        ticks_per_beat=480,
        metadata={},
    )
    tokens = tokenizer.tokenize(midi_dict)
    return tokens


def run_all_tests(model, tokenizer):
    all_results = {}
    total_start = time.time()

    # =========================================================
    # TEST 1: Prompt Variations
    # =========================================================
    print("\n" + "=" * 60, flush=True)
    print("TEST 1: PROMPT VARIATIONS", flush=True)
    print("=" * 60, flush=True)

    prompt_experiments = [
        {"name": "baseline_piano",
         "prompt": [tokenizer.bos_tok, ("prefix", "instrument", "piano")]},
        {"name": "chopin_nocturne",
         "prompt": [tokenizer.bos_tok, ("prefix", "instrument", "piano"),
                    ("prefix", "composer", "chopin"), ("prefix", "form", "nocturne")]},
        {"name": "bach_fugue",
         "prompt": [tokenizer.bos_tok, ("prefix", "instrument", "piano"),
                    ("prefix", "composer", "bach"), ("prefix", "form", "fugue")]},
        {"name": "debussy_prelude",
         "prompt": [tokenizer.bos_tok, ("prefix", "instrument", "piano"),
                    ("prefix", "composer", "debussy"), ("prefix", "form", "prelude")]},
        {"name": "jazz_piano",
         "prompt": [tokenizer.bos_tok, ("prefix", "instrument", "piano"),
                    ("prefix", "genre", "jazz")]},
        {"name": "classical_waltz",
         "prompt": [tokenizer.bos_tok, ("prefix", "instrument", "piano"),
                    ("prefix", "genre", "classical"), ("prefix", "form", "waltz")]},
        {"name": "liszt_etude",
         "prompt": [tokenizer.bos_tok, ("prefix", "instrument", "piano"),
                    ("prefix", "composer", "liszt"), ("prefix", "form", "étude")]},
        {"name": "ravel_impromptu",
         "prompt": [tokenizer.bos_tok, ("prefix", "instrument", "piano"),
                    ("prefix", "composer", "ravel"), ("prefix", "form", "impromptu")]},
    ]

    for exp in prompt_experiments:
        exp_dir = os.path.join(SAVE_BASE, "1_prompt", exp["name"])
        # Skip if already completed
        if os.path.isdir(exp_dir) and len([f for f in os.listdir(exp_dir) if f.endswith('.mid')]) >= NUM_SAMPLES:
            print(f"\n  >> {exp['name']} — SKIPPED (already done)", flush=True)
            analyses = [analyze_midi(os.path.join(exp_dir, f"sample_{i}.mid")) for i in range(NUM_SAMPLES)]
            for i, a in enumerate(analyses):
                a["file"] = f"sample_{i}.mid"
                a["file_size"] = os.path.getsize(os.path.join(exp_dir, f"sample_{i}.mid"))
                print(f"     {a['file']}: {a['notes']} notes, {a['unique_pitches']} uniq, "
                      f"rep={a['rep_8gram']}%, dur={a['duration_sec']}s", flush=True)
            all_results[f"1_prompt/{exp['name']}"] = {
                "category": "prompt_variation",
                "prompt_prefixes": [str(p) for p in exp["prompt"] if isinstance(p, tuple)],
                "gen_params": {"temp": 0.95, "min_p": 0.035, "rep_penalty": 1.2, "max_tokens": 2048},
                "samples": analyses,
                "gen_time": 0,
            }
            continue
        prefixes_str = str([p for p in exp["prompt"] if isinstance(p, tuple)])
        print(f"\n  >> {exp['name']} (prefixes: {prefixes_str})", flush=True)
        start = time.time()
        results = generate(model, tokenizer, exp["prompt"], NUM_SAMPLES, 2048)
        elapsed = time.time() - start
        analyses = save_results(results, tokenizer, exp_dir)
        for a in analyses:
            print(f"     {a['file']}: {a['notes']} notes, {a['unique_pitches']} uniq, "
                  f"rep={a['rep_8gram']}%, dur={a['duration_sec']}s", flush=True)
        all_results[f"1_prompt/{exp['name']}"] = {
            "category": "prompt_variation",
            "prompt_prefixes": [str(p) for p in exp["prompt"] if isinstance(p, tuple)],
            "gen_params": {"temp": 0.95, "min_p": 0.035, "rep_penalty": 1.2, "max_tokens": 2048},
            "samples": analyses,
            "gen_time": round(elapsed, 1),
        }

    # =========================================================
    # TEST 2: Parameter Tuning
    # =========================================================
    print("\n" + "=" * 60, flush=True)
    print("TEST 2: PARAMETER TUNING", flush=True)
    print("=" * 60, flush=True)

    base_prompt = [tokenizer.bos_tok, ("prefix", "instrument", "piano")]
    param_experiments = [
        {"name": "low_temp_0.7",   "temp": 0.7,  "min_p": 0.035, "rep": 1.2},
        {"name": "high_temp_1.1",  "temp": 1.1,  "min_p": 0.035, "rep": 1.2},
        {"name": "no_rep_penalty", "temp": 0.95, "min_p": 0.035, "rep": 1.0},
        {"name": "heavy_rep_1.5",  "temp": 0.95, "min_p": 0.035, "rep": 1.5},
        {"name": "high_min_p_0.1", "temp": 0.95, "min_p": 0.1,   "rep": 1.2},
        {"name": "low_min_p_0.01", "temp": 0.95, "min_p": 0.01,  "rep": 1.2},
        {"name": "conservative",   "temp": 0.8,  "min_p": 0.05,  "rep": 1.3},
        {"name": "creative",       "temp": 1.05, "min_p": 0.02,  "rep": 1.1},
    ]

    for exp in param_experiments:
        exp_dir = os.path.join(SAVE_BASE, "2_params", exp["name"])
        print(f"\n  >> {exp['name']} (temp={exp['temp']}, min_p={exp['min_p']}, rep={exp['rep']})", flush=True)
        start = time.time()
        results = generate(model, tokenizer, base_prompt, NUM_SAMPLES, 2048,
                           temp=exp["temp"], min_p=exp["min_p"], rep_penalty=exp["rep"])
        elapsed = time.time() - start
        analyses = save_results(results, tokenizer, exp_dir)
        for a in analyses:
            print(f"     {a['file']}: {a['notes']} notes, {a['unique_pitches']} uniq, "
                  f"rep={a['rep_8gram']}%, dur={a['duration_sec']}s", flush=True)
        all_results[f"2_params/{exp['name']}"] = {
            "category": "parameter_tuning",
            "gen_params": {"temp": exp["temp"], "min_p": exp["min_p"], "rep_penalty": exp["rep"], "max_tokens": 2048},
            "samples": analyses,
            "gen_time": round(elapsed, 1),
        }

    # =========================================================
    # TEST 3: MIDI Prompt Continuation
    # =========================================================
    print("\n" + "=" * 60, flush=True)
    print("TEST 3: MIDI PROMPT CONTINUATION", flush=True)
    print("=" * 60, flush=True)

    seed_tokens = create_seed_prompt(tokenizer)
    # Build prompt: bos + piano prefix + seed notes
    midi_prompt = [tokenizer.bos_tok, ("prefix", "instrument", "piano")]
    # Add only note/onset/dur/velocity tokens from seed (skip bos/eos/prefix)
    for tok in seed_tokens:
        if isinstance(tok, tuple) and tok[0] in ("onset", "dur", "piano", "prefix"):
            continue
        if tok in (tokenizer.bos_tok, tokenizer.eos_tok, tokenizer.dim_tok):
            continue
        midi_prompt.append(tok)

    # Actually, let's use the tokenized output properly
    # The tokenizer output includes the musical content we want
    midi_prompt_full = [tokenizer.bos_tok, ("prefix", "instrument", "piano")]
    for tok in seed_tokens:
        if tok == tokenizer.bos_tok or tok == tokenizer.eos_tok:
            continue
        if isinstance(tok, tuple) and tok[0] == "prefix":
            continue
        midi_prompt_full.append(tok)

    continuation_experiments = [
        {"name": "continue_default",   "temp": 0.95, "rep": 1.2},
        {"name": "continue_creative",  "temp": 1.05, "rep": 1.1},
        {"name": "continue_faithful",  "temp": 0.75, "rep": 1.3},
    ]

    print(f"  Seed: C major arpeggio (C4-E4-G4-C5), {len(midi_prompt_full)} tokens", flush=True)

    for exp in continuation_experiments:
        exp_dir = os.path.join(SAVE_BASE, "3_continuation", exp["name"])
        print(f"\n  >> {exp['name']} (temp={exp['temp']}, rep={exp['rep']})", flush=True)
        start = time.time()
        results = generate(model, tokenizer, midi_prompt_full, NUM_SAMPLES, 2048,
                           temp=exp["temp"], rep_penalty=exp["rep"])
        elapsed = time.time() - start
        analyses = save_results(results, tokenizer, exp_dir)
        for a in analyses:
            print(f"     {a['file']}: {a['notes']} notes, {a['unique_pitches']} uniq, "
                  f"rep={a['rep_8gram']}%, dur={a['duration_sec']}s", flush=True)
        all_results[f"3_continuation/{exp['name']}"] = {
            "category": "midi_continuation",
            "seed": "C_major_arpeggio_C4_E4_G4_C5",
            "seed_tokens": len(midi_prompt_full),
            "gen_params": {"temp": exp["temp"], "min_p": 0.035, "rep_penalty": exp["rep"], "max_tokens": 2048},
            "samples": analyses,
            "gen_time": round(elapsed, 1),
        }

    # =========================================================
    # TEST 4: Generation Length
    # =========================================================
    print("\n" + "=" * 60, flush=True)
    print("TEST 4: GENERATION LENGTH", flush=True)
    print("=" * 60, flush=True)

    length_experiments = [
        {"name": "short_512",   "max_tokens": 512},
        {"name": "medium_2048", "max_tokens": 2048},
        {"name": "long_4096",   "max_tokens": 4096},
        {"name": "xlong_8192",  "max_tokens": 8192},
    ]

    for exp in length_experiments:
        exp_dir = os.path.join(SAVE_BASE, "4_length", exp["name"])
        print(f"\n  >> {exp['name']} (max_tokens={exp['max_tokens']})", flush=True)
        start = time.time()
        results = generate(model, tokenizer, base_prompt, NUM_SAMPLES, exp["max_tokens"])
        elapsed = time.time() - start
        analyses = save_results(results, tokenizer, exp_dir)
        for a in analyses:
            print(f"     {a['file']}: {a['notes']} notes, {a['unique_pitches']} uniq, "
                  f"rep={a['rep_8gram']}%, dur={a['duration_sec']}s", flush=True)
        all_results[f"4_length/{exp['name']}"] = {
            "category": "generation_length",
            "gen_params": {"temp": 0.95, "min_p": 0.035, "rep_penalty": 1.2, "max_tokens": exp["max_tokens"]},
            "samples": analyses,
            "gen_time": round(elapsed, 1),
        }

    # =========================================================
    # SAVE FULL REPORT
    # =========================================================
    total_elapsed = time.time() - total_start
    report = {
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": "liszt_v3",
        "total_time_sec": round(total_elapsed, 1),
        "total_experiments": len(all_results),
        "samples_per_experiment": NUM_SAMPLES,
        "experiments": all_results,
    }
    report_path = os.path.join(SAVE_BASE, "report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n\n{'=' * 60}", flush=True)
    print(f"COMPLETE — {len(all_results)} experiments, {total_elapsed:.0f}s total", flush=True)
    print(f"Report: {report_path}", flush=True)
    print(f"{'=' * 60}", flush=True)

    # Print summary table
    print(f"\n{'Category':<22} {'Experiment':<22} {'Notes':<8} {'Uniq':<6} {'Rep%':<7} {'Dur(s)':<8} {'Time':<6}", flush=True)
    print("-" * 79, flush=True)
    for key, data in all_results.items():
        cat = data["category"]
        name = key.split("/")[1]
        samples = data["samples"]
        if any("error" in s for s in samples):
            print(f"{cat:<22} {name:<22} ERROR", flush=True)
            continue
        avg_notes = sum(s["notes"] for s in samples) / len(samples)
        avg_uniq = sum(s["unique_pitches"] for s in samples) / len(samples)
        avg_rep = sum(s["rep_8gram"] for s in samples) / len(samples)
        avg_dur = sum(s["duration_sec"] for s in samples) / len(samples)
        print(f"{cat:<22} {name:<22} {avg_notes:<8.0f} {avg_uniq:<6.0f} {avg_rep:<7.1f} {avg_dur:<8.1f} {data['gen_time']:<6.0f}s", flush=True)


if __name__ == "__main__":
    print("Loading model...", flush=True)
    t = AbsTokenizer()
    cp_base = r"C:\Users\leo\liszt\output\liszt_v3\training_run\checkpoints"
    cps = sorted(
        [d for d in os.listdir(cp_base) if os.path.isdir(os.path.join(cp_base, d))],
        key=lambda x: os.path.getmtime(os.path.join(cp_base, x)),
    )
    last_cp = os.path.join(cp_base, cps[-1], "model.safetensors")
    print(f"Checkpoint: {cps[-1]}", flush=True)
    model = _load_inference_model_torch(checkpoint_path=last_cp, config_name="medium", strict=False)
    print("Model loaded. Starting test suite...\n", flush=True)
    run_all_tests(model, t)
