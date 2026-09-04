"""
Liszt v5 LoRA Training — Pop/NewAge 장르 확장
=============================================
V4 체크포인트(step10000) 위에 LoRA 어댑터 학습
POP909 + ADL Piano MIDI (pop/newage 필터) 사용

Usage: python train_lora_v5.py
"""
import subprocess, sys, os, time, json, random, shutil, glob

# === Encoding fix (Windows cp949 방지) ===
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VENV_PYTHON = r"C:\Users\leo\liszt\venv\Scripts\python.exe"
ARIA_DIR = r"C:\Users\leo\liszt\aria"
V4_CHECKPOINT = r"C:\Users\leo\liszt\output\liszt_v4\training_run\checkpoints\epoch0_step10000\model.safetensors"
OUTPUT_DIR = r"C:\Users\leo\liszt\output\liszt_v5_lora"
DATA_DIR = os.path.join(OUTPUT_DIR, "midi_data")
LOG_FILE = os.path.join(OUTPUT_DIR, "v5_lora.log")

# LoRA config
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LR = 5e-5
EPOCHS = 3
BATCH_SIZE = 1
GRAD_ACC = 8

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def download_datasets():
    """POP909 + ADL Piano MIDI 다운로드"""
    pop909_dir = os.path.join(DATA_DIR, "pop909")
    adl_dir = os.path.join(DATA_DIR, "adl")

    # POP909
    if not os.path.exists(pop909_dir) or len(os.listdir(pop909_dir)) < 10:
        log("Downloading POP909...")
        os.makedirs(pop909_dir, exist_ok=True)
        cmd = ["git", "clone", "--depth=1",
               "https://github.com/music-x-lab/POP909-Dataset.git",
               os.path.join(DATA_DIR, "POP909-Dataset")]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            # POP909 MIDI 파일 수집
            count = 0
            for root, dirs, files in os.walk(os.path.join(DATA_DIR, "POP909-Dataset")):
                for f in files:
                    if f.lower().endswith('.mid') or f.lower().endswith('.midi'):
                        src = os.path.join(root, f)
                        dst = os.path.join(pop909_dir, f"pop909_{count:04d}.mid")
                        shutil.copy2(src, dst)
                        count += 1
            log(f"POP909: {count} MIDI files collected")
        else:
            log(f"POP909 download failed: {result.stderr[:300]}")
    else:
        log(f"POP909 already exists: {len(os.listdir(pop909_dir))} files")

    # ADL Piano MIDI
    if not os.path.exists(adl_dir) or len(os.listdir(adl_dir)) < 10:
        log("Downloading ADL Piano MIDI...")
        os.makedirs(adl_dir, exist_ok=True)
        cmd = ["git", "clone", "--depth=1",
               "https://github.com/lucasnfe/adl-piano-midi.git",
               os.path.join(DATA_DIR, "adl-piano-midi")]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            # Pop + NewAge 필터링
            count = 0
            for root, dirs, files in os.walk(os.path.join(DATA_DIR, "adl-piano-midi")):
                folder_lower = root.lower()
                # Pop, New Age, R&B, Soul, Soundtrack 등 비클래식 장르
                if any(g in folder_lower for g in ['pop', 'rock', 'new age', 'newage',
                       'r&b', 'soul', 'soundtrack', 'jazz', 'blues', 'country',
                       'electronic', 'folk']):
                    for f in files:
                        if f.lower().endswith('.mid') or f.lower().endswith('.midi'):
                            src = os.path.join(root, f)
                            dst = os.path.join(adl_dir, f"adl_{count:04d}.mid")
                            shutil.copy2(src, dst)
                            count += 1
            log(f"ADL (non-classical filter): {count} MIDI files collected")
        else:
            log(f"ADL download failed: {result.stderr[:300]}")
    else:
        log(f"ADL already exists: {len(os.listdir(adl_dir))} files")

    # 전체 데이터 목록
    all_midi = []
    for d in [pop909_dir, adl_dir]:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.lower().endswith(('.mid', '.midi')):
                    all_midi.append(os.path.join(d, f))
    log(f"Total MIDI files: {len(all_midi)}")
    return all_midi


def build_dataset(midi_files):
    """MIDI → Aria JSONL format"""
    sys.path.insert(0, ARIA_DIR)
    from ariautils.midi import MidiDict

    train_jsonl = os.path.join(OUTPUT_DIR, "dataset_train.jsonl")
    val_jsonl = os.path.join(OUTPUT_DIR, "dataset_val.jsonl")

    if os.path.exists(train_jsonl) and os.path.getsize(train_jsonl) > 1000:
        log(f"Dataset already built: {train_jsonl}")
        return train_jsonl, val_jsonl

    random.shuffle(midi_files)
    val_split = max(1, int(len(midi_files) * 0.05))
    val_files = midi_files[:val_split]
    train_files = midi_files[val_split:]

    for label, files, out_path in [("train", train_files, train_jsonl), ("val", val_files, val_jsonl)]:
        count = 0
        errors = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for mf in files:
                try:
                    mid = MidiDict.from_midi(mf)
                    seq = mid.to_dict()
                    # pop/newage 프리픽스 추가
                    entry = {"prefix": [["prefix", "instrument", "piano"],
                                        ["prefix", "genre", "pop"]],
                             "raw": seq}
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    count += 1
                except Exception as e:
                    errors += 1
        log(f"{label}: {count} ok, {errors} errors → {out_path}")

    return train_jsonl, val_jsonl


def train_lora(train_jsonl, val_jsonl):
    """LoRA fine-tuning using PEFT"""
    log("=" * 60)
    log("Starting LoRA training...")
    log(f"  Base: V4 step10000")
    log(f"  LoRA: r={LORA_R}, alpha={LORA_ALPHA}, dropout={LORA_DROPOUT}")
    log(f"  LR={LR}, epochs={EPOCHS}, bs={BATCH_SIZE}, grad_acc={GRAD_ACC}")
    log("=" * 60)

    # LoRA 학습 스크립트를 별도 파일로 생성
    lora_script = os.path.join(OUTPUT_DIR, "_lora_train.py")
    with open(lora_script, "w", encoding="utf-8") as f:
        f.write(f'''
import sys, os, json, time, torch
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, r"{ARIA_DIR}")

from peft import LoraConfig, get_peft_model, TaskType
from torch.utils.data import Dataset, DataLoader
from ariautils.tokenizer import AbsTokenizer
from ariautils.midi import MidiDict
from aria.run import _load_inference_model_torch

DTYPE = torch.bfloat16
DEVICE = "cuda"

print("Loading tokenizer...", flush=True)
tokenizer = AbsTokenizer()

print("Loading V4 base model...", flush=True)
model = _load_inference_model_torch(
    checkpoint_path=r"{V4_CHECKPOINT}",
    config_name="medium",
    strict=False
)
model = model.to(DEVICE)

# LoRA config
lora_config = LoraConfig(
    r={LORA_R},
    lora_alpha={LORA_ALPHA},
    lora_dropout={LORA_DROPOUT},
    target_modules=["mixed_qkv", "att_proj_linear",
                     "ff_gate_proj", "ff_up_proj", "ff_down_proj"],
    bias="none",
)

print("Applying LoRA...", flush=True)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Dataset
class MidiJsonlDataset(Dataset):
    def __init__(self, jsonl_path, tokenizer, max_len=4096):
        self.data = []
        self.tokenizer = tokenizer
        self.max_len = max_len
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    self.data.append(entry)
                except:
                    pass
        print(f"Loaded {{len(self.data)}} samples from {{jsonl_path}}", flush=True)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        entry = self.data[idx]
        try:
            mid = MidiDict.from_dict(entry["raw"])
            seq = self.tokenizer.tokenize(mid)
            # Add prefix
            prefix = entry.get("prefix", [])
            seq = [self.tokenizer.bos_tok] + prefix + seq + [self.tokenizer.eos_tok]
            # Encode to IDs
            ids = self.tokenizer.encode(seq)
            # Truncate/pad
            if len(ids) > self.max_len:
                ids = ids[:self.max_len]
            else:
                ids = ids + [self.tokenizer.tok_to_id[self.tokenizer.pad_tok]] * (self.max_len - len(ids))
            return torch.tensor(ids, dtype=torch.long)
        except Exception as e:
            # Return zeros on error
            return torch.zeros(self.max_len, dtype=torch.long)

print("Loading dataset...", flush=True)
train_ds = MidiJsonlDataset(r"{os.path.join(OUTPUT_DIR, 'dataset_train.jsonl')}", tokenizer, max_len=4096)
val_ds = MidiJsonlDataset(r"{os.path.join(OUTPUT_DIR, 'dataset_val.jsonl')}", tokenizer, max_len=4096)

train_loader = DataLoader(train_ds, batch_size={BATCH_SIZE}, shuffle=True, num_workers=0, drop_last=True)
val_loader = DataLoader(val_ds, batch_size={BATCH_SIZE}, shuffle=False, num_workers=0)

# Optimizer
optimizer = torch.optim.AdamW(model.parameters(), lr={LR}, weight_decay=0.01)
scaler = torch.amp.GradScaler("cuda")
pad_id = tokenizer.tok_to_id[tokenizer.pad_tok]

log_path = r"{os.path.join(OUTPUT_DIR, 'lora_training.log')}"
save_dir = r"{os.path.join(OUTPUT_DIR, 'lora_checkpoints')}"
os.makedirs(save_dir, exist_ok=True)

def log_train(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{{ts}}] {{msg}}"
    print(line, flush=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\\n")

log_train(f"Training: {{len(train_ds)}} train, {{len(val_ds)}} val")
log_train(f"Steps per epoch: {{len(train_loader)}}, grad_acc: {GRAD_ACC}")

model.train()
global_step = 0
best_val_loss = float("inf")

for epoch in range({EPOCHS}):
    epoch_loss = 0
    optimizer.zero_grad()

    for step, batch in enumerate(train_loader):
        batch = batch.to(DEVICE)
        input_ids = batch[:, :-1]
        labels = batch[:, 1:]

        with torch.amp.autocast("cuda", dtype=DTYPE):
            # Forward
            logits = model(input_ids)
            if hasattr(logits, "logits"):
                logits = logits.logits

            # Loss (ignore padding)
            loss = torch.nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                labels.reshape(-1),
                ignore_index=pad_id
            )
            loss = loss / {GRAD_ACC}

        scaler.scale(loss).backward()
        epoch_loss += loss.item() * {GRAD_ACC}

        if (step + 1) % {GRAD_ACC} == 0:
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad()
            global_step += 1

            if global_step % 10 == 0:
                avg = epoch_loss / (step + 1)
                log_train(f"Epoch {{epoch}} step {{global_step}} loss {{avg:.4f}}")

            if global_step % 100 == 0:
                # Save checkpoint
                cp_path = os.path.join(save_dir, f"lora_step{{global_step}}")
                model.save_pretrained(cp_path)
                log_train(f"Saved checkpoint: lora_step{{global_step}}")

    # Epoch validation
    model.eval()
    val_loss = 0
    val_steps = 0
    with torch.no_grad():
        for batch in val_loader:
            batch = batch.to(DEVICE)
            input_ids = batch[:, :-1]
            labels = batch[:, 1:]
            with torch.amp.autocast("cuda", dtype=DTYPE):
                logits = model(input_ids)
                if hasattr(logits, "logits"):
                    logits = logits.logits
                loss = torch.nn.functional.cross_entropy(
                    logits.reshape(-1, logits.size(-1)),
                    labels.reshape(-1),
                    ignore_index=pad_id
                )
            val_loss += loss.item()
            val_steps += 1

    avg_val = val_loss / max(val_steps, 1)
    log_train(f"Epoch {{epoch}} val_loss {{avg_val:.4f}}")

    if avg_val < best_val_loss:
        best_val_loss = avg_val
        best_path = os.path.join(save_dir, "lora_best")
        model.save_pretrained(best_path)
        log_train(f"New best! val_loss={{avg_val:.4f}}")

    model.train()

# Final save
final_path = os.path.join(save_dir, "lora_final")
model.save_pretrained(final_path)
log_train("Training complete!")
log_train(f"Best val_loss: {{best_val_loss:.4f}}")
''')

    log(f"LoRA script written: {lora_script}")

    # 실행
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    process = subprocess.Popen(
        [VENV_PYTHON, lora_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=ARIA_DIR
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
    return ret


def main():
    log("=" * 60)
    log("Liszt v5 LoRA — Pop/NewAge Genre Expansion")
    log("=" * 60)

    # Step 1: Download data
    midi_files = download_datasets()
    if not midi_files:
        log("ERROR: No MIDI files found!")
        return

    # Step 2: Build dataset
    train_jsonl, val_jsonl = build_dataset(midi_files)

    # Step 3: Train LoRA
    train_lora(train_jsonl, val_jsonl)


if __name__ == "__main__":
    main()
