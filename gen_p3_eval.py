"""Quincy P3 eval — lyrical piano focus, same eval prompts as P2 for comparison."""
import sys, os, json, time, statistics
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Users\leo\liszt")
sys.path.insert(0, r"C:\Users\leo\liszt\aria")

import torch
from safetensors.torch import load_file
from tqdm import tqdm
from ariautils.tokenizer import AbsTokenizer
from ariautils.midi import MidiDict
from aria.config import load_model_config
from aria.model import ModelConfig
from aria.model import TransformerLM as TrainingTransformerLM
from aria.inference.model_cuda import TransformerLM as InferenceTransformerLM
from aria.inference import sample_min_p

DTYPE = torch.bfloat16
BASE_CP = r"D:\liszt\output\quincy_p2\base_remapped.safetensors"
LORA_DIR = r"D:\liszt\output\quincy_p3\lora_checkpoints\lora_best"
EVAL_DIR = r"C:\Users\leo\liszt\eval\quincy_p3_eval"


def apply_repetition_penalty_fast(logits, generated_ids, penalty, window=512):
    if penalty == 1.0 or generated_ids.shape[1] == 0:
        return logits
    recent = generated_ids[:, -window:]
    score = torch.gather(logits, 1, recent)
    score = torch.where(score > 0, score / penalty, score * penalty)
    logits.scatter_(1, recent, score)
    return logits


def load_model_with_lora(base_cp, lora_dir):
    print("Loading P2 base model...", flush=True)
    tokenizer = AbsTokenizer()
    model_config = ModelConfig(**load_model_config("medium"))
    model_config.vocab_size = tokenizer.vocab_size

    train_model = TrainingTransformerLM(model_config)
    state_dict = load_file(base_cp)
    train_model.load_state_dict(state_dict, strict=False)
    print(f"Base loaded, vocab={tokenizer.vocab_size}", flush=True)

    print("Loading P3 LoRA adapter...", flush=True)
    adapter_path = os.path.join(lora_dir, "adapter_model.safetensors")
    adapter_config_path = os.path.join(lora_dir, "adapter_config.json")
    with open(adapter_config_path, "r") as f:
        lora_config = json.load(f)
    lora_r = lora_config.get("r", 16)
    lora_alpha = lora_config.get("lora_alpha", 32)
    scaling = lora_alpha / lora_r

    lora_weights = load_file(adapter_path)

    lora_pairs = {}
    modules_to_save_map = {
        "base_model.model.lm_head.weight": "lm_head.weight",
        "base_model.model.model.tok_embeddings.weight": "model.tok_embeddings.weight",
    }

    for k, v in lora_weights.items():
        if k in modules_to_save_map:
            continue
        elif "lora_A" in k:
            base_key = k.replace(".lora_A.weight", "").replace("base_model.model.", "")
            if base_key not in lora_pairs: lora_pairs[base_key] = {}
            lora_pairs[base_key]["A"] = v
        elif "lora_B" in k:
            base_key = k.replace(".lora_B.weight", "").replace("base_model.model.", "")
            if base_key not in lora_pairs: lora_pairs[base_key] = {}
            lora_pairs[base_key]["B"] = v

    base_sd = dict(train_model.named_parameters())
    merged = 0
    for base_key, pair in lora_pairs.items():
        if "A" not in pair or "B" not in pair:
            continue
        weight_key = base_key + ".weight"
        if weight_key in base_sd:
            param = base_sd[weight_key]
            delta = (pair["B"].to(param.dtype) @ pair["A"].to(param.dtype)) * scaling
            param.data += delta.to(param.device)
            merged += 1
    print(f"  Merged {merged} LoRA layers (scaling={scaling})", flush=True)

    saved = 0
    for adapter_key, model_key in modules_to_save_map.items():
        if adapter_key in lora_weights and model_key in base_sd:
            v = lora_weights[adapter_key]
            base_sd[model_key].data.copy_(v.to(base_sd[model_key].dtype))
            saved += 1
            print(f"  Replaced: {model_key}", flush=True)
    print(f"  Applied {saved} modules_to_save weights", flush=True)

    print("Converting to inference model...", flush=True)
    merged_sd = train_model.state_dict()
    inf_model = InferenceTransformerLM(model_config).cuda()
    inf_model.load_state_dict(merged_sd, strict=False)
    del train_model
    torch.cuda.empty_cache()
    print(f"Inference model ready, GPU={torch.cuda.memory_allocated()/1024**2:.0f}MB", flush=True)

    return inf_model


@torch.autocast("cuda", dtype=DTYPE)
@torch.inference_mode()
def generate(model, tokenizer, prompt, num_variations, max_new_tokens,
             temp=0.95, min_p=0.035, rep_penalty=1.2, rep_window=512):
    prompt_len = len(prompt)
    total_len = prompt_len + max_new_tokens
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
    mid = MidiDict.from_midi(midi_path)
    notes = mid.note_msgs
    pitches = [n['data']['pitch'] for n in notes]
    velocities = [n['data']['velocity'] for n in notes]
    if len(pitches) < 10:
        return {'notes': len(pitches), 'unique_pitches': 0, 'rep_8gram': 0,
                'vel_range': 0, 'vel_std': 0, 'pitch_range': 0, 'duration_s': 0}
    window = 8
    patterns = {}
    for i in range(len(pitches) - window + 1):
        p = tuple(pitches[i:i+window])
        patterns[p] = patterns.get(p, 0) + 1
    repeated = sum(c - 1 for c in patterns.values() if c > 1)
    total = len(pitches) - window + 1
    rep_ratio = repeated / total if total > 0 else 0

    starts = [n['data']['start'] for n in notes]
    ends = [n['data']['end'] for n in notes]
    duration_s = (max(ends) - min(starts)) / 1e6 if ends else 0

    if len(starts) > 4:
        diffs = [starts[i+1] - starts[i] for i in range(min(len(starts)-1, 100))
                 if starts[i+1] > starts[i]]
        if diffs:
            avg_ioi = sum(diffs) / len(diffs) / 1e6
            est_bpm = 60 / avg_ioi if avg_ioi > 0 else 0
            while est_bpm > 200: est_bpm /= 2
            while est_bpm < 40: est_bpm *= 2
        else:
            est_bpm = 0
    else:
        est_bpm = 0

    return {
        'notes': len(pitches), 'unique_pitches': len(set(pitches)),
        'pitch_range': max(pitches) - min(pitches),
        'rep_8gram': round(rep_ratio * 100, 1),
        'vel_range': max(velocities) - min(velocities),
        'vel_std': round(statistics.stdev(velocities), 1) if len(velocities) > 1 else 0,
        'duration_s': round(duration_s, 1),
        'est_bpm': round(est_bpm, 0),
    }


if __name__ == "__main__":
    t = AbsTokenizer()
    model = load_model_with_lora(BASE_CP, LORA_DIR)

    # Same eval prompts as P2 for direct comparison
    tempos = ['slow', 'medium', 'fast', 'very_fast']
    forms = ['ballad', 'groove', 'anthem', 'arpeggio']

    styles = []

    # 1) Tempo x Form (pop) — 16
    for tempo in tempos:
        for form in forms:
            styles.append({
                "name": f"{tempo}_{form}_pop",
                "prompt": [
                    t.bos_tok,
                    ("prefix", "instrument", "piano"),
                    ("prefix", "genre", "pop"),
                    ("prefix", "tempo", tempo),
                    ("prefix", "form", form),
                ],
            })

    # 2) Classical ballad variants — 4
    for tempo in tempos:
        styles.append({
            "name": f"{tempo}_ballad_classical",
            "prompt": [
                t.bos_tok,
                ("prefix", "instrument", "piano"),
                ("prefix", "genre", "classical"),
                ("prefix", "tempo", tempo),
                ("prefix", "form", "ballad"),
            ],
        })

    # 3) Tempo-only — 4
    for tempo in tempos:
        styles.append({
            "name": f"{tempo}_only",
            "prompt": [
                t.bos_tok,
                ("prefix", "instrument", "piano"),
                ("prefix", "tempo", tempo),
            ],
        })

    print(f"\nTotal styles: {len(styles)}", flush=True)

    os.makedirs(EVAL_DIR, exist_ok=True)
    os.makedirs(os.path.join(EVAL_DIR, "midi"), exist_ok=True)
    all_results = {}

    for style in styles:
        sname = style["name"]
        sdir = os.path.join(EVAL_DIR, "midi", sname)
        os.makedirs(sdir, exist_ok=True)
        print(f"\n=== {sname} ===", flush=True)
        t0 = time.time()

        results = generate(
            model=model, tokenizer=t, prompt=style["prompt"],
            num_variations=3, max_new_tokens=4096,
            temp=0.95, min_p=0.035, rep_penalty=1.2, rep_window=512,
        )
        elapsed = time.time() - t0
        analyses = []

        for idx, seq in enumerate(results):
            if ("prefix", "instrument", "piano") not in seq:
                seq.insert(1, ("prefix", "instrument", "piano"))
            mid = t.detokenize(seq)
            midi = mid.to_midi()
            fpath = os.path.join(sdir, f"sample_{idx}.mid")
            midi.save(fpath)
            a = analyze_midi(fpath)
            analyses.append(a)
            print(f"  sample_{idx}: notes={a['notes']} uniq={a['unique_pitches']} "
                  f"rep={a['rep_8gram']}% bpm~{a['est_bpm']}", flush=True)

        all_results[sname] = {
            "prompt": str(style["prompt"]),
            "samples": analyses,
            "gen_time": round(elapsed, 1),
        }

    rpath = os.path.join(EVAL_DIR, "results.json")
    with open(rpath, "w") as f:
        json.dump(all_results, f, indent=2)

    # P2 vs P3 comparison
    p2_results_path = r"C:\Users\leo\liszt\eval\quincy_p2_eval\results.json"
    if os.path.exists(p2_results_path):
        with open(p2_results_path) as f:
            p2_results = json.load(f)

        print(f"\n{'='*90}", flush=True)
        print(f"{'Style':<30} {'P2 Notes':>8} {'P3 Notes':>8} {'P2 Rep%':>7} "
              f"{'P3 Rep%':>7} {'P2 BPM':>7} {'P3 BPM':>7}", flush=True)
        print("-" * 90, flush=True)

        for name in all_results:
            if name in p2_results:
                p2 = p2_results[name]["samples"]
                p3 = all_results[name]["samples"]
                avg = lambda ss, k: sum(s[k] for s in ss) / len(ss) if ss else 0
                print(f"{name:<30} "
                      f"{avg(p2,'notes'):>8.0f} {avg(p3,'notes'):>8.0f} "
                      f"{avg(p2,'rep_8gram'):>6.1f}% {avg(p3,'rep_8gram'):>6.1f}% "
                      f"{avg(p2,'est_bpm'):>7.0f} {avg(p3,'est_bpm'):>7.0f}", flush=True)

    print(f"\nResults: {rpath}", flush=True)
    print("=== P3 EVAL COMPLETE ===", flush=True)
