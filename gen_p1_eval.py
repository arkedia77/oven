"""Quincy P1 eval - generate samples with V9 remapped base + LoRA + modules_to_save."""
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
BASE_CP = r"D:\liszt\output\liszt_v9_prefix\base_remapped.safetensors"
LORA_DIR = r"D:\liszt\output\liszt_v9_prefix\lora_checkpoints\lora_best"
EVAL_DIR = r"C:\Users\leo\liszt\eval\quincy_p1_crossover"

def apply_repetition_penalty_fast(logits, generated_ids, penalty, window=512):
    if penalty == 1.0 or generated_ids.shape[1] == 0:
        return logits
    recent = generated_ids[:, -window:]
    score = torch.gather(logits, 1, recent)
    score = torch.where(score > 0, score / penalty, score * penalty)
    logits.scatter_(1, recent, score)
    return logits

def load_model_with_lora(base_cp, lora_dir):
    print("Loading V9 remapped base model...", flush=True)
    tokenizer = AbsTokenizer()
    model_config = ModelConfig(**load_model_config("medium"))
    model_config.vocab_size = tokenizer.vocab_size

    # Load weights into training model first for merging
    train_model = TrainingTransformerLM(model_config)
    state_dict = load_file(base_cp)
    train_model.load_state_dict(state_dict, strict=False)
    print(f"Base loaded, vocab={tokenizer.vocab_size}", flush=True)

    # Load and merge LoRA + modules_to_save
    print("Loading LoRA adapter (with modules_to_save)...", flush=True)
    adapter_path = os.path.join(lora_dir, "adapter_model.safetensors")
    adapter_config_path = os.path.join(lora_dir, "adapter_config.json")
    with open(adapter_config_path, "r") as f:
        lora_config = json.load(f)
    lora_r = lora_config.get("r", 16)
    lora_alpha = lora_config.get("lora_alpha", 32)
    scaling = lora_alpha / lora_r

    lora_weights = load_file(adapter_path)

    # Separate LoRA pairs and modules_to_save weights
    lora_pairs = {}
    modules_to_save_map = {
        "base_model.model.lm_head.weight": "lm_head.weight",
        "base_model.model.model.tok_embeddings.weight": "model.tok_embeddings.weight",
    }

    for k, v in lora_weights.items():
        if k in modules_to_save_map:
            continue  # handle separately
        elif "lora_A" in k:
            base_key = k.replace(".lora_A.weight", "").replace("base_model.model.", "")
            if base_key not in lora_pairs: lora_pairs[base_key] = {}
            lora_pairs[base_key]["A"] = v
        elif "lora_B" in k:
            base_key = k.replace(".lora_B.weight", "").replace("base_model.model.", "")
            if base_key not in lora_pairs: lora_pairs[base_key] = {}
            lora_pairs[base_key]["B"] = v

    # Merge LoRA into training model
    base_sd = dict(train_model.named_parameters())
    merged = 0
    for base_key, pair in lora_pairs.items():
        if "A" not in pair or "B" not in pair: continue
        weight_key = base_key + ".weight"
        if weight_key in base_sd:
            param = base_sd[weight_key]
            delta = (pair["B"].to(param.dtype) @ pair["A"].to(param.dtype)) * scaling
            param.data += delta.to(param.device)
            merged += 1
    print(f"  Merged {merged} LoRA layers (scaling={scaling})", flush=True)

    # Apply modules_to_save (tok_embeddings, lm_head)
    saved = 0
    for adapter_key, model_key in modules_to_save_map.items():
        if adapter_key in lora_weights and model_key in base_sd:
            v = lora_weights[adapter_key]
            base_sd[model_key].data.copy_(v.to(base_sd[model_key].dtype))
            saved += 1
            print(f"  Replaced: {model_key} from modules_to_save", flush=True)
    print(f"  Applied {saved} modules_to_save weights", flush=True)

    # Convert to inference model
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
        if all(eos_tok_seen): break
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
    return {
        'notes': len(pitches), 'unique_pitches': len(set(pitches)),
        'pitch_range': max(pitches) - min(pitches),
        'rep_8gram': round(rep_ratio * 100, 1),
        'vel_range': max(velocities) - min(velocities),
        'vel_std': round(statistics.stdev(velocities), 1) if len(velocities) > 1 else 0,
        'duration_s': round(duration_s, 1),
    }

if __name__ == "__main__":
    t = AbsTokenizer()
    model = load_model_with_lora(BASE_CP, LORA_DIR)

    # Quincy P1 Crossover — 장르/폼 혼합 조합
    styles = [
        # Pop × Classical 크로스오버
        {"name": "xo_pop_classical_groove",   "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "genre", "pop"), ("prefix", "genre", "classical"), ("prefix", "form", "groove")]},
        {"name": "xo_pop_classical_ballad",   "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "genre", "pop"), ("prefix", "genre", "classical"), ("prefix", "form", "ballad")]},
        {"name": "xo_pop_classical_anthem",   "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "genre", "pop"), ("prefix", "genre", "classical"), ("prefix", "form", "anthem")]},
        # 폼 크로스오버
        {"name": "xo_ambient_stride",         "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "form", "ambient"), ("prefix", "form", "stride")]},
        {"name": "xo_groove_rubato",          "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "form", "groove"), ("prefix", "form", "rubato")]},
        {"name": "xo_ballad_riff",            "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "form", "ballad"), ("prefix", "form", "riff")]},
        {"name": "xo_anthem_arpeggio",        "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "form", "anthem"), ("prefix", "form", "arpeggio")]},
        # Pop × 다중 폼
        {"name": "xo_pop_rubato_ballad",      "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "genre", "pop"), ("prefix", "form", "rubato"), ("prefix", "form", "ballad")]},
        {"name": "xo_pop_stride_groove",      "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "genre", "pop"), ("prefix", "form", "stride"), ("prefix", "form", "groove")]},
        {"name": "xo_pop_ambient_arpeggio",   "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "genre", "pop"), ("prefix", "form", "ambient"), ("prefix", "form", "arpeggio")]},
        # Classical × 다중 폼
        {"name": "xo_classical_groove_riff",  "prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "genre", "classical"), ("prefix", "form", "groove"), ("prefix", "form", "riff")]},
        {"name": "xo_classical_anthem_stride","prompt": [t.bos_tok, ("prefix", "instrument", "piano"), ("prefix", "genre", "classical"), ("prefix", "form", "anthem"), ("prefix", "form", "stride")]},
    ]

    os.makedirs(EVAL_DIR, exist_ok=True)
    all_results = {}

    for style in styles:
        sname = style["name"]
        sdir = os.path.join(EVAL_DIR, sname)
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
            print(f"  sample_{idx}: notes={a['notes']} uniq={a['unique_pitches']} rep={a['rep_8gram']}% vel={a['vel_range']} dur={a['duration_s']}s", flush=True)

        all_results[sname] = {"prompt": str(style["prompt"]), "samples": analyses, "gen_time": round(elapsed, 1)}

    rpath = os.path.join(EVAL_DIR, "results.json")
    with open(rpath, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*70}", flush=True)
    print(f"{'Style':<20} {'Notes':>6} {'Uniq':>5} {'Rep%':>6} {'Vel':>5} {'VStd':>5} {'Dur':>6}", flush=True)
    print("-"*70, flush=True)
    for name, data in all_results.items():
        ss = data["samples"]
        n = len(ss)
        if n == 0: continue
        print(f"{name:<20} {sum(s['notes'] for s in ss)/n:>6.0f} {sum(s['unique_pitches'] for s in ss)/n:>5.1f} "
              f"{sum(s['rep_8gram'] for s in ss)/n:>5.1f}% {sum(s['vel_range'] for s in ss)/n:>5.0f} "
              f"{sum(s['vel_std'] for s in ss)/n:>5.1f} {sum(s['duration_s'] for s in ss)/n:>5.1f}s", flush=True)
    print(f"\nResults: {rpath}", flush=True)
