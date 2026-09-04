"""
Liszt v5 — Pop/NewAge Fine-tune
================================
V4 체크포인트(step10000) 위에 POP909 데이터로 추가 학습
Aria train.py 기반 (V4와 동일 파이프라인)

Usage: python train_v5_pop.py
"""
import subprocess, sys, os, time, json, random, shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VENV_PYTHON = r"C:\Users\leo\liszt\venv\Scripts\python.exe"
ARIA_DIR = r"C:\Users\leo\liszt\aria"
TRAIN_PY = os.path.join(ARIA_DIR, "aria", "training", "train.py")
V4_CHECKPOINT = r"C:\Users\leo\liszt\output\liszt_v4\training_run\checkpoints\epoch0_step10000\model.safetensors"
OUTPUT_DIR = r"C:\Users\leo\liszt\output\liszt_v5_pop"
DATA_DIR = os.path.join(OUTPUT_DIR, "midi_data")
LOG_FILE = os.path.join(OUTPUT_DIR, "v5_pop.log")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def download_pop909():
    """POP909 다운로드 — 909곡 팝 피아노"""
    pop_dir = os.path.join(DATA_DIR, "pop909")
    if os.path.exists(pop_dir) and len([f for f in os.listdir(pop_dir) if f.endswith('.mid')]) > 100:
        count = len([f for f in os.listdir(pop_dir) if f.endswith('.mid')])
        log(f"POP909 already exists: {count} files")
        return pop_dir

    # 이전 실행에서 이미 받았을 수 있음
    prev_dir = r"C:\Users\leo\liszt\output\liszt_v5_lora\midi_data\pop909"
    if os.path.exists(prev_dir) and len(os.listdir(prev_dir)) > 100:
        log(f"Copying POP909 from previous run...")
        os.makedirs(pop_dir, exist_ok=True)
        for f in os.listdir(prev_dir):
            if f.endswith('.mid'):
                shutil.copy2(os.path.join(prev_dir, f), os.path.join(pop_dir, f))
        count = len([f for f in os.listdir(pop_dir) if f.endswith('.mid')])
        log(f"POP909 copied: {count} files")
        return pop_dir

    log("Downloading POP909...")
    os.makedirs(pop_dir, exist_ok=True)
    clone_dir = os.path.join(DATA_DIR, "POP909-Dataset")
    cmd = ["git", "clone", "--depth=1",
           "https://github.com/music-x-lab/POP909-Dataset.git", clone_dir]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log(f"Download failed: {result.stderr[:300]}")
        return None

    count = 0
    for root, dirs, files in os.walk(clone_dir):
        for f in files:
            if f.lower().endswith(('.mid', '.midi')):
                src = os.path.join(root, f)
                dst = os.path.join(pop_dir, f"pop_{count:04d}.mid")
                shutil.copy2(src, dst)
                count += 1
    log(f"POP909: {count} MIDI files collected")
    return pop_dir


def build_dataset_jsonl(midi_dir):
    """MIDI → Aria JSONL format"""
    sys.path.insert(0, ARIA_DIR)
    from ariautils.midi import MidiDict

    train_jsonl = os.path.join(OUTPUT_DIR, "dataset_train.jsonl")
    val_jsonl = os.path.join(OUTPUT_DIR, "dataset_val.jsonl")

    if os.path.exists(train_jsonl) and os.path.getsize(train_jsonl) > 1000:
        log(f"Dataset already built")
        return train_jsonl, val_jsonl

    midi_files = sorted([os.path.join(midi_dir, f)
                         for f in os.listdir(midi_dir) if f.endswith('.mid')])
    random.shuffle(midi_files)

    val_n = max(1, int(len(midi_files) * 0.05))
    val_files = midi_files[:val_n]
    train_files = midi_files[val_n:]

    for label, files, out in [("train", train_files, train_jsonl),
                               ("val", val_files, val_jsonl)]:
        ok, err = 0, 0
        with open(out, "w", encoding="utf-8") as f:
            for mf in files:
                try:
                    mid = MidiDict.from_midi(mf)
                    d = mid.get_msg_dict()
                    f.write(json.dumps(d, default=str, ensure_ascii=False) + "\n")
                    ok += 1
                except Exception as e:
                    err += 1
        log(f"{label}: {ok} ok, {err} errors → {out}")

    return train_jsonl, val_jsonl


def tokenize_data(train_jsonl, val_jsonl):
    """JSONL → tokenized data for Aria train.py"""
    train_data = os.path.join(OUTPUT_DIR, "train_data")
    val_data = os.path.join(OUTPUT_DIR, "val_data")

    aria_exe = os.path.join(os.path.dirname(VENV_PYTHON), "aria")

    if not os.path.exists(train_data) or len(os.listdir(train_data)) == 0:
        log("Tokenizing train data...")
        cmd = [aria_exe, "pretrain-dataset",
               "--load_path", train_jsonl,
               "--save_dir", train_data,
               "--tokenizer_name", "abs",
               "--seq_len", "8192",
               "--num_epochs", "3"]
        result = subprocess.run(cmd, cwd=ARIA_DIR, capture_output=True, text=True,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                                timeout=600)
        log(f"Train tokenize: {result.stdout[-500:] if result.stdout else 'none'}")
        if result.returncode != 0:
            log(f"ERROR: {result.stderr[-500:]}")
            return None, None
    else:
        log("Train data already tokenized")

    if not os.path.exists(val_data) or len(os.listdir(val_data)) == 0:
        log("Tokenizing val data...")
        cmd = [aria_exe, "pretrain-dataset",
               "--load_path", val_jsonl,
               "--save_dir", val_data,
               "--tokenizer_name", "abs",
               "--seq_len", "8192",
               "--num_epochs", "1"]
        result = subprocess.run(cmd, cwd=ARIA_DIR, capture_output=True, text=True,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                                timeout=300)
        log(f"Val tokenize: {result.stdout[-500:] if result.stdout else 'none'}")
        if result.returncode != 0:
            log(f"ERROR: {result.stderr[-500:]}")
            return None, None
    else:
        log("Val data already tokenized")

    return train_data, val_data


def patch_lr():
    """train.py LR 패치 — pop은 LR 좀 더 높게 (3e-5)"""
    log("Patching train.py: LR=3e-5, weight_decay=0.05")
    with open(TRAIN_PY, "r") as f:
        content = f.read()

    # LR 패치 (이전 V4 패치가 남아있을 수 있음)
    import re
    content = re.sub(r'LR\s*=\s*[\d.e-]+', 'LR = 3e-5', content, count=1)

    if "weight_decay" not in content:
        content = content.replace(
            "torch.optim.AdamW(model.parameters(), lr=LR)",
            "torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.05)"
        )

    with open(TRAIN_PY, "w") as f:
        f.write(content)
    log("Patched!")


def train(train_data, val_data):
    """Aria train.py로 fine-tune"""
    log("=" * 60)
    log("Starting V5 Pop training...")
    log(f"  Base: V4 step10000")
    log(f"  Data: POP909 (~2900 songs)")
    log(f"  Config: 3 epochs, LR=3e-5, bs=1, grad_acc=8, bf16")
    log("=" * 60)

    patch_lr()

    cmd = [
        VENV_PYTHON, "-m", "accelerate.commands.launch",
        "--mixed_precision=bf16", "--num_processes=1",
        TRAIN_PY,
        "train", "medium",
        "--train_data", train_data,
        "--val_data", val_data,
        "--cp_path", V4_CHECKPOINT,
        "--epochs", "3",
        "--bs", "1",
        "--grad_acc_steps", "8",
        "--workers", "0",
        "--pdir", os.path.join(OUTPUT_DIR, "training_run"),
        "--spc", "200",
    ]
    log(f"Command: {' '.join(cmd)}")

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=env, cwd=ARIA_DIR
    )

    stdout_log = os.path.join(OUTPUT_DIR, "v5_stdout.log")
    with open(stdout_log, "w", encoding="utf-8") as fout:
        for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if line:
                log(line)
                fout.write(line + "\n")
                fout.flush()

    ret = process.wait()
    log(f"Training finished with exit code {ret}")

    # Eval
    if ret == 0:
        run_eval()

    return ret


def run_eval():
    """V5 eval — V4와 동일한 5스타일 + pop 추가"""
    log("Running V5 evaluation...")
    gen_script = os.path.join(OUTPUT_DIR, "_gen_v5.py")
    with open(gen_script, "w", encoding="utf-8") as f:
        f.write(f'''
import sys, os, json, torch
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"{ARIA_DIR}")

from ariautils.tokenizer import AbsTokenizer
from ariautils.midi import MidiDict
from aria.run import _load_inference_model_torch
from aria.inference import sample_min_p

DTYPE = torch.bfloat16
t = AbsTokenizer()

cp_base = r"{os.path.join(OUTPUT_DIR, 'training_run', 'checkpoints')}"
cps = sorted([d for d in os.listdir(cp_base) if os.path.isdir(os.path.join(cp_base, d))],
             key=lambda x: os.path.getmtime(os.path.join(cp_base, x)))
last_cp = os.path.join(cp_base, cps[-1], "model.safetensors")
print(f"Checkpoint: {{cps[-1]}}", flush=True)

model = _load_inference_model_torch(checkpoint_path=last_cp, config_name="medium", strict=False)

configs = [
    {{"name": "baseline", "prefixes": [("prefix", "instrument", "piano")]}},
    {{"name": "pop_ballad", "prefixes": [("prefix", "instrument", "piano"), ("prefix", "genre", "pop")]}},
    {{"name": "chopin_nocturne", "prefixes": [("prefix", "instrument", "piano"), ("prefix", "composer", "chopin")]}},
    {{"name": "jazz", "prefixes": [("prefix", "instrument", "piano"), ("prefix", "genre", "jazz")]}},
]

save_dir = r"{os.path.join(OUTPUT_DIR, 'eval')}"
os.makedirs(save_dir, exist_ok=True)
all_results = {{}}

def apply_rep_penalty(logits, gen_ids, penalty=1.2, window=512):
    if penalty == 1.0 or gen_ids.shape[1] == 0:
        return logits
    recent = gen_ids[:, -window:]
    score = torch.gather(logits, 1, recent)
    score = torch.where(score > 0, score / penalty, score * penalty)
    logits.scatter_(1, recent, score)
    return logits

@torch.autocast("cuda", dtype=DTYPE)
@torch.inference_mode()
def generate(model, prompt, n=3, max_tokens=2048, temp=0.95, min_p=0.035, rep=1.2):
    prompt_len = len(prompt)
    total_len = prompt_len + max_tokens
    model.cuda().eval()
    seq = torch.stack([torch.tensor(t.encode(prompt + [t.pad_tok] * max_tokens)) for _ in range(n)]).cuda()
    model.setup_cache(batch_size=n, max_seq_len=total_len, dtype=DTYPE)
    eos_seen = [False] * n
    for idx in range(prompt_len, total_len):
        with torch.nn.attention.sdpa_kernel(torch.nn.attention.SDPBackend.MATH):
            if idx == prompt_len:
                logits = model.forward(idxs=seq[:, :idx], input_pos=torch.arange(0, idx, device=seq.device))[:, -1]
            else:
                logits = model.forward(idxs=seq[:, idx-1:idx], input_pos=torch.tensor([idx-1], device=seq.device, dtype=torch.int))[:, -1]
        gen_so_far = seq[:, prompt_len:idx]
        if rep > 1.0 and gen_so_far.shape[1] > 0:
            logits = apply_rep_penalty(logits, gen_so_far, rep)
        probs = torch.softmax(logits / temp, dim=-1)
        next_ids = sample_min_p(probs, min_p).flatten()
        for j in range(n):
            if eos_seen[j]: next_ids[j] = t.tok_to_id[t.pad_tok]
            elif next_ids[j] == t.tok_to_id[t.eos_tok]: eos_seen[j] = True
        seq[:, idx] = next_ids
        if all(eos_seen): break
    results = [t.decode(s) for s in seq.tolist()]
    return [r[:r.index(t.eos_tok)+1] if t.eos_tok in r else r for r in results]

def analyze(path):
    mid = MidiDict.from_midi(path)
    notes = mid.note_msgs
    if len(notes) < 5: return {{"error": "too_few"}}
    pitches = [n["data"]["pitch"] for n in notes]
    vels = [n["data"]["velocity"] for n in notes]
    dur = max(n["data"]["end"] for n in notes) / 1000.0
    w = 8
    pats = {{}}
    for i in range(len(pitches)-w+1):
        p = tuple(pitches[i:i+w])
        pats[p] = pats.get(p,0)+1
    rep = sum(c-1 for c in pats.values() if c>1)
    tot = len(pitches)-w+1
    return {{"notes": len(pitches), "unique_pitches": len(set(pitches)), "avg_vel": round(sum(vels)/len(vels),1),
             "nps": round(len(notes)/dur,1) if dur>0 else 0, "rep_pct": round(rep/tot*100,1) if tot>0 else 0}}

for cfg in configs:
    name = cfg["name"]
    print(f"\\n=== {{name}} ===", flush=True)
    prompt = [t.bos_tok] + cfg["prefixes"]
    results = generate(model, prompt)
    analyses = []
    cfg_dir = os.path.join(save_dir, name)
    os.makedirs(cfg_dir, exist_ok=True)
    for i, seq in enumerate(results):
        if ("prefix", "instrument", "piano") not in seq:
            seq.insert(1, ("prefix", "instrument", "piano"))
        mid = t.detokenize(seq)
        path = os.path.join(cfg_dir, f"sample_{{i}}.mid")
        mid.to_midi().save(path)
        a = analyze(path)
        analyses.append(a)
        print(f"  sample_{{i}}: {{a}}", flush=True)
    all_results[name] = analyses

with open(os.path.join(save_dir, "results.json"), "w") as f:
    json.dump(all_results, f, indent=2)
print("\\nV5 Evaluation complete!", flush=True)
''')

    result = subprocess.run(
        [VENV_PYTHON, gen_script],
        capture_output=True, text=True, timeout=1200,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}
    )
    log(result.stdout[-2000:] if result.stdout else "no stdout")
    if result.returncode != 0:
        log(f"Gen error: {result.stderr[-500:]}")


def main():
    log("=" * 60)
    log("Liszt v5 — Pop/NewAge Fine-tune Pipeline")
    log("=" * 60)

    # Step 1
    pop_dir = download_pop909()
    if not pop_dir:
        log("ERROR: No data!")
        return

    # Step 2
    train_jsonl, val_jsonl = build_dataset_jsonl(pop_dir)

    # Step 3
    train_data, val_data = tokenize_data(train_jsonl, val_jsonl)
    if not train_data:
        log("ERROR: Tokenization failed!")
        return

    # Step 4
    train(train_data, val_data)

    log("=" * 60)
    log("V5 Pipeline complete!")
    log("=" * 60)


if __name__ == "__main__":
    main()
